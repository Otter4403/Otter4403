import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.vision.annotate import render_annotated_photo, _score_color, GOOD_COLOR, FAIR_COLOR, POOR_COLOR
from app.vision.centering import CenteringResult
from app.vision.corners import CornerResult
from app.vision.edges import EdgeResult
from app.vision.surface import SurfaceResult


def make_card(w=350, h=500):
    return np.full((h, w, 3), 180, dtype=np.uint8)


def make_results(corner_scores=None, edge_scores=None, blemish_fraction=0.0):
    corner_scores = corner_scores or {"top_left": 10.0, "top_right": 10.0, "bottom_left": 10.0, "bottom_right": 10.0}
    edge_scores = edge_scores or {"top": 10.0, "bottom": 10.0, "left": 10.0, "right": 10.0}
    corners = CornerResult(average=sum(corner_scores.values()) / 4, per_corner=corner_scores)
    edges = EdgeResult(average=sum(edge_scores.values()) / 4, per_edge=edge_scores)
    mask = np.zeros((100, 100), dtype=bool)
    if blemish_fraction > 0:
        mask[:10, :10] = True
    surface = SurfaceResult(score=10.0 - blemish_fraction * 40, blemish_fraction=blemish_fraction,
                             blemish_mask=mask, margin_y=50, margin_x=40)
    centering = CenteringResult(lr=(50.0, 50.0), tb=(50.0, 50.0), left_px=20, right_px=20, top_px=20, bottom_px=20)
    return corners, edges, surface, centering


def test_score_color_thresholds():
    assert _score_color(10.0) == GOOD_COLOR
    assert _score_color(9.5) == GOOD_COLOR
    assert _score_color(9.4) == FAIR_COLOR
    assert _score_color(8.0) == FAIR_COLOR
    assert _score_color(7.9) == POOR_COLOR


def test_render_annotated_photo_produces_valid_png_with_centering():
    corners, edges, surface, centering = make_results()
    png_bytes = render_annotated_photo(make_card(), corners, edges, surface, centering=centering)
    assert png_bytes[:8] == b"\x89PNG\r\n\x1a\n"
    img = Image.open(__import__("io").BytesIO(png_bytes))
    assert img.format == "PNG"


def test_render_annotated_photo_works_without_centering():
    # The back-of-card render has no centering measurement.
    corners, edges, surface, _ = make_results()
    png_bytes = render_annotated_photo(make_card(), corners, edges, surface, centering=None)
    assert len(png_bytes) > 0


def test_render_annotated_photo_handles_missing_corner_or_edge_keys():
    corners = CornerResult(average=10.0, per_corner={})
    edges = EdgeResult(average=10.0, per_edge={})
    _, _, surface, centering = make_results()
    png_bytes = render_annotated_photo(make_card(), corners, edges, surface, centering=centering)
    assert len(png_bytes) > 0


def test_render_annotated_photo_handles_empty_blemish_mask():
    corners, edges, _, centering = make_results()
    surface = SurfaceResult(score=10.0, blemish_fraction=0.0, blemish_mask=np.zeros((0, 0), dtype=bool),
                             margin_y=0, margin_x=0)
    png_bytes = render_annotated_photo(make_card(), corners, edges, surface, centering=centering)
    assert len(png_bytes) > 0
