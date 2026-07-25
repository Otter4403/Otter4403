"""Edge condition analysis.

Looks at thin strips running along each of the 4 sides (excluding the
corner regions, which are scored separately) for whitening/chipping --
small nicks where the border color gives way to lighter exposed material.
"""

from dataclasses import dataclass
from typing import Dict

import cv2
import numpy as np

STRIP_FRACTION = 0.035
CORNER_MARGIN_FRACTION = 0.08


@dataclass
class EdgeResult:
    average: float
    per_edge: Dict[str, float]


def _whitening_fraction(strip: np.ndarray, border_val: float, border_sat: float) -> float:
    if strip.size == 0:
        return 0.0
    hsv = cv2.cvtColor(strip, cv2.COLOR_BGR2HSV).astype(np.float64)
    sat = hsv[..., 1]
    val = hsv[..., 2]
    whitening = np.clip((val - border_val) / 60.0, 0, 1) * np.clip((border_sat - sat) / 60.0, 0, 1)
    return float(whitening.mean())


def _border_reference(card_img: np.ndarray) -> (float, float):
    h, w = card_img.shape[:2]
    band = card_img[int(h * 0.35):int(h * 0.65), int(w * 0.02):int(w * 0.06)]
    if band.size == 0:
        band = card_img
    hsv = cv2.cvtColor(band, cv2.COLOR_BGR2HSV).astype(np.float64)
    return float(hsv[..., 2].mean()), float(hsv[..., 1].mean())


def measure_edges(card_img: np.ndarray) -> EdgeResult:
    h, w = card_img.shape[:2]
    strip_h = max(2, int(h * STRIP_FRACTION))
    strip_w = max(2, int(w * STRIP_FRACTION))
    margin_h = max(1, int(h * CORNER_MARGIN_FRACTION))
    margin_w = max(1, int(w * CORNER_MARGIN_FRACTION))

    strips = {
        "top": card_img[0:strip_h, margin_w:w - margin_w],
        "bottom": card_img[h - strip_h:h, margin_w:w - margin_w],
        "left": card_img[margin_h:h - margin_h, 0:strip_w],
        "right": card_img[margin_h:h - margin_h, w - strip_w:w],
    }

    border_val, border_sat = _border_reference(card_img)

    scores = {}
    for name, strip in strips.items():
        whitening = _whitening_fraction(strip, border_val, border_sat)
        scores[name] = float(np.clip(10.0 - whitening * 9.0, 1.0, 10.0))

    average = sum(scores.values()) / len(scores)
    return EdgeResult(average=average, per_edge=scores)
