"""
Main pipeline: gather -> analyze -> store -> notify.
Run from project root: python -m src.run [--dry-run] [--no-notify] [-v]
"""
from __future__ import annotations

import argparse
import sys

from src.gather import fetch_rss_items, fetch_full_articles
from src.analyze import summarize_items
from src.analyze.summarize import SummarizedDigest
from src.store import save_digest
from src.notify import send_notification
from src.config import get_settings
from src.logging_config import setup_logging, get_logger

logger = get_logger("run")


def main() -> int:
    parser = argparse.ArgumentParser(description="AI News pipeline: gather, summarize, store, notify")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only gather and analyze; do not write files or send email",
    )
    parser.add_argument(
        "--no-notify",
        action="store_true",
        help="Store digest but do not send notification",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose logging")
    args = parser.parse_args()

    setup_logging(verbose=args.verbose)
    settings = get_settings()
    notify_cfg = settings.get("notify") or {}

    # 1. Gather
    items = fetch_rss_items()
    items = fetch_full_articles(items)
    if not items:
        logger.warning("No items gathered. Check config/sources.yaml and network.")
        if not args.dry_run and notify_cfg.get("send_on_failure"):
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

    if args.dry_run:
        logger.info("Dry run: would store %d items and optionally notify.", len(digest.raw_items))
        logger.info("Summary preview: %.200s...", (digest.summary_text or "(none)")[:200])
        return 0

    # 3. Store
    path = save_digest(digest)
    logger.info("Digest saved to %s", path)

    # 4. Notify
    if not args.no_notify and notify_cfg.get("send_on_success"):
        send_notification(digest, success=True, detail=str(path))

    return 0


if __name__ == "__main__":
    sys.exit(main())
