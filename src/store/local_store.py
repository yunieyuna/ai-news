"""Save digests to local files (free, no DB cost)."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from src.config import PROJECT_ROOT, get_settings
from src.analyze.summarize import SummarizedDigest
from src.logging_config import get_logger

logger = get_logger("store")


def _digest_to_jsonable(digest: SummarizedDigest) -> dict:
    return {
        "summary": digest.summary_text,
        "provider": digest.provider,
        "item_count": len(digest.raw_items),
        "items": [
            {
                "title": it.title,
                "link": it.link,
                "published": it.published,
                "source_name": it.source_name,
            }
            for it in digest.raw_items
        ],
    }


def save_digest(digest: SummarizedDigest) -> Path:
    """Write digest to data/digests as markdown and optional JSON. Returns path to .md file."""
    settings = get_settings()
    store = settings.get("store") or {}
    output_dir = store.get("output_dir", "data/digests")
    save_json = store.get("save_json", True)
    out = PROJECT_ROOT / output_dir
    out.mkdir(parents=True, exist_ok=True)

    stamp = datetime.utcnow().strftime("%Y-%m-%d_%H-%M")
    md_path = out / f"digest_{stamp}.md"

    lines = [
        f"# AI News Digest — {stamp} UTC",
        "",
        "## Summary",
        "",
        digest.summary_text or "(No summary)",
        "",
        "## Items",
        "",
    ]
    for it in digest.raw_items:
        lines.append(f"- **{it.title}**")
        lines.append(f"  - Source: {it.source_name}")
        lines.append(f"  - {it.link}")
        if it.published:
            lines.append(f"  - {it.published}")
        lines.append("")

    md_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info("Saved digest to %s", md_path)

    if save_json:
        json_path = out / f"digest_{stamp}.json"
        meta = {
            "stamp": stamp,
            "path": str(md_path),
            **(_digest_to_jsonable(digest)),
        }
        json_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")

    return md_path
