"""Frame quality measurements."""

from __future__ import annotations

import cv2
import numpy as np


def grayscale(frame: np.ndarray) -> np.ndarray:
    """Convert BGR input to grayscale, preserving grayscale input."""
    return frame if frame.ndim == 2 else cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)


def sharpness_score(frame: np.ndarray) -> float:
    """Measure focus using Laplacian variance."""
    return float(cv2.Laplacian(grayscale(frame), cv2.CV_64F).var())


def brightness_score(frame: np.ndarray) -> float:
    """Return mean grayscale brightness in [0, 255]."""
    return float(np.mean(grayscale(frame)))


def perceptual_hash(frame: np.ndarray, hash_size: int = 8) -> np.ndarray:
    """Produce a lightweight 64-bit perceptual DCT hash."""
    gray = cv2.resize(grayscale(frame), (32, 32), interpolation=cv2.INTER_AREA)
    dct = cv2.dct(np.float32(gray))[:hash_size, :hash_size]
    return dct > np.median(dct)


def hash_distance(left: np.ndarray, right: np.ndarray) -> int:
    """Return Hamming distance between perceptual hashes."""
    return int(np.count_nonzero(left != right))
