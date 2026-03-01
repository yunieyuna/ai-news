"""Fetch full article content from item links and attach to NewsItem for summarization."""
from __future__ import annotations

import time
from dataclasses import replace

from src.config import get_settings
from src.gather.rss import NewsItem
from src.logging_config import get_logger

logger = get_logger("gather")

# Max chars per article to send to LLM (keeps token cost under control)
MAX_ARTICLE_CHARS = 3000


def _fetch_one(url: str, timeout: int) -> str | None:
    try:
        import httpx
        from trafilatura import extract

        from src.gather.rss import USER_AGENT

        with httpx.Client(timeout=timeout, follow_redirects=True, headers={"User-Agent": USER_AGENT}) as client:
            resp = client.get(url)
            resp.raise_for_status()
            raw = resp.text
        if not raw:
            return None
        text = extract(raw, url=url, include_comments=False, include_tables=False)
        return (text or "").strip()[:MAX_ARTICLE_CHARS] if text else None
    except Exception as e:
        logger.debug("Fetch failed %s: %s", url[:50], e)
        return None


def fetch_full_articles(items: list[NewsItem]) -> list[NewsItem]:
    """Fetch full article body for the first N items; return new list with full_text set where successful."""
    settings = get_settings()
    gather = settings.get("gather") or {}
    if not gather.get("fetch_full_content", False):
        return items
    max_fetch = gather.get("max_articles_to_fetch", 15)
    timeout = gather.get("article_timeout_seconds", 12)
    out: list[NewsItem] = []
    for i, item in enumerate(items):
        if i >= max_fetch:
            out.append(item)
            continue
        text = _fetch_one(item.link, timeout)
        if text:
            out.append(replace(item, full_text=text))
            logger.info("Fetched full text: %s", item.title[:50])
        else:
            out.append(item)
        time.sleep(0.3)
    return out
