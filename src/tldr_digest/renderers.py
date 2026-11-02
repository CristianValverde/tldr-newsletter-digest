from __future__ import annotations

import html

from .models import DigestArtifact, DigestArticle


def _render_article_html(article: DigestArticle, principal: bool) -> str:
    why_block = ""
    if article.why_important:
        why_block = (
            "<div style=\"margin-top:12px;\">"
            "<div style=\"font-size:12px;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;color:#7c3aed;\">"
            "Why it&#x27;s important"
            "</div>"
            f"<p style=\"margin:6px 0 0 0;font-size:15px;line-height:1.6;color:#1f2937;\">{html.escape(article.why_important)}</p>"
            "</div>"
        )
    return (
        "<article style=\"padding:20px 0;border-top:1px solid #e5e7eb;\">"
        f"<h3 style=\"margin:0 0 6px 0;font-size:21px;line-height:1.3;color:#111827;\">{html.escape(article.title)}</h3>"
        f"<div style=\"font-size:13px;color:#6b7280;margin-bottom:12px;\">{html.escape(article.source_newsletter)}</div>"
        f"<p style=\"margin:0;font-size:16px;line-height:1.7;color:#111827;\">{html.escape(article.tldr_summary)}</p>"
        f"{why_block if principal or article.why_important else ''}"
        f"<p style=\"margin:14px 0 0 0;\"><a href=\"{html.escape(article.url)}\" style=\"color:#0f766e;text-decoration:none;font-weight:600;\">Open article</a></p>"
        "</article>"
    )


def render_email_html(artifact: DigestArtifact, subject: str) -> str:
    principal_html = "".join(_render_article_html(article, principal=True) for article in artifact.principal_articles)
    secondary_html = "".join(_render_article_html(article, principal=False) for article in artifact.secondary_articles)
    notes_html = "".join(
        f"<li style=\"margin:0 0 8px 0;\">{html.escape(note)}</li>" for note in artifact.extraction_notes
    )
    newsletters = ", ".join(artifact.source_newsletters)
    return f"""<!DOCTYPE html>
<html lang="en">
  <body style="margin:0;padding:0;background:#f4f4ef;color:#111827;font-family:Georgia,'Times New Roman',serif;">
    <div style="max-width:760px;margin:0 auto;padding:32px 20px 48px 20px;">
      <div style="background:#fffdf7;border:1px solid #e7e0cf;border-radius:24px;overflow:hidden;box-shadow:0 16px 50px rgba(17,24,39,0.08);">
        <div style="padding:32px;background:linear-gradient(135deg,#0b1220,#0f766e 58%,#14b8a6);color:#ffffff;">
          <div style="font-size:12px;letter-spacing:0.14em;text-transform:uppercase;color:#ccfbf1;font-weight:700;">TLDR Daily Snapshot</div>
          <h1 style="margin:10px 0 8px 0;font-size:34px;line-height:1.15;color:#ffffff;">{html.escape(subject)}</h1>
          <p style="margin:0;font-size:16px;line-height:1.6;max-width:620px;color:#f0fdfa;">{html.escape(artifact.executive_summary)}</p>
          <p style="margin:14px 0 0 0;font-size:13px;color:#ccfbf1;">Sources included: {html.escape(newsletters)}</p>
        </div>
        <div style="padding:28px 32px;">
          <h2 style="margin:0 0 8px 0;font-size:24px;color:#111827;">Principal Articles</h2>
          {principal_html or '<p style="font-size:15px;color:#6b7280;">No principal articles were selected.</p>'}
          <h2 style="margin:28px 0 8px 0;font-size:24px;color:#111827;">Secondary Articles</h2>
          {secondary_html or '<p style="font-size:15px;color:#6b7280;">No secondary articles were selected.</p>'}
          <h2 style="margin:28px 0 8px 0;font-size:24px;color:#111827;">Extraction Notes</h2>
          <ul style="padding-left:20px;margin:0;font-size:15px;line-height:1.6;color:#374151;">{notes_html or '<li>No extraction warnings.</li>'}</ul>
        </div>
      </div>
    </div>
  </body>
</html>"""


def render_email_text(artifact: DigestArtifact, subject: str) -> str:
    lines = [subject, "", artifact.executive_summary, "", f"Sources: {', '.join(artifact.source_newsletters)}", ""]
    lines.append("Principal Articles")
    lines.append("")
    for article in artifact.principal_articles:
        lines.extend(
            [
                article.title,
                article.source_newsletter,
                article.tldr_summary,
                f"Why it's important: {article.why_important}" if article.why_important else "",
                article.url,
                "",
            ]
        )
    lines.append("Secondary Articles")
    lines.append("")
    for article in artifact.secondary_articles:
        lines.extend([article.title, article.source_newsletter, article.tldr_summary, article.url, ""])
    lines.append("Extraction Notes")
    lines.extend(artifact.extraction_notes or ["No extraction warnings."])
    return "\n".join(line for line in lines if line is not None)


def render_telegram_text(artifact: DigestArtifact, max_items: int = 5) -> str:
    lines = [
        f"TLDR Digest — {artifact.target_date}",
        "",
        artifact.executive_summary,
        "",
        "Top items:",
    ]
    for article in artifact.principal_articles[:max_items]:
        compact_summary = article.tldr_summary
        if len(compact_summary) > 220:
            compact_summary = compact_summary[:217].rstrip() + "..."
        lines.extend(
            [
                f"• {article.title} ({article.source_newsletter})",
                compact_summary,
                f"Why it matters: {article.why_important}" if article.why_important else "",
                article.url,
                "",
            ]
        )
    lines.append("Full digest sent to Gmail.")
    return "\n".join(line for line in lines if line)
