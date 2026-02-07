from __future__ import annotations

import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from modelwatch.cli import main


class CliTests(unittest.TestCase):
    def test_local_export_needs_no_network_and_is_deterministic(self) -> None:
        fixture = Path(__file__).parent / "fixtures" / "catalog.json"
        with tempfile.TemporaryDirectory() as directory:
            output = StringIO()
            with redirect_stdout(output):
                exit_code = main(
                    [
                        "export",
                        str(fixture),
                        "--out-dir",
                        directory,
                        "--generated-at",
                        "2026-01-01T00:00:00Z",
                    ]
                )
            exported = Path(directory) / "free-models-20260101T000000Z.json"
            payload = json.loads(exported.read_text(encoding="utf-8"))
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["count"], 1)
            self.assertEqual(payload["generated_at"], "2026-01-01T00:00:00Z")
            self.assertIn("Wrote 1 models", output.getvalue())


if __name__ == "__main__":
    unittest.main()
