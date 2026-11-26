import tempfile
import unittest
from autonomous_development_engine import create_task, write_artifact, get_task
from orchestration_engine import start, record, approve

class OrchestrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = self.tmp.name
        self.task = create_task("Orchestration", "Build and verify sample", "build", self.home)
        self.tid = self.task["id"]

    def tearDown(self): self.tmp.cleanup()

    def test_full_role_sequence_requires_owner_approval(self):
        self.assertEqual(start(self.tid, self.home)["role"], "planner")
        self.assertEqual(record(self.tid, "planner", "pass", home=self.home)["role"], "coder")
        write_artifact(self.tid, "main.py", "print('ok')\\n", self.home)
        self.assertEqual(record(self.tid, "coder", "pass", home=self.home)["role"], "tester")
        self.assertEqual(record(self.tid, "tester", "pass", home=self.home)["role"], "security_reviewer")
        self.assertEqual(record(self.tid, "security_reviewer", "pass", home=self.home)["status"], "awaiting_owner_approval")
        with self.assertRaises(PermissionError): approve(self.tid, "self approve", actor="agent", home=self.home)
        self.assertEqual(approve(self.tid, "owner checked", home=self.home)["status"], "completed")
        self.assertEqual(get_task(self.tid, self.home)["status"], "completed")

    def test_workspace_change_invalidates_review(self):
        start(self.tid, self.home)
        record(self.tid, "planner", "pass", home=self.home)
        write_artifact(self.tid, "main.py", "print(1)\\n", self.home)
        record(self.tid, "coder", "pass", home=self.home)
        record(self.tid, "tester", "pass", home=self.home)
        record(self.tid, "security_reviewer", "pass", home=self.home)
        write_artifact(self.tid, "main.py", "print(2)\\n", self.home)
        with self.assertRaisesRegex(ValueError, "workspace changed"):
            approve(self.tid, "approve", home=self.home)

    def test_roles_cannot_skip(self):
        start(self.tid, self.home)
        with self.assertRaises(ValueError): record(self.tid, "coder", "pass", home=self.home)

if __name__ == "__main__": unittest.main()
