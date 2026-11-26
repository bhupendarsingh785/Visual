import os
import tempfile
import unittest
from pathlib import Path
from autonomous_development_engine import (
    add_research, create_task, get_task, list_artifacts, transition,
    validate_artifacts, write_artifact,
)


class DevelopmentEngineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = self.tmp.name
        self.task = create_task("Demo", "Build a small Python tool", "build", self.home)
        self.tid = self.task["id"]

    def tearDown(self):
        self.tmp.cleanup()

    def test_task_state_transitions_are_checked_and_durable(self):
        self.assertEqual(transition(self.tid, "planning", "plan", home=self.home), "planning")
        with self.assertRaises(ValueError):
            transition(self.tid, "completed", "skip validation", home=self.home)
        self.assertEqual(get_task(self.tid, self.home)["status"], "planning")
        self.assertEqual(list_tasks_for_test(self.home)[0]["id"], self.tid)

    def test_research_requires_https_and_is_persisted(self):
        with self.assertRaises(ValueError):
            add_research(self.tid, "http://example.com", "bad", "summary", home=self.home)
        add_research(self.tid, "https://example.com/docs", "Docs", "Claims are documented", "Section 2", self.home)
        self.assertEqual(get_task(self.tid, self.home)["research"][0]["title"], "Docs")

    def test_artifacts_are_confined_and_hashed(self):
        item = write_artifact(self.tid, "src/main.py", "print('hello')\n", self.home)
        self.assertEqual(len(item["sha256"]), 64)
        self.assertEqual(list_artifacts(self.tid), ["src/main.py"])
        with self.assertRaises(ValueError):
            write_artifact(self.tid, "../escape.py", "bad", self.home)

    def test_static_validation_does_not_execute_python(self):
        write_artifact(self.tid, "good.py", "x = 1\n", self.home)
        write_artifact(self.tid, "bad.py", "def broken(:\n", self.home)
        marker = Path(self.task["workspace"]) / "executed.txt"
        write_artifact(self.tid, "attack.py", f"open({str(marker)!r}, 'w').write('oops')\n", self.home)
        result = validate_artifacts(self.tid, self.home)
        self.assertFalse(result["ok"])
        self.assertTrue(any("bad.py" in e for e in result["errors"]))
        self.assertFalse(marker.exists())

    def test_secret_pattern_rejected(self):
        with self.assertRaises(ValueError):
            write_artifact(self.tid, "secret.py", "TOKEN='sk-" + "a"*24 + "'", self.home)


def list_tasks_for_test(home):
    from autonomous_development_engine import list_tasks
    return list_tasks(home)


if __name__ == "__main__":
    unittest.main()
