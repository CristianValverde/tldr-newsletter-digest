from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


@dataclass
class DigestSettings:
    allowed_feeds: tuple[str, ...]
    timezone_name: str
    cutoff_hour: int
    gmail_address: str | None
    gmail_app_password: str | None
    gmail_imap_host: str
    gmail_smtp_host: str
    gmail_smtp_port: int
    digest_to_email: str | None
    digest_from_email: str | None
    telegram_bot_token: str | None
    telegram_chat_id: str | None
    output_root: Path

    @classmethod
    def from_env(cls) -> "DigestSettings":
        repo_root = Path(__file__).resolve().parents[2]
        _load_dotenv(repo_root / ".env")
        output_root = Path(os.getenv("DIGEST_OUTPUT_ROOT", "output/runs"))
        if not output_root.is_absolute():
            output_root = repo_root / output_root
        feeds = tuple(
            part.strip()
            for part in os.getenv("TLDR_FEEDS", "TLDR,TLDR AI,TLDR Data,TLDR DevOps,TLDR IT").split(",")
            if part.strip()
        )
        return cls(
            allowed_feeds=feeds,
            timezone_name=os.getenv("DIGEST_TIMEZONE", "Europe/Madrid"),
            cutoff_hour=int(os.getenv("DIGEST_CUTOFF_HOUR", "17")),
            gmail_address=os.getenv("GMAIL_ADDRESS"),
            gmail_app_password=os.getenv("GMAIL_APP_PASSWORD"),
            gmail_imap_host=os.getenv("GMAIL_IMAP_HOST", "imap.gmail.com"),
            gmail_smtp_host=os.getenv("GMAIL_SMTP_HOST", "smtp.gmail.com"),
            gmail_smtp_port=int(os.getenv("GMAIL_SMTP_PORT", "587")),
            digest_to_email=os.getenv("DIGEST_TO_EMAIL"),
            digest_from_email=os.getenv("DIGEST_FROM_EMAIL") or os.getenv("GMAIL_ADDRESS"),
            telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN"),
            telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID"),
            output_root=output_root,
        )
