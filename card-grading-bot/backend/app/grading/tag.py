"""TAG (Technical Authentication & Grading) style grading approximation.

TAG markets itself as using computerized, camera-based measurement rather
than a human eyeballing the card -- of the six companies modeled here, it
is the closest in spirit to this project. TAG's own published materials
describe a two-layer scale: an internal 100-1000 point "TAG Score" (so two
different cards can both show as an Industry-Standard grade of "10" while
having different underlying scores, e.g. 962 vs 991), which then maps down
to the familiar 1-10 scale in half-point steps -- except TAG does not have
a 9.5: the top of the scale is 900-949 = "9", 950-989 = "10" with a "Gem
Mint" qualifier, and 990-1000 = "10" with a "Pristine" qualifier. TAG also
publishes specific front/back centering tolerances for its top tiers (about
51/49 front for Pristine, about 55/45 front for Gem Mint, tighter still for
some card types); we use the "sports card" tolerances TAG publishes as our
anchors, since this tool doesn't distinguish card type. TAG does not
publish the exact weighting formula that combines centering, the 4 corner
subgrades, the 4 edge subgrades, and surface into the final TAG Score, so
that weighting (and the centering curve below TAG's two confirmed anchors)
is our own approximation.
"""

from .base import (
    GradeResult, SubGrades, clamp, piecewise_centering_score, worst_axis_pct,
    round_to_granularity, DISCLAIMER,
)

GRANULARITY = 0.1

WEIGHTS = {
    "centering": 0.30,
    "corners": 0.25,
    "edges": 0.25,
    "surface": 0.20,
}

CORNER_KEYS = ["top_left", "top_right", "bottom_left", "bottom_right"]
EDGE_KEYS = ["top", "bottom", "left", "right"]

# TAG's own published tolerances anchor the top of this curve (51/49 for
# Pristine, 55/45 for Gem Mint, both "sports" tolerances); the rest is our
# own extrapolation.
FRONT_CENTERING_BREAKPOINTS = [
    (51.0, 10.0), (55.0, 9.9), (60.0, 9.5), (70.0, 8.5), (80.0, 7.0), (90.0, 5.0), (100.0, 1.0),
]
BACK_CENTERING_BREAKPOINTS = [
    (54.5, 10.0), (70.0, 9.5), (85.0, 7.0), (100.0, 1.0),
]

# TAG's condition-name convention for each half-grade step below 9; 9 and
# above use the Gem Mint / Pristine qualifiers handled separately.
GRADE_NAMES = {
    1.0: "Poor", 1.5: "Fair", 2.0: "Good", 2.5: "Good+", 3.0: "Very Good",
    3.5: "Very Good+", 4.0: "VG-EX", 4.5: "VG-EX+", 5.0: "Excellent",
    5.5: "Excellent+", 6.0: "EX-MT", 6.5: "EX-MT+", 7.0: "Near Mint",
    7.5: "Near Mint+", 8.0: "NM-MT", 8.5: "NM-MT+", 9.0: "Mint",
}


def _tag_score_to_grade(tag_score: float) -> "tuple[float, str]":
    """TAG's published band structure: 50-point steps from 100-949 map to
    half-grades 1-9, then 950-989 and 990-1000 both display as "10" with
    different qualifiers (TAG has no 9.5)."""
    if tag_score >= 990:
        return 10.0, "Pristine"
    if tag_score >= 950:
        return 10.0, "Gem Mint"
    clamped = clamp(tag_score, 100, 949)
    band = int((clamped - 100) // 50)
    grade = round(1.0 + band * 0.5, 1)
    grade = min(grade, 9.0)
    return grade, GRADE_NAMES.get(grade, "")


def grade_tag(sg: SubGrades) -> GradeResult:
    front_worst = max(worst_axis_pct(sg.centering_lr), worst_axis_pct(sg.centering_tb))
    back_worst = max(worst_axis_pct(sg.back_centering_lr), worst_axis_pct(sg.back_centering_tb))

    front_centering = piecewise_centering_score(front_worst, FRONT_CENTERING_BREAKPOINTS, granularity=GRANULARITY)
    back_centering = piecewise_centering_score(back_worst, BACK_CENTERING_BREAKPOINTS, granularity=GRANULARITY)
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
    composite_0_10 = sum(composite_inputs[k] * WEIGHTS[k] for k in WEIGHTS)
    tag_score = round(clamp(composite_0_10 * 100, 100, 1000))

    overall, qualifier = _tag_score_to_grade(tag_score)

    subgrades = {
        "centering": centering,
        **{f"corner_{k}": v for k, v in corner_scores.items()},
        **{f"edge_{k}": v for k, v in edge_scores.items()},
        "surface": surface,
        "tag_score": tag_score,
    }

    notes = [
        f"Front centering measured at {front_worst:.1f}/{100 - front_worst:.1f} -> subgrade "
        f"{front_centering:.1f}; back at {back_worst:.1f}/{100 - back_worst:.1f} -> subgrade "
        f"{back_centering:.1f} (TAG's published tolerances: ~51/49 front for Pristine, ~55/45 "
        f"front for Gem Mint).",
        f"TAG Score {tag_score}/1000 = weighted composite of centering, 4 corner subgrades, "
        f"4 edge subgrades, and surface, then mapped to TAG's Industry-Standard grade -- TAG's "
        f"scale has no 9.5: 950-989 shows as \"10 (Gem Mint)\" and 990-1000 as \"10 (Pristine)\".",
        DISCLAIMER,
    ]

    return GradeResult(
        company="TAG",
        overall=overall,
        label=f"TAG {overall:g} {qualifier}",
        subgrades=subgrades,
        scale="1.0-10.0 (half-point increments, no 9.5; TAG Score 100-1000 underneath)",
        notes=notes,
    )
