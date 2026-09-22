from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.validate_profile import (
    extract_link_targets,
    run_all,
    validate_language_parity,
    validate_local_links,
    validate_registered_links,
    validate_text_hygiene,
)


class ProfileValidationTests(unittest.TestCase):
    def test_profile_is_valid(self) -> None:
        self.assertEqual(run_all(), [])

    def test_language_parity(self) -> None:
        self.assertEqual(validate_language_parity(), [])

    def test_registered_links(self) -> None:
        self.assertEqual(validate_registered_links(), [])

    def test_local_links(self) -> None:
        self.assertEqual(validate_local_links(), [])

    def test_text_hygiene(self) -> None:
        self.assertEqual(validate_text_hygiene(), [])

    def test_badge_link_parsing(self) -> None:
        text = (
            "[![LinkedIn](https://img.shields.io/badge/LinkedIn-profile-blue)]"
            "(https://example.com/profile)"
        )
        self.assertEqual(
            extract_link_targets(text),
            ["https://example.com/profile"],
        )


if __name__ == "__main__":
    unittest.main()
