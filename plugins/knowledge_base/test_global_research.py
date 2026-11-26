import tempfile
import unittest
from unittest.mock import patch
from global_research import DOMAIN_QUERIES, collect_global_research

class GlobalResearchTests(unittest.TestCase):
    def test_catalog_covers_requested_core_domains(self):
        for key in ("medicine", "history", "education", "coding", "ai", "agents", "tools", "india", "deep_learning", "computer_vision", "audio_speech", "semiconductor_research"):
            self.assertIn(key, DOMAIN_QUERIES)
        from global_research import PROVIDERS
        self.assertEqual(len(DOMAIN_QUERIES), 100)
        self.assertEqual(len(PROVIDERS), 15)

    @patch("global_research.time.sleep")
    @patch("global_research.harvest_public_metadata")
    def test_run_obeys_request_cap(self, harvest, _sleep):
        harvest.return_value = {"status": "indexed", "indexed_characters": 100}
        result = collect_global_research(["medicine", "coding"], 4, 3, "/tmp/visual-test")
        self.assertEqual(result["requests_attempted"], 3)
        self.assertEqual(result["successful_requests"], 3)
        self.assertEqual(harvest.call_count, 3)

    def test_empty_search_results_are_not_counted_as_failures(self):
        with tempfile.TemporaryDirectory() as home:
            with patch("global_research.harvest_public_metadata", side_effect=[
                {"provider": "openalex", "status": "empty", "indexed_characters": 0},
                {"provider": "crossref", "status": "indexed", "indexed_characters": 100},
            ]), patch("global_research.time.sleep"):
                result = collect_global_research(["medicine"], 25, 2, home)
            self.assertEqual(result["successful_requests"], 1)
            self.assertEqual(result["empty_results"], 1)
            self.assertEqual(result["failed_requests"], 0)
            self.assertEqual(result["provider_status_counts"]["openalex"]["empty"], 1)
            self.assertEqual(result["provider_status_counts"]["crossref"]["indexed"], 1)

    def test_manual_runs_persist_and_rotate_task_cursor(self):
        with tempfile.TemporaryDirectory() as home:
            providers = []
            def record(provider, query, limit, root, topic=None):
                providers.append(provider)
                return {"status": "indexed", "indexed_characters": 100}
            with patch("global_research.harvest_public_metadata", side_effect=record), patch("global_research.time.sleep"):
                first = collect_global_research(["medicine"], 25, 1, home)
                all_topics = collect_global_research(None, 25, 1, home)
                second = collect_global_research(["medicine"], 25, 1, home)
            self.assertEqual(providers, ["openalex", "openalex", "crossref"])
            self.assertEqual(first["task_offset"], 0)
            self.assertEqual(all_topics["task_offset"], 0)
            self.assertEqual(second["task_offset"], 1)
            self.assertEqual(second["next_task_offset"], 2)

    def test_unknown_topic_rejected(self):
        with self.assertRaises(ValueError):
            collect_global_research(["not-a-topic"])

if __name__ == "__main__":
    unittest.main()
