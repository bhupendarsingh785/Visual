import unittest
from unittest.mock import patch
import compute_fabric


class ComputeFabricPlanTests(unittest.TestCase):
    def test_cpu_fallback_is_explicit(self):
        profile = {
            "host": {"logical_cpus": 8},
            "pytorch": {"installed": False, "available": False, "devices": []},
            "onnxruntime": {"version": None, "providers": ["CPUExecutionProvider"]},
            "training_tools": {},
            "custom_visual_accelerator": {"rtl_present": True, "runtime_driver_available": False,
                                          "active": False, "reason": "not deployed"}
        }
        with patch.object(compute_fabric, "compute_fabric_profile", return_value=profile):
            plan = compute_fabric.compute_fabric_plan("training", training=True)
        self.assertEqual(plan["selected_primary"], "cpu")
        self.assertFalse(plan["training_started"])
        self.assertFalse(plan["custom_rtl_used"])
        self.assertTrue(any("PyTorch is not installed" in item for item in plan["limitations"]))

    def test_cuda_training_device_is_selected_only_when_reported(self):
        profile = {
            "host": {"logical_cpus": 16},
            "pytorch": {"installed": True, "available": True,
                        "devices": [{"kind": "cuda", "index": 0, "name": "test GPU", "memory_bytes": 8_000_000_000}]},
            "onnxruntime": {"version": "test", "providers": ["CUDAExecutionProvider", "CPUExecutionProvider"]},
            "training_tools": {"torchrun": "/usr/bin/torchrun"},
            "custom_visual_accelerator": {"rtl_present": True, "runtime_driver_available": False,
                                          "active": False, "reason": "not deployed"}
        }
        with patch.object(compute_fabric, "compute_fabric_profile", return_value=profile):
            plan = compute_fabric.compute_fabric_plan("training", training=True, memory_budget_gb=6)
        self.assertEqual(plan["selected_primary"], "cuda")
        self.assertEqual(plan["memory_budget_gb"], 6.0)
        self.assertFalse(plan["training_started"])
        self.assertFalse(plan["custom_rtl_used"])

    def test_onnx_accelerator_provider_can_be_selected_for_inference(self):
        profile = {
            "host": {"logical_cpus": 4},
            "pytorch": {"installed": False, "available": False, "devices": []},
            "onnxruntime": {"version": "test", "providers": ["DmlExecutionProvider", "CPUExecutionProvider"]},
            "training_tools": {},
            "custom_visual_accelerator": {"rtl_present": True, "runtime_driver_available": False,
                                          "active": False, "reason": "not deployed"}
        }
        with patch.object(compute_fabric, "compute_fabric_profile", return_value=profile):
            plan = compute_fabric.compute_fabric_plan("inference")
        self.assertEqual(plan["selected_primary"], "DmlExecutionProvider")
        self.assertFalse(plan["custom_rtl_used"])


if __name__ == "__main__":
    unittest.main()
