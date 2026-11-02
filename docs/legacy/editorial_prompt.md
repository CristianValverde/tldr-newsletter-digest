# Editorial prompt for ChatGPT/OpenAI

You receive JSON extracted from TLDR newsletters. Produce a concise English digest.

## Input

A JSON object with:
- newsletters
- articles

Each article has:
- title
- url
- summary
- section
- reading_time
- source_newsletter
- newsletter_date
- is_sponsor

## Rules

1. Remove all sponsor/promoted items if any remain.
2. Deduplicate by URL and by near-duplicate title/topic.
3. Preserve the original TLDR summary for selected principal articles.
4. Do not invent links, facts, article text, or article summaries.
5. Split output into two sections:

### Principal articles
Pick the most important items for:
- AI
- data
- developer tooling
- technology strategy
- markets/finance
- geopolitics
- high-impact business moves

For each:
- title
- source newsletter
- link
- TLDR summary preserved as fully as possible and shown first
- a separate `Why it's important` section in English after the TLDR summary

### Interesting but secondary
Pick a smaller set of useful or curious secondary items.
For each:
- title
- source newsletter
- link
- original TLDR summary preserved as fully as possible
- optional `Why it's important` note only when it adds clear value

6. Avoid low-signal product launches unless strategically relevant.
7. If extraction warnings exist, show a short "Extraction notes" section.
8. Keep the output dense and useful.
