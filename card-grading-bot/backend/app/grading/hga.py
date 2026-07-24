"""HGA (Hybrid Grading Approach) style grading approximation.

HGA markets itself, like TAG, around camera/AI-based measurement rather
than a human grader's eye, and reports grades to two decimal places (e.g.
9.75, 8.83) rather than whole or half points -- the finest granularity of
any company modeled here. We mirror TAG's structure (a weighted composite
across centering, all 4 corners, all 4 edges, and surface) but at hundredth
-of-a-point precision and with our own weighting, leaning slightly more on
surface, which HGA's marketing emphasizes (raking-light surface imaging).
"""

from .base import (
    GradeResult, SubGrades, clamp, centering_score_linear, worst_axis_pct,
    round_to_granularity, DISCLAIMER,
)

GRANULARITY = 0.01

WEIGHTS = {
    "centering": 0.25,
    "corners": 0.25,
    "edges": 0.20,
    "surface": 0.30,
}

CORNER_KEYS = ["top_left", "top_right", "bottom_left", "bottom_right"]
EDGE_KEYS = ["top", "bottom", "left", "right"]


def _label(overall: float) -> str:
    if overall >= 10:
        return "HGA 10 Pristine"
    if overall >= 9.5:
        return "HGA 9.5+ Gem Mint"
    if overall >= 9.0:
        return "HGA 9 Mint"
    if overall >= 8.0:
        return "HGA 8 NM-MT"
    if overall >= 7.0:
        return "HGA 7 Near Mint"
    if overall >= 6.0:
        return "HGA 6 EX-MT"
    if overall >= 5.0:
        return "HGA 5 Excellent"
    return "HGA <5"


def grade_hga(sg: SubGrades) -> GradeResult:
    worst_pct = max(worst_axis_pct(sg.centering_lr), worst_axis_pct(sg.centering_tb))
    centering = centering_score_linear(worst_pct, granularity=GRANULARITY)

    corner_details = sg.corner_details or {k: sg.corners for k in CORNER_KEYS}
    edge_details = sg.edge_details or {k: sg.edges for k in EDGE_KEYS}

    corner_scores = {k: round_to_granularity(clamp(corner_details.get(k, sg.corners), 1, 10), GRANULARITY)
                      for k in CORNER_KEYS}
    edge_scores = {k: round_to_granularity(clamp(edge_details.get(k, sg.edges), 1, 10), GRANULARITY)
                   for k in EDGE_KEYS}

    corners_avg = sum(corner_scores.values()) / len(corner_scores)
    edges_avg = sum(edge_scores.values()) / len(edge_scores)
    surface = round_to_granularity(clamp(sg.surface, 1, 10), GRANULARITY)

    composite_inputs = {
        "centering": centering,
        "corners": corners_avg,
        "edges": edges_avg,
        "surface": surface,
    }
    overall = sum(composite_inputs[k] * WEIGHTS[k] for k in WEIGHTS)
    overall = clamp(round_to_granularity(overall, GRANULARITY), 1, 10)

    subgrades = {
        "centering": centering,
        **{f"corner_{k}": v for k, v in corner_scores.items()},
        **{f"edge_{k}": v for k, v in edge_scores.items()},
        "surface": surface,
    }

    notes = [
        f"Worst-side centering measured at {worst_pct:.1f}/{100 - worst_pct:.1f} "
        f"-> centering subgrade {centering:.2f}.",
        "Overall = weighted composite of centering, 4 corner subgrades, 4 edge "
        "subgrades, and surface, reported to the hundredth of a point -- "
        "mirroring HGA's published imaging-based measurement approach.",
        DISCLAIMER,
    ]

    return GradeResult(
        company="HGA",
        overall=overall,
        label=_label(overall),
        subgrades=subgrades,
        scale="1.00-10.00 (hundredth-point increments)",
        notes=notes,
    )
