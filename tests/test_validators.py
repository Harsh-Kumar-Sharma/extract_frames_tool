"""Validator tests."""

import argparse
from pathlib import Path

import pytest

from frame_extractor.validators import parse_roi, parse_time, validate_args, validate_output_path


def test_parse_time_seconds_and_clock() -> None:
    assert parse_time("300") == 300
    assert parse_time("01:02:03.5") == 3723.5


@pytest.mark.parametrize("value", ["-1", "1:99:00", "bad"])
def test_parse_time_rejects_invalid(value: str) -> None:
    with pytest.raises(argparse.ArgumentTypeError):
        parse_time(value)


def test_parse_roi() -> None:
    assert parse_roi("10, 20, 100, 200") == (10, 20, 100, 200)
    with pytest.raises(argparse.ArgumentTypeError):
        parse_roi("10,20,5,30")


def test_output_path_rejects_file(tmp_path: Path) -> None:
    file = tmp_path / "file"
    file.write_text("x")
    with pytest.raises(ValueError):
        validate_output_path(file)


def test_cross_argument_validation() -> None:
    args = argparse.Namespace(
        fps=1,
        interval=None,
        every_n_frames=None,
        max_frames=None,
        workers=1,
        width=None,
        height=None,
        end_time=5,
        start_time=10,
        jpeg_quality=95,
        duplicate_threshold=5,
        overwrite=False,
        resume=False,
        zip_with_metadata=False,
        create_cvat_zip=False,
    )
    with pytest.raises(ValueError, match="end-time"):
        validate_args(args)
