import json
import tempfile
import unittest
from pathlib import Path
from knowledge_engine import _connect
from training_prep import prepare_training_corpus

class TrainingPrepTests(unittest.TestCase):
    def test_license_gate_dedup_and_deterministic_splits(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            with _connect(home) as db:
                for sid, license_name, url, text in [
                    ("s1", "CC0", "https://example.org/a", "A" * 400),
                    ("s2", "unknown", "https://example.org/b", "B" * 400),
                    ("s3", "CC-BY-4.0", "https://example.org/c", "C" * 400),
                    ("s4", "CC-BY-NC", "https://example.org/d", "D" * 400),
                    ("s5", "CC0 metadata; linked full text has separate rights", "https://example.org/e", "E" * 400),
                ]:
                    db.execute("INSERT INTO sources(id,url,domain,license,status,added_at) VALUES(?,?,?,?,?,?)",
                               (sid,url,"example.org",license_name,"indexed",1))
                    import hashlib
                    digest=hashlib.sha256(text.encode()).hexdigest()
                    db.execute("INSERT INTO documents(id,source_id,title,text,content_hash,topic,created_at) VALUES(?,?,?,?,?,?,?)",
                               ("d"+sid,sid,"title",text,digest,"test",1))
            out = Path(tmp) / "prepared"
            result = prepare_training_corpus(home=home, output_dir=out)
            self.assertEqual(result["total_eligible"], 3)
            self.assertEqual(result["skipped"]["license"], 2)
            self.assertEqual(result["skipped"]["duplicate"], 0)
            records=[]
            for split in ("train","validation","test"):
                records += [json.loads(line) for line in (out/(split+".jsonl")).read_text().splitlines()]
            self.assertEqual(len(records),3)
            self.assertTrue(all(x["source_url"].startswith("https://") for x in records))
            self.assertTrue((out/"dataset_manifest.json").exists())
            manifest = json.loads((out/"dataset_manifest.json").read_text())
            self.assertIn("cc0metadata", manifest["metadata_cc0_prefixes"])
            split_counts = [sum(1 for line in (out/(split+".jsonl")).read_text().splitlines()) for split in ("train","validation","test")]
            self.assertEqual(sum(1 for count in split_counts if count), 1, "same source domain must not leak across splits")

if __name__ == "__main__":
    unittest.main()
