"""CGC Cards style grading approximation.

CGC grades on a 1-10 scale in half-point increments and describes its
process as a holistic evaluation of centering, corners, edges, and surface
plus overall eye appeal, performed by a review committee rather than a
single grader. CGC has begun showing subgrades on some labels. We model it
similarly to Beckett (weighted average of the four attributes) but with an
evenly-balanced weighting and a slightly more forgiving gap allowance,
reflecting CGC's own description of weighing eye appeal holistically rather
than being ruled by a single weakest attribute.
"""

from .base import GradeResult, SubGrades, clamp, centering_score_linear, worst_axis_pct, round_to_granularity, DISCLAIMER

GRANULARITY = 0.5

WEIGHTS = {
    "centering": 0.25,
    "corners": 0.25,
    "edges": 0.25,
    "surface": 0.25,
}

MAX_GAP_ABOVE_MIN = 1.5


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
    worst_pct = max(worst_axis_pct(sg.centering_lr), worst_axis_pct(sg.centering_tb))
    centering = centering_score_linear(worst_pct, granularity=GRANULARITY)
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
        f"Worst-side centering measured at {worst_pct:.1f}/{100 - worst_pct:.1f} "
        f"-> centering subgrade {centering}.",
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
