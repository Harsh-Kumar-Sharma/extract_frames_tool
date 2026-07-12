"""Image resizing and durable writing."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np


def resize_frame(frame: np.ndarray, width: int | None, height: int | None, mode: str) -> np.ndarray:
    """Resize according to requested dimensions and aspect rules."""
    original_h, original_w = frame.shape[:2]
    if width is None and height is None:
        return frame
    if width is None:
        assert height is not None
        width = max(1, round(original_w * height / original_h))
    elif height is None:
        height = max(1, round(original_h * width / original_w))
    elif mode == "fit":
        ratio = min(width / original_w, height / original_h)
        width, height = max(1, round(original_w * ratio)), max(1, round(original_h * ratio))
    assert width is not None and height is not None
    interpolation = cv2.INTER_AREA if width < original_w or height < original_h else cv2.INTER_LINEAR
    return cv2.resize(frame, (width, height), interpolation=interpolation)


def write_image(path: Path, frame: np.ndarray, image_format: str, jpeg_quality: int) -> int:
    """Encode and write an image, returning its byte size."""
    params = [cv2.IMWRITE_JPEG_QUALITY, jpeg_quality] if image_format == "jpg" else [cv2.IMWRITE_PNG_COMPRESSION, 3]
    ok, encoded = cv2.imencode(f".{image_format}", frame, params)
    if not ok:
        raise OSError(f"OpenCV failed to encode {path.name}")
    path.write_bytes(encoded.tobytes())
    return path.stat().st_size
