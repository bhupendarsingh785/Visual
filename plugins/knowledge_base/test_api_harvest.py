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

    @patch("api_harvest.ingest_source", return_value={"status":"indexed","characters":500,"duplicate":False})
    @patch("api_harvest.add_source", return_value={"source_id":"src_topic","status":"queued"})
    def test_explicit_research_domain_is_stored(self, add, ingest):
        harvest_public_metadata("openalex", "neural networks", 10, "/tmp/visual-test", topic="deep_learning")
        self.assertEqual(add.call_args.args[2], "deep_learning")
    @patch("api_harvest.time.sleep")
    @patch("api_harvest.ingest_source")
    @patch("api_harvest.add_source", return_value={"source_id":"src_retry","status":"queued"})
    def test_rate_limit_response_is_retried(self, add, ingest, sleep):
        import urllib.error
        ingest.side_effect = [urllib.error.HTTPError("https://api.example.org", 429, "Too Many Requests", {}, None),
                              {"status":"indexed","characters":700,"duplicate":False}]
        result = harvest_public_metadata("openalex", "neural networks", 10, "/tmp/visual-test")
        self.assertEqual(result["status"], "indexed")
        self.assertEqual(ingest.call_count, 2)
        self.assertGreaterEqual(sleep.call_count, 2)
        self.assertEqual(sleep.call_args_list[-1].args[0], 2.0)
    @patch("api_harvest.ingest_source", return_value={"status": "indexed", "characters": 1200, "duplicate": True})
    @patch("api_harvest.add_source", return_value={"source_id": "src_duplicate", "status": "queued"})
    def test_duplicate_content_is_not_counted_as_new_indexed_characters(self, add, ingest):
        result = harvest_public_metadata("openalex", "duplicate metadata", 10, "/tmp/visual-test")
        self.assertEqual(result["indexed_characters"], 0)
        self.assertEqual(result["fetched_characters"], 1200)
        self.assertTrue(result["duplicate"])

    def test_open_media_and_archive_query_shapes(self):
        from api_harvest import PROVIDERS
        images = PROVIDERS["openverse_images"]["build"]("forest wildlife", 25)
        audio = PROVIDERS["openverse_audio"]["build"]("wolf howling", 25)
        commons = PROVIDERS["wikimedia_commons"]["build"]("ancient architecture", 25)
        archive = PROVIDERS["internet_archive"]["build"]("ancient manuscripts", 25)
        self.assertEqual(images["page_size"], 20)
        self.assertEqual(audio["page_size"], 20)
        self.assertEqual(commons["gsrlimit"], 25)
        self.assertIn("extmetadata", commons["iiprop"])
        self.assertEqual(archive["rows"], 25)
        self.assertIn("licenseurl", archive["fl[]"])

    def test_unknown_provider_is_rejected(self):
        with self.assertRaises(ValueError):
            harvest_public_metadata("unknown", "test")

    def test_gbif_and_nasa_providers_are_allowlisted(self):
        from api_harvest import PROVIDERS
        self.assertIn("gbif", PROVIDERS)
        self.assertIn("nasa_cmr", PROVIDERS)
        for provider in ("huggingface", "pubmed", "stackoverflow", "arxiv", "europe_pmc", "wikidata"):
            self.assertIn(provider, PROVIDERS)

    def test_global_research_rotates_all_allowlisted_api_providers(self):
        from global_research import PROVIDERS
        self.assertIn("europe_pmc", PROVIDERS)
        self.assertIn("wikidata", PROVIDERS)
        self.assertEqual(len(PROVIDERS), 15)

    def test_open_media_and_archive_connectors_are_allowlisted(self):
        from api_harvest import PROVIDERS
        for provider in ("openverse_images", "openverse_audio", "wikimedia_commons", "internet_archive"):
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
