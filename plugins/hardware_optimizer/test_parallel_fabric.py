import unittest
from unittest.mock import patch
from parallel_fabric import build_parallel_fabric, distributed_training_preflight


class ParallelFabricTests(unittest.TestCase):
    def test_cpu_only_has_no_fabricated_gpu_workers(self):
        with patch("parallel_fabric.importlib.util.find_spec", return_value=None), patch("parallel_fabric.os.cpu_count", return_value=8):
            plan = build_parallel_fabric(cpu_workers=4)
        self.assertEqual(plan["physical_gpu_count"], 0)
        self.assertEqual(plan["logical_gpu_worker_count"], 0)
        self.assertEqual(plan["cpu_worker_count"], 4)
        self.assertFalse(plan["distributed_training_ready"])

    def test_worker_replica_limits(self):
        with self.assertRaises(ValueError):
            build_parallel_fabric(gpu_workers_per_device=9)
        with self.assertRaises(ValueError):
            build_parallel_fabric(cpu_workers=257)

    def test_gpu_replicas_are_not_claimed_as_physical_devices(self):
        # Mock a two-device CUDA host while keeping the test independent of hardware.
        class Props:
            name = "Mock GPU"
            total_memory = 8 * 1024**3
        class Cuda:
            @staticmethod
            def is_available(): return True
            @staticmethod
            def device_count(): return 2
            @staticmethod
            def get_device_properties(_): return Props()
        class Torch:
            cuda = Cuda()
            class backends:
                class mps:
                    @staticmethod
                    def is_available(): return False
            xpu = None
        with patch("parallel_fabric.importlib.util.find_spec", return_value=object()), patch.dict("sys.modules", {"torch": Torch()}), patch("parallel_fabric.os.cpu_count", return_value=8):
            plan = build_parallel_fabric(cpu_workers=3, gpu_workers_per_device=2)
        self.assertEqual(plan["physical_gpu_count"], 2)
        self.assertEqual(plan["logical_gpu_worker_count"], 4)
        self.assertEqual(len(plan["gpu_workers"]), 4)
        self.assertIn("Shares this physical GPU", plan["gpu_workers"][0]["note"])

    def test_preflight_without_torch(self):
        with patch("parallel_fabric.importlib.util.find_spec", return_value=None):
            result = distributed_training_preflight()
        self.assertFalse(result["ready"])


if __name__ == "__main__":
    unittest.main()
