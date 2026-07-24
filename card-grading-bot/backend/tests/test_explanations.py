import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.grading.base import SubGrades
from app.vision.surface import SurfaceResult
from app.explanations import build_explanations

EXPECTED_KEYS = {"centering", "corners", "edges", "surface"}


def _surface(fraction: float) -> SurfaceResult:
    return SurfaceResult(score=10.0 - fraction * 40, blemish_fraction=fraction,
                          blemish_mask=np.zeros((1, 1), dtype=bool), margin_y=0, margin_x=0)


def perfect_subgrades() -> SubGrades:
    return SubGrades(
        centering_lr=(50.0, 50.0), centering_tb=(50.0, 50.0),
        corners=10.0, edges=10.0, surface=10.0,
        corner_details={"top_left": 10.0, "top_right": 10.0, "bottom_left": 10.0, "bottom_right": 10.0},
        edge_details={"top": 10.0, "bottom": 10.0, "left": 10.0, "right": 10.0},
    )


def test_build_explanations_returns_all_four_keys():
    result = build_explanations(perfect_subgrades(), _surface(0.0), _surface(0.0))
    assert set(result.keys()) == EXPECTED_KEYS
    assert all(isinstance(v, str) and v for v in result.values())


def test_perfect_card_gets_reassuring_explanations():
    result = build_explanations(perfect_subgrades(), _surface(0.0), _surface(0.0))
    assert "perfect" in result["centering"].lower()
    assert "perfect" in result["corners"].lower()
    assert "perfect" in result["edges"].lower()
    assert "no meaningful" in result["surface"].lower()


def test_off_center_card_names_the_limiting_axis():
    sg = perfect_subgrades()
    sg.centering_lr = (62.0, 38.0)
    sg.centering_tb = (51.0, 49.0)
    result = build_explanations(sg, _surface(0.0), _surface(0.0))
    assert "left-right" in result["centering"]
    assert "62.0/38.0" in result["centering"]


def test_weak_corner_is_named_and_others_listed():
    sg = perfect_subgrades()
    sg.corner_details = {"top_left": 7.0, "top_right": 9.9, "bottom_left": 9.9, "bottom_right": 9.9}
    result = build_explanations(sg, _surface(0.0), _surface(0.0))
    assert "top-left" in result["corners"]
    assert "7.0" in result["corners"]


def test_weak_edge_is_named():
    sg = perfect_subgrades()
    sg.edge_details = {"top": 9.9, "bottom": 9.9, "left": 6.5, "right": 9.9}
    result = build_explanations(sg, _surface(0.0), _surface(0.0))
    assert "left" in result["edges"]
    assert "6.5" in result["edges"]


def test_back_centering_named_as_limiting_when_front_is_perfect():
    sg = perfect_subgrades()
    sg.back_centering_lr = (80.0, 20.0)
    sg.back_centering_tb = (51.0, 49.0)
    result = build_explanations(sg, _surface(0.0), _surface(0.0))
    assert "back" in result["centering"]
    assert "80.0/20.0" in result["centering"]


def test_surface_explanation_names_the_worse_side():
    sg = perfect_subgrades()
    result = build_explanations(sg, _surface(0.05), _surface(0.01))
    assert "front" in result["surface"]
    assert "5.0%" in result["surface"]
