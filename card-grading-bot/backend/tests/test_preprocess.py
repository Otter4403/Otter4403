import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.vision.preprocess import detect_card, detect_card_with_confidence, STANDARD_ASPECT


def make_synthetic_card(width=350, height=500, bg_size=700):
    """A gray background with a white card-shaped rectangle roughly centered,
    simulating a photo of a card on a table."""
    bg = np.full((bg_size, bg_size, 3), 60, dtype=np.uint8)
    x0 = (bg_size - width) // 2
    y0 = (bg_size - height) // 2
    bg[y0:y0 + height, x0:x0 + width] = 230
    return bg


def make_rotated_card(width=350, height=500, bg_size=900, angle_deg=20, notch=0):
    """A card-shaped rectangle rotated in-plane by `angle_deg`, simulating a
    photo taken at an angle instead of straight-on. `notch` optionally cuts
    a triangular corner out (a stand-in for a shadow, glare, or slight
    occlusion rounding a corner off in a real photo), which is what makes
    approxPolyDP fail to collapse to a clean 4-point polygon at a single
    fixed tolerance."""
    bg = np.full((bg_size, bg_size, 3), 60, dtype=np.uint8)
    cx, cy = bg_size // 2, bg_size // 2
    box = cv2.boxPoints(((cx, cy), (width, height), angle_deg)).astype(np.int32)
    cv2.fillConvexPoly(bg, box, (230, 230, 230))
    if notch:
        corner = box[0]
        p1 = box[0] + (box[1] - box[0]) * (notch / np.linalg.norm(box[1] - box[0]))
        p2 = box[0] + (box[3] - box[0]) * (notch / np.linalg.norm(box[3] - box[0]))
        cv2.fillConvexPoly(bg, np.array([corner, p1, p2], dtype=np.int32), (60, 60, 60))
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


def test_detect_card_corrects_perspective_across_a_range_of_angles():
    for angle in (0, 8, 15, 25, 35):
        img = make_rotated_card(angle_deg=angle)
        warped, quad_found = detect_card_with_confidence(img)
        h, w = warped.shape[:2]
        aspect = min(w, h) / max(w, h)
        assert quad_found is True
        assert abs(aspect - STANDARD_ASPECT) < 0.05, f"angle={angle} aspect={aspect}"


def test_detect_card_recovers_a_clean_quad_when_a_corner_is_occluded():
    # A big-enough notch makes a single fixed approxPolyDP tolerance fail
    # to collapse to 4 points -- the old fallback (axis-aligned bounding
    # box) would bake the tilt in instead of correcting it. Trying a range
    # of tolerances (or falling back to the rotated minAreaRect) should
    # still recover a proper perspective correction.
    img = make_rotated_card(angle_deg=25, notch=110)
    warped, quad_found = detect_card_with_confidence(img)
    h, w = warped.shape[:2]
    aspect = min(w, h) / max(w, h)
    assert quad_found is True
    assert abs(aspect - STANDARD_ASPECT) < 0.05


def test_detect_card_still_returns_a_usable_crop_when_truly_ambiguous():
    # Even in a worst case where neither approxPolyDP nor minAreaRect
    # produce a plausible card-shaped quad, detection should still return
    # *something* usable rather than raising or returning an empty image.
    img = make_rotated_card(angle_deg=25, notch=170)
    warped, _ = detect_card_with_confidence(img)
    assert warped.shape[0] > 0 and warped.shape[1] > 0
