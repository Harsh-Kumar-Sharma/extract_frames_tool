"""Metadata and filename tests."""

from pathlib import Path

from frame_extractor.metadata import FRAME_FIELDS, read_csv, write_csv
from frame_extractor.utils import frame_filename


def test_filename_generation() -> None:
    assert frame_filename(Path("Traffic Camera!.mp4"), 1, 1000, "jpg") == "Traffic_Camera_frame_000001_time_00001000.jpg"


def test_metadata_csv_round_trip(tmp_path: Path) -> None:
    row = {field: "" for field in FRAME_FIELDS}
    row.update({"sequential_id": 1, "filename": "a.jpg", "source_frame_number": 3})
    path = tmp_path / "frames.csv"
    write_csv(path, FRAME_FIELDS, [row])
    assert read_csv(path)[0]["filename"] == "a.jpg"
