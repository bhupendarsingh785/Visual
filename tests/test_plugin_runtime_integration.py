"""End-to-end wiring test for the loaded VISUAL development plugin."""
import json
import os
import sys
import tempfile
import unittest

os.environ.setdefault("VISUAL_SELFTEST", "1")
sys.argv = ["visual.py"]
import visual


class PluginRuntimeIntegrationTests(unittest.TestCase):
    def test_development_plugin_runner_keeps_engine_references_after_load(self):
        create = visual.TOOLS["dev_task_create"]["fn"]
        run_tests = visual.TOOLS["dev_task_run_tests"]["fn"]
        status = visual.TOOLS["dev_task_status"]["fn"]
        namespace = create.__globals__
        previous_home = namespace.get("HOME")
        with tempfile.TemporaryDirectory() as home:
            namespace["HOME"] = home
            try:
                task = json.loads(create("CI integration smoke", "Verify plugin runtime wiring", "build"))
                report = json.loads(run_tests(task["id"], "python", 1))
                self.assertIn(report["status"], {"passed", "failed", "unavailable"})
                current = json.loads(status(task["id"]))
                self.assertEqual(current["task"]["id"], task["id"])
                self.assertTrue(current["events"])
            finally:
                namespace["HOME"] = previous_home


if __name__ == "__main__":
    unittest.main()
