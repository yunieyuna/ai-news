"""
Main pipeline: gather -> analyze -> store -> notify.
Run from project root: python -m src.run
"""
from __future__ import annotations

import sys

from src.gather import fetch_rss_items
from src.analyze import summarize_items
from src.analyze.summarize import SummarizedDigest
from src.store import save_digest
from src.notify import send_notification
from src.config import get_settings


def main() -> int:
    settings = get_settings()
    notify_cfg = settings.get("notify") or {}

    # 1. Gather
    items = fetch_rss_items()
    if not items:
        print("[run] No items gathered. Check config/sources.yaml and network.")
        if notify_cfg.get("send_on_failure"):
            send_notification(
                digest=SummarizedDigest(raw_items=[], summary_text="", provider="none"),
                success=False,
                detail="No items gathered.",
            )
        return 1

    # 2. Analyze
    digest = summarize_items(items)
    if digest is None:
        digest = SummarizedDigest(raw_items=items, summary_text="", provider="none")

    # 3. Store
    path = save_digest(digest)
    print(f"[run] Digest saved to {path}")

    # 4. Notify
    if notify_cfg.get("send_on_success"):
        send_notification(digest, success=True, detail=str(path))

    return 0


if __name__ == "__main__":
    sys.exit(main())
