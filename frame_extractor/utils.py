"""Small shared utilities."""

from __future__ import annotations

import re
from pathlib import Path


def safe_stem(path: Path) -> str:
    """Return a filesystem-safe video stem."""
    value = re.sub(r"[^A-Za-z0-9_-]+", "_", path.stem).strip("_")
    return value or "video"


def frame_filename(video: Path, sequence: int, timestamp_ms: int, extension: str) -> str:
    """Build a lexically sortable output filename."""
    return f"{safe_stem(video)}_frame_{sequence:06d}_time_{timestamp_ms:08d}.{extension}"


def human_bytes(size: int) -> str:
    """Format a byte count for terminal output."""
    value = float(size)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if value < 1024 or unit == "TiB":
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} TiB"
