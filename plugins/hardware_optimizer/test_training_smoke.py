import tempfile
import unittest

from training_runtime import run_training


class ActualTrainingSmokeTests(unittest.TestCase):
    def test_cpu_training_updates_weights_and_writes_checkpoint(self):
        try:
            import torch
        except ImportError:
            self.skipTest("PyTorch is optional outside the dedicated CI training job")

        torch.manual_seed(7)
        model = torch.nn.Linear(1, 1)
        initial = [p.detach().clone() for p in model.parameters()]
        x = torch.tensor([[0.0], [1.0], [2.0], [3.0]])
        y = 2.0 * x + 1.0
        train = torch.utils.data.DataLoader(torch.utils.data.TensorDataset(x, y), batch_size=2, shuffle=False)
        valid = torch.utils.data.DataLoader(torch.utils.data.TensorDataset(x, y), batch_size=2, shuffle=False)
        optimizer = torch.optim.SGD(model.parameters(), lr=0.1)
        with tempfile.TemporaryDirectory() as directory:
            report = run_training(
                model, train, valid, optimizer,
                torch.nn.MSELoss(), device="cpu", epochs=5,
                max_steps_per_epoch=4, validation_steps=4,
                patience=5, max_seconds=30, checkpoint_dir=directory,
            )
            self.assertEqual(report["device"], "cpu")
            self.assertGreater(report["epochs_completed"], 0)
            self.assertTrue(report["rolled_back_to_best_weights"])
            self.assertTrue(report["best_checkpoint"])
            self.assertTrue(__import__("os").path.isfile(report["best_checkpoint"]))
            self.assertTrue(any(not torch.equal(before, after) for before, after in zip(initial, model.parameters())))
            self.assertTrue(all(torch.isfinite(torch.tensor(row["validation_loss"])) for row in report["history"]))


if __name__ == "__main__":
    unittest.main()
