import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from bulk_download import _destination, download_dataset, _validate_url


class Response:
    def __init__(self, body=b"dataset bytes", status=200, headers=None):
        self.body = body
        self.status = status
        self.headers = headers or {"Content-Length": str(len(body)), "Content-Type": "application/octet-stream"}
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self, size=-1):
        body, self.body = self.body, b""
        return body


class Opener:
    def __init__(self, response): self.response = response
    def open(self, req, timeout=30): return self.response


class BulkDownloadTests(unittest.TestCase):
    def test_nonstandard_https_port_is_rejected(self):
        with self.assertRaises(ValueError):
            _validate_url("https://data.example.org:8443/dataset.bin")

    def test_destination_traversal_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            home = Path(td) / ".visual"
            with self.assertRaises(ValueError):
                _destination(str(home / ".." / "escape.bin"), home)

    def test_missing_home_is_created_for_safe_destination(self):
        with tempfile.TemporaryDirectory() as td:
            home = Path(td) / ".visual"
            dest = _destination(str(home / "datasets" / "sample.bin"), home)
            self.assertEqual(dest, home / "datasets" / "sample.bin")
            self.assertTrue(dest.parent.is_dir())

    def test_download_checks_sha_and_writes_provenance(self):
        with tempfile.TemporaryDirectory() as td:
            home = Path(td) / ".visual"
            body = b"verified public dataset payload"
            response = Response(body)
            with patch("bulk_download._validate_url", return_value=("https://data.example.org/file.bin", "data.example.org")), \
                 patch("bulk_download.urllib.request.build_opener", return_value=Opener(response)):
                result = download_dataset(
                    "https://data.example.org/file.bin",
                    str(home / "datasets" / "file.bin"),
                    expected_sha256=hashlib.sha256(body).hexdigest(),
                    home=home,
                )
            target = home / "datasets" / "file.bin"
            self.assertEqual(result["status"], "downloaded")
            self.assertEqual(target.read_bytes(), body)
            self.assertTrue(target.with_name("file.bin.download.json").is_file())

    def test_resume_rejects_invalid_content_range_total(self):
        with tempfile.TemporaryDirectory() as td:
            home = Path(td) / ".visual"
            dest = home / "datasets" / "partial.bin"
            dest.parent.mkdir(parents=True)
            dest.with_name("partial.bin.part").write_bytes(b"abc")
            response = Response(b"def", status=206, headers={
                "Content-Length": "3", "Content-Range": "bytes 3-5/*",
                "Content-Type": "application/octet-stream",
            })
            with patch("bulk_download._validate_url", return_value=("https://data.example.org/file.bin", "data.example.org")), \
                 patch("bulk_download.urllib.request.build_opener", return_value=Opener(response)):
                with self.assertRaises(ValueError):
                    download_dataset("https://data.example.org/file.bin", str(dest), home=home)
            self.assertEqual(dest.with_name("partial.bin.part").read_bytes(), b"abc")


if __name__ == "__main__":
    unittest.main()
