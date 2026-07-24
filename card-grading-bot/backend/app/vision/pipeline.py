"""Orchestrates the full front+back analysis into a single SubGrades."""

import numpy as np

from ..grading.base import SubGrades
from .preprocess import detect_card
from .centering import measure_centering
from .corners import measure_corners
from .edges import measure_edges
from .surface import measure_surface

CORNER_FRONT_WEIGHT = 0.6
EDGE_FRONT_WEIGHT = 0.6


def analyze_card(front_img: np.ndarray, back_img: np.ndarray) -> SubGrades:
    front = detect_card(front_img)
    back = detect_card(back_img)

    centering = measure_centering(front)

    corners_front = measure_corners(front)
    corners_back = measure_corners(back)
    corners_score = (corners_front.average * CORNER_FRONT_WEIGHT
                      + corners_back.average * (1 - CORNER_FRONT_WEIGHT))
    corner_details = {
        k: corners_front.per_corner[k] * CORNER_FRONT_WEIGHT
        + corners_back.per_corner[k] * (1 - CORNER_FRONT_WEIGHT)
        for k in corners_front.per_corner
    }

    edges_front = measure_edges(front)
    edges_back = measure_edges(back)
    edges_score = (edges_front.average * EDGE_FRONT_WEIGHT
                   + edges_back.average * (1 - EDGE_FRONT_WEIGHT))
    edge_details = {
        k: edges_front.per_edge[k] * EDGE_FRONT_WEIGHT
        + edges_back.per_edge[k] * (1 - EDGE_FRONT_WEIGHT)
        for k in edges_front.per_edge
    }

    surface_front = measure_surface(front)
    surface_back = measure_surface(back)
    surface_score = min(surface_front.score, surface_back.score)

    notes = [
        "Centering measured from the front image only, per standard grading practice.",
        "Corners and edges are a 60/40 front/back weighted blend; surface uses the worse of the two sides.",
    ]

    return SubGrades(
        centering_lr=centering.lr,
        centering_tb=centering.tb,
        corners=corners_score,
        edges=edges_score,
        surface=surface_score,
        corner_details=corner_details,
        edge_details=edge_details,
        notes=notes,
    )
