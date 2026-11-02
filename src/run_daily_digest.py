#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from zoneinfo import ZoneInfo

from tldr_digest.config import DigestSettings
from tldr_digest.delivery import send_email, send_telegram_text
from tldr_digest.extraction import extract_from_urls
from tldr_digest.intake import collect_snapshot_sources, fetch_recent_gmail_envelopes, sent_subject_exists
from tldr_digest.models import DeliveryStatus, DigestArtifact
from tldr_digest.renderers import render_email_html, render_email_text, render_telegram_text
from tldr_digest.workflow import (
    email_subject_for_date,
    ensure_run_dir,
    load_manifest,
    resolve_target_date,
    run_dir_for_date,
    save_manifest,
    should_send_email,
    should_send_telegram,
    snapshot_cutoff_utc,
    write_json_file,
)


LOGGER = logging.getLogger("daily_digest")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the daily TLDR digest pipeline.")
    parser.add_argument("command", choices=["snapshot", "finalize"])
    parser.add_argument("--date", default="today", help="Target date in YYYY-MM-DD format or 'today'.")
    parser.add_argument("--skip-delivery", action="store_true", help="Render outputs but skip email and Telegram delivery.")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    return parser.parse_args()


def snapshot_command(settings: DigestSettings, raw_date: str) -> Path:
    target_date = resolve_target_date(raw_date, settings.timezone_name)
    cutoff_utc = snapshot_cutoff_utc(target_date, settings.timezone_name, settings.cutoff_hour)
    run_dir = ensure_run_dir(settings.output_root, target_date)
    manifest = load_manifest(run_dir, target_date, cutoff_utc, settings.allowed_feeds)
    manifest.target_date = target_date.isoformat()
    manifest.cutoff_at = cutoff_utc.astimezone(ZoneInfo(settings.timezone_name)).isoformat()
    manifest.allowed_feeds = list(settings.allowed_feeds)

    messages = fetch_recent_gmail_envelopes(settings)
    sources = collect_snapshot_sources(
        messages=messages,
        target_date=target_date,
        timezone_name=settings.timezone_name,
        cutoff_hour=settings.cutoff_hour,
        allowed_feeds=set(settings.allowed_feeds),
    )
    write_json_file(run_dir / "source_messages.json", [source.to_dict() for source in sources])
    manifest.source_messages = [source.to_dict() for source in sources]

    if not sources:
        manifest.snapshot_status = "no_input"
        save_manifest(run_dir, manifest)
        LOGGER.info("No eligible TLDR-family emails arrived before cutoff for %s", target_date.isoformat())
        return run_dir

    newsletters, output = extract_from_urls([source.view_online_url for source in sources])
    write_json_file(run_dir / "articles.json", output)
    manifest.snapshot_status = "complete"
    manifest.digest_status = "pending"
    if newsletters:
        write_json_file(
            run_dir / "newsletter_sources.json",
            [{"source": newsletter.source, "date": newsletter.date} for newsletter in newsletters],
        )
    save_manifest(run_dir, manifest)
    LOGGER.info("Snapshot written to %s", run_dir)
    return run_dir


def finalize_command(settings: DigestSettings, raw_date: str, skip_delivery: bool) -> Path:
    target_date = resolve_target_date(raw_date, settings.timezone_name)
    cutoff_utc = snapshot_cutoff_utc(target_date, settings.timezone_name, settings.cutoff_hour)
    run_dir = run_dir_for_date(settings.output_root, target_date)
    if not run_dir.exists():
        raise FileNotFoundError(f"Run directory does not exist: {run_dir}")

    manifest = load_manifest(run_dir, target_date, cutoff_utc, settings.allowed_feeds)
    digest_path = run_dir / "digest.json"
    if not digest_path.exists():
        raise FileNotFoundError(f"digest.json is missing in {run_dir}")

    artifact = DigestArtifact.from_dict(json.loads(digest_path.read_text(encoding="utf-8")))
    subject = email_subject_for_date(artifact.target_date)
    html_body = render_email_html(artifact, subject)
    text_body = render_email_text(artifact, subject)
    telegram_text = render_telegram_text(artifact)

    (run_dir / "email.html").write_text(html_body, encoding="utf-8")
    (run_dir / "email.txt").write_text(text_body, encoding="utf-8")
    (run_dir / "telegram.txt").write_text(telegram_text, encoding="utf-8")
    manifest.digest_status = "ready"

    if not skip_delivery:
        email_guard = sent_subject_exists(settings, subject)
        if email_guard:
            manifest.email = DeliveryStatus(state="sent", attempted_at=None, detail="Found matching subject in Sent Mail.")
        elif should_send_email(manifest, sent_subject_present=False):
            send_email(settings, subject, html_body, text_body)
            manifest.email = DeliveryStatus(state="sent", attempted_at=cutoff_utc.isoformat())
        save_manifest(run_dir, manifest)

        if should_send_telegram(manifest):
            try:
                send_telegram_text(settings, telegram_text)
                manifest.telegram = DeliveryStatus(state="sent", attempted_at=cutoff_utc.isoformat())
            except Exception as exc:
                manifest.telegram = DeliveryStatus(
                    state="pending",
                    attempted_at=cutoff_utc.isoformat(),
                    detail=str(exc),
                )
                save_manifest(run_dir, manifest)
                raise

    save_manifest(run_dir, manifest)
    LOGGER.info("Finalize complete for %s", target_date.isoformat())
    return run_dir


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=getattr(logging, args.log_level), format="%(levelname)s %(message)s")
    settings = DigestSettings.from_env()

    if args.command == "snapshot":
        run_dir = snapshot_command(settings, args.date)
    else:
        run_dir = finalize_command(settings, args.date, args.skip_delivery)

    print(run_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
