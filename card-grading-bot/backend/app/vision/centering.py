"""Centering measurement.

Estimates the left/right and top/bottom border widths by finding the
strongest gradient (the printed border-to-artwork line) within a search
band near each side of the card, then expresses the result as a percentage
split, e.g. (58.0, 42.0) for 58/42 left/right centering.
"""

from dataclasses import dataclass
from typing import Tuple

import cv2
import numpy as np

SEARCH_FRACTION = 0.25  # only look for the border line within the outer 25% of each side


@dataclass
class CenteringResult:
    lr: Tuple[float, float]
    tb: Tuple[float, float]
    left_px: int
    right_px: int
    top_px: int
    bottom_px: int


def _find_border_offset(profile: np.ndarray, search_px: int) -> int:
    """Return the index within the first `search_px` samples of `profile`
    with the strongest gradient magnitude -- i.e. the likely border line."""
    search_px = max(1, min(search_px, len(profile) - 1))
    window = profile[:search_px]
    if len(window) < 2:
        return 0
    grad = np.abs(np.diff(window))
    if grad.size == 0 or grad.max() <= 0:
        return search_px // 2
    return int(np.argmax(grad)) + 1


def measure_centering(card_img: np.ndarray) -> CenteringResult:
    gray = cv2.cvtColor(card_img, cv2.COLOR_BGR2GRAY).astype(np.float64)
    h, w = gray.shape

    col_profile = gray.mean(axis=0)  # average brightness per column
    row_profile = gray.mean(axis=1)  # average brightness per row

    search_w = int(w * SEARCH_FRACTION)
    search_h = int(h * SEARCH_FRACTION)

    left_px = _find_border_offset(col_profile, search_w)
    right_px = _find_border_offset(col_profile[::-1], search_w)
    top_px = _find_border_offset(row_profile, search_h)
    bottom_px = _find_border_offset(row_profile[::-1], search_h)

    lr = _to_pct(left_px, right_px)
    tb = _to_pct(top_px, bottom_px)

    return CenteringResult(lr=lr, tb=tb, left_px=left_px, right_px=right_px,
                            top_px=top_px, bottom_px=bottom_px)


def _to_pct(a: int, b: int) -> Tuple[float, float]:
    total = a + b
    if total <= 0:
        return (50.0, 50.0)
    return (round(a / total * 100, 1), round(b / total * 100, 1))
