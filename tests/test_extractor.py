"""Extraction lifecycle tests using a tiny generated video."""

from pathlib import Path
from zipfile import ZipFile

import cv2
import numpy as np

from frame_extractor.cli import main


def make_video(path: Path) -> None:
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), 5, (64, 48))
    assert writer.isOpened()
    for index in range(10):
        frame = np.full((48, 64, 3), 30 + index * 15, dtype=np.uint8)
        cv2.putText(frame, str(index), (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        writer.write(frame)
    writer.release()


def test_extract_resume_and_existing_protection(tmp_path: Path) -> None:
    video, output = tmp_path / "sample.avi", tmp_path / "out"
    make_video(video)
    base = [
        "--video",
        str(video),
        "--output",
        str(output),
        "--every-n-frames",
        "2",
        "--disable-blur-filter",
        "--quiet",
        "--create-cvat-zip",
        "--zip-with-metadata",
    ]
    assert main(base) == 0
    assert len(list((output / "images").glob("*.jpg"))) == 5
    with ZipFile(output / "cvat_upload.zip") as archive:
        names = archive.namelist()
        assert len([name for name in names if name.endswith(".jpg")]) == 5
        assert "metadata/frames.csv" in names
    assert main(base) == 4
    assert main(base + ["--resume"]) == 0
    assert len(list((output / "images").glob("*.jpg"))) == 5


def test_dry_run_writes_nothing(tmp_path: Path) -> None:
    video, output = tmp_path / "sample.avi", tmp_path / "out"
    make_video(video)
    assert main(["--video", str(video), "--output", str(output), "--dry-run"]) == 0
    assert not output.exists()
