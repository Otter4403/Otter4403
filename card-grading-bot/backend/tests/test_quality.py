import sys
from pathlib import Path

import numpy as np
import cv2

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.vision.quality import assess_quality, has_blocking_issue
from app.vision.preprocess import detect_card_with_confidence


def make_sharp_card(w=350, h=500):
    card = np.full((h, w, 3), 210, dtype=np.uint8)
    card[10:h - 10, 15:w - 15] = 180
    cv2.putText(card, "SAMPLE TEXT HERE", (20, h // 2), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (30, 30, 30), 2)
    for x in range(0, w, 7):
        cv2.line(card, (x, 0), (x, h), (60, 60, 60), 1)
    return card


def test_sharp_high_contrast_photo_has_no_issues():
    card = make_sharp_card()
    issues = assess_quality(card, quad_found=True, side="front")
    assert issues == []
    assert not has_blocking_issue(issues)


def test_heavily_blurred_photo_is_blocking():
    card = make_sharp_card()
    blurred = cv2.GaussianBlur(card, (45, 45), 20)
    issues = assess_quality(blurred, quad_found=True, side="front")
    assert has_blocking_issue(issues)
    codes = {i.code for i in issues}
    assert "too_blurry" in codes


def test_tiny_image_is_blocking_on_resolution():
    card = make_sharp_card()
    tiny = cv2.resize(card, (20, 28))
    issues = assess_quality(tiny, quad_found=True, side="back")
    assert has_blocking_issue(issues)
    codes = {i.code for i in issues}
    assert "too_low_resolution" in codes


def test_flat_dark_image_is_blocking_on_contrast():
    flat = np.full((500, 350, 3), 20, dtype=np.uint8)
    issues = assess_quality(flat, quad_found=True, side="front")
    assert has_blocking_issue(issues)
    codes = {i.code for i in issues}
    assert "too_low_contrast" in codes


def test_missing_quad_adds_a_non_blocking_warning():
    card = make_sharp_card()
    issues = assess_quality(card, quad_found=False, side="front")
    assert not has_blocking_issue(issues)
    codes = {i.code for i in issues}
    assert "card_not_isolated" in codes


def test_issues_are_tagged_with_the_correct_side():
    card = make_sharp_card()
    blurred = cv2.GaussianBlur(card, (45, 45), 20)
    issues = assess_quality(blurred, quad_found=True, side="back")
    assert all(i.side == "back" for i in issues)


def test_detect_card_with_confidence_reports_false_on_ambiguous_background():
    # A flat, featureless image gives no strong contour to find.
    flat = np.full((400, 400, 3), 128, dtype=np.uint8)
    _, quad_found = detect_card_with_confidence(flat)
    assert quad_found is False
