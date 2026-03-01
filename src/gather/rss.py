"""Fetch AI-related news from RSS feeds (no API cost)."""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import feedparser
import httpx

from src.config import get_sources, get_settings


@dataclass
class NewsItem:
    title: str
    link: str
    published: str | None
    summary: str | None
    source_name: str
    raw: dict[str, Any]


def fetch_rss_items() -> list[NewsItem]:
    """Fetch items from all configured RSS feeds. Returns flattened list."""
    sources = get_sources()
    feeds = sources.get("rss_feeds") or []
    settings = get_settings()
    gather = settings.get("gather") or {}
    max_per_feed = gather.get("max_items_per_feed", 10)
    timeout = gather.get("request_timeout_seconds", 15)

    items: list[NewsItem] = []
    for feed_cfg in feeds:
        name = feed_cfg.get("name", "Unknown")
        url = feed_cfg.get("url")
        if not url:
            continue
        try:
            with httpx.Client(timeout=timeout) as client:
                resp = client.get(url)
                resp.raise_for_status()
                data = feedparser.parse(resp.text)
        except Exception as e:
            # Log and skip this feed
            print(f"[gather] Skip feed {name}: {e}")
            continue

        for entry in (data.entries or [])[:max_per_feed]:
            items.append(
                NewsItem(
                    title=entry.get("title") or "",
                    link=entry.get("link") or "",
                    published=entry.get("published"),
                    summary=(entry.get("summary") or "")[:2000] if entry.get("summary") else None,
                    source_name=name,
                    raw=dict(entry),
                )
            )
        time.sleep(0.5)  # Be nice to servers

    return items
