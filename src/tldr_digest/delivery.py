from __future__ import annotations

import smtplib
from email.message import EmailMessage

import requests

from .config import DigestSettings


def send_email(
    settings: DigestSettings,
    subject: str,
    html_body: str,
    text_body: str,
) -> None:
    if not settings.gmail_address or not settings.gmail_app_password:
        raise ValueError("Gmail SMTP credentials are not configured.")
    if not settings.digest_to_email or not settings.digest_from_email:
        raise ValueError("Digest email recipients are not configured.")

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.digest_from_email
    message["To"] = settings.digest_to_email
    message.set_content(text_body)
    message.add_alternative(html_body, subtype="html")

    with smtplib.SMTP(settings.gmail_smtp_host, settings.gmail_smtp_port, timeout=30) as client:
        client.ehlo()
        client.starttls()
        client.ehlo()
        client.login(settings.gmail_address, settings.gmail_app_password)
        client.send_message(message)


def split_telegram_messages(text: str, limit: int = 3500) -> list[str]:
    if len(text) <= limit:
        return [text]

    chunks: list[str] = []
    current = ""
    for paragraph in text.split("\n\n"):
        if len(paragraph) > limit:
            lines = paragraph.splitlines()
            for line in lines:
                if len(line) > limit:
                    if current:
                        chunks.append(current)
                        current = ""
                    for start in range(0, len(line), limit):
                        chunks.append(line[start : start + limit])
                    continue

                candidate = line if not current else f"{current}\n{line}"
                if len(candidate) <= limit:
                    current = candidate
                    continue
                if current:
                    chunks.append(current)
                current = line
            continue

        candidate = paragraph if not current else f"{current}\n\n{paragraph}"
        if len(candidate) <= limit:
            current = candidate
            continue
        if current:
            chunks.append(current)
        current = paragraph
    if current:
        chunks.append(current)
    return chunks


def send_telegram_text(settings: DigestSettings, text: str) -> None:
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        raise ValueError("Telegram bot credentials are not configured.")

    endpoint = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    for chunk in split_telegram_messages(text):
        response = requests.post(
            endpoint,
            json={
                "chat_id": settings.telegram_chat_id,
                "text": chunk,
                "disable_web_page_preview": True,
            },
            timeout=30,
        )
        response.raise_for_status()
