import importlib.util
import unittest
from pathlib import Path

MODULE = Path(__file__).with_name("engine.py")
SPEC = importlib.util.spec_from_file_location("visual_hardware_engine_test", MODULE)
ENGINE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ENGINE)

class HardwareOptimizerTests(unittest.TestCase):
    def test_profile_has_core_fields(self):
        p = ENGINE.hardware_profile()
        for key in ("machine", "logical_cpu_count", "memory", "onnx_execution_providers",
                    "gpu_device_nodes", "local_inference_tools", "cpu_telemetry", "thermal_zones", "accelerator_telemetry"):
            self.assertIn(key, p)
        self.assertGreaterEqual(p["logical_cpu_count"], 1)

    def test_plan_is_explicit_about_measurement(self):
        p = ENGINE.optimization_plan("llm", 512)
        self.assertEqual(p["ram_budget_mb"], 512)
        self.assertTrue(any("Measure baseline" in x for x in p["steps"]))
        self.assertIn("recommended_backend_order", p)
        self.assertIn("limitations", p)

    def test_unknown_backend_is_not_invented(self):
        p = ENGINE.hardware_profile()
        plan = ENGINE.optimization_plan("vision", 0)
        self.assertTrue(set(plan["recommended_backend_order"]).issubset(
            set(p["onnx_execution_providers"])))

    def test_onnx_path_outside_allowlist_rejected(self):
        with self.assertRaises(ValueError):
            ENGINE.create_onnx_session("/tmp/not-allowed.onnx")

if __name__ == "__main__":
    unittest.main()
