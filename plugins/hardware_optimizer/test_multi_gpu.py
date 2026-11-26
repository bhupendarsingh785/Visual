import unittest
from unittest.mock import Mock
import multi_gpu


class MultiGpuTopologyTests(unittest.TestCase):
    def fake_torch(self, count):
        torch = Mock()
        torch.cuda.is_available.return_value = count > 0
        torch.cuda.device_count.return_value = count
        torch.cuda.get_device_properties.side_effect = lambda i: type(
            "Props", (), {"name": f"Mock GPU {i}", "total_memory": 8_000_000_000}
        )()
        return torch

    def test_no_gpu_keeps_cpu_coordinator_only(self):
        report = multi_gpu.multi_gpu_topology(self.fake_torch(0))
        self.assertEqual(report["mode"], "cpu_only")
        self.assertFalse(report["multi_gpu_training_ready"])
        self.assertEqual(len(report["physical_cuda_gpus"]), 0)

    def test_multiple_gpus_create_replica_workers(self):
        report = multi_gpu.multi_gpu_topology(self.fake_torch(3))
        self.assertEqual(report["mode"], "multi_cuda_data_parallel")
        self.assertTrue(report["multi_gpu_training_ready"])
        self.assertEqual(report["replica_count"], 3)
        self.assertEqual([w["device"] for w in report["logical_workers"][1:]],
                         ["cuda:0", "cuda:1", "cuda:2"])

    def test_single_gpu_does_not_claim_multi_gpu(self):
        report = multi_gpu.multi_gpu_topology(self.fake_torch(1))
        self.assertEqual(report["mode"], "single_cuda_gpu")
        self.assertFalse(report["multi_gpu_training_ready"])


if __name__ == "__main__":
    unittest.main()
