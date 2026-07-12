"""CLI parser tests."""

import pytest

from frame_extractor.cli import build_parser


def test_extraction_modes_are_mutually_exclusive() -> None:
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["--video", "x", "--output", "y", "--fps", "1", "--interval", "2"])


def test_default_mode_is_resolved_by_engine() -> None:
    args = build_parser().parse_args(["--video", "x", "--output", "y"])
    assert args.fps is None and args.interval is None and args.every_n_frames is None
