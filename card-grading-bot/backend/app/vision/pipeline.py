"""Orchestrates the full front+back analysis into a single SubGrades."""

from dataclasses import dataclass, field
from typing import List

import numpy as np

from ..grading.base import SubGrades
from .preprocess import detect_card_with_confidence
from .centering import CenteringResult, measure_centering
from .corners import CornerResult, measure_corners
from .edges import EdgeResult, measure_edges
from .quality import QualityIssue, assess_quality
from .surface import SurfaceResult, measure_surface

CORNER_FRONT_WEIGHT = 0.6
EDGE_FRONT_WEIGHT = 0.6


@dataclass
class AnalysisResult:
    subgrades: SubGrades
    front_card: np.ndarray
    back_card: np.ndarray
    # Raw per-side measurements, kept around so the diagnostic overlay can
    # show exactly what was measured on each photo.
    front_centering: CenteringResult
    back_centering: CenteringResult
    front_corners: CornerResult
    back_corners: CornerResult
    front_edges: EdgeResult
    back_edges: EdgeResult
    front_surface: SurfaceResult
    back_surface: SurfaceResult
    quality_issues: List[QualityIssue] = field(default_factory=list)


def analyze_card(front_img: np.ndarray, back_img: np.ndarray) -> AnalysisResult:
    front, front_quad_found = detect_card_with_confidence(front_img)
    back, back_quad_found = detect_card_with_confidence(back_img)

    quality_issues = (
        assess_quality(front, front_quad_found, "front")
        + assess_quality(back, back_quad_found, "back")
    )

    centering = measure_centering(front)
    back_centering = measure_centering(back)

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
        "Centering is measured on both the front and back photos, since every "
        "company's published standard grades both (back is usually more lenient).",
        "Corners and edges are a 60/40 front/back weighted blend; surface uses the worse of the two sides.",
    ]

    subgrades = SubGrades(
        centering_lr=centering.lr,
        centering_tb=centering.tb,
        back_centering_lr=back_centering.lr,
        back_centering_tb=back_centering.tb,
        corners=corners_score,
        edges=edges_score,
        surface=surface_score,
        corner_details=corner_details,
        edge_details=edge_details,
        notes=notes,
    )
    return AnalysisResult(
        subgrades=subgrades, front_card=front, back_card=back,
        front_centering=centering, back_centering=back_centering,
        front_corners=corners_front, back_corners=corners_back,
        front_edges=edges_front, back_edges=edges_back,
        front_surface=surface_front, back_surface=surface_back,
        quality_issues=quality_issues,
    )
