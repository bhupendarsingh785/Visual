import json
import re
import unittest
from pathlib import Path


class ResearchSourceRegistryTests(unittest.TestCase):
    def test_registry_is_valid_and_has_unique_sources(self):
        root = Path(__file__).parent
        registry = json.loads(
            (root / "research_sources_registry.json").read_text(encoding="utf-8")
        )
        self.assertEqual(registry["registry_version"], 1)
        sources = registry["sources"]
        self.assertGreaterEqual(len(sources), 15)
        ids = [item["id"] for item in sources]
        self.assertEqual(len(ids), len(set(ids)))

    def test_all_registry_domains_exist_in_research_map(self):
        root = Path(__file__).parent
        registry = json.loads(
            (root / "research_sources_registry.json").read_text(encoding="utf-8")
        )
        code = (root / "global_research.py").read_text(encoding="utf-8")
        block = code.split("DOMAIN_QUERIES = {", 1)[1].split("\n}", 1)[0]
        known = set(re.findall(r'^\s*"([a-z0-9_]+)":', block, re.MULTILINE))
        self.assertGreaterEqual(len(known), 100)
        for source in registry["sources"]:
            self.assertTrue(source.get("entry_url", "").startswith("https://"))
            self.assertTrue(source.get("license_policy"))
            self.assertTrue(source.get("collection_status"))
            for domain in source.get("domains", []):
                self.assertIn(domain, known, f"{source['id']} references unknown domain {domain}")

    def test_registry_requires_item_level_rights_and_provenance(self):
        root = Path(__file__).parent
        registry = json.loads(
            (root / "research_sources_registry.json").read_text(encoding="utf-8")
        )
        policy = registry["collection_policy"]
        self.assertTrue(policy["download_requires_item_level_review"])
        self.assertTrue(policy["store_source_url_and_accessed_at"])
        self.assertTrue(policy["store_license_text_and_attribution"])
        self.assertTrue(policy["store_checksum_and_byte_size"])
        self.assertGreaterEqual(len(registry["quality_gates"]), 10)


if __name__ == "__main__":
    unittest.main()
