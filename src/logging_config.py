"""Simple logging setup for the pipeline."""
from __future__ import annotations

import logging
import sys


def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        format="[%(levelname)s] %(message)s",
        level=level,
        stream=sys.stdout,
    )


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
