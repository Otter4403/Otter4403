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


def test_measure_centering_ignores_a_thin_edge_artifact():
    # Simulates a perspective-correction artifact: a 1-2px sliver of a very
    # different color bleeding in right at the true edge (e.g. background
    # from an imperfect corner fit), which used to create a spurious,
    # dominant gradient at offset ~0 and make every card read as 50/50
    # regardless of its actual border.
    card = make_card_with_border(left=42, right=7, top=32, bottom=7,
                                  width=353, height=503)
    card[:, 0:2] = 5      # thin dark sliver on the left edge
    card[:, -2:] = 5      # and the right edge
    card[0:2, :] = 5      # and top/bottom
    card[-2:, :] = 5
    result = measure_centering(card)
    l, r = result.lr
    t, b = result.tb
    # should still find the real border deep at ~42/7 and ~32/7, not the
    # artifact at ~0-2, so the measured split should be meaningfully
    # off-center rather than reading as ~50/50
    assert l > 70
    assert t > 70
