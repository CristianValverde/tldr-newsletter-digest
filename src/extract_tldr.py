#!/usr/bin/env python3
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from tldr_digest.extraction import extract_from_urls, output_text


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract articles from TLDR View Online URLs.")
    parser.add_argument("--url", action="append", required=True, help="TLDR View Online URL. Can be passed multiple times.")
    parser.add_argument("--out", default="-", help="Output JSON path. Use '-' for stdout.")
    parser.add_argument("--include-sponsors", action="store_true", help="Include sponsors in output instead of filtering them.")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    logging.basicConfig(level=getattr(logging, args.log_level), format="%(levelname)s %(message)s")
    _, output = extract_from_urls(args.url, include_sponsors=args.include_sponsors)
    rendered = output_text(output)

    if args.out == "-":
        print(rendered)
    else:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(rendered, encoding="utf-8")
        logging.getLogger("tldr_extract").info("Wrote %s", out_path)

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
