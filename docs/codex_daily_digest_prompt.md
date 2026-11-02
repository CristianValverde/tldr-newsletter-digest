# Codex Daily Digest Automation Prompt

Run the daily TLDR digest pipeline for today in `Europe/Madrid`.

This prompt is intended for the scheduled Codex automation that runs on weekdays at `17:00 Europe/Madrid`.

1. Run `python src/run_daily_digest.py snapshot`.
2. If today's run manifest says `snapshot_status` is `no_input`, stop and report that no eligible TLDR-family emails had arrived before the 17:00 Madrid cutoff.
3. Otherwise, read today's `articles.json` and create `digest.json` in the same run directory with this contract:
   - `target_date`
   - `source_newsletters`
   - `executive_summary`
   - `principal_articles`
   - `secondary_articles`
   - `extraction_notes`
4. For each principal article:
   - preserve the original TLDR summary in `tldr_summary`
   - add a separate `why_important` field after it
5. Keep the digest dense, useful, and English-language.
6. Run `python src/run_daily_digest.py finalize`.
7. Confirm in `run_manifest.json` that email and Telegram delivery are marked `sent`, or clearly report which delivery step failed.
