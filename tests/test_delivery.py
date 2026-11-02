import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tldr_digest.delivery import split_telegram_messages


class DeliveryTests(unittest.TestCase):
    def test_split_telegram_messages_splits_long_single_block(self) -> None:
        text = "Header\n" + ("A" * 3600) + "\nFooter"

        chunks = split_telegram_messages(text, limit=3500)

        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(chunk) <= 3500 for chunk in chunks))


if __name__ == "__main__":
    unittest.main()
