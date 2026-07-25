"""CGC Cards style grading approximation.

CGC grades on a 1-10 scale in half-point increments and describes its
process as a holistic evaluation of centering, corners, edges, and surface
plus overall eye appeal, performed by a review committee rather than a
single grader. CGC's published standard confirms a centering subgrade of 10
needs about 55/45 front and 60/40 back, a 9.5 needs about 60/40 front, and a
9 needs about 65/35 front; reverse centering is described as generally not
exceeding about 75/25 for good grades. CGC doesn't publish anchors for
every tier or the exact combination formula, so the rest of each curve and
the weighted-average-with-a-cap logic are our own approximation, modeled
similarly to Beckett but with an evenly-balanced weighting and a slightly
more forgiving gap allowance, reflecting CGC's own description of weighing
eye appeal holistically rather than being ruled by a single weakest
attribute.
"""

from .base import (
    GradeResult, SubGrades, clamp, piecewise_centering_score, worst_axis_pct,
    round_to_granularity, DISCLAIMER,
)

GRANULARITY = 0.5

WEIGHTS = {
    "centering": 0.25,
    "corners": 0.25,
    "edges": 0.25,
    "surface": 0.25,
}

MAX_GAP_ABOVE_MIN = 1.5

# 55/45->10, 60/40->9.5, and 65/35->9 (front) are CGC's confirmed published
# anchors; everything beyond that is our own extrapolation.
FRONT_CENTERING_BREAKPOINTS = [
    (55.0, 10), (60.0, 9.5), (65.0, 9), (70.0, 8), (80.0, 6.5), (90.0, 4), (100.0, 1),
]
BACK_CENTERING_BREAKPOINTS = [
    (60.0, 10), (75.0, 8), (90.0, 4), (100.0, 1),
]


def _label(overall: float) -> str:
    if overall >= 10:
        return "Pristine"
    if overall >= 9.5:
        return "Gem Mint"
    if overall >= 9.0:
        return "Mint"
    if overall >= 8.0:
        return "NM/Mint+"
    if overall >= 7.0:
        return "Near Mint"
    if overall >= 6.0:
        return "EX-NM"
    if overall >= 5.0:
        return "Excellent"
    if overall >= 4.0:
        return "VG-EX"
    if overall >= 3.0:
        return "Very Good"
    if overall >= 2.0:
        return "Good"
    return "Poor"


def grade_cgc(sg: SubGrades) -> GradeResult:
    front_worst = max(worst_axis_pct(sg.centering_lr), worst_axis_pct(sg.centering_tb))
    back_worst = max(worst_axis_pct(sg.back_centering_lr), worst_axis_pct(sg.back_centering_tb))

    front_centering = piecewise_centering_score(front_worst, FRONT_CENTERING_BREAKPOINTS, granularity=GRANULARITY)
    back_centering = piecewise_centering_score(back_worst, BACK_CENTERING_BREAKPOINTS, granularity=GRANULARITY)
    centering = min(front_centering, back_centering)

    corners = round_to_granularity(clamp(sg.corners, 1, 10), GRANULARITY)
    edges = round_to_granularity(clamp(sg.edges, 1, 10), GRANULARITY)
    surface = round_to_granularity(clamp(sg.surface, 1, 10), GRANULARITY)

    subgrades = {"centering": centering, "corners": corners, "edges": edges, "surface": surface}

    weighted = sum(subgrades[k] * WEIGHTS[k] for k in WEIGHTS)
    weighted = round_to_granularity(weighted, GRANULARITY)

    min_sub = min(subgrades.values())
    capped = min(weighted, min_sub + MAX_GAP_ABOVE_MIN)
    overall = clamp(round_to_granularity(capped, GRANULARITY), 1, 10)

    if all(v == 10 for v in subgrades.values()):
        overall = 10.0

    notes = [
        f"Front centering measured at {front_worst:.1f}/{100 - front_worst:.1f} -> subgrade "
        f"{front_centering}; back centering at {back_worst:.1f}/{100 - back_worst:.1f} -> subgrade "
        f"{back_centering} (a 10 needs ~55/45 front and ~60/40 back per CGC's published standard).",
        f"Overall = evenly-weighted average of subgrades, capped at (lowest subgrade + {MAX_GAP_ABOVE_MIN}), "
        "approximating CGC's holistic eye-appeal review.",
        DISCLAIMER,
    ]

    return GradeResult(
        company="CGC",
        overall=overall,
        label=_label(overall),
        subgrades=subgrades,
        scale="1-10 (half-point increments)",
        notes=notes,
    )
