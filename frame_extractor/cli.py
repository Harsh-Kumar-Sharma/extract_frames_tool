"""Command-line parsing and application orchestration."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from . import __version__
from .extractor import OutputError, StorageError, estimate_bytes, expected_count, extract, extraction_mode
from .logging_config import configure_logging
from .utils import human_bytes
from .validators import parse_roi, parse_time, validate_args, validate_roi
from .video_info import VideoInfo, VideoOpenError, inspect_video


def build_parser() -> argparse.ArgumentParser:
    """Build the public CLI parser."""
    parser = argparse.ArgumentParser(prog="video-frame-extractor", description="Extract useful, CVAT-ready frames from video files.")
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--fps", type=float)
    modes.add_argument("--interval", type=float)
    modes.add_argument("--every-n-frames", type=int)
    parser.add_argument("--max-frames", type=int)
    parser.add_argument("--start-time", type=parse_time, default=0.0)
    parser.add_argument("--end-time", type=parse_time)
    parser.add_argument("--min-sharpness", type=float, default=80.0)
    parser.add_argument("--disable-blur-filter", action="store_true")
    parser.add_argument("--min-brightness", type=float, default=25.0)
    parser.add_argument("--disable-brightness-filter", action="store_true")
    parser.add_argument("--remove-duplicates", action="store_true")
    parser.add_argument("--duplicate-threshold", type=int, default=5)
    parser.add_argument("--roi", type=parse_roi)
    parser.add_argument("--format", choices=("jpg", "png"), default="jpg")
    parser.add_argument("--jpeg-quality", type=int, default=95)
    parser.add_argument("--width", type=int)
    parser.add_argument("--height", type=int)
    parser.add_argument("--resize-mode", choices=("fit", "stretch"), default="fit")
    parser.add_argument("--create-cvat-zip", action="store_true")
    parser.add_argument("--zip-with-metadata", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--workers", type=int, default=1, help="Reserved processing worker count (ordered streaming remains deterministic)")
    parser.add_argument("--log-level", choices=("DEBUG", "INFO", "WARNING", "ERROR"), default="INFO")
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def _dry_run(info: VideoInfo, args: argparse.Namespace) -> None:
    mode, value = extraction_mode(args)
    print(
        f"Video path: {info.path}\n"
        f"Duration: {info.duration:.3f} seconds\n"
        f"FPS: {info.fps:.3f}\n"
        f"Resolution: {info.width}x{info.height}\n"
        f"Total frames: {info.total_frames}"
    )
    print(
        f"Extraction mode: {mode}={value}\n"
        f"Expected extracted frames: {expected_count(info, args)}\n"
        f"Estimated output storage: {human_bytes(estimate_bytes(info, args))}"
    )
    blur = "off" if args.disable_blur_filter else args.min_sharpness
    brightness = "off" if args.disable_brightness_filter else args.min_brightness
    duplicates = "on" if args.remove_duplicates else "off"
    filters = f"blur={blur}, brightness={brightness}, duplicates={duplicates}, roi={args.roi or 'full frame'}"
    print(f"Selected filters: {filters}\nOutput location: {args.output.expanduser().resolve()}")


def main(argv: list[str] | None = None) -> int:
    """Run the CLI and translate failures to documented exit codes."""
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        validate_args(args)
    except ValueError as exc:
        parser.error(str(exc))
    try:
        info = inspect_video(args.video.expanduser())
        if args.start_time >= info.duration:
            parser.error("--start-time must be smaller than video duration")
        if args.end_time is not None and args.end_time > info.duration:
            args.end_time = info.duration
        validate_roi(args.roi, info.width, info.height)
        if args.dry_run:
            _dry_run(info, args)
            return 0
        output = args.output.expanduser().resolve()
        logger = configure_logging(args.log_level, args.quiet, None)
        result = extract(info, output, args, logger)
        return 6 if result.interrupted else 0
    except VideoOpenError as exc:
        print(f"Input video error: {exc}", file=sys.stderr)
        return 3
    except StorageError as exc:
        print(f"Insufficient storage: {exc}", file=sys.stderr)
        return 5
    except (OutputError, PermissionError, OSError) as exc:
        logging.getLogger("frame_extractor").exception("Output operation failed")
        print(f"Output error: {exc}", file=sys.stderr)
        return 4
    except ValueError as exc:
        print(f"Invalid argument: {exc}", file=sys.stderr)
        return 2
