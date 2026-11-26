import json
import time
import unittest
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "plugin.py"

class BridgeSourceContractTests(unittest.TestCase):
    def test_bridge_is_not_a_shell_proxy(self):
        source = SOURCE.read_text(encoding="utf-8")
        self.assertIn('BRIDGE_ALLOWED = {"knowledge_collect_global_research", "knowledge_status"}', source)
        self.assertNotIn('shell=True', source)
        self.assertNotIn('os.system(', source)

    def test_private_repo_and_owner_are_pinned(self):
        source = SOURCE.read_text(encoding="utf-8")
        self.assertIn('BRIDGE_REPO = "bhupendarsingh785/visual-data"', source)
        self.assertIn('BRIDGE_OWNER = "bhupendarsingh785"', source)
        self.assertIn('if private.lower() != "true"', source)

    def test_command_has_expiry_nonce_and_bounded_research(self):
        source = SOURCE.read_text(encoding="utf-8")
        for required in ("nonce", "expires_at", "max_requests", "per_request", "24 hours"):
            self.assertIn(required, source)

    def test_crash_ledger_is_fail_closed(self):
        source = SOURCE.read_text(encoding="utf-8")
        self.assertIn("manual repair required", source)
        self.assertIn('status": "running"', source)
        self.assertIn("never replayed automatically", source)

if __name__ == "__main__":
    unittest.main()
