"""Summarize gathered items with an LLM. Supports Ollama (local), Groq (free tier), or OpenAI."""
from __future__ import annotations

import os
import re
from dataclasses import dataclass

from src.config import get_settings
from src.gather.rss import NewsItem
from src.logging_config import get_logger

logger = get_logger("analyze")


@dataclass
class SummarizedDigest:
    raw_items: list[NewsItem]
    summary_text: str
    provider: str


def _strip_html(text: str) -> str:
    if not text:
        return ""
    return re.sub(r"<[^>]+>", "", text).strip()


def _build_prompt(items: list[NewsItem], max_items: int = 25) -> str:
    system = (
        "You write AI/tech news digests focused on LEARNING VALUE. "
        "Your goal: help the reader identify what is most worth studying this week.\n\n"
        "Reply using these markdown section headers (##) in this order "
        "(skip any section with no relevant content):\n"
        "## 🔥 Must Read — the 2–3 most impactful items everyone following AI should know\n"
        "## News — company moves, product launches, policy, industry shifts\n"
        "## Tools — new apps, APIs, or dev tools worth trying\n"
        "## Research — papers, model releases, technical breakthroughs\n"
        "## Skills & Learning — tutorials, courses, how-tos\n"
        "## Other — anything else notable\n\n"
        "Under each ## header write 2–4 bullet points. For each bullet:\n"
        "1) One concise English sentence with the key point.\n"
        "2) Next line: short Simplified Chinese explanation (简体中文) of the same point.\n\n"
        "After all sections, always finish with:\n"
        "## 📚 Skills to Study This Week\n"
        "List 3–5 specific skills or technologies from this digest that are most worth studying. "
        "For each, write one sentence explaining why it matters right now.\n\n"
        "No intro, no preamble. Be specific and actionable. "
        "Focus on what matters for someone actively learning AI/ML."
    )
    parts = [
        f"Summarize the following {len(items)} articles into the categories above. "
        "Use the full article text when provided.\n\n"
    ]
    for i, it in enumerate(items[:max_items], 1):
        parts.append(f"--- Article {i}: [{it.source_name}] {it.title} ---\n")
        parts.append(f"URL: {it.link}\n\n")
        if it.full_text:
            parts.append(it.full_text[:2800].strip())
            if len(it.full_text) > 2800:
                parts.append("\n[... truncated]")
        elif it.summary:
            parts.append(_strip_html(it.summary)[:800])
        else:
            parts.append("(No content)")
        parts.append("\n\n")
    return system + "\n\n" + "".join(parts)


def summarize_items(items: list[NewsItem]) -> SummarizedDigest | None:
    """Summarize a batch of news items. Returns None if provider is 'none' or missing key."""
    settings = get_settings()
    analyze = settings.get("analyze") or {}
    provider = (analyze.get("provider") or "none").lower()
    model = analyze.get("model", "")
    max_tokens = analyze.get("max_tokens", 500)

    if provider == "none" or not items:
        return SummarizedDigest(raw_items=items, summary_text="", provider="none")

    if provider == "groq":
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            logger.warning("Summarization skipped: GROQ_API_KEY not set")
            return SummarizedDigest(
                raw_items=items,
                summary_text="[Summarization skipped: GROQ_API_KEY not set]",
                provider="groq",
            )
        return _summarize_groq(items, api_key, model, max_tokens)

    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning("Summarization skipped: OPENAI_API_KEY not set")
            return SummarizedDigest(
                raw_items=items,
                summary_text="[Summarization skipped: OPENAI_API_KEY not set]",
                provider="openai",
            )
        return _summarize_openai(items, api_key, model, max_tokens)

    if provider == "ollama":
        return _summarize_ollama(items, model, max_tokens, analyze)

    return SummarizedDigest(raw_items=items, summary_text="", provider=provider)


def _summarize_groq(
    items: list[NewsItem], api_key: str, model: str, max_tokens: int
) -> SummarizedDigest:
    try:
        from groq import Groq

        client = Groq(api_key=api_key)
        prompt = _build_prompt(items)
        resp = client.chat.completions.create(
            model=model or "llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
        )
        text = (resp.choices[0].message.content or "").strip()
        logger.info("Summarized %d items with Groq", len(items))
        return SummarizedDigest(raw_items=items, summary_text=text, provider="groq")
    except Exception as e:
        logger.exception("Summarization error: %s", e)
        return SummarizedDigest(
            raw_items=items,
            summary_text=f"[Summarization error: {e}]",
            provider="groq",
        )


def _summarize_openai(
    items: list[NewsItem], api_key: str, model: str, max_tokens: int
) -> SummarizedDigest:
    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        prompt = _build_prompt(items)
        resp = client.chat.completions.create(
            model=model or "gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
        )
        text = (resp.choices[0].message.content or "").strip()
        logger.info("Summarized %d items with OpenAI", len(items))
        return SummarizedDigest(raw_items=items, summary_text=text, provider="openai")
    except Exception as e:
        logger.exception("Summarization error: %s", e)
        return SummarizedDigest(
            raw_items=items,
            summary_text=f"[Summarization error: {e}]",
            provider="openai",
        )


def _summarize_ollama(
    items: list[NewsItem], model: str, max_tokens: int, analyze: dict
) -> SummarizedDigest:
    """Use a local model via Ollama (OpenAI-compatible API). No API key, no cloud cost."""
    try:
        from openai import OpenAI

        base_url = analyze.get("ollama_base_url") or os.getenv("OLLAMA_BASE_URL") or "http://localhost:11434/v1"
        client = OpenAI(base_url=base_url, api_key="ollama")
        prompt = _build_prompt(items)
        resp = client.chat.completions.create(
            model=model or "llama3.2",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
        )
        text = (resp.choices[0].message.content or "").strip()
        logger.info("Summarized %d items with Ollama", len(items))
        return SummarizedDigest(raw_items=items, summary_text=text, provider="ollama")
    except Exception as e:
        logger.exception("Summarization error: %s", e)
        return SummarizedDigest(
            raw_items=items,
            summary_text=f"[Summarization error: {e}]",
            provider="ollama",
        )
