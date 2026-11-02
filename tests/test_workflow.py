import datetime as dt
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tldr_digest.models import DeliveryStatus, RunManifest
from tldr_digest.workflow import email_subject_for_date, should_send_email, should_send_telegram, snapshot_cutoff_utc


class WorkflowTests(unittest.TestCase):
    def test_snapshot_cutoff_utc_uses_madrid_timezone(self) -> None:
        cutoff = snapshot_cutoff_utc(dt.date(2026, 6, 12), "Europe/Madrid", 17)

        self.assertEqual(cutoff, dt.datetime(2026, 6, 12, 15, 0, tzinfo=dt.UTC))

    def test_idempotency_blocks_duplicate_email_but_allows_pending_telegram(self) -> None:
        manifest = RunManifest(
            target_date="2026-06-12",
            cutoff_at="2026-06-12T17:00:00+02:00",
            allowed_feeds=["TLDR", "TLDR AI"],
            source_messages=[],
            snapshot_status="complete",
            digest_status="ready",
            email=DeliveryStatus(state="sent", attempted_at="2026-06-12T17:05:00+02:00"),
            telegram=DeliveryStatus(state="pending", attempted_at=None),
        )

        self.assertFalse(should_send_email(manifest, sent_subject_present=False))
        self.assertTrue(should_send_telegram(manifest))

    def test_sent_mailbox_guard_blocks_duplicate_email(self) -> None:
        manifest = RunManifest(
            target_date="2026-06-12",
            cutoff_at="2026-06-12T17:00:00+02:00",
            allowed_feeds=["TLDR"],
            source_messages=[],
            snapshot_status="complete",
            digest_status="ready",
            email=DeliveryStatus(state="pending", attempted_at=None),
            telegram=DeliveryStatus(state="pending", attempted_at=None),
        )

        self.assertFalse(should_send_email(manifest, sent_subject_present=True))

    def test_email_subject_is_ascii_safe(self) -> None:
        self.assertEqual(email_subject_for_date("2026-06-12"), "TLDR Digest - 2026-06-12")


if __name__ == "__main__":
    unittest.main()
