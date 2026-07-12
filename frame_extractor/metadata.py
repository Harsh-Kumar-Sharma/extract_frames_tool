"""CSV and JSON metadata persistence."""

from __future__ import annotations

import csv
import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

FRAME_FIELDS = [
    "sequential_id",
    "filename",
    "source_video",
    "source_frame_number",
    "timestamp_seconds",
    "timestamp_milliseconds",
    "video_fps",
    "frame_width",
    "frame_height",
    "output_width",
    "output_height",
    "sharpness_score",
    "brightness_score",
    "duplicate_score",
    "file_size_bytes",
    "extraction_status",
]
SKIP_FIELDS = ["source_frame_number", "timestamp_seconds", "skip_reason", "sharpness_score", "brightness_score", "duplicate_score"]


def write_csv(path: Path, fields: list[str], rows: Iterable[dict[str, Any]]) -> None:
    """Atomically rewrite a metadata CSV."""
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def read_csv(path: Path) -> list[dict[str, str]]:
    """Read existing metadata for resume."""
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_summary(path: Path, summary: dict[str, Any]) -> None:
    """Write pretty UTF-8 JSON atomically."""
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    temporary.replace(path)
