#!/usr/bin/env python3
"""
Build a copy-paste handoff package for ChatGPT/OpenAI from extracted TLDR JSON.

The goal is deliberately simple: take the clean extractor output plus the editorial
prompt and emit a single markdown document that can be pasted into ChatGPT.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a ChatGPT handoff package from extracted TLDR JSON.")
    parser.add_argument("--articles", required=True, help="Path to output/articles.json.")
    parser.add_argument("--prompt", default="editorial_prompt.md", help="Path to the editorial prompt.")
    parser.add_argument("--out", default="-", help="Output markdown path. Use '-' for stdout.")
    return parser.parse_args()


def build_summary_block(data: dict) -> str:
    newsletters = data.get("newsletters", [])
    warnings = []
    for newsletter in newsletters:
        for warning in newsletter.get("warnings", []):
            warnings.append(f"- {newsletter.get('source') or 'Unknown'}: {warning}")

    lines = [
        "## Resumen de extracción",
        "",
        f"- Newsletters procesadas: {data.get('newsletter_count', 0)}",
        f"- Artículos finales: {data.get('article_count', 0)}",
        "",
        "### Artículos brutos por newsletter",
        "",
    ]

    for newsletter in newsletters:
        source = newsletter.get("source") or "Unknown"
        date = newsletter.get("date") or "Unknown date"
        raw_count = newsletter.get("article_count_raw", 0)
        lines.append(f"- {source} {date}: {raw_count}")

    if warnings:
        lines.extend(
            [
                "",
                "### Warnings de extracción",
                "",
                *warnings,
            ]
        )

    return "\n".join(lines)


def build_handoff(prompt_text: str, articles_json_text: str, data: dict) -> str:
    summary_block = build_summary_block(data)
    return "\n".join(
        [
            "# Handoff para ChatGPT",
            "",
            "Pega este documento completo en ChatGPT para generar el digest editorial final.",
            "",
            summary_block,
            "",
            "## Prompt editorial",
            "",
            prompt_text.strip(),
            "",
            "## JSON extraído",
            "",
            "```json",
            articles_json_text.strip(),
            "```",
            "",
        ]
    )


def main() -> int:
    args = parse_args()

    articles_path = Path(args.articles)
    prompt_path = Path(args.prompt)

    data = json.loads(articles_path.read_text(encoding="utf-8"))
    articles_json_text = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True)
    prompt_text = prompt_path.read_text(encoding="utf-8")
    handoff_text = build_handoff(prompt_text=prompt_text, articles_json_text=articles_json_text, data=data)

    if args.out == "-":
        print(handoff_text)
    else:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(handoff_text, encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
