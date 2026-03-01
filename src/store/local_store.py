"""Save digests to local files (free, no DB cost)."""
from __future__ import annotations

from pathlib import Path
from datetime import datetime

from src.config import PROJECT_ROOT, get_settings
from src.analyze.summarize import SummarizedDigest


def save_digest(digest: SummarizedDigest) -> Path:
    """Write digest to data/digests as markdown. Returns path to main file."""
    settings = get_settings()
    store = settings.get("store") or {}
    output_dir = store.get("output_dir", "data/digests")
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
    return md_path
