"""Corner condition analysis.

Corner wear on a trading card typically shows up as whitening (the white
cardboard core exposed through worn ink/coating) concentrated right at the
tip, and/or a softened, no-longer-sharp point. We approximate both:

- whitening: fraction of pixels in a small tip-weighted patch that are
  much brighter and less saturated than the card's border color.
- softness: how strong the corner (Harris) response is right at the tip --
  a sharp, undamaged corner produces a strong, localized response.
"""

from dataclasses import dataclass
from typing import Dict

import cv2
import numpy as np

PATCH_FRACTION = 0.07


@dataclass
class CornerResult:
    average: float
    per_corner: Dict[str, float]


def _radial_weight(ph: int, pw: int, corner: str) -> np.ndarray:
    """Weight mask that peaks at the exact corner tip and fades inward,
    so defects right at the point matter more than the patch interior."""
    yy, xx = np.mgrid[0:ph, 0:pw].astype(np.float64)
    if corner == "top_left":
        dist = np.sqrt(xx ** 2 + yy ** 2)
    elif corner == "top_right":
        dist = np.sqrt((pw - 1 - xx) ** 2 + yy ** 2)
    elif corner == "bottom_left":
        dist = np.sqrt(xx ** 2 + (ph - 1 - yy) ** 2)
    else:  # bottom_right
        dist = np.sqrt((pw - 1 - xx) ** 2 + (ph - 1 - yy) ** 2)
    max_dist = np.sqrt(ph ** 2 + pw ** 2)
    return 1.0 - np.clip(dist / max_dist, 0, 1)


def _score_patch(patch: np.ndarray, corner: str, border_val: float, border_sat: float) -> float:
    if patch.size == 0:
        return 10.0
    hsv = cv2.cvtColor(patch, cv2.COLOR_BGR2HSV).astype(np.float64)
    sat = hsv[..., 1]
    val = hsv[..., 2]
    ph, pw = patch.shape[:2]
    weight = _radial_weight(ph, pw, corner)

    whitening = np.clip((val - border_val) / 60.0, 0, 1) * np.clip((border_sat - sat) / 60.0, 0, 1)
    whiteness_score = float(np.sum(whitening * weight) / max(np.sum(weight), 1e-6))

    gray = cv2.cvtColor(patch, cv2.COLOR_BGR2GRAY)
    harris = cv2.cornerHarris(np.float32(gray), 2, 3, 0.04)
    tip_region = harris * weight
    corner_strength = float(np.max(tip_region)) if tip_region.size else 0.0
    norm_strength = np.tanh(max(corner_strength, 0) / (harris.std() + 1e-6) / 5)
    softness_penalty = 1.0 - norm_strength

    penalty = whiteness_score * 7.0 + softness_penalty * 2.0
    return float(np.clip(10.0 - penalty, 1.0, 10.0))


def _border_reference(card_img: np.ndarray) -> (float, float):
    h, w = card_img.shape[:2]
    band = card_img[int(h * 0.35):int(h * 0.65), int(w * 0.02):int(w * 0.06)]
    if band.size == 0:
        band = card_img
    hsv = cv2.cvtColor(band, cv2.COLOR_BGR2HSV).astype(np.float64)
    return float(hsv[..., 2].mean()), float(hsv[..., 1].mean())


def measure_corners(card_img: np.ndarray) -> CornerResult:
    h, w = card_img.shape[:2]
    ph, pw = max(4, int(h * PATCH_FRACTION)), max(4, int(w * PATCH_FRACTION))
    border_val, border_sat = _border_reference(card_img)

    patches = {
        "top_left": card_img[0:ph, 0:pw],
        "top_right": card_img[0:ph, w - pw:w],
        "bottom_left": card_img[h - ph:h, 0:pw],
        "bottom_right": card_img[h - ph:h, w - pw:w],
    }

    scores = {name: _score_patch(patch, name, border_val, border_sat) for name, patch in patches.items()}
    average = sum(scores.values()) / len(scores)
    return CornerResult(average=average, per_corner=scores)
