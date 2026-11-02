import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tldr_digest.config import DigestSettings


class ConfigTests(unittest.TestCase):
    def test_from_env_loads_repo_dotenv(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            dotenv_path = repo_root / ".env"
            dotenv_path.write_text(
                "\n".join(
                    [
                        "GMAIL_ADDRESS=test@example.com",
                        "GMAIL_APP_PASSWORD=secret",
                        "DIGEST_TO_EMAIL=dest@example.com",
                        "DIGEST_FROM_EMAIL=from@example.com",
                        "TELEGRAM_BOT_TOKEN=bot-token",
                        "TELEGRAM_CHAT_ID=12345",
                    ]
                ),
                encoding="utf-8",
            )

            with patch.dict(os.environ, {}, clear=True):
                with patch("tldr_digest.config.Path.resolve", return_value=repo_root / "src" / "tldr_digest" / "config.py"):
                    settings = DigestSettings.from_env()

            self.assertEqual(settings.gmail_address, "test@example.com")
            self.assertEqual(settings.gmail_app_password, "secret")
            self.assertEqual(settings.digest_to_email, "dest@example.com")
            self.assertEqual(settings.digest_from_email, "from@example.com")
            self.assertEqual(settings.telegram_bot_token, "bot-token")
            self.assertEqual(settings.telegram_chat_id, "12345")
            self.assertEqual(settings.output_root, repo_root / "output" / "runs")


if __name__ == "__main__":
    unittest.main()
