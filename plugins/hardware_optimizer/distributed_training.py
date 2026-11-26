"""Explicit torchrun-based DDP helpers for VISUAL.

One process per GPU. NCCL is selected only for CUDA; Gloo is the CPU test/fallback.
Launch the caller's entrypoint with torchrun; this module never spawns workers on import.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path


def distributed_info():
    world_size = int(os.environ.get("WORLD_SIZE", "1"))
    rank = int(os.environ.get("RANK", "0"))
    local_rank = int(os.environ.get("LOCAL_RANK", "0"))
    if world_size < 1 or not 0 <= rank < world_size or local_rank < 0:
        raise ValueError("Invalid torchrun rank environment")
    return {"world_size": world_size, "rank": rank, "local_rank": local_rank,
            "distributed": world_size > 1}


def initialize_process_group(timeout_seconds=180):
    """Initialize once from torchrun env; return (torch, device, info)."""
    import datetime
    import torch
    info = distributed_info()
    if info["world_size"] == 1:
        device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
        if device.type == "cuda":
            torch.cuda.set_device(device)
        return torch, device, info
    if not torch.distributed.is_available():
        raise RuntimeError("torch.distributed is unavailable in this PyTorch build")
    if not torch.distributed.is_initialized():
        if torch.cuda.is_available():
            if info["local_rank"] >= torch.cuda.device_count():
                raise RuntimeError("LOCAL_RANK exceeds visible CUDA device count")
            torch.cuda.set_device(info["local_rank"])
            device = torch.device("cuda", info["local_rank"])
            backend = "nccl"
        else:
            device = torch.device("cpu")
            backend = "gloo"
        torch.distributed.init_process_group(
            backend=backend, init_method="env://",
            timeout=datetime.timedelta(seconds=int(timeout_seconds)))
    else:
        backend = torch.distributed.get_backend()
        device = (torch.device("cuda", info["local_rank"])
                  if backend == "nccl" else torch.device("cpu"))
    info["backend"] = backend
    info["rank"] = torch.distributed.get_rank()
    info["world_size"] = torch.distributed.get_world_size()
    info["distributed"] = info["world_size"] > 1
    return torch, device, info


def make_distributed_sampler(dataset, *, shuffle=True, drop_last=False, seed=0):
    """Shard a dataset consistently; call sampler.set_epoch(epoch) each epoch."""
    import torch
    info = distributed_info()
    if info["world_size"] == 1:
        return None
    return torch.utils.data.distributed.DistributedSampler(
        dataset, num_replicas=info["world_size"], rank=info["rank"],
        shuffle=shuffle, seed=int(seed), drop_last=drop_last)


def wrap_ddp(model, device, *, find_unused_parameters=False, static_graph=False):
    import torch
    info = distributed_info()
    model = model.to(device)
    if info["world_size"] == 1:
        return model
    if not torch.distributed.is_initialized():
        raise RuntimeError("Initialize process group before wrapping DDP")
    kwargs = {"find_unused_parameters": bool(find_unused_parameters),
              "static_graph": bool(static_graph)}
    if device.type == "cuda":
        kwargs.update(device_ids=[device.index], output_device=device.index)
    return torch.nn.parallel.DistributedDataParallel(model, **kwargs)


def reduce_weighted_mean(local_total, local_count, device):
    """All-reduce sum and count, avoiding a mean-of-rank-means bias."""
    import torch
    pair = torch.tensor([float(local_total), float(local_count)],
                        dtype=torch.float64, device=device)
    if distributed_info()["world_size"] > 1:
        torch.distributed.all_reduce(pair, op=torch.distributed.ReduceOp.SUM)
    if pair[1].item() <= 0:
        return None
    return (pair[0] / pair[1]).item()


def save_checkpoint(path, *, model, optimizer=None, epoch=0, metadata=None,
                    scheduler=None, scaler=None):
    """Atomic rank-0 checkpoint. Returns path on rank 0, None elsewhere."""
    import torch
    info = distributed_info()
    if info["rank"] != 0:
        return None
    target = Path(path).expanduser()
    target.parent.mkdir(parents=True, exist_ok=True)
    module = getattr(model, "module", model)
    payload = {
        "format_version": 1,
        "model_state": module.state_dict(),
        "optimizer_state": optimizer.state_dict() if optimizer else None,
        "scheduler_state": scheduler.state_dict() if scheduler else None,
        "scaler_state": scaler.state_dict() if scaler else None,
        "epoch": int(epoch), "metadata": metadata or {},
    }
    fd, temp_name = tempfile.mkstemp(prefix=".visual-checkpoint-", suffix=".tmp",
                                     dir=str(target.parent))
    os.close(fd)
    try:
        torch.save(payload, temp_name)
        os.replace(temp_name, target)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)
    return str(target)


def load_checkpoint(path, *, model, optimizer=None, scheduler=None, scaler=None,
                    map_location="cpu", strict=True):
    """Restore model and optional optimizer/scheduler/scaler for deterministic continuation."""
    import torch
    payload = torch.load(Path(path).expanduser(), map_location=map_location,
                         weights_only=False)
    if payload.get("format_version") != 1 or "model_state" not in payload:
        raise ValueError("Unsupported or malformed VISUAL checkpoint")
    module = getattr(model, "module", model)
    module.load_state_dict(payload["model_state"], strict=bool(strict))
    for key, obj in (("optimizer_state", optimizer), ("scheduler_state", scheduler),
                     ("scaler_state", scaler)):
        if obj is not None and payload.get(key) is not None:
            obj.load_state_dict(payload[key])
    return {"epoch": int(payload.get("epoch", 0)),
            "metadata": payload.get("metadata", {})}


def cleanup_process_group():
    import torch
    if torch.distributed.is_available() and torch.distributed.is_initialized():
        torch.distributed.destroy_process_group()
