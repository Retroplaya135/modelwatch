from __future__ import annotations

import unittest

from modelwatch.cleaner import clean_text, parse_entry


class CleanerTests(unittest.TestCase):
    def test_parses_supported_entry(self) -> None:
        entry = parse_entry("Example: Alpha (free) 32K tokens Text (#1) A useful model.")
        self.assertEqual(entry[0], "Example: Alpha")
        self.assertEqual(entry[1], "32K tokens")
        self.assertEqual(entry[3], ["Text (#1)"])

    def test_cleans_bullets_and_preserves_truncated_text(self) -> None:
        result = clean_text("* Example: Alpha (free) 32K tokens Text (#1) Truncated…")
        self.assertIn("Truncated…", result)
        self.assertNotIn("\ufffc", result)

    def test_empty_input_is_stable(self) -> None:
        self.assertEqual(clean_text(""), "## Zero-priced model catalog\n\n\n")


if __name__ == "__main__":
    unittest.main()
