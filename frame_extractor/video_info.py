"""Video inspection utilities."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

import cv2


class VideoOpenError(RuntimeError):
    """Raised when OpenCV cannot decode a video."""


@dataclass(frozen=True)
class VideoInfo:
    """Properties reported by OpenCV VideoCapture."""

    path: Path
    fps: float
    total_frames: int
    width: int
    height: int
    duration: float

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["path"] = str(self.path)
        return data


def inspect_video(path: Path) -> VideoInfo:
    """Open a video and return validated stream metadata."""
    if not path.exists() or not path.is_file():
        raise VideoOpenError(f"Video file does not exist: {path}")
    capture = cv2.VideoCapture(str(path))
    try:
        if not capture.isOpened():
            raise VideoOpenError("OpenCV cannot open the video; verify the file or install FFmpeg/convert its codec")
        fps = float(capture.get(cv2.CAP_PROP_FPS))
        total = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        if fps <= 0 or total <= 0 or width <= 0 or height <= 0:
            raise VideoOpenError("Video metadata is invalid; the file may be corrupted or use an unsupported codec")
        return VideoInfo(path.resolve(), fps, total, width, height, total / fps)
    finally:
        capture.release()
