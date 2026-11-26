import gzip
import json
import tempfile
import unittest
from pathlib import Path

from local_import import import_local_file
from knowledge_engine import search_knowledge, knowledge_stats


class LocalImportTests(unittest.TestCase):
    def test_gzip_jsonl_stream_import_and_dedup(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            home = root / ".visual"
            home.mkdir(parents=True, exist_ok=True)
            source = home / "sample.jsonl.gz"
            rows = [
                {"id": "1", "title": "Python programming", "body": "Python functions and classes are reusable programming structures."},
                {"id": "2", "title": "Neural networks", "body": "Neural networks learn patterns from training data using optimization."},
            ]
            with gzip.open(source, "wt", encoding="utf-8") as f:
                for row in rows:
                    f.write(json.dumps(row) + "\n")
            first = import_local_file(str(source), "test", str(home))
            second = import_local_file(str(source), "test", str(home))
            self.assertEqual(first["indexed_records"], 2)
            self.assertEqual(second["indexed_records"], 0)
            self.assertEqual(second["skipped_or_duplicate"], 2)
            self.assertTrue(search_knowledge("Python programming", 5, str(home)))
            self.assertEqual(knowledge_stats(str(home))["documents"], 2)

    def test_rejects_outside_paths(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            home = root / ".visual"
            outside = root / "outside.txt"
            outside.write_text("This is a sufficiently long sample document for indexing.", encoding="utf-8")
            with self.assertRaises(ValueError):
                import_local_file(str(outside), home=str(home))


if __name__ == "__main__":
    unittest.main()
