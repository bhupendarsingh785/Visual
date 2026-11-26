import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from knowledge_engine import add_source, collect_queued

class BatchCollectorTests(unittest.TestCase):
    def test_collect_queued_is_bounded_and_reports_failures(self):
        with tempfile.TemporaryDirectory() as tmp:
            home=Path(tmp)
            with patch("knowledge_engine._public_url", side_effect=lambda u:(u,"docs.example.org")):
                for n in range(4):
                    add_source(f"https://docs.example.org/{n}", "MIT", "docs", home)
            calls = {"count": 0}
            def fake_ingest(source_id, home):
                calls["count"] += 1
                if calls["count"] == 1:
                    raise RuntimeError("offline")
                return {"status":"indexed","document_id":"doc"}
            with patch("knowledge_engine.ingest_source", side_effect=fake_ingest), patch("knowledge_engine.time.sleep"):
                result=collect_queued(2, home)
            self.assertEqual(result["processed"],2)
            self.assertEqual(result["results"][0]["status"],"error")
            self.assertEqual(result["results"][1]["status"],"indexed")

if __name__ == "__main__":
    unittest.main()
