import os
import tempfile
import unittest
from pathlib import Path
from autonomous_development_engine import (
    add_research, create_task, get_task, list_artifacts, record_execution_result, transition,
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
        with self.assertRaises(PermissionError):
            transition(self.tid, "completed", "skip validation", home=self.home)
        self.assertEqual(get_task(self.tid, self.home)["status"], "planning")
        self.assertEqual(list_tasks_for_test(self.home)[0]["id"], self.tid)

    def test_only_owner_can_complete_after_successful_validation(self):
        transition(self.tid, "planning", home=self.home)
        transition(self.tid, "implementing", home=self.home)
        transition(self.tid, "validating", home=self.home)
        write_artifact(self.tid, "main.py", "print('ok')\n", self.home)
        validate_artifacts(self.tid, self.home)
        with self.assertRaises(ValueError):
            transition(self.tid, "awaiting_approval", "runtime tests missing", home=self.home)
        record_execution_result(self.tid, {"status":"passed","profile":"python","network":"disabled","secrets_forwarded":False,"results":[{"status":"passed"}]}, self.home)
        transition(self.tid, "awaiting_approval", "static and isolated runtime tests passed", home=self.home)
        with self.assertRaises(PermissionError):
            transition(self.tid, "completed", "agent tries self-approval", actor="agent", home=self.home)
        self.assertEqual(transition(self.tid, "completed", "owner approved", actor="owner", home=self.home), "completed")

    def test_workspace_change_after_runtime_test_invalidates_approval(self):
        transition(self.tid, "planning", home=self.home)
        transition(self.tid, "implementing", home=self.home)
        transition(self.tid, "validating", home=self.home)
        write_artifact(self.tid, "main.py", "print(1)\n", self.home)
        validate_artifacts(self.tid, self.home)
        record_execution_result(self.tid, {"status":"passed","profile":"python","results":[{"status":"passed"}]}, self.home)
        write_artifact(self.tid, "main.py", "print(2)\n", self.home)
        validate_artifacts(self.tid, self.home)
        with self.assertRaisesRegex(ValueError, "workspace badla hai"):
            transition(self.tid, "awaiting_approval", "stale test result", home=self.home)

    def test_research_requires_https_and_is_persisted(self):
        with self.assertRaises(ValueError):
            add_research(self.tid, "http://example.com", "bad", "summary", home=self.home)
        add_research(self.tid, "https://example.com/docs", "Docs", "Claims are documented", "Section 2", self.home)
        self.assertEqual(get_task(self.tid, self.home)["research"][0]["title"], "Docs")

    def test_artifacts_are_confined_and_hashed(self):
        item = write_artifact(self.tid, "src/main.py", "print('hello')\n", self.home)
        self.assertEqual(len(item["sha256"]), 64)
        self.assertEqual(list_artifacts(self.tid,self.home), ["src/main.py"])
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


    def test_plugin_registers_expected_tools(self):
        import builtins
        registered = {}
        def fake_tool(description, params=None, risky=False):
            def deco(fn):
                registered[fn.__name__] = {"fn":fn,"risky":risky}
                return fn
            return deco
        ns = {"tool":fake_tool,"S":lambda desc,**kw:{"type":"string","description":desc,**kw},
              "N":lambda desc,**kw:{"type":"number","description":desc,**kw},
              "HOME":self.home}
        source = Path(__file__).with_name("plugin.py").read_text(encoding="utf-8")
        exec(compile(source,"plugin.py","exec"),ns)
        expected = {"dev_task_create","dev_task_status","dev_task_list","dev_task_transition",
                    "dev_task_add_research","dev_task_write_file","dev_task_files","dev_task_validate",
                    "dev_task_approve","dev_task_run_tests","dev_task_run_manifest"}
        self.assertTrue(expected.issubset(registered))
        self.assertTrue(registered["dev_task_approve"]["risky"])

    def test_secret_pattern_rejected(self):
        with self.assertRaises(ValueError):
            write_artifact(self.tid, "secret.py", "TOKEN='sk-" + "a"*24 + "'", self.home)


def list_tasks_for_test(home):
    from autonomous_development_engine import list_tasks
    return list_tasks(home)


if __name__ == "__main__":
    unittest.main()
