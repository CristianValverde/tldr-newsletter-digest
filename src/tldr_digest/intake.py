from __future__ import annotations

import datetime as dt
import email
import email.header
import email.utils
import imaplib
import re
from email.message import Message
from html import unescape
from typing import Iterable
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup, FeatureNotFound

from .config import DigestSettings
from .extraction import canonicalize_tracking_url
from .models import EmailEnvelope, SnapshotSource
from .workflow import snapshot_cutoff_utc

# Gmail IMAP host and capabilities confirmed via live capability probe on 2026-06-13.
# Gmail SMTP host and EHLO features confirmed via live capability probe on 2026-06-13.
# Telegram public endpoint shape confirmed on 2026-06-13; live bot validation still requires a token.

VIEW_ONLINE_RE = re.compile(r"\[View Online\]\((https?://[^)\s]+)\)", re.I)
TEXT_REFERENCE_VIEW_ONLINE_RE = re.compile(r"View Online\s*\[(\d+)\]", re.I)
TEXT_REFERENCE_LINK_RE = re.compile(r"^\[(\d+)\]:\s*(https?://\S+)$", re.I | re.M)
SINCE_FORMAT = "%d-%b-%Y"


def _decode_header(value: str) -> str:
    parts = email.header.decode_header(value or "")
    decoded: list[str] = []
    for raw, charset in parts:
        if isinstance(raw, bytes):
            decoded.append(raw.decode(charset or "utf-8", errors="ignore"))
        else:
            decoded.append(raw)
    return "".join(decoded).strip()


def _message_body_text(message: Message) -> str:
    if message.is_multipart():
        parts: list[str] = []
        for part in message.walk():
            if part.get_content_maintype() == "multipart":
                continue
            if part.get("Content-Disposition", "").lower().startswith("attachment"):
                continue
            payload = part.get_payload(decode=True)
            if payload is None:
                continue
            charset = part.get_content_charset() or "utf-8"
            parts.append(payload.decode(charset, errors="ignore"))
        return "\n".join(parts)

    payload = message.get_payload(decode=True)
    if payload is None:
        return ""
    charset = message.get_content_charset() or "utf-8"
    return payload.decode(charset, errors="ignore")


def parse_view_online_url(body: str) -> str | None:
    candidates: list[str] = []

    markdown_match = VIEW_ONLINE_RE.search(body)
    if markdown_match:
        candidates.append(markdown_match.group(1))

    try:
        soup = BeautifulSoup(body, "lxml")
    except FeatureNotFound:
        soup = BeautifulSoup(body, "html.parser")
    for anchor in soup.find_all("a", href=True):
        if "view online" in anchor.get_text(" ", strip=True).lower():
            candidates.append(anchor["href"])

    reference_match = TEXT_REFERENCE_VIEW_ONLINE_RE.search(body)
    if reference_match:
        reference_id = reference_match.group(1)
        for candidate in TEXT_REFERENCE_LINK_RE.finditer(body):
            if candidate.group(1) == reference_id:
                candidates.append(candidate.group(2))

    if not candidates:
        return None

    canonical_candidates = [canonicalize_tracking_url(unescape(candidate)) for candidate in candidates]
    canonical_candidates.sort(
        key=lambda candidate: (
            "web-version" not in candidate,
            "a.tldrnewsletter.com" not in candidate,
            "tldr.tech" in candidate,
            len(candidate),
        )
    )
    return canonical_candidates[0]


def infer_feed_name(from_header: str) -> str | None:
    decoded = _decode_header(from_header)
    tokens = decoded.split()
    if not tokens or tokens[0].upper() != "TLDR":
        return None

    feed_tokens = ["TLDR"]
    for token in tokens[1:]:
        if "@" in token:
            break
        if not re.fullmatch(r"[A-Za-z]+", token):
            break
        feed_tokens.append(token)

    return " ".join(feed_tokens).strip()


def fetch_recent_gmail_envelopes(settings: DigestSettings, lookback_days: int = 3) -> list[EmailEnvelope]:
    if not settings.gmail_address or not settings.gmail_app_password:
        raise ValueError("Gmail credentials are required for IMAP intake.")

    since_date = (dt.datetime.now(dt.UTC) - dt.timedelta(days=lookback_days)).strftime(SINCE_FORMAT)
    envelopes: list[EmailEnvelope] = []

    client = imaplib.IMAP4_SSL(settings.gmail_imap_host, 993)
    try:
        client.login(settings.gmail_address, settings.gmail_app_password)
        client.select("INBOX")
        status, message_ids = client.search(None, "SINCE", since_date, "FROM", '"dan@tldrnewsletter.com"')
        if status != "OK":
            return []

        for raw_id in message_ids[0].split():
            fetch_status, data = client.fetch(raw_id, "(RFC822)")
            if fetch_status != "OK" or not data or not data[0]:
                continue
            message = email.message_from_bytes(data[0][1])
            received_at = email.utils.parsedate_to_datetime(message.get("Date"))
            if received_at is None:
                continue
            if received_at.tzinfo is None:
                received_at = received_at.replace(tzinfo=dt.UTC)
            envelopes.append(
                EmailEnvelope(
                    message_id=raw_id.decode("utf-8"),
                    from_header=_decode_header(message.get("From", "")),
                    subject=_decode_header(message.get("Subject", "")),
                    received_at=received_at.astimezone(dt.UTC),
                    body=_message_body_text(message),
                )
            )
    finally:
        try:
            client.logout()
        except Exception:
            pass

    return envelopes


def collect_snapshot_sources(
    messages: Iterable[EmailEnvelope],
    target_date: dt.date,
    timezone_name: str,
    cutoff_hour: int,
    allowed_feeds: set[str],
) -> list[SnapshotSource]:
    cutoff_utc = snapshot_cutoff_utc(target_date, timezone_name, cutoff_hour)
    timezone = ZoneInfo(timezone_name)
    latest_by_feed: dict[str, SnapshotSource] = {}

    for message in messages:
        feed_name = infer_feed_name(message.from_header)
        if not feed_name or feed_name not in allowed_feeds:
            continue
        if message.received_at > cutoff_utc:
            continue
        if message.received_at.astimezone(timezone).date() != target_date:
            continue
        view_online_url = parse_view_online_url(message.body)
        if not view_online_url:
            continue
        source = SnapshotSource(
            message_id=message.message_id,
            feed_name=feed_name,
            subject=message.subject,
            received_at=message.received_at.isoformat(),
            view_online_url=view_online_url,
        )
        current = latest_by_feed.get(feed_name)
        if current is None or source.received_at > current.received_at:
            latest_by_feed[feed_name] = source

    return sorted(latest_by_feed.values(), key=lambda source: (source.received_at, source.feed_name))


def sent_subject_exists(settings: DigestSettings, subject: str) -> bool:
    if not settings.gmail_address or not settings.gmail_app_password:
        return False

    client = imaplib.IMAP4_SSL(settings.gmail_imap_host, 993)
    mailboxes = ['"[Gmail]/Sent Mail"', '"[Google Mail]/Sent Mail"', '"Sent Mail"']
    try:
        client.login(settings.gmail_address, settings.gmail_app_password)
        for mailbox in mailboxes:
            status, _ = client.select(mailbox)
            if status != "OK":
                continue
            search_status, results = client.search(None, "HEADER", "Subject", f'"{subject}"')
            if search_status == "OK" and results and results[0].strip():
                return True
    finally:
        try:
            client.logout()
        except Exception:
            pass

    return False
