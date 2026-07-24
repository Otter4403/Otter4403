"""Beckett Grading Services (BGS) style grading approximation.

BGS is well known for printing four numeric subgrades (Centering, Corners,
Edges, Surface) on its labels in half-point increments, then an overall
grade. Beckett does not publish the exact rounding/weighting formula it uses
to combine the four subgrades, but collector-documented behavior is widely
understood to be close to a weighted average, with the constraint that the
overall grade cannot exceed the lowest subgrade by more than about one full
point, and that a "Black Label" Pristine 10 requires all four subgrades to
be a perfect 10. We implement that widely-observed pattern.
"""

from .base import GradeResult, SubGrades, clamp, centering_score_linear, worst_axis_pct, round_to_granularity, DISCLAIMER

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
