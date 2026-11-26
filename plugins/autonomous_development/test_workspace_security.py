"""Adversarial regression tests for the VISUAL development workspace boundary."""
import tempfile
import unittest
from pathlib import Path

from autonomous_development_engine import create_task, write_artifact


class DevelopmentWorkspaceSecurityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = self.tmp.name
        self.task = create_task("Boundary tests", "Exercise workspace safety", "build", self.home)
        self.tid = self.task["id"]
        self.workspace = Path(self.task["workspace"])

    def tearDown(self):
        self.tmp.cleanup()

    def test_parent_traversal_is_rejected(self):
        with self.assertRaises(ValueError):
            write_artifact(self.tid, "../escape.txt", "no", self.home)

    def test_absolute_path_is_rejected(self):
        with self.assertRaises(ValueError):
            write_artifact(self.tid, str(Path(self.home) / "escape.txt"), "no", self.home)

    def test_windows_style_parent_traversal_is_rejected(self):
        with self.assertRaises(ValueError):
            write_artifact(self.tid, r"..\\escape.txt", "no", self.home)

    def test_symlink_component_is_rejected(self):
        outside = Path(self.home) / "outside"
        outside.mkdir()
        link = self.workspace / "linked"
        try:
            link.symlink_to(outside, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks are unavailable on this runner")
        with self.assertRaisesRegex(ValueError, "symlink"):
            write_artifact(self.tid, "linked/payload.txt", "no", self.home)
        self.assertFalse((outside / "payload.txt").exists())

    def test_secret_like_token_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "secret-looking"):
            write_artifact(self.tid, "config.py", 'API_KEY = "ghp_' + "A" * 36 + '"', self.home)

    def test_oversized_single_artifact_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "1 MB"):
            write_artifact(self.tid, "large.bin", "x" * 1_000_001, self.home)

    def test_atomic_write_leaves_no_temporary_file(self):
        result = write_artifact(self.tid, "nested/module.py", "print('safe')\\n", self.home)
        self.assertTrue((self.workspace / "nested/module.py").is_file())
        self.assertFalse((self.workspace / "nested/module.py.tmp").exists())
        self.assertEqual(len(result["sha256"]), 64)

    def test_empty_and_invalid_task_metadata_are_rejected(self):
        with self.assertRaises(ValueError):
            create_task("", "goal", "build", self.home)
        with self.assertRaises(ValueError):
            create_task("title", "goal", "unrestricted", self.home)


if __name__ == "__main__":
    unittest.main()
