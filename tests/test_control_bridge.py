import importlib.util
import json
import time
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "visual-control-bridge.py"
spec = importlib.util.spec_from_file_location("visual_control_bridge", SCRIPT)
bridge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)

class PayloadTests(unittest.TestCase):
    def envelope(self, action, args=None, **extra):
        return json.dumps({"action": action, "args": args or {}, "nonce": "nonce_1234567890",
                           "expires_at": int(time.time()) + 60, **extra})

    def test_status_accepts_empty_args(self):
        self.assertEqual(bridge.parse_payload(self.envelope("knowledge_status")),
                         ("knowledge_status", {}, "nonce_1234567890"))

    def test_rejects_unknown_action(self):
        with self.assertRaises(ValueError):
            bridge.parse_payload(self.envelope("shell", {"cmd": "id"}))

    def test_rejects_expired_command(self):
        payload = {"action":"knowledge_status","args":{},"nonce":"nonce_1234567890","expires_at":1}
        with self.assertRaises(ValueError):
            bridge.parse_payload(json.dumps(payload))

    def test_research_bounds(self):
        with self.assertRaises(ValueError):
            bridge.parse_payload(self.envelope("knowledge_collect_global_research", {"max_requests":9999}))
        action, args, _ = bridge.parse_payload(self.envelope(
            "knowledge_collect_global_research", {"topics":"ai","per_request":25,"max_requests":300}))
        self.assertEqual(action, "knowledge_collect_global_research")
        self.assertEqual(args["max_requests"], 300)

    def test_rejects_extra_envelope_field(self):
        with self.assertRaises(ValueError):
            bridge.parse_payload(self.envelope("knowledge_status", surprise=True))

if __name__ == "__main__":
    unittest.main()
