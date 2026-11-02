import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tldr_digest.models import DigestArtifact, DigestArticle
from tldr_digest.renderers import render_email_html, render_telegram_text


class RendererTests(unittest.TestCase):
    def test_email_renders_tldr_summary_before_editorial_take(self) -> None:
        artifact = DigestArtifact(
            target_date="2026-06-12",
            source_newsletters=["TLDR", "TLDR AI"],
            executive_summary="A strong day for coding agents and infra moves.",
            principal_articles=[
                DigestArticle(
                    title="OpenAI Acquired Ona for Long-Running Agents",
                    source_newsletter="TLDR AI",
                    url="https://openai.com/index/openai-to-acquire-ona",
                    tldr_summary="OpenAI announced it would acquire Ona to bring secure cloud execution and orchestration capabilities into the Codex platform.",
                    why_important="This pushes OpenAI further into persistent agent infrastructure.",
                )
            ],
            secondary_articles=[],
            extraction_notes=["One paywalled article resolved to Bloomberg."],
        )

        html = render_email_html(artifact, subject="TLDR Digest - 2026-06-12")

        self.assertIn("Principal Articles", html)
        self.assertIn("Why it&#x27;s important", html)
        self.assertIn("color:#ffffff;", html)
        self.assertIn("color:#f0fdfa;", html)
        self.assertLess(
            html.index("OpenAI announced it would acquire Ona"),
            html.index("This pushes OpenAI further into persistent agent infrastructure."),
        )

    def test_telegram_render_includes_email_note_and_top_links(self) -> None:
        artifact = DigestArtifact(
            target_date="2026-06-12",
            source_newsletters=["TLDR"],
            executive_summary="Today centered on infrastructure and agent tooling.",
            principal_articles=[
                DigestArticle(
                    title="Building a Good Vertical Agent",
                    source_newsletter="TLDR",
                    url="https://example.com/vertical-agent",
                    tldr_summary="Earlier models needed custom tools and everything spelled out to work.",
                    why_important="Useful framing for real agent workflow design.",
                )
            ],
            secondary_articles=[],
            extraction_notes=[],
        )

        text = render_telegram_text(artifact)

        self.assertIn("Full digest sent to Gmail.", text)
        self.assertIn("Building a Good Vertical Agent", text)
        self.assertIn("https://example.com/vertical-agent", text)


if __name__ == "__main__":
    unittest.main()
