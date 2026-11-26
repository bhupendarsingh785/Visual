"""Security regression tests for same-origin browser access through HTTPS tunnels."""
import os
import sys
import unittest
from unittest.mock import patch

os.environ.setdefault("VISUAL_SELFTEST", "1")
sys.argv = ["visual.py"]
import visual


class RemoteOriginTests(unittest.TestCase):
    def make_handler(self, headers, path="/api/chat"):
        handler = visual.Web.__new__(visual.Web)
        handler.headers = headers
        handler.path = path
        return handler

    def test_accepts_same_host_https_origin_with_session_token(self):
        handler = self.make_handler({
            "Host": "blue-fox.trycloudflare.com",
            "Origin": "https://blue-fox.trycloudflare.com",
            "X-Visual-Token": visual.WEB_TOKEN,
        })
        self.assertTrue(handler._ok_origin())

    def test_rejects_cross_site_origin_even_with_token(self):
        handler = self.make_handler({
            "Host": "blue-fox.trycloudflare.com",
            "Origin": "https://attacker.example",
            "X-Visual-Token": visual.WEB_TOKEN,
        })
        self.assertFalse(handler._ok_origin())

    def test_rejects_cross_site_referer(self):
        handler = self.make_handler({
            "Host": "blue-fox.trycloudflare.com",
            "Referer": "https://attacker.example/page",
            "X-Visual-Token": visual.WEB_TOKEN,
        })
        self.assertFalse(handler._ok_origin())

    def test_requires_session_token(self):
        handler = self.make_handler({
            "Host": "blue-fox.trycloudflare.com",
            "Origin": "https://blue-fox.trycloudflare.com",
        })
        self.assertFalse(handler._ok_origin())


if __name__ == "__main__":
    unittest.main()
