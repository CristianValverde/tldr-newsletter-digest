# Codex task: build and validate TLDR newsletter extractor

You are working on a small Python project called `tldr-digest`.

## Goal

Create a robust extractor for TLDR newsletters using the public `View Online` URLs. The extractor must not rely on Gmail/Outlook body content because those connectors truncate long newsletter bodies.

## Requirements

1. Accept one or more `View Online` URLs from the command line.
2. Fetch each URL with HTTP.
3. Follow redirects.
4. Parse the newsletter HTML.
5. Extract article blocks with:
   - source newsletter, e.g. `TLDR`, `TLDR AI`, `TLDR Data`
   - newsletter date
   - section
   - title
   - canonical article URL
   - reading time if present
   - full TLDR-provided summary
   - sponsor flag
6. Remove or flag:
   - sponsors
   - ads
   - top nav links
   - unsubscribe/manage subscription links
   - tracking/open pixels
   - footer/social links
7. Deduplicate across newsletters:
   - first by normalized canonical URL
   - then by normalized title similarity
8. Output deterministic JSON.
9. Include logs/warnings when:
   - a newsletter could not be fetched
   - HTML structure is unexpected
   - an article has no summary or URL
10. Keep implementation simple and practical. No overengineered framework, no database, no unnecessary dependencies.

## Important behavior

Sponsors should not be included in the final `articles` list unless `--include-sponsors` is explicitly set.

For principal articles later, ChatGPT will preserve the full TLDR summary. Do not rewrite summaries here. The extractor should preserve original summaries as clean text.

## Initial test

Run the extractor with two manually provided TLDR `View Online` URLs from 2026-06-09:
- TLDR general
- TLDR AI

Expected result:
- Sponsor blocks are removed.
- Real articles are extracted.
- `Apple Introduced Siri AI` appears only once after deduplication if present in both newsletters.
- Output JSON is readable and stable.

## Deliverables

- Working `src/extract_tldr.py`
- `requirements.txt`
- README usage examples
- If parser assumptions are fragile, document them in comments.
