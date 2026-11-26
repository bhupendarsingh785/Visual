import tempfile
import unittest
from pathlib import Path

from self_intelligence_engine import (
    assess_snapshot, collect_snapshot, create_plan, latest_report,
    plan_history, save_snapshot, update_plan,
)


class SelfIntelligenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.home = self.temp.name
        self.root = Path(self.home) / "repo"
        self.root.mkdir()
        (self.root / "visual.py").write_text("# runtime", encoding="utf-8")
        (self.root / "api_key.txt").write_text("must not inventory secret-named file", encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def test_snapshot_inventory_omits_secret_named_files(self):
        snapshot = collect_snapshot({
            "root": str(self.root), "python": "3.13", "platform": "test",
            "providers": {"gemini": {"model": "flash", "vision": True, "tools": True}},
            "tools": {"brains": {}, "self_info": {}}, "plugins": {"demo": True},
            "plugin_errors": {}, "tasks": {}, "config": {"keys": {"gemini": "SECRET"}, "confirm_risky": True},
        })
        paths = [item["path"] for item in snapshot["file_inventory"]["files"]]
        self.assertIn("visual.py", paths)
        self.assertNotIn("api_key.txt", paths)
        serialized = str(snapshot)
        self.assertNotIn("SECRET", serialized)

    def test_assessment_detects_plugin_and_security_findings(self):
        findings = assess_snapshot({
            "plugin_errors": {"bad": "ImportError"},
            "tool_count": 1, "providers": {"gemini": {}},
            "file_inventory": {"count": 2, "truncated": False},
            "task_status_counts": {}, "config_profile": {"confirm_risky": False},
        })
        titles = [x[2] for x in findings]
        self.assertIn("Plugin load errors present", titles)
        self.assertIn("Risky-action confirmation is disabled", titles)

    def test_snapshot_and_findings_persist(self):
        snap = {"tool_count": 2, "providers": {"gemini": {}}, "file_inventory": {"count": 1}}
        findings = assess_snapshot({
            "plugin_errors": {}, "tool_count": 2, "providers": {"gemini": {}},
            "file_inventory": {"count": 1, "truncated": False}, "task_status_counts": {},
            "config_profile": {"confirm_risky": True},
        })
        saved = save_snapshot(snap, findings, self.home)
        report = latest_report(self.home)
        self.assertEqual(report["snapshot"]["id"], saved["snapshot_id"])
        self.assertTrue(report["findings"])

    def test_snapshot_delta_is_reported(self):
        first = {"file_inventory": {"files": [{"path": "a.py", "size": 1, "mtime": 1}], "truncated": False}}
        second = {"file_inventory": {"files": [{"path": "a.py", "size": 2, "mtime": 2}, {"path": "b.py", "size": 1, "mtime": 1}], "truncated": False}}
        save_snapshot(first, [("info", "health", "first", "baseline")], self.home)
        save_snapshot(second, [("info", "health", "second", "follow-up")], self.home)
        delta = latest_report(self.home)["change_summary"]
        self.assertEqual(delta["added"], ["b.py"])
        self.assertEqual(delta["changed"], ["a.py"])
        self.assertEqual(delta["removed"], [])

    def test_improvement_lifecycle_and_validation(self):
        pid = create_plan("Better agent control", "agent/task state", "tasks lack checkpoints",
                          "no source edits; revert plan", "restart resumes from saved checkpoint", self.home)
        self.assertEqual(plan_history(self.home)[0]["status"], "proposed")
        update_plan(pid, "approved", "reviewed", self.home)
        self.assertEqual(plan_history(self.home)[0]["status"], "approved")
        with self.assertRaises(ValueError):
            update_plan(pid, "self_authorized", "", self.home)
        with self.assertRaises(ValueError):
            update_plan(pid, "completed", "self-certified", self.home)
        with self.assertRaises(KeyError):
            update_plan("missing", "approved", "", self.home)


if __name__ == "__main__":
    unittest.main()
