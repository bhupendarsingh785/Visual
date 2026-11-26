import json
import unittest
from pathlib import Path


class DatasetCatalogTests(unittest.TestCase):
    def test_catalog_has_complete_rights_metadata_and_safe_defaults(self):
        path = Path(__file__).with_name("datasets_catalog.json")
        catalog = json.loads(path.read_text(encoding="utf-8"))
        entries = catalog["datasets"]
        self.assertEqual(catalog["catalog_version"], 6)
        self.assertEqual(len(entries), 152)
        self.assertEqual(sum(bool(item.get("metadata_enabled")) for item in entries), 15)
        self.assertEqual(sum(item.get("enabled") is True for item in entries), 0)
        names = [item["name"] for item in entries]
        self.assertEqual(len(names), len(set(names)))
        required = ("name", "topic", "url", "access", "license", "size_class", "coverage", "enabled")
        for item in entries:
            for key in required:
                self.assertTrue(item.get(key), f"{item.get('name', '<unnamed>')} missing {key}")
            self.assertTrue(item["url"].startswith("https://"), item["name"])


if __name__ == "__main__":
    unittest.main()
