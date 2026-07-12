"""Quality filter tests."""

import cv2
import numpy as np

from frame_extractor.filters import brightness_score, hash_distance, perceptual_hash, sharpness_score


def test_brightness() -> None:
    assert brightness_score(np.full((10, 10, 3), 42, dtype=np.uint8)) == 42


def test_sharpness_distinguishes_edges() -> None:
    flat = np.full((100, 100, 3), 100, dtype=np.uint8)
    edges = flat.copy()
    cv2.rectangle(edges, (20, 20), (80, 80), (255, 255, 255), 3)
    assert sharpness_score(edges) > sharpness_score(flat)


def test_duplicate_hash() -> None:
    image = np.zeros((50, 50, 3), dtype=np.uint8)
    assert hash_distance(perceptual_hash(image), perceptual_hash(image.copy())) == 0
