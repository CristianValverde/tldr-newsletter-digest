from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from zoneinfo import ZoneInfo

from .models import RunManifest


def snapshot_cutoff_utc(target_date: dt.date, timezone_name: str, cutoff_hour: int) -> dt.datetime:
    local_dt = dt.datetime.combine(target_date, dt.time(hour=cutoff_hour), tzinfo=ZoneInfo(timezone_name))
    return local_dt.astimezone(dt.UTC)


def current_target_date(timezone_name: str) -> dt.date:
    return dt.datetime.now(ZoneInfo(timezone_name)).date()


def resolve_target_date(raw_value: str | None, timezone_name: str) -> dt.date:
    if not raw_value or raw_value == "today":
        return current_target_date(timezone_name)
    return dt.date.fromisoformat(raw_value)


def run_dir_for_date(output_root: Path, target_date: dt.date) -> Path:
    return output_root / target_date.isoformat()


def ensure_run_dir(output_root: Path, target_date: dt.date) -> Path:
    run_dir = run_dir_for_date(output_root, target_date)
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def manifest_path(run_dir: Path) -> Path:
    return run_dir / "run_manifest.json"


def default_manifest(target_date: dt.date, cutoff_at: dt.datetime, allowed_feeds: tuple[str, ...]) -> RunManifest:
    return RunManifest(
        target_date=target_date.isoformat(),
        cutoff_at=cutoff_at.astimezone(ZoneInfo("Europe/Madrid")).isoformat(),
        allowed_feeds=list(allowed_feeds),
    )


def load_manifest(run_dir: Path, target_date: dt.date, cutoff_at: dt.datetime, allowed_feeds: tuple[str, ...]) -> RunManifest:
    path = manifest_path(run_dir)
    if not path.exists():
        return default_manifest(target_date, cutoff_at, allowed_feeds)
    return RunManifest.from_dict(json.loads(path.read_text(encoding="utf-8")))


def save_manifest(run_dir: Path, manifest: RunManifest) -> None:
    manifest_path(run_dir).write_text(
        json.dumps(manifest.to_dict(), ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def write_json_file(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def should_send_email(manifest: RunManifest, sent_subject_present: bool) -> bool:
    if sent_subject_present:
        return False
    return manifest.email.state != "sent"


def should_send_telegram(manifest: RunManifest) -> bool:
    return manifest.email.state == "sent" and manifest.telegram.state != "sent"


def email_subject_for_date(target_date: str) -> str:
    return f"TLDR Digest - {target_date}"
