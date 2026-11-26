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
    def test_source_topic_is_preserved_in_search_index(self, _url):
        source = add_source("https://docs.example.org/python", "CC-BY", "deep_learning", self.home)
        with patch("knowledge_engine._robots_allowed", return_value=True), patch("knowledge_engine._open_public", return_value=Response()):
            result = ingest_source(source["source_id"], self.home)
        self.assertEqual(result["status"], "indexed")
        found = search_knowledge("Python programming debugging", home=self.home)
        self.assertTrue(found)
        self.assertEqual(found[0]["topic"], "deep_learning")

    @patch("knowledge_engine._public_url", return_value=("https://docs.example.org/python", "docs.example.org"))
    def test_short_response_is_marked_error(self, _url):
        class ShortResponse(Response):
            def read(self, size=-1): return b"too short"
        source = add_source("https://docs.example.org/python", "CC-BY", "test", self.home)
        with patch("knowledge_engine._robots_allowed", return_value=True), patch("knowledge_engine._open_public", return_value=ShortResponse()):
            with self.assertRaises(ValueError):
                ingest_source(source["source_id"], self.home)
        self.assertEqual(add_source("https://docs.example.org/python", "CC-BY", "test", self.home)["status"], "error")

    def test_redirects_to_non_public_targets_are_rejected(self):
        from knowledge_engine import _PublicRedirectHandler
        from urllib.request import Request
        handler = _PublicRedirectHandler()
        request = Request("https://docs.example.org/start")
        with patch("knowledge_engine._public_url", side_effect=ValueError("private target blocked")):
            with self.assertRaises(ValueError):
                handler.redirect_request(request, None, 302, "Found", {}, "https://127.0.0.1/admin")
    def test_nonstandard_https_port_is_rejected(self):
        from knowledge_engine import _public_url
        with self.assertRaises(ValueError):
            _public_url("https://docs.example.org:8443/data")

    def test_original_request_is_revalidated_before_network_access(self):
        from knowledge_engine import _open_public
        from urllib.request import Request
        with patch("knowledge_engine._public_url", side_effect=ValueError("private host")):
            with self.assertRaises(ValueError):
                _open_public(Request("https://127.0.0.1/private"), timeout=1)

    def test_legacy_database_gets_topic_column(self):
        import sqlite3
        from knowledge_engine import _db_path, _connect
        path = _db_path(self.home)
        legacy = sqlite3.connect(str(path))
        legacy.execute("""CREATE TABLE sources (
            id TEXT PRIMARY KEY, url TEXT UNIQUE NOT NULL, domain TEXT NOT NULL,
            title TEXT NOT NULL DEFAULT '', license TEXT NOT NULL DEFAULT 'unknown',
            status TEXT NOT NULL, added_at REAL NOT NULL, fetched_at REAL, etag TEXT,
            last_modified TEXT, content_hash TEXT, error TEXT NOT NULL DEFAULT '')""")
        legacy.commit()
        legacy.close()
        with _connect(self.home) as db:
            columns = {row[1] for row in db.execute("PRAGMA table_info(sources)")}
            self.assertIn("topic", columns)

    def test_sqlite_connection_closes_after_context(self):
        from knowledge_engine import _connect
        with _connect(self.home) as db:
            db.execute("SELECT 1")
        with self.assertRaises(Exception):
            db.execute("SELECT 1")\n    @patch("knowledge_engine._public_url", return_value=("https://docs.example.org/python", "docs.example.org"))
    def test_add_ingest_search_and_deduplicate(self, _url):
        source = add_source("https://docs.example.org/python", "CC-BY", "python", self.home)
        with patch("knowledge_engine._robots_allowed", return_value=True), patch("knowledge_engine._open_public", return_value=Response()):
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
        with patch("knowledge_engine._robots_allowed", return_value=False), patch("knowledge_engine._open_public") as fetch:
            result = ingest_source(source["source_id"], self.home)
        self.assertEqual(result["status"], "blocked")
        fetch.assert_not_called()

if __name__ == "__main__":
    unittest.main()
