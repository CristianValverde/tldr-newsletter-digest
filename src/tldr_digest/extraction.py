from __future__ import annotations

import datetime as dt
import html
import json
import logging
import re
from dataclasses import asdict
from difflib import SequenceMatcher
from urllib.parse import parse_qsl, unquote, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup, FeatureNotFound, Tag

from .models import Article, Newsletter


LOGGER = logging.getLogger("tldr_extract")

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; TLDRDigestExtractor/0.3; "
        "+https://example.local/tldr-digest)"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

SPONSOR_PATTERNS = re.compile(
    r"(?:^|\b)(sponsor|together with|partner|advertisement|promoted|brought to you by)(?:\b|$)",
    re.I,
)
READING_TIME_RE = re.compile(r"\((\d+\s+(?:minute|min)\s+read)\)", re.I)
NEWSLETTER_HEADER_RE = re.compile(r"^(TLDR(?:\s+[A-Za-z]+)*)\s+(\d{4}-\d{2}-\d{2})$", re.I)
DATE_RE = re.compile(r"\b(20\d{2}-\d{2}-\d{2})\b")
NOISE_BLOCK_PATTERNS = re.compile(
    r"(love tldr|track your referrals here|want to work at tldr|thanks for reading|"
    r"manage your subscription|unsubscribe|privacy policy|terms of service)",
    re.I,
)
SHORTLINK_HOSTS = {"links.tldrnewsletter.com", "tracking.tldrnewsletter.com"}
TRACKING_QUERY_KEYS = {
    "accesstoken",
    "dclid",
    "fbclid",
    "gad_campaignid",
    "gad_source",
    "gclid",
    "mc_cid",
    "mc_eid",
    "mod",
    "ref",
    "ref_src",
    "reflink",
    "scid",
    "smid",
    "s",
    "siteid",
    "st",
    "unlocked_article_code",
    "utm_campaign",
    "utm_content",
    "utm_medium",
    "utm_source",
    "utm_term",
}
TOKEN_KEEP_SHORT = {"ai", "ar", "ml", "vr", "ui", "ux", "ipo", "s1", "5g", "it"}
TOKEN_STOPWORDS = {
    "a",
    "an",
    "and",
    "around",
    "at",
    "built",
    "by",
    "for",
    "from",
    "how",
    "in",
    "into",
    "is",
    "its",
    "more",
    "new",
    "now",
    "of",
    "on",
    "our",
    "plan",
    "says",
    "than",
    "that",
    "the",
    "their",
    "this",
    "to",
    "was",
    "with",
}


def append_warning(newsletter: Newsletter, message: str) -> None:
    if message not in newsletter.warnings:
        newsletter.warnings.append(message)


def fetch_html(session: requests.Session, url: str, timeout: int = 30) -> tuple[str, str]:
    response = session.get(url, headers=REQUEST_HEADERS, timeout=timeout, allow_redirects=True)
    response.raise_for_status()
    return response.text, response.url


def clean_text(text: str) -> str:
    text = html.unescape(text or "")
    text = re.sub(r"\u200c|\u200b|\ufeff|\xa0", " ", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\s*\n\s*", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def strip_tracking_query(url: str) -> str:
    parsed = urlparse(url)
    if not parsed.query:
        return url

    filtered_items = []
    for key, value in parse_qsl(parsed.query, keep_blank_values=True):
        lower_key = key.lower()
        if lower_key.startswith("utm_") or lower_key in TRACKING_QUERY_KEYS:
            continue
        filtered_items.append((key, value))

    return urlunparse(parsed._replace(query="&".join(f"{k}={v}" for k, v in filtered_items)))


def canonicalize_tracking_url(url: str) -> str:
    if not url:
        return ""

    url = html.unescape(url.strip())
    parsed = urlparse(url)

    if "tracking.tldrnewsletter.com" in parsed.netloc:
        for part in parsed.path.split("/"):
            decoded = unquote(part)
            if decoded.startswith("http://") or decoded.startswith("https://"):
                decoded_parsed = urlparse(decoded)
                if decoded_parsed.netloc == "a.tldrnewsletter.com" and "web-version" in decoded_parsed.path:
                    return decoded
                return strip_tracking_query(decoded)

    if parsed.netloc == "a.tldrnewsletter.com" and "web-version" in parsed.path:
        return url

    return strip_tracking_query(url)


def normalize_url(url: str) -> str:
    normalized = canonicalize_tracking_url(url)
    parsed = urlparse(normalized)
    hostname = parsed.netloc.lower()
    return urlunparse(parsed._replace(netloc=hostname, fragment="")).rstrip("/")


def resolve_canonical_article_url(
    session: requests.Session,
    url: str,
    cache: dict[str, str],
    newsletter: Newsletter,
    timeout: int = 30,
) -> str:
    normalized = normalize_url(url)
    if not normalized:
        return ""

    if normalized in cache:
        return cache[normalized]

    parsed = urlparse(normalized)
    if parsed.netloc not in SHORTLINK_HOSTS:
        cache[normalized] = normalized
        return normalized

    try:
        response = session.get(
            normalized,
            headers=REQUEST_HEADERS,
            timeout=timeout,
            allow_redirects=True,
            stream=True,
        )
        resolved = normalize_url(response.url)
        if response.status_code >= 400:
            append_warning(
                newsletter,
                f"Resolved short URL {normalized} to {resolved} but destination returned HTTP {response.status_code}",
            )
        LOGGER.debug("Resolved %s -> %s", normalized, resolved)
    except Exception as exc:  # pragma: no cover
        resolved = normalized
        append_warning(newsletter, f"Could not resolve short URL {normalized}: {exc}")

    cache[normalized] = resolved
    return resolved


def normalize_title(title: str) -> str:
    title = clean_text(title).lower()
    title = READING_TIME_RE.sub("", title)
    title = re.sub(r"[^a-z0-9]+", " ", title)
    return title.strip()


def normalize_token(token: str) -> str:
    token = token.lower()
    token = re.sub(r"[^a-z0-9]", "", token)
    if token.endswith("ingly") and len(token) > 7:
        token = token[:-5]
    elif token.endswith("ingly") and len(token) > 6:
        token = token[:-5]
    elif token.endswith("ly") and len(token) > 6:
        token = token[:-2]
    elif token.endswith("ing") and len(token) > 6:
        token = token[:-3]
    elif token.endswith("ied") and len(token) > 5:
        token = token[:-3] + "y"
    elif token.endswith("ed") and len(token) > 5:
        token = token[:-1]
    elif token.endswith("es") and len(token) > 5:
        token = token[:-2]
    elif token.endswith("s") and len(token) > 5:
        token = token[:-1]
    token = {
        "ipo": "publicoffering",
        "s1": "publicoffering",
        "file": "submit",
        "filed": "submit",
        "files": "submit",
        "filing": "submit",
        "submit": "submit",
        "submitted": "submit",
        "submits": "submit",
        "confidentially": "confidential",
    }.get(token, token)
    return token


def tokenize_similarity(text: str) -> list[str]:
    normalized = normalize_title(text)
    tokens: list[str] = []

    for raw_token in normalized.split():
        token = normalize_token(raw_token)
        if not token:
            continue
        if len(token) < 3 and token not in TOKEN_KEEP_SHORT:
            continue
        if token in TOKEN_STOPWORDS:
            continue
        tokens.append(token)

    return tokens


def fuzzy_token_overlap(tokens_a: list[str], tokens_b: list[str]) -> int:
    if not tokens_a or not tokens_b:
        return 0

    smaller = tokens_a if len(tokens_a) <= len(tokens_b) else tokens_b
    larger = tokens_b if smaller is tokens_a else tokens_a
    used_indexes: set[int] = set()
    overlap = 0

    for token in smaller:
        best_index = -1
        best_ratio = 0.0
        for index, candidate in enumerate(larger):
            if index in used_indexes:
                continue
            ratio = SequenceMatcher(None, token, candidate).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_index = index
        if best_index >= 0 and best_ratio >= 0.84:
            used_indexes.add(best_index)
            overlap += 1

    return overlap


def articles_look_duplicate(left: Article, right: Article, title_threshold: float = 0.88) -> bool:
    if normalize_url(left.url) == normalize_url(right.url):
        return True

    left_title = normalize_title(left.title)
    right_title = normalize_title(right.title)
    if left_title == right_title:
        return True

    if SequenceMatcher(None, left_title, right_title).ratio() >= title_threshold:
        return True

    left_title_tokens = tokenize_similarity(left.title)
    right_title_tokens = tokenize_similarity(right.title)
    title_overlap = fuzzy_token_overlap(left_title_tokens, right_title_tokens)
    if title_overlap < 3:
        return False

    left_summary_tokens = tokenize_similarity(left.summary)
    right_summary_tokens = tokenize_similarity(right.summary)
    summary_overlap = fuzzy_token_overlap(left_summary_tokens[:18], right_summary_tokens[:18])
    return summary_overlap >= 3 or title_overlap >= 4


def article_preference_key(article: Article) -> tuple[int, int, int, int]:
    specialized_newsletter = int(bool(article.source_newsletter and article.source_newsletter != "TLDR"))
    non_shortlink = int(urlparse(article.url).netloc not in SHORTLINK_HOSTS)
    return (
        specialized_newsletter,
        non_shortlink,
        len(clean_text(article.summary)),
        -len(clean_text(article.title)),
    )


def choose_preferred_article(current: Article, candidate: Article) -> Article:
    if article_preference_key(candidate) > article_preference_key(current):
        return candidate
    return current


def get_visible_text(soup: BeautifulSoup) -> str:
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    return clean_text(soup.get_text("\n"))


def detect_source_and_date(soup: BeautifulSoup) -> tuple[str | None, str | None]:
    first_h1 = soup.find("h1")
    if first_h1:
        header_text = clean_text(first_h1.get_text(" ", strip=True))
        header_match = NEWSLETTER_HEADER_RE.match(header_text)
        if header_match:
            return clean_text(header_match.group(1)), header_match.group(2)

    visible_text = get_visible_text(soup)
    header_match = NEWSLETTER_HEADER_RE.search(visible_text)
    if header_match:
        return clean_text(header_match.group(1)), header_match.group(2)

    date_match = DATE_RE.search(visible_text)
    return None, date_match.group(1) if date_match else None


def infer_section(block: Tag) -> str | None:
    for header in block.find_all_previous("h1", limit=8):
        text = clean_text(header.get_text(" ", strip=True))
        if not text:
            continue
        if NEWSLETTER_HEADER_RE.match(text):
            continue
        return text
    return None


def find_primary_anchor(block: Tag, is_sponsor: bool) -> Tag | None:
    anchors = [anchor for anchor in block.find_all("a", href=True) if clean_text(anchor.get_text(" ", strip=True))]
    if not anchors:
        return None

    if is_sponsor:
        for anchor in anchors:
            text = clean_text(anchor.get_text(" ", strip=True))
            if SPONSOR_PATTERNS.search(text):
                return anchor
        return anchors[0]

    for anchor in anchors:
        text = clean_text(anchor.get_text(" ", strip=True))
        if READING_TIME_RE.search(text):
            return anchor

    return anchors[0]


def extract_summary_from_block(block: Tag, title_with_meta: str) -> str:
    full_text = clean_text(" ".join(block.stripped_strings))
    if not full_text:
        return ""

    summary = full_text
    if title_with_meta and summary.startswith(title_with_meta):
        summary = summary[len(title_with_meta) :].strip()
    elif title_with_meta:
        summary = summary.replace(title_with_meta, "", 1).strip()

    summary = re.sub(r"\s+", " ", summary).strip()
    return summary


def iter_editorial_blocks(soup: BeautifulSoup) -> list[Tag]:
    blocks: list[Tag] = []

    for block in soup.select("div.text-block"):
        text = clean_text(" ".join(block.stripped_strings))
        if not text:
            continue
        if NOISE_BLOCK_PATTERNS.search(text):
            continue
        if READING_TIME_RE.search(text) or SPONSOR_PATTERNS.search(text):
            blocks.append(block)

    return blocks


def extract_articles_from_html(
    raw_html: str,
    view_url: str,
    final_url: str,
    session: requests.Session,
    resolve_cache: dict[str, str],
) -> Newsletter:
    try:
        soup = BeautifulSoup(raw_html, "lxml")
    except FeatureNotFound:
        soup = BeautifulSoup(raw_html, "html.parser")
    source, newsletter_date = detect_source_and_date(soup)
    newsletter = Newsletter(
        source=source,
        date=newsletter_date,
        view_online_url=view_url,
        final_url=final_url,
    )

    editorial_blocks = iter_editorial_blocks(soup)
    if not editorial_blocks:
        append_warning(newsletter, "No editorial blocks were found. TLDR HTML structure may have changed.")
        return newsletter

    for block in editorial_blocks:
        block_text = clean_text(" ".join(block.stripped_strings))
        is_sponsor = bool(SPONSOR_PATTERNS.search(block_text))
        primary_anchor = find_primary_anchor(block, is_sponsor=is_sponsor)

        if primary_anchor is None:
            append_warning(newsletter, f"Skipped block with no link: {block_text[:120]}")
            continue

        title_with_meta = clean_text(primary_anchor.get_text(" ", strip=True))
        if not title_with_meta:
            append_warning(newsletter, f"Skipped block with empty title: {block_text[:120]}")
            continue

        if not is_sponsor and not READING_TIME_RE.search(title_with_meta):
            append_warning(
                newsletter,
                f"Skipped non-sponsor block without reading time in title: {title_with_meta[:120]}",
            )
            continue

        reading_time_match = READING_TIME_RE.search(title_with_meta)
        reading_time = reading_time_match.group(1) if reading_time_match else None
        title = clean_text(READING_TIME_RE.sub("", title_with_meta))
        url = resolve_canonical_article_url(
            session=session,
            url=primary_anchor.get("href", ""),
            cache=resolve_cache,
            newsletter=newsletter,
        )
        summary = extract_summary_from_block(block, title_with_meta)
        section = infer_section(block)

        article = Article(
            title=title,
            url=url,
            summary=summary,
            section=section,
            reading_time=reading_time,
            is_sponsor=is_sponsor,
            source_newsletter=source,
            newsletter_date=newsletter_date,
        )
        newsletter.articles.append(article)

        if not article.url:
            append_warning(newsletter, f"Article has no URL: {article.title}")
        if not article.summary:
            append_warning(newsletter, f"Article has no summary: {article.title}")
        if article.section is None and not article.is_sponsor:
            append_warning(newsletter, f"Article has no section: {article.title}")

    return newsletter


def deduplicate_articles(newsletters: list[Newsletter]) -> list[Article]:
    result: list[Article] = []

    for newsletter in newsletters:
        for article in newsletter.articles:
            if article.is_sponsor:
                continue

            duplicate_index = None
            for index, existing in enumerate(result):
                if articles_look_duplicate(existing, article):
                    duplicate_index = index
                    break

            if duplicate_index is None:
                result.append(article)
                continue

            preferred = choose_preferred_article(result[duplicate_index], article)
            result[duplicate_index] = preferred

    return result


def build_output(newsletters: list[Newsletter], include_sponsors: bool = False) -> dict:
    if include_sponsors:
        final_articles = [article for newsletter in newsletters for article in newsletter.articles]
    else:
        final_articles = deduplicate_articles(newsletters)

    return {
        "generated_at": dt.datetime.now(dt.UTC).isoformat(),
        "newsletter_count": len(newsletters),
        "article_count": len(final_articles),
        "newsletters": [
            {
                "source": newsletter.source,
                "date": newsletter.date,
                "view_online_url": newsletter.view_online_url,
                "final_url": newsletter.final_url,
                "article_count_raw": len(newsletter.articles),
                "warnings": newsletter.warnings,
            }
            for newsletter in newsletters
        ],
        "articles": [asdict(article) for article in final_articles],
    }


def extract_from_urls(urls: list[str], include_sponsors: bool = False) -> tuple[list[Newsletter], dict]:
    newsletters: list[Newsletter] = []
    resolve_cache: dict[str, str] = {}

    with requests.Session() as session:
        for url in urls:
            LOGGER.info("Fetching %s", url)
            try:
                raw_html, final_url = fetch_html(session=session, url=url)
                newsletter = extract_articles_from_html(
                    raw_html=raw_html,
                    view_url=url,
                    final_url=final_url,
                    session=session,
                    resolve_cache=resolve_cache,
                )
                newsletters.append(newsletter)
                LOGGER.info(
                    "Extracted %s raw blocks from %s %s",
                    len(newsletter.articles),
                    newsletter.source or "unknown source",
                    newsletter.date or "unknown date",
                )
            except Exception as exc:  # pragma: no cover
                LOGGER.exception("Failed to process %s", url)
                newsletters.append(
                    Newsletter(
                        source=None,
                        date=None,
                        view_online_url=url,
                        final_url=url,
                        warnings=[f"Failed to fetch/parse: {exc}"],
                    )
                )

    return newsletters, build_output(newsletters, include_sponsors=include_sponsors)


def output_text(output: dict) -> str:
    return json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True)
