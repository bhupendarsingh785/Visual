import hashlib
import tempfile
import unittest
from pathlib import Path
from dataset_manifest import build_dataset_manifest, write_dataset_manifest


class DatasetManifestTests(unittest.TestCase):
    def test_hash_and_license_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "data"
            root.mkdir()
            payload = b"example training row\n"
            (root / "train.txt").write_bytes(payload)
            manifest = build_dataset_manifest(
                root, source="user-provided local corpus", license_name="unknown"
            )
            self.assertEqual(manifest["files"][0]["sha256"], hashlib.sha256(payload).hexdigest())
            self.assertFalse(manifest["training_eligible"])
            self.assertEqual(manifest["quarantine_reason"], "license_unverified")

    def test_verified_dataset_is_eligible(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "data"
            root.mkdir()
            (root / "data.jsonl").write_text('{"x":1}\n', encoding="utf-8")
            manifest = build_dataset_manifest(
                root, source="approved source", license_name="CC-BY-4.0"
            )
            self.assertTrue(manifest["training_eligible"])

    def test_manifest_cannot_be_written_inside_dataset(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "data"
            root.mkdir()
            manifest = build_dataset_manifest(root, source="local", license_name="MIT")
            with self.assertRaises(ValueError):
                write_dataset_manifest(manifest, root / "manifest.json")


if __name__ == "__main__":
    unittest.main()
