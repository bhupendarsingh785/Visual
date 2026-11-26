import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from knowledge_engine import add_source, ingest_source, search_knowledge, knowledge_stats

class Response:
    headers = {"Content-Type":"text/plain; charset=utf-8", "ETag":"test-etag"}
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self, size=-1):
        return (b"Python programming documentation explains functions, classes, modules, testing, "
                b"debugging, packages, and application development. " * 8)[:size]

class KnowledgeBaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
    def tearDown(self):
        self.tmp.cleanup()

    @patch("knowledge_engine._public_url", return_value=("https://docs.example.org/python", "docs.example.org"))
    def test_add_ingest_search_and_deduplicate(self, _url):
        source = add_source("https://docs.example.org/python", "CC-BY", "python", self.home)
        with patch("knowledge_engine._robots_allowed", return_value=True), patch("knowledge_engine.urllib.request.urlopen", return_value=Response()):
            result = ingest_source(source["source_id"], self.home)
        self.assertEqual(result["status"], "indexed")
        found = search_knowledge("Python programming debugging", home=self.home)
        self.assertTrue(found)
        self.assertIn("https://docs.example.org/python", found[0]["url"])
        self.assertEqual(knowledge_stats(self.home)["documents"], 1)
        again = add_source("https://docs.example.org/python", "CC-BY", "python", self.home)
        self.assertEqual(again["source_id"], source["source_id"])

    @patch("knowledge_engine._public_url", return_value=("https://docs.example.org/python", "docs.example.org"))
    def test_robots_disallow_prevents_fetch(self, _url):
        source = add_source("https://docs.example.org/python", home=self.home)
        with patch("knowledge_engine._robots_allowed", return_value=False), patch("knowledge_engine.urllib.request.urlopen") as fetch:
            result = ingest_source(source["source_id"], self.home)
        self.assertEqual(result["status"], "blocked")
        fetch.assert_not_called()

if __name__ == "__main__":
    unittest.main()
