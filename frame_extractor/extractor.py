"""Streaming video extraction engine."""

from __future__ import annotations

import logging
import platform
import shutil
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import cv2
from tqdm import tqdm

from .cvat_zip import create_cvat_zip
from .filters import brightness_score, hash_distance, perceptual_hash, sharpness_score
from .image_writer import resize_frame, write_image
from .metadata import FRAME_FIELDS, SKIP_FIELDS, read_csv, write_csv, write_summary
from .utils import frame_filename
from .validators import validate_output_path, validate_roi
from .video_info import VideoInfo


class OutputError(RuntimeError):
    """Output directory preparation or write error."""


class StorageError(RuntimeError):
    """Insufficient estimated free storage."""


@dataclass
class ExtractionResult:
    """Extraction outcome returned to the CLI."""

    saved: int
    skipped: int
    interrupted: bool
    summary: dict[str, Any]


def extraction_mode(args: Any) -> tuple[str, float | int]:
    """Return normalized mode name and value."""
    if args.interval is not None:
        return "interval", args.interval
    if args.every_n_frames is not None:
        return "every_n_frames", args.every_n_frames
    return "fps", args.fps if args.fps is not None else 1.0


def selected_frame_numbers(info: VideoInfo, args: Any) -> range:
    """Return the source-frame selection range."""
    start = round((args.start_time or 0) * info.fps)
    end_time = min(args.end_time if args.end_time is not None else info.duration, info.duration)
    end = min(info.total_frames, int(end_time * info.fps))
    mode, value = extraction_mode(args)
    if mode == "fps":
        step = max(1, round(info.fps / float(value)))
    elif mode == "interval":
        step = max(1, round(info.fps * float(value)))
    else:
        step = int(value)
    return range(start, end, step)


def expected_count(info: VideoInfo, args: Any) -> int:
    """Estimate selected frames before quality filtering."""
    count = len(selected_frame_numbers(info, args))
    return min(count, args.max_frames) if args.max_frames else count


def estimate_bytes(info: VideoInfo, args: Any) -> int:
    """Conservatively estimate output image storage."""
    width, height = info.width, info.height
    if args.width and args.height:
        if args.resize_mode == "stretch":
            width, height = args.width, args.height
        else:
            ratio = min(args.width / width, args.height / height)
            width, height = round(width * ratio), round(height * ratio)
    elif args.width:
        height, width = round(height * args.width / width), args.width
    elif args.height:
        width, height = round(width * args.height / height), args.height
    bytes_per_pixel = 0.55 if args.format == "jpg" else 2.2
    return int(expected_count(info, args) * width * height * bytes_per_pixel)


def _prepare_output(output: Path, args: Any) -> tuple[Path, Path, Path]:
    """Create safe tool directories and enforce conflict policy."""
    output = validate_output_path(output)
    images, metadata, logs = output / "images", output / "metadata", output / "logs"
    existing_images = images.exists() and any(images.iterdir())
    if existing_images and not args.overwrite and not args.resume:
        raise OutputError(f"Output already contains images: {images}. Use --overwrite or --resume.")
    if args.overwrite:
        for generated in (images, metadata, logs):
            if generated.exists():
                shutil.rmtree(generated)
        (output / "cvat_upload.zip").unlink(missing_ok=True)
    try:
        images.mkdir(parents=True, exist_ok=True)
        metadata.mkdir(parents=True, exist_ok=True)
        logs.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise OutputError(f"Cannot create output structure: {exc}") from exc
    return images, metadata, logs


def _row_float(value: Any) -> float | None:
    if value in (None, "", "None"):
        return None
    return float(value)


def extract(info: VideoInfo, output: Path, args: Any, logger: logging.Logger) -> ExtractionResult:
    """Stream selected frames through filters and persist results."""
    images, metadata, _ = _prepare_output(output, args)
    log_file = logging.FileHandler(output / "logs" / "extraction.log", encoding="utf-8")
    log_file.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(log_file)
    validate_roi(args.roi, info.width, info.height)
    needed = estimate_bytes(info, args)
    free = shutil.disk_usage(output).free
    if needed > free * 0.95:
        raise StorageError(f"Estimated output requires {needed} bytes but only {free} bytes are free")

    frame_csv, skip_csv = metadata / "frames.csv", metadata / "skipped_frames.csv"
    existing_rows = read_csv(frame_csv) if args.resume else []
    frame_rows: list[dict[str, Any]] = list(existing_rows)
    skip_rows: list[dict[str, Any]] = read_csv(skip_csv) if args.resume else []
    completed = {int(row["source_frame_number"]) for row in frame_rows}
    completed.update(int(row["source_frame_number"]) for row in skip_rows if row.get("source_frame_number", "").isdigit())
    sequence = max((int(row["sequential_id"]) for row in frame_rows), default=0)
    current_saved = len(frame_rows)
    start_wall = time.monotonic()
    started = datetime.now(timezone.utc)
    counts = {"blurry": 0, "too_dark": 0, "duplicate": 0, "invalid_frame": 0}
    for row in skip_rows:
        reason = row.get("skip_reason")
        if reason in counts:
            counts[reason] += 1
    hashes: deque[Any] = deque(maxlen=5)
    interrupted = False
    processed_run = 0
    selected = selected_frame_numbers(info, args)
    capture = cv2.VideoCapture(str(info.path))
    progress = tqdm(total=len(selected), desc="Extracting", unit="frame", disable=args.quiet)
    progress.set_postfix(saved=current_saved, skipped=len(skip_rows))
    try:
        for source_number in selected:
            if args.max_frames is not None and current_saved >= args.max_frames:
                break
            if source_number in completed:
                progress.update(1)
                continue
            capture.set(cv2.CAP_PROP_POS_FRAMES, source_number)
            ok, frame = capture.read()
            timestamp = source_number / info.fps
            processed_run += 1
            if not ok or frame is None:
                reason, sharp, bright, duplicate = "invalid_frame", None, None, None
            else:
                check = frame
                if args.roi:
                    x1, y1, x2, y2 = args.roi
                    check = frame[y1:y2, x1:x2]
                sharp = sharpness_score(check)
                bright = brightness_score(check)
                current_hash = perceptual_hash(check) if args.remove_duplicates else None
                duplicate = None
                if current_hash is not None:
                    duplicate = min((hash_distance(current_hash, prior) for prior in hashes), default=None)
                reason = None
                if not args.disable_blur_filter and sharp < args.min_sharpness:
                    reason = "blurry"
                elif not args.disable_brightness_filter and bright < args.min_brightness:
                    reason = "too_dark"
                elif args.remove_duplicates and duplicate is not None and duplicate <= args.duplicate_threshold:
                    reason = "duplicate"
            if reason:
                counts[reason] += 1
                skip_rows.append(
                    {
                        "source_frame_number": source_number,
                        "timestamp_seconds": round(timestamp, 6),
                        "skip_reason": reason,
                        "sharpness_score": sharp,
                        "brightness_score": bright,
                        "duplicate_score": duplicate,
                    }
                )
            else:
                assert sharp is not None and bright is not None
                sequence += 1
                timestamp_ms = round(timestamp * 1000)
                filename = frame_filename(info.path, sequence, timestamp_ms, args.format)
                resized = resize_frame(frame, args.width, args.height, args.resize_mode)
                size = write_image(images / filename, resized, args.format, args.jpeg_quality)
                output_h, output_w = resized.shape[:2]
                frame_rows.append(
                    {
                        "sequential_id": sequence,
                        "filename": filename,
                        "source_video": str(info.path),
                        "source_frame_number": source_number,
                        "timestamp_seconds": round(timestamp, 6),
                        "timestamp_milliseconds": timestamp_ms,
                        "video_fps": round(info.fps, 6),
                        "frame_width": info.width,
                        "frame_height": info.height,
                        "output_width": output_w,
                        "output_height": output_h,
                        "sharpness_score": round(sharp, 4),
                        "brightness_score": round(bright, 4),
                        "duplicate_score": duplicate,
                        "file_size_bytes": size,
                        "extraction_status": "saved",
                    }
                )
                current_saved += 1
                if current_hash is not None:
                    hashes.append(current_hash)
            if processed_run % 25 == 0:
                write_csv(frame_csv, FRAME_FIELDS, frame_rows)
                write_csv(skip_csv, SKIP_FIELDS, skip_rows)
            progress.set_postfix(saved=current_saved, skipped=len(skip_rows))
            progress.update(1)
    except KeyboardInterrupt:
        interrupted = True
        logger.warning("Interrupted; saving partial metadata")
    finally:
        capture.release()
        progress.close()
        write_csv(frame_csv, FRAME_FIELDS, frame_rows)
        write_csv(skip_csv, SKIP_FIELDS, skip_rows)

    ended = datetime.now(timezone.utc)
    summary = {
        "source_video_path": str(info.path),
        "source_video_filename": info.path.name,
        "video_duration_seconds": round(info.duration, 6),
        "video_fps": round(info.fps, 6),
        "total_source_frames": info.total_frames,
        "source_resolution": {"width": info.width, "height": info.height},
        "extraction_mode": extraction_mode(args)[0],
        "extraction_settings": {
            "mode_value": extraction_mode(args)[1],
            "max_frames": args.max_frames,
            "start_time": args.start_time,
            "end_time": args.end_time,
            "roi": args.roi,
            "format": args.format,
            "width": args.width,
            "height": args.height,
            "resize_mode": args.resize_mode,
            "blur_filter": not args.disable_blur_filter,
            "min_sharpness": args.min_sharpness,
            "brightness_filter": not args.disable_brightness_filter,
            "min_brightness": args.min_brightness,
            "remove_duplicates": args.remove_duplicates,
            "duplicate_threshold": args.duplicate_threshold,
        },
        "processed_frame_count": len(frame_rows) + len(skip_rows),
        "saved_frame_count": len(frame_rows),
        "skipped_blurry_count": counts["blurry"],
        "skipped_dark_count": counts["too_dark"],
        "skipped_duplicate_count": counts["duplicate"],
        "invalid_frame_count": counts["invalid_frame"],
        "output_folder": str(output.resolve()),
        "processing_start_time": started.isoformat(),
        "processing_end_time": ended.isoformat(),
        "total_processing_duration_seconds": round(time.monotonic() - start_wall, 3),
        "estimated_disk_usage_bytes": sum(int(row["file_size_bytes"]) for row in frame_rows),
        "python_version": platform.python_version(),
        "opencv_version": cv2.__version__,
        "status": "interrupted" if interrupted else "completed",
        "workers": args.workers,
    }
    write_summary(metadata / "summary.json", summary)
    if args.create_cvat_zip and not interrupted:
        create_cvat_zip(output, args.zip_with_metadata)
    logger.info("Saved %d frames; skipped %d", len(frame_rows), len(skip_rows))
    return ExtractionResult(len(frame_rows), len(skip_rows), interrupted, summary)
