import os
import socket
import tempfile
import unittest
from pathlib import Path

from distributed_training import (distributed_info, make_distributed_sampler,
    save_checkpoint, load_checkpoint, initialize_process_group,
    wrap_ddp, cleanup_process_group)
from profiler import profile_callable

try:
    import torch
except ImportError:
    torch = None


@unittest.skipIf(torch is None, "PyTorch not installed")
class CheckpointAndProfilerTests(unittest.TestCase):
    def test_checkpoint_restores_model_optimizer_epoch(self):
        model = torch.nn.Linear(2, 1)
        opt = torch.optim.SGD(model.parameters(), lr=0.2)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "resume.pt"
            original = [p.detach().clone() for p in model.parameters()]
            save_checkpoint(path, model=model, optimizer=opt, epoch=7,
                            metadata={"run": "unit"})
            with torch.no_grad():
                for p in model.parameters():
                    p.add_(10)
            restored = load_checkpoint(path, model=model, optimizer=opt)
            self.assertEqual(restored["epoch"], 7)
            self.assertEqual(restored["metadata"]["run"], "unit")
            self.assertTrue(all(torch.equal(a, b) for a, b in zip(original, model.parameters())))

    def test_distributed_sampler_shards_without_overlap(self):
        old = {key: os.environ.get(key) for key in ("WORLD_SIZE", "RANK")}
        try:
            os.environ["WORLD_SIZE"] = "2"
            os.environ["RANK"] = "0"
            rank0 = list(make_distributed_sampler(list(range(10)), shuffle=False))
            os.environ["RANK"] = "1"
            rank1 = list(make_distributed_sampler(list(range(10)), shuffle=False))
            self.assertEqual(len(rank0), 5)
            self.assertEqual(len(rank1), 5)
            self.assertFalse(set(rank0) & set(rank1))
            self.assertEqual(set(rank0) | set(rank1), set(range(10)))
        finally:
            for key, value in old.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    def test_profiler_exports_trace(self):
        with tempfile.TemporaryDirectory() as tmp:
            x = torch.ones(8, 8)
            def step():
                (x @ x).sum().item()
            result = profile_callable(step, trace_dir=tmp, wait=0, warmup=0,
                                      active=1, repeat=1)
            self.assertEqual(result["status"], "completed")
            self.assertTrue(result["trace_files"])
            self.assertTrue(Path(result["trace_files"][0]).is_file())


def _ddp_worker(rank, world_size, init_file, output_dir):
    os.environ.update(RANK=str(rank), WORLD_SIZE=str(world_size),
                      LOCAL_RANK=str(rank), MASTER_ADDR="127.0.0.1",
                      MASTER_PORT=os.environ["MASTER_PORT"])
    torch, device, info = initialize_process_group(timeout_seconds=60)
    try:
        model = torch.nn.Linear(1, 1, bias=False)
        with torch.no_grad():
            model.weight.fill_(1.0)
        ddp = wrap_ddp(model, device)
        x = torch.tensor([[float(rank + 1)]])
        loss = (ddp(x) - torch.tensor([[0.0]])).pow(2).mean()
        loss.backward()
        grad = ddp.module.weight.grad.detach().clone()
        torch.distributed.all_reduce(grad)
        grad /= world_size
        if not torch.allclose(ddp.module.weight.grad, grad):
            raise AssertionError("DDP gradients differ across ranks")
        if rank == 0:
            torch.save({"weight": ddp.module.weight.detach().cpu()},
                       Path(output_dir) / "rank0.pt")
    finally:
        cleanup_process_group()


@unittest.skipIf(torch is None, "PyTorch not installed")
class DDPGlooIntegrationTests(unittest.TestCase):
    def test_two_process_gloo_gradient_sync(self):
        if not torch.distributed.is_available():
            self.skipTest("torch.distributed unavailable")
        with tempfile.TemporaryDirectory() as tmp:
            # File rendezvous avoids fixed-port collisions in parallel CI.
            init_file = str(Path(tmp) / "rendezvous")
            os.environ["MASTER_ADDR"] = "127.0.0.1"
            with socket.socket() as sock:
                sock.bind(("127.0.0.1", 0))
                os.environ["MASTER_PORT"] = str(sock.getsockname()[1])
            torch.multiprocessing.spawn(_ddp_worker,
                args=(2, init_file, tmp), nprocs=2, join=True)
            self.assertTrue((Path(tmp) / "rank0.pt").is_file())


if __name__ == "__main__":
    unittest.main()
