"""HGA (Hybrid Grading Approach) style grading approximation.

HGA markets itself, like TAG, around camera/AI-based measurement rather
than a human grader's eye, and reports grades to two decimal places (e.g.
9.75, 8.83) rather than whole or half points -- the finest granularity of
any company modeled here. Unlike PSA/BGS/CGC/SGC/TAG, we could not find any
specific published centering-percentage breakpoints from HGA, so its
centering curve stays the generic linear model (50/50=10 down to 95/5=1)
used as a fallback elsewhere in this project, applied to both front and
back photos. We mirror TAG's structure (a weighted composite across
centering, all 4 corners, all 4 edges, and surface) but at hundredth-of-a
-point precision and with our own weighting, leaning slightly more on
surface, which HGA's marketing emphasizes (raking-light surface imaging).
"""

from .base import (
    GradeResult, SubGrades, centering_score_linear, clamp, worst_axis_pct,
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
    front_worst = max(worst_axis_pct(sg.centering_lr), worst_axis_pct(sg.centering_tb))
    back_worst = max(worst_axis_pct(sg.back_centering_lr), worst_axis_pct(sg.back_centering_tb))
    front_centering = centering_score_linear(front_worst, granularity=GRANULARITY)
    back_centering = centering_score_linear(back_worst, granularity=GRANULARITY)
    centering = min(front_centering, back_centering)

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
        f"Front centering measured at {front_worst:.1f}/{100 - front_worst:.1f} -> subgrade "
        f"{front_centering:.2f}; back at {back_worst:.1f}/{100 - back_worst:.1f} -> subgrade "
        f"{back_centering:.2f} (no published HGA centering breakpoints were found, so this "
        f"uses our generic 50/50=10 to 95/5=1 fallback curve for both sides).",
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
