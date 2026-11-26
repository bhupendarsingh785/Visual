import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import subprocess
from unittest.mock import patch
from autonomous_development_engine import create_task
import execution_engine


class ExecutionEngineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = self.tmp.name
        self.task = create_task("Runner demo", "test isolated runner", "build", self.home)
        self.workspace = Path(self.task["workspace"])

    def tearDown(self):
        self.tmp.cleanup()

    @patch("execution_engine._docker_available", return_value=(None, "not installed"))
    def test_missing_docker_fails_closed_without_execution(self, _docker):
        result = execution_engine.run_profile(self.task["id"], "python", self.home)
        self.assertEqual(result["status"], "unavailable")
        self.assertFalse(result["secrets_forwarded"])
        self.assertEqual(result["network"], "disabled")

    @patch("execution_engine.subprocess.run")
    def test_runner_uses_readonly_input_and_ephemeral_workspace(self, run):
        run.return_value = subprocess.CompletedProcess(["docker"], 0, "ok", "")
        result = execution_engine._run_one("docker", self.workspace, "python:3.12-slim", ["python", "-m", "unittest"], 10)
        self.assertEqual(result["status"], "passed")
        cmd = run.call_args.args[0]
        self.assertIn("--network=none", cmd)
        self.assertIn("--read-only", cmd)
        self.assertIn(str(self.workspace) + ":/input:ro", cmd)
        self.assertIn("/workspace:rw,exec,nosuid,size=256m,uid=65534,gid=65534,mode=0700", cmd)
        self.assertNotIn("--privileged", cmd)
        self.assertNotIn("-e", cmd[cmd.index("-v") + 2:])

    def test_unknown_profile_rejected(self):
        with self.assertRaises(ValueError):
            execution_engine.run_profile(self.task["id"], "bash", self.home)

    def test_manifest_requires_argv_arrays(self):
        with self.assertRaises(ValueError):
            execution_engine.run_manifest(self.task["id"], {"profile":"python","commands":["python -c 'bad'"]}, self.home)

    def test_manifest_rejects_null_bytes_and_oversized_arguments(self):
        with self.assertRaises(ValueError):
            execution_engine.run_manifest(self.task["id"], {"profile":"python","commands":[["python","\x00"]]}, self.home)

    def test_manifest_rejects_shell_entrypoints(self):
        with self.assertRaises(ValueError):
            execution_engine.run_manifest(self.task["id"], {"profile":"python","commands":[["sh","-c","id"]]}, self.home)

    @patch("execution_engine._docker_available", return_value=(None, "not installed"))
    def test_manifest_does_not_fallback_to_host(self, _docker):
        result = execution_engine.run_manifest(self.task["id"], {"profile":"python","commands":[["python","-m","unittest"]]}, self.home)
        self.assertEqual(result["status"], "unavailable")
        self.assertIn("No direct local execution fallback", result["limitations"])


if __name__ == "__main__":
    unittest.main()
