import unittest
from unittest.mock import patch
from global_research import DOMAIN_QUERIES, collect_global_research

class GlobalResearchTests(unittest.TestCase):
    def test_catalog_covers_requested_core_domains(self):
        for key in ("medicine", "history", "education", "coding", "ai", "agents", "tools", "india"):
            self.assertIn(key, DOMAIN_QUERIES)

    @patch("global_research.time.sleep")
    @patch("global_research.harvest_public_metadata")
    def test_run_obeys_request_cap(self, harvest, _sleep):
        harvest.return_value = {"status": "indexed", "indexed_characters": 100}
        result = collect_global_research(["medicine", "coding"], 4, 3, "/tmp/visual-test")
        self.assertEqual(result["requests_attempted"], 3)
        self.assertEqual(result["successful_requests"], 3)
        self.assertEqual(harvest.call_count, 3)

    def test_unknown_topic_rejected(self):
        with self.assertRaises(ValueError):
            collect_global_research(["not-a-topic"])

if __name__ == "__main__":
    unittest.main()
