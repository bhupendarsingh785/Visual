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
    def test_memory_repeat_tools_share_persistent_store(self):
        save = visual.TOOLS["store_last"]["fn"]
        recall = visual.TOOLS["recall_last"]["fn"]
        repeat = visual.TOOLS["handle_dohrao"]["fn"]
        store = save.__globals__["store"]
        memory_namespace = store.store_last.__globals__
        previous_path = memory_namespace["MEMORY_FILE"]
        with tempfile.TemporaryDirectory() as home:
            memory_namespace["MEMORY_FILE"] = os.path.join(home, "last_statement.json")
            try:
                self.assertIn("saved", save("integration check"))
                self.assertEqual(recall(), "integration check")
                self.assertEqual(repeat(), "integration check")
            finally:
                memory_namespace["MEMORY_FILE"] = previous_path

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
                self.assertEqual(current["id"], task["id"])
                self.assertTrue(current["events"])
            finally:
                namespace["HOME"] = previous_home


if __name__ == "__main__":
    unittest.main()
