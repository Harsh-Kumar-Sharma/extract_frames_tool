"""Logging setup."""

from __future__ import annotations

import logging
from pathlib import Path


def configure_logging(level: str, quiet: bool, log_path: Path | None) -> logging.Logger:
    """Configure console and optional UTF-8 file handlers."""
    logger = logging.getLogger("frame_extractor")
    logger.handlers.clear()
    logger.setLevel(getattr(logging, level.upper()))
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    if not quiet:
        console = logging.StreamHandler()
        console.setFormatter(formatter)
        logger.addHandler(console)
    if log_path:
        handler = logging.FileHandler(log_path, encoding="utf-8")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger
