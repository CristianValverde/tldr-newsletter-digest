import datetime as dt
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tldr_digest.intake import EmailEnvelope, collect_snapshot_sources, parse_view_online_url


class IntakeTests(unittest.TestCase):
    def test_parse_view_online_url_from_tldr_body(self) -> None:
        body = """
|[Advertise](https://tracking.tldrnewsletter.com/...)|[View Online](https://tracking.tldrnewsletter.com/CL0/https:%2F%2Fa.tldrnewsletter.com%2Fweb-version%3Fep=1%26lc=abc/1/xyz)
"""

        url = parse_view_online_url(body)

        self.assertEqual(
            url,
            "https://a.tldrnewsletter.com/web-version?ep=1&lc=abc",
        )

    def test_parse_view_online_url_from_html_anchor_with_nested_span(self) -> None:
        body = """
<a href="https://tracking.tldrnewsletter.com/CL0/https:%2F%2Fa.tldrnewsletter.com%2Fweb-version%3Fep=1%26lc=html/1/xyz"><span>View Online</span></a>
"""

        url = parse_view_online_url(body)

        self.assertEqual(
            url,
            "https://a.tldrnewsletter.com/web-version?ep=1&lc=html",
        )

    def test_parse_view_online_url_from_text_reference_format(self) -> None:
        body = """
View Online [3]

[3]: https://tracking.tldrnewsletter.com/CL0/https:%2F%2Fa.tldrnewsletter.com%2Fweb-version%3Fep=1%26lc=ref/1/xyz
"""

        url = parse_view_online_url(body)

        self.assertEqual(
            url,
            "https://a.tldrnewsletter.com/web-version?ep=1&lc=ref",
        )

    def test_parse_view_online_url_prefers_web_version_over_generic_tldr_page(self) -> None:
        body = """
<a href="https://tracking.tldrnewsletter.com/CL0/https:%2F%2Ftldr.tech%2Fai%3Futm_source=tldrai/1/xyz"><span>View Online</span></a>
View Online [3]

[3]: https://tracking.tldrnewsletter.com/CL0/https:%2F%2Fa.tldrnewsletter.com%2Fweb-version%3Fep=1%26lc=best/1/xyz
"""

        url = parse_view_online_url(body)

        self.assertEqual(
            url,
            "https://a.tldrnewsletter.com/web-version?ep=1&lc=best",
        )

    def test_parse_view_online_url_preserves_web_version_signature_params(self) -> None:
        body = """
<a href="https://tracking.tldrnewsletter.com/CL0/https:%2F%2Fa.tldrnewsletter.com%2Fweb-version%3Fep=1%26lc=signed%26p=abc%26pt=campaign%26t=123%26s=secret/1/xyz"><span>View Online</span></a>
"""

        url = parse_view_online_url(body)

        self.assertEqual(
            url,
            "https://a.tldrnewsletter.com/web-version?ep=1&lc=signed&p=abc&pt=campaign&t=123&s=secret",
        )

    def test_collect_snapshot_sources_uses_latest_allowed_feed_before_cutoff(self) -> None:
        messages = [
            EmailEnvelope(
                message_id="old-general",
                from_header="TLDR dan@tldrnewsletter.com",
                subject="Earlier TLDR",
                received_at=dt.datetime(2026, 6, 12, 9, 0, tzinfo=dt.UTC),
                body="[View Online](https://a.tldrnewsletter.com/web-version?ep=1&lc=general-old)",
            ),
            EmailEnvelope(
                message_id="latest-general",
                from_header="TLDR dan@tldrnewsletter.com",
                subject="Latest TLDR",
                received_at=dt.datetime(2026, 6, 12, 10, 56, tzinfo=dt.UTC),
                body="[View Online](https://a.tldrnewsletter.com/web-version?ep=1&lc=general-new)",
            ),
            EmailEnvelope(
                message_id="ai",
                from_header="TLDR AI dan@tldrnewsletter.com",
                subject="Latest TLDR AI",
                received_at=dt.datetime(2026, 6, 12, 13, 15, tzinfo=dt.UTC),
                body="[View Online](https://a.tldrnewsletter.com/web-version?ep=1&lc=ai-new)",
            ),
            EmailEnvelope(
                message_id="late-data",
                from_header="TLDR Data dan@tldrnewsletter.com",
                subject="Late TLDR Data",
                received_at=dt.datetime(2026, 6, 12, 15, 30, tzinfo=dt.UTC),
                body="[View Online](https://a.tldrnewsletter.com/web-version?ep=1&lc=data-late)",
            ),
            EmailEnvelope(
                message_id="ignored-it",
                from_header="TLDR IT dan@tldrnewsletter.com",
                subject="TLDR IT",
                received_at=dt.datetime(2026, 6, 12, 12, 43, tzinfo=dt.UTC),
                body="[View Online](https://a.tldrnewsletter.com/web-version?ep=1&lc=it)",
            ),
        ]

        sources = collect_snapshot_sources(
            messages=messages,
            target_date=dt.date(2026, 6, 12),
            timezone_name="Europe/Madrid",
            cutoff_hour=17,
            allowed_feeds={"TLDR", "TLDR AI", "TLDR Data"},
        )

        self.assertEqual([source.feed_name for source in sources], ["TLDR", "TLDR AI"])
        self.assertEqual(sources[0].message_id, "latest-general")
        self.assertEqual(sources[0].view_online_url, "https://a.tldrnewsletter.com/web-version?ep=1&lc=general-new")
        self.assertEqual(sources[1].message_id, "ai")


if __name__ == "__main__":
    unittest.main()
