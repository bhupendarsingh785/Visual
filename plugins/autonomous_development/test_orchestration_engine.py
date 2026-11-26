import tempfile
import unittest
from autonomous_development_engine import create_task, write_artifact, get_task, record_execution_result
from orchestration_engine import start, record, approve

REVIEW = '{"secrets":"clear","dependencies":"reviewed","permissions":"reviewed","sandbox":"reviewed","data_flow":"reviewed","auth":"reviewed"}'
PASS = {"status":"passed","profile":"python","network":"disabled","secrets_forwarded":False,"results":[{"status":"passed","exit_code":0,"command":["python","-m","unittest"]}]}

class OrchestrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = self.tmp.name
        self.task = create_task("Orchestration", "Build and verify sample", "build", self.home)
        self.tid = self.task["id"]

    def tearDown(self): self.tmp.cleanup()

    def _reach_security(self, source="print('ok')\n"):
        start(self.tid, self.home)
        record(self.tid, "planner", "pass", home=self.home)
        write_artifact(self.tid, "main.py", source, self.home)
        record(self.tid, "coder", "pass", home=self.home)
        record_execution_result(self.tid, PASS, self.home)
        self.assertEqual(record(self.tid, "tester", "pass", home=self.home)["role"], "security_reviewer")

    def test_full_role_sequence_requires_owner_approval(self):
        self._reach_security()
        self.assertEqual(record(self.tid, "security_reviewer", "pass", notes=REVIEW, home=self.home)["status"], "awaiting_owner_approval")
        with self.assertRaises(PermissionError): approve(self.tid, "self approve", actor="agent", home=self.home)
        self.assertEqual(approve(self.tid, "owner checked", home=self.home)["status"], "completed")
        self.assertEqual(get_task(self.tid, self.home)["status"], "completed")

    def test_workspace_change_invalidates_review(self):
        self._reach_security("print(1)\n")
        record(self.tid, "security_reviewer", "pass", notes=REVIEW, home=self.home)
        write_artifact(self.tid, "main.py", "print(2)\n", self.home)
        with self.assertRaisesRegex(ValueError, "workspace changed"):
            approve(self.tid, "approve", home=self.home)

    def test_roles_cannot_skip(self):
        start(self.tid, self.home)
        with self.assertRaises(ValueError): record(self.tid, "coder", "pass", home=self.home)

    def test_security_review_requires_checklist(self):
        self._reach_security()
        state = record(self.tid, "security_reviewer", "pass", notes="looks fine", home=self.home)
        self.assertEqual(state["role"], "coder")
        self.assertEqual(state["status"], "running")

if __name__ == "__main__": unittest.main()
