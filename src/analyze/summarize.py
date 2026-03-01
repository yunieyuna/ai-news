"""Summarize gathered items with an LLM. Supports Groq (free tier) or OpenAI."""
from __future__ import annotations

import os
from dataclasses import dataclass

from src.config import get_settings
from src.gather.rss import NewsItem


@dataclass
class SummarizedDigest:
    raw_items: list[NewsItem]
    summary_text: str
    provider: str


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
            return SummarizedDigest(
                raw_items=items,
                summary_text="[Summarization skipped: GROQ_API_KEY not set]",
                provider="groq",
            )
        return _summarize_groq(items, api_key, model, max_tokens)

    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return SummarizedDigest(
                raw_items=items,
                summary_text="[Summarization skipped: OPENAI_API_KEY not set]",
                provider="openai",
            )
        return _summarize_openai(items, api_key, model, max_tokens)

    return SummarizedDigest(raw_items=items, summary_text="", provider=provider)


def _build_prompt(items: list[NewsItem]) -> str:
    parts = [
        "Summarize these AI/tech news headlines in a short digest (bullet points, 2–4 sentences per topic). "
        "Focus on what matters for someone tracking AI news.\n\n"
    ]
    for i, it in enumerate(items[:30], 1):
        parts.append(f"{i}. [{it.source_name}] {it.title}\n   {it.link}\n")
        if it.summary:
            parts.append(f"   {it.summary[:300]}...\n")
    return "".join(parts)


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
        return SummarizedDigest(raw_items=items, summary_text=text, provider="groq")
    except Exception as e:
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
        return SummarizedDigest(raw_items=items, summary_text=text, provider="openai")
    except Exception as e:
        return SummarizedDigest(
            raw_items=items,
            summary_text=f"[Summarization error: {e}]",
            provider="openai",
        )
