"""TAG (Technical Authentication & Grading) style grading approximation.

TAG markets itself as using computerized, camera-based measurement rather
than a human eyeballing the card -- of the four companies modeled here, it
is the closest in spirit to this project. TAG reports individual numeric
subgrades (to one decimal place) for centering, each of the 4 corners, each
of the 4 edges, and surface, then a single weighted composite "TAG Number".
We mirror that structure: if per-corner/per-edge detail is available from
the vision pipeline we use it directly, otherwise we fall back to the
aggregate corners/edges scores for all four positions.
"""

from .base import GradeResult, SubGrades, clamp, centering_score_linear, worst_axis_pct, round_to_granularity, DISCLAIMER

GRANULARITY = 0.1

WEIGHTS = {
    "centering": 0.30,
    "corners": 0.25,
    "edges": 0.25,
    "surface": 0.20,
}

CORNER_KEYS = ["top_left", "top_right", "bottom_left", "bottom_right"]
EDGE_KEYS = ["top", "bottom", "left", "right"]


def _label(overall: float) -> str:
    if overall >= 10:
        return "TAG 10 Pristine"
    if overall >= 9.5:
        return "TAG 9.5+ Gem Mint"
    if overall >= 9.0:
        return "TAG 9 Mint"
    if overall >= 8.0:
        return "TAG 8 NM-MT"
    if overall >= 7.0:
        return "TAG 7 Near Mint"
    if overall >= 6.0:
        return "TAG 6 EX-MT"
    if overall >= 5.0:
        return "TAG 5 Excellent"
    return "TAG <5"


def grade_tag(sg: SubGrades) -> GradeResult:
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
        f"-> centering subgrade {centering}.",
        "Overall = weighted composite of centering, 4 corner subgrades, 4 edge "
        "subgrades, and surface, reported to one decimal place -- mirroring "
        "TAG's published automated-measurement approach.",
        DISCLAIMER,
    ]

    return GradeResult(
        company="TAG",
        overall=overall,
        label=_label(overall),
        subgrades=subgrades,
        scale="1.0-10.0 (tenth-point increments)",
        notes=notes,
    )
