import unittest
from unittest.mock import patch
from api_harvest import harvest_public_metadata

class PublicMetadataHarvesterTests(unittest.TestCase):
    @patch("api_harvest.ingest_source", return_value={"status":"indexed","characters":900,"duplicate":False})
    @patch("api_harvest.add_source", return_value={"source_id":"src_test","status":"queued"})
    def test_openalex_search_is_bounded_and_indexed(self, add, ingest):
        result = harvest_public_metadata("openalex", "climate adaptation", 999, "/tmp/visual-test")
        self.assertEqual(result["status"], "indexed")
        self.assertEqual(result["requested_records_max"], 25)
        self.assertIn("per-page=25", result["url"])
        self.assertIn("climate+adaptation", result["url"])
        add.assert_called_once()
        ingest.assert_called_once_with("src_test", "/tmp/visual-test", respect_robots=False)

    def test_unknown_provider_is_rejected(self):
        with self.assertRaises(ValueError):
            harvest_public_metadata("unknown", "test")

    def test_gbif_and_nasa_providers_are_allowlisted(self):
        from api_harvest import PROVIDERS
        self.assertIn("gbif", PROVIDERS)
        self.assertIn("nasa_cmr", PROVIDERS)
        for provider in ("huggingface", "pubmed", "stackoverflow", "arxiv", "europe_pmc", "wikidata"):
            self.assertIn(provider, PROVIDERS)

    def test_animal_and_veterinary_topics_are_available(self):
        from global_research import DOMAIN_QUERIES
        self.assertIn("animals_wildlife", DOMAIN_QUERIES)
        self.assertIn("veterinary", DOMAIN_QUERIES)

    def test_empty_query_is_rejected(self):
        with self.assertRaises(ValueError):
            harvest_public_metadata("zenodo", " ")

if __name__ == "__main__":
    unittest.main()
