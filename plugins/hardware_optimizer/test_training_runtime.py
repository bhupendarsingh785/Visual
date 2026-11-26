import unittest
import tempfile
from pathlib import Path
from training_runtime import validate_training_limits, run_training

try:
    import torch
except ImportError:
    torch = None


class TrainingLimitTests(unittest.TestCase):
    def test_defaults_are_bounded(self):
        limits = validate_training_limits()
        self.assertEqual(limits["epochs"], 3)
        self.assertEqual(limits["max_seconds"], 3600)

    def test_rejects_unbounded_or_invalid_values(self):
        for kwargs in (
            {"epochs": 0},
            {"epochs": 501},
            {"max_steps_per_epoch": 100001},
            {"max_seconds": 86401},
            {"patience": 0},
            {"gradient_clip_norm": float("nan")},
        ):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(ValueError):
                    validate_training_limits(**kwargs)

@unittest.skipIf(torch is None, "PyTorch not installed in lightweight CI")
class RealTrainingSmokeTests(unittest.TestCase):
    def test_optimizer_updates_and_validation_steps_are_batches(self):
        model = torch.nn.Linear(1, 1, bias=False)
        with torch.no_grad():
            model.weight.fill_(0.0)
        optimizer = torch.optim.SGD(model.parameters(), lr=0.1)
        train = [
            (torch.tensor([[1.0], [2.0]]), torch.tensor([[2.0], [4.0]])),
            (torch.tensor([[3.0], [4.0]]), torch.tensor([[6.0], [8.0]])),
        ]
        validation = [
            (torch.tensor([[1.0], [2.0], [3.0]]), torch.tensor([[2.0], [4.0], [6.0]])),
            (torch.tensor([[4.0]]), torch.tensor([[8.0]])),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            result = run_training(
                model, train, validation, optimizer,
                lambda output, target: torch.nn.functional.mse_loss(output, target),
                device="cpu", epochs=1, max_steps_per_epoch=1,
                validation_steps=1, max_seconds=30, checkpoint_dir=tmp,
            )
            self.assertEqual(result["training_updates"], 1)
            self.assertEqual(result["history"][0]["steps"], 1)
            self.assertEqual(result["history"][0]["training_samples"], 2)
            self.assertTrue(result["validation_is_sample_weighted"])
            self.assertTrue(Path(result["best_checkpoint"]).is_file())
            self.assertNotEqual(float(model.weight.detach().item()), 0.0)

    def test_cpu_bfloat16_amp_updates_parameters(self):
        model = torch.nn.Linear(2, 1)
        optimizer = torch.optim.SGD(model.parameters(), lr=0.05)
        before = [p.detach().clone() for p in model.parameters()]
        batch = (torch.ones(4, 2), torch.ones(4, 1))
        with tempfile.TemporaryDirectory() as tmp:
            result = run_training(
                model, [batch], [batch], optimizer,
                lambda output, target: torch.nn.functional.mse_loss(output, target),
                device="cpu", precision="bf16", epochs=1,
                max_steps_per_epoch=1, validation_steps=1,
                max_seconds=30, checkpoint_dir=tmp,
            )
        self.assertEqual(result["precision"], "bf16")
        self.assertTrue(result["amp_enabled"])
        self.assertTrue(any(not torch.equal(old, new) for old, new in zip(before, model.parameters())))

    def test_rejects_unsupported_precision(self):
        model = torch.nn.Linear(1, 1)
        optimizer = torch.optim.SGD(model.parameters(), lr=0.1)
        with self.assertRaises(ValueError):
            run_training(model, [], [], optimizer, lambda a, b: a.sum(), precision="int8")


if __name__ == "__main__":
    unittest.main()
