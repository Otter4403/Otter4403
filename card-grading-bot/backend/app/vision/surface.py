"""Surface condition analysis.

Looks at the interior of the card (excluding the border, which is handled
by centering/corners/edges) for localized defects -- scratches, print
lines, stains -- using a morphological top-hat / black-hat filter, which
highlights small bright or dark blobs against the local background without
being fooled by large-scale, legitimate print artwork.
"""

from dataclasses import dataclass

import cv2
import numpy as np

INTERIOR_MARGIN_FRACTION = 0.12
KERNEL_SIZE = 9
BLEMISH_THRESHOLD = 18


@dataclass
class SurfaceResult:
    score: float
    blemish_fraction: float


def _interior(card_img: np.ndarray) -> np.ndarray:
    h, w = card_img.shape[:2]
    my, mx = int(h * INTERIOR_MARGIN_FRACTION), int(w * INTERIOR_MARGIN_FRACTION)
    return card_img[my:h - my, mx:w - mx]


def measure_surface(card_img: np.ndarray) -> SurfaceResult:
    interior = _interior(card_img)
    if interior.size == 0:
        return SurfaceResult(score=10.0, blemish_fraction=0.0)

    gray = cv2.cvtColor(interior, cv2.COLOR_BGR2GRAY)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (KERNEL_SIZE, KERNEL_SIZE))
    tophat = cv2.morphologyEx(gray, cv2.MORPH_TOPHAT, kernel)
    blackhat = cv2.morphologyEx(gray, cv2.MORPH_BLACKHAT, kernel)
    defect_map = cv2.max(tophat, blackhat)

    blemish_mask = defect_map > BLEMISH_THRESHOLD
    blemish_fraction = float(blemish_mask.mean())

    score = 10.0 - np.clip(blemish_fraction * 40.0, 0, 9.0)
    return SurfaceResult(score=float(score), blemish_fraction=blemish_fraction)
