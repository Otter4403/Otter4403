import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.vision.centering import measure_centering


def make_card_with_border(width=350, height=500, left=30, right=30, top=40, bottom=40):
    """Solid border color with a lighter inner 'artwork' rectangle offset by
    the given margins, simulating a printed card border."""
    card = np.full((height, width, 3), 40, dtype=np.uint8)  # dark border
    card[top:height - bottom, left:width - right] = 200  # light interior
    return card


def test_measure_centering_detects_perfectly_centered_card():
    card = make_card_with_border(left=30, right=30, top=40, bottom=40)
    result = measure_centering(card)
    l, r = result.lr
    t, b = result.tb
    assert abs(l - 50) < 5
    assert abs(t - 50) < 5


def test_measure_centering_detects_off_center_card():
    # left border much wider than right -> left's share of the total margin should be larger
    card = make_card_with_border(left=45, right=15, top=40, bottom=40)
    result = measure_centering(card)
    l, r = result.lr
    assert l > r
