"""Fetch AI-related news from RSS feeds (no API cost)."""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Any

import feedparser
import httpx

from src.config import get_sources, get_settings
from src.logging_config import get_logger

logger = get_logger("gather")

# User-Agent so feeds don't block us
USER_AGENT = "AiNewsHelper/1.0 (+https://github.com/yunieyuna/ai-news)"


@dataclass
class NewsItem:
    title: str
    link: str
    published: str | None
    summary: str | None
    source_name: str
    raw: dict[str, Any]
    # For sorting: time struct (year, month, day, ...) or None
    published_parsed: tuple[int, ...] | None = field(default=None, repr=False)
    # Fetched full article text (set by fetch_full_articles when fetch_full_content is on)
    full_text: str | None = field(default=None, repr=False)


def _strip_html(text: str) -> str:
    if not text:
        return ""
    return re.sub(r"<[^>]+>", "", text).strip()


def _matches_keywords(text: str, keywords: list[str]) -> bool:
    if not keywords:
        return True
    lower = (text or "").lower()
    return any(kw.lower() in lower for kw in keywords)


def _parse_published(entry: dict) -> tuple[str | None, tuple[int, ...] | None]:
    published = entry.get("published")
    parsed = entry.get("published_parsed")
    if parsed and len(parsed) >= 6:
        return published, tuple(parsed[:6])
    return published, None


def fetch_rss_items() -> list[NewsItem]:
    """Fetch from all configured RSS feeds. Dedupes by link, optional keyword filter, newest first."""
    sources = get_sources()
    feeds = sources.get("rss_feeds") or []
    settings = get_settings()
    gather = settings.get("gather") or {}
    max_per_feed = gather.get("max_items_per_feed", 10)
    timeout = gather.get("request_timeout_seconds", 15)
    dedupe = gather.get("dedupe_by_link", True)
    keywords = gather.get("filter_keywords") or []

    items: list[NewsItem] = []
    seen_links: set[str] = set()

    for feed_cfg in feeds:
        name = feed_cfg.get("name", "Unknown")
        url = feed_cfg.get("url")
        if not url:
            continue
        try:
            with httpx.Client(timeout=timeout, headers={"User-Agent": USER_AGENT}) as client:
                resp = client.get(url)
                resp.raise_for_status()
                data = feedparser.parse(resp.text)
        except Exception as e:
            logger.warning("Skip feed %s: %s", name, e)
            continue

        for entry in (data.entries or [])[:max_per_feed]:
            link = (entry.get("link") or "").strip()
            title = (entry.get("title") or "").strip()
            summary_raw = entry.get("summary") or ""
            summary = _strip_html(summary_raw)[:2000] if summary_raw else None
            published, published_parsed = _parse_published(entry)

            if not link or not title:
                continue
            if dedupe and link in seen_links:
                continue
            if keywords and not _matches_keywords(f"{title} {summary or ''}", keywords):
                continue

            seen_links.add(link)
            items.append(
                NewsItem(
                    title=title,
                    link=link,
                    published=published,
                    summary=summary,
                    source_name=name,
                    raw=dict(entry),
                    published_parsed=published_parsed,
                )
            )
        time.sleep(0.5)

    # Newest first (parsed date; items without date go to end)
    def sort_key(it: NewsItem) -> tuple:
        if it.published_parsed:
            return (0, it.published_parsed)
        return (1, (0, 0, 0, 0, 0, 0))

    items.sort(key=sort_key, reverse=True)
    logger.info("Fetched %d items from %d feeds", len(items), len(feeds))
    return items
