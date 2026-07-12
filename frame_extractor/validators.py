"""Argument and path validation."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


def parse_time(value: str | float | int | None) -> float | None:
    """Parse seconds or HH:MM:SS into seconds."""
    if value is None:
        return None
    text = str(value).strip()
    try:
        if ":" not in text:
            result = float(text)
        else:
            parts = text.split(":")
            if len(parts) != 3 or not re.fullmatch(r"\d+:[0-5]?\d:[0-5]?\d(?:\.\d+)?", text):
                raise ValueError
            result = int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"Invalid time '{value}'; use seconds or HH:MM:SS") from exc
    if result < 0:
        raise argparse.ArgumentTypeError("Time cannot be negative")
    return result


def parse_roi(value: str | None) -> tuple[int, int, int, int] | None:
    """Parse x1,y1,x2,y2 ROI coordinates."""
    if value is None:
        return None
    try:
        coords = tuple(int(item.strip()) for item in value.split(","))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("ROI must contain integer coordinates x1,y1,x2,y2") from exc
    if len(coords) != 4 or min(coords) < 0 or coords[0] >= coords[2] or coords[1] >= coords[3]:
        raise argparse.ArgumentTypeError("ROI must satisfy 0 <= x1 < x2 and 0 <= y1 < y2")
    return coords[0], coords[1], coords[2], coords[3]


def validate_roi(roi: tuple[int, int, int, int] | None, width: int, height: int) -> None:
    """Ensure ROI fits the decoded frame."""
    if roi and (roi[2] > width or roi[3] > height):
        raise ValueError(f"ROI {roi} is outside video dimensions {width}x{height}")


def validate_output_path(output: Path) -> Path:
    """Reject paths that cannot safely be used as a tool output directory."""
    resolved = output.expanduser().resolve()
    if resolved == Path(resolved.anchor) or resolved == Path.home().resolve():
        raise ValueError("Output cannot be a filesystem root or the user home directory")
    if resolved.exists() and not resolved.is_dir():
        raise ValueError("Output path exists and is not a directory")
    return resolved


def validate_args(args: argparse.Namespace) -> None:
    """Validate cross-argument constraints."""
    positive = ("fps", "interval", "every_n_frames", "max_frames", "workers", "width", "height")
    for name in positive:
        value = getattr(args, name, None)
        if value is not None and value <= 0:
            raise ValueError(f"--{name.replace('_', '-')} must be greater than zero")
    if args.end_time is not None and args.start_time is not None and args.end_time <= args.start_time:
        raise ValueError("--end-time must be greater than --start-time")
    if not 0 <= args.jpeg_quality <= 100:
        raise ValueError("--jpeg-quality must be between 0 and 100")
    if args.duplicate_threshold < 0:
        raise ValueError("--duplicate-threshold cannot be negative")
    if args.overwrite and args.resume:
        raise ValueError("--overwrite and --resume cannot be used together")
    if args.zip_with_metadata and not args.create_cvat_zip:
        raise ValueError("--zip-with-metadata requires --create-cvat-zip")
