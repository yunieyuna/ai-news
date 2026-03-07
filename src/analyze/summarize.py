"""Summarize gathered items with an LLM. Supports Ollama (local), Groq (free tier), or OpenAI."""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

from src.config import get_settings
from src.gather.rss import NewsItem
from src.logging_config import get_logger

logger = get_logger("analyze")


@dataclass
class SummarizedDigest:
    raw_items: list[NewsItem]
    summary_text: str
    provider: str
    summary_zh: str = field(default="")


def _strip_html(text: str) -> str:
    if not text:
        return ""
    return re.sub(r"<[^>]+>", "", text).strip()


def _strip_think(text: str) -> str:
    """Remove <think>...</think> chain-of-thought blocks (e.g. DeepSeek-R1)."""
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


def _clean_output(text: str) -> str:
    """Strip any model preamble before the first ## header."""
    m = re.search(r"^##", text, re.MULTILINE)
    return text[m.start():].strip() if m else text


_SYSTEM_PROMPT = (
    "你是AI/科技新闻摘要编辑。\n"
    "重要规则：\n"
    "1. 全部用简体中文输出，禁止使用英文、日文或其他语言。\n"
    "2. 直接从第一个##标题开始，不要任何开场白或解释。\n"
    "3. 严格按照下面的格式输出，不要改变结构。\n\n"
    "格式（有内容才写该分类）：\n"
    "## 🔥 必读\n"
    "- 一句话核心要点。（[阅读原文](文章URL)）\n"
    "## 新闻\n"
    "- 一句话核心要点。（[阅读原文](文章URL)）\n"
    "## 工具\n"
    "- 一句话核心要点。（[阅读原文](文章URL)）\n"
    "## 研究\n"
    "- 一句话核心要点。（[阅读原文](文章URL)）\n"
    "## 技能与学习\n"
    "- 一句话核心要点。（[阅读原文](文章URL)）\n"
    "## 其他\n"
    "- 一句话核心要点。（[阅读原文](文章URL)）\n"
    "## 📚 本周值得学习的技能\n"
    "- 技能名称：一句话说明为何现在学它重要。\n"
)


def _build_messages(items: list[NewsItem], max_items: int = 20) -> list[dict]:
    """Return a messages list with separate system and user roles."""
    parts = [f"请整理以下 {len(items[:max_items])} 篇文章：\n\n"]
    for i, it in enumerate(items[:max_items], 1):
        parts.append(f"--- 文章 {i}: [{it.source_name}] {it.title} ---\n")
        parts.append(f"URL: {it.link}\n\n")
        if it.full_text:
            parts.append(it.full_text[:2800].strip())
            if len(it.full_text) > 2800:
                parts.append("\n[... truncated]")
        elif it.summary:
            parts.append(_strip_html(it.summary)[:800])
        else:
            parts.append("(无内容)")
        parts.append("\n\n")
    return [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": "".join(parts)},
    ]


def _build_prompt(items: list[NewsItem], max_items: int = 25) -> str:
    """Legacy single-string prompt for providers that don't use message lists."""
    msgs = _build_messages(items, max_items)
    return msgs[0]["content"] + "\n\n" + msgs[1]["content"]


def _translate_prompt(english_summary: str) -> str:
    return (
        "Translate the following AI news digest to Simplified Chinese (简体中文). "
        "Preserve all markdown formatting exactly (## headers, * bullets, **bold**). "
        "Keep URLs, model names, and company names in English.\n\n"
        + english_summary
    )


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
        zh = ""
        try:
            tr = client.chat.completions.create(
                model=model or "llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": _translate_prompt(text)}],
                max_tokens=max_tokens,
            )
            zh = (tr.choices[0].message.content or "").strip()
        except Exception as e:
            logger.warning("Chinese translation failed: %s", e)
        logger.info("Summarized %d items with Groq", len(items))
        return SummarizedDigest(raw_items=items, summary_text=text, provider="groq", summary_zh=zh)
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
        zh = ""
        try:
            tr = client.chat.completions.create(
                model=model or "gpt-4o-mini",
                messages=[{"role": "user", "content": _translate_prompt(text)}],
                max_tokens=max_tokens,
            )
            zh = (tr.choices[0].message.content or "").strip()
        except Exception as e:
            logger.warning("Chinese translation failed: %s", e)
        logger.info("Summarized %d items with OpenAI", len(items))
        return SummarizedDigest(raw_items=items, summary_text=text, provider="openai", summary_zh=zh)
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
        resp = client.chat.completions.create(
            model=model or "llama3.2",
            messages=_build_messages(items),
            max_tokens=max_tokens,
        )
        text = _clean_output(_strip_think((resp.choices[0].message.content or "").strip()))

        # Translate to Chinese (local models often ignore Chinese instructions)
        zh = text
        try:
            tr_messages = [
                {
                    "role": "system",
                    "content": (
                        "你是翻译助手。将输入的新闻摘要翻译成简体中文。"
                        "严格保留所有markdown格式（##标题、-列表、**粗体**、链接）。"
                        "公司名、模型名、URL保持英文不变。只输出翻译结果，不要任何解释。"
                    ),
                },
                {"role": "user", "content": text},
            ]
            tr_resp = client.chat.completions.create(
                model=model or "llama3.2",
                messages=tr_messages,
                max_tokens=max_tokens,
            )
            zh = _strip_think((tr_resp.choices[0].message.content or "").strip()) or text
        except Exception as e:
            logger.warning("Chinese translation failed: %s", e)

        logger.info("Summarized %d items with Ollama", len(items))
        return SummarizedDigest(raw_items=items, summary_text=zh, provider="ollama")
    except Exception as e:
        logger.exception("Summarization error: %s", e)
        return SummarizedDigest(
            raw_items=items,
            summary_text=f"[Summarization error: {e}]",
            provider="ollama",
        )
