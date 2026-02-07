from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from email.message import Message
from pathlib import Path

from modelwatch.catalog import CatalogError, fetch_catalog, free_models, is_free, render_markdown, write_export


class FakeResponse:
    def __init__(self, body: bytes, *, status: int = 200, content_type: str = "application/json") -> None:
        self._body = body
        self.status = status
        self.headers = Message()
        self.headers["Content-Type"] = content_type

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def getcode(self) -> int:
        return self.status

    def read(self, limit: int) -> bytes:
        return self._body[:limit]


class CatalogTests(unittest.TestCase):
    def test_recognizes_equivalent_zero_prices(self) -> None:
        for zero in (0, 0.0, "0", "0.00", "0e-8"):
            with self.subTest(zero=zero):
                self.assertTrue(is_free({"id": "example/model", "pricing": {"prompt": zero, "completion": zero}}))
        self.assertFalse(is_free({"id": "example/model", "pricing": {"prompt": "invalid", "completion": "0"}}))
        self.assertFalse(is_free({"id": "example/model", "pricing": {}}))

    def test_fetch_validates_response_contract(self) -> None:
        fixture = Path(__file__).parent / "fixtures" / "catalog.json"
        body = fixture.read_bytes()
        result = fetch_catalog(opener=lambda request, timeout: FakeResponse(body))
        self.assertEqual(len(result), 2)
        with self.assertRaises(CatalogError):
            fetch_catalog(opener=lambda request, timeout: FakeResponse(b"not json", content_type="text/html"))
        with self.assertRaises(CatalogError):
            fetch_catalog(opener=lambda request, timeout: FakeResponse(b"{}"))

    def test_export_is_deterministic_and_escapes_markdown(self) -> None:
        fixture = json.loads((Path(__file__).parent / "fixtures" / "catalog.json").read_text())
        models = free_models(fixture["data"])
        rendered = render_markdown(models, "2026-01-01T00:00:00Z")
        self.assertIn("Alpha \\| Preview", rendered)
        with tempfile.TemporaryDirectory() as directory:
            json_path, markdown_path = write_export(
                models,
                Path(directory),
                now=datetime(2026, 1, 1, tzinfo=timezone.utc),
            )
            self.assertEqual(json_path.name, "free-models-20260101T000000Z.json")
            self.assertTrue(markdown_path.is_file())


if __name__ == "__main__":
    unittest.main()
