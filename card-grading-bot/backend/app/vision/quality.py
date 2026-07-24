"""Checks whether a submitted photo is actually good enough to grade
reliably, so a blurry or overly dark photo doesn't silently produce a
misleading grade -- the user gets asked to retake it instead.

Every threshold here is our own empirical heuristic, not a published
standard from any grading company; they're deliberately conservative
(erring toward a warning rather than blocking) since photo conditions vary
a lot phone to phone.
"""

from dataclasses import dataclass

import cv2
import numpy as np

# Blur: variance of the Laplacian on a size-normalized grayscale image.
# Lower variance means fewer sharp edges, i.e. a softer/blurrier photo.
BLUR_NORMALIZE_WIDTH = 800
BLUR_BLOCKING = 25.0
BLUR_WARNING = 70.0

# Resolution: the shorter side of the rectified card crop, in pixels.
RESOLUTION_BLOCKING = 120
RESOLUTION_WARNING = 260

# Contrast: standard deviation of grayscale pixel values. Very low means a
# flat, washed-out, or very dark/bright photo with little usable detail.
CONTRAST_BLOCKING = 8.0
CONTRAST_WARNING = 18.0


@dataclass
class QualityIssue:
    side: str        # "front" or "back"
    severity: str    # "blocking" or "warning"
    code: str
    message: str


def _sharpness_score(gray: np.ndarray) -> float:
    h, w = gray.shape[:2]
    long_side = max(h, w, 1)
    scale = min(1.0, BLUR_NORMALIZE_WIDTH / long_side)
    if scale < 1.0:
        gray = cv2.resize(gray, (max(1, int(w * scale)), max(1, int(h * scale))))
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def assess_quality(rectified_card: np.ndarray, quad_found: bool, side: str) -> "list[QualityIssue]":
    issues: "list[QualityIssue]" = []
    gray = cv2.cvtColor(rectified_card, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape[:2]

    sharpness = _sharpness_score(gray)
    if sharpness < BLUR_BLOCKING:
        issues.append(QualityIssue(
            side, "blocking", "too_blurry",
            f"The {side} photo looks too blurry to analyze reliably. Hold the camera steady, "
            f"let it focus on the card, and take it again.",
        ))
    elif sharpness < BLUR_WARNING:
        issues.append(QualityIssue(
            side, "warning", "soft_focus",
            f"The {side} photo looks a little soft/out of focus, which can affect corner and "
            f"surface accuracy. Consider retaking it in sharper focus.",
        ))

    min_dim = min(h, w)
    if min_dim < RESOLUTION_BLOCKING:
        issues.append(QualityIssue(
            side, "blocking", "too_low_resolution",
            f"The {side} photo's resolution is too low to measure corners and edges reliably. "
            f"Move closer to the card (without cropping it out) or use a higher-resolution camera setting.",
        ))
    elif min_dim < RESOLUTION_WARNING:
        issues.append(QualityIssue(
            side, "warning", "low_resolution",
            f"The {side} photo is a bit low-resolution for fine detail like corner whitening. "
            f"A closer, higher-resolution shot would improve accuracy.",
        ))

    contrast = float(gray.std())
    if contrast < CONTRAST_BLOCKING:
        issues.append(QualityIssue(
            side, "blocking", "too_low_contrast",
            f"The {side} photo looks very flat, too dark, or washed out, with too little detail "
            f"to analyze. Retake it in even, brighter lighting.",
        ))
    elif contrast < CONTRAST_WARNING:
        issues.append(QualityIssue(
            side, "warning", "low_contrast",
            f"The {side} photo looks a little low-contrast (dim lighting, glare, or a washed-out "
            f"shot). Better, even lighting would improve accuracy.",
        ))

    if not quad_found:
        issues.append(QualityIssue(
            side, "warning", "card_not_isolated",
            f"Couldn't clearly find the {side} card's edges against the background, so "
            f"measurements may be less precise. Try a plain surface with good contrast against the card.",
        ))

    return issues


def has_blocking_issue(issues: "list[QualityIssue]") -> bool:
    return any(issue.severity == "blocking" for issue in issues)
