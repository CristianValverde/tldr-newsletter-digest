# Editorial prompt for ChatGPT/OpenAI

You receive JSON extracted from TLDR newsletters. Produce a concise Spanish digest.

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

### Artículos principales
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
- why it matters, in Spanish
- original TLDR summary preserved as fully as possible

### Interesantes pero secundarios
Pick a smaller set of useful or curious secondary items.
For each:
- title
- source newsletter
- link
- 1-2 sentence Spanish summary

6. Avoid low-signal product launches unless strategically relevant.
7. If extraction warnings exist, show a short "Notas de extracción" section.
8. Keep the output dense and useful.
