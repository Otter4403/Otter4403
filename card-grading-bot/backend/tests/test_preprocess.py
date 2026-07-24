import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.vision.preprocess import detect_card, STANDARD_ASPECT


def make_synthetic_card(width=350, height=500, bg_size=700):
    """A gray background with a white card-shaped rectangle roughly centered,
    simulating a photo of a card on a table."""
    bg = np.full((bg_size, bg_size, 3), 60, dtype=np.uint8)
    x0 = (bg_size - width) // 2
    y0 = (bg_size - height) // 2
    bg[y0:y0 + height, x0:x0 + width] = 230
    return bg


def test_detect_card_returns_portrait_orientation():
    img = make_synthetic_card()
    warped = detect_card(img)
    h, w = warped.shape[:2]
    assert h >= w  # portrait or square, never landscape


def test_detect_card_approximates_standard_aspect_ratio():
    img = make_synthetic_card(width=350, height=500)
    warped = detect_card(img)
    h, w = warped.shape[:2]
    aspect = w / h
    assert abs(aspect - STANDARD_ASPECT) < 0.15


def test_detect_card_handles_already_tight_crop():
    # No background contrast at all -> should fall back gracefully, not raise
    img = np.full((500, 350, 3), 200, dtype=np.uint8)
    warped = detect_card(img)
    assert warped.shape[0] > 0 and warped.shape[1] > 0
