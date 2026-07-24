"""Beckett Grading Services (BGS) style grading approximation.

BGS is well known for printing four numeric subgrades (Centering, Corners,
Edges, Surface) on its labels in half-point increments, then an overall
grade. BGS's published materials confirm a centering subgrade of 10
requires front centering of about 55/45 or better and back centering of
about 70/30 or better; BGS does not publish anchors for every grade tier or
the exact rounding/weighting formula used to combine the four subgrades
into an overall grade, so the lower-grade tail below those two confirmed
anchors, and the weighted-average-with-a-cap combination logic, are our own
approximation of widely-documented collector consensus: the overall grade
is close to a weighted average, capped so it can't exceed the lowest
subgrade by more than about one full point, and a "Black Label" Pristine 10
requires all four subgrades to be a perfect 10.
"""

from .base import (
    GradeResult, SubGrades, clamp, piecewise_centering_score, worst_axis_pct,
    round_to_granularity, DISCLAIMER,
)

GRANULARITY = 0.5

# Weights are our own approximation of the emphasis collectors commonly
# attribute to each attribute; not an official Beckett figure.
WEIGHTS = {
    "centering": 0.20,
    "corners": 0.25,
    "edges": 0.25,
    "surface": 0.30,
}

MAX_GAP_ABOVE_MIN = 1.0

# Only the 10-subgrade anchor (55/45 front, 70/30 back) is confirmed from
# BGS's own published materials; the rest of each curve is our own
# extrapolation below that anchor.
FRONT_CENTERING_BREAKPOINTS = [
    (55.0, 10), (60.0, 9.5), (65.0, 9), (70.0, 8), (80.0, 7), (85.0, 6), (90.0, 4), (100.0, 1),
]
BACK_CENTERING_BREAKPOINTS = [
    (70.0, 10), (85.0, 7), (100.0, 1),
]


def _label(overall: float, subgrades: dict) -> str:
    if overall == 10 and all(v == 10 for v in subgrades.values()):
        return "Pristine 10 (Black Label)"
    if overall >= 9.5:
        return "Gem Mint"
    if overall >= 9.0:
        return "Mint"
    if overall >= 8.5:
        return "NM-MT+"
    if overall >= 8.0:
        return "NM-MT"
    if overall >= 7.0:
        return "Near Mint"
    if overall >= 6.0:
        return "EX-MT"
    if overall >= 5.0:
        return "Excellent"
    if overall >= 4.0:
        return "VG-EX"
    if overall >= 3.0:
        return "Very Good"
    if overall >= 2.0:
        return "Good"
    return "Poor"


def grade_beckett(sg: SubGrades) -> GradeResult:
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
        f"{back_centering} (a 10 needs ~55/45 front and ~70/30 back per BGS's published standard).",
        f"Overall = weighted average of subgrades, capped at (lowest subgrade + {MAX_GAP_ABOVE_MIN}).",
        "Black Label 10 requires a perfect 10 on all four subgrades.",
        DISCLAIMER,
    ]

    return GradeResult(
        company="Beckett (BGS)",
        overall=overall,
        label=_label(overall, subgrades),
        subgrades=subgrades,
        scale="1-10 (half-point increments)",
        notes=notes,
    )
