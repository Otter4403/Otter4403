"""PSA-style grading approximation.

PSA (Professional Sports Authenticator) grades on a 1-10 whole-number scale
and publicly describes its grades primarily in terms of centering ranges
(e.g. "55/45 or better" for Gem Mint 10) plus qualitative descriptions of
corners, edges, surface and print quality. The front-centering anchors below
(55/45=10, 60/40=9, 65/35=8, 70/30=7, 80/20=6, 85/15=5) and the back-centering
anchors (75/25=10, 90/10 floor through grade 7) come from PSA's own published
grading standards; PSA does not publish numbers for every grade tier or an
exact formula for combining centering with corners/edges/surface, so the
lower-grade tail and the interpolation between anchors are our own
approximation. Collector consensus, backed by PSA's own grade descriptions,
is that the overall grade is effectively capped by the worst single attribute
(a "weakest link" model) -- a single sharp corner ding or off-white edge
will cap an otherwise sharp card. That weakest-link model is what we
implement here.
"""

from .base import (
    GradeResult, SubGrades, clamp, piecewise_centering_score, worst_axis_pct, DISCLAIMER,
)

LABELS = {
    10: "Gem Mint",
    9: "Mint",
    8: "NM-MT",
    7: "Near Mint",
    6: "EX-MT",
    5: "Excellent",
    4: "VG-EX",
    3: "Very Good",
    2: "Good",
    1: "Poor",
}

# (worst-side centering %, grade) anchors from PSA's published grading
# standards. Anchors above 85% are our own extrapolation beyond what PSA
# publishes.
FRONT_CENTERING_BREAKPOINTS = [
    (55.0, 10), (60.0, 9), (65.0, 8), (70.0, 7), (80.0, 6), (85.0, 5), (90.0, 3), (95.0, 2), (100.0, 1),
]
BACK_CENTERING_BREAKPOINTS = [
    (75.0, 10), (90.0, 7), (100.0, 1),
]


def grade_psa(sg: SubGrades) -> GradeResult:
    front_worst = max(worst_axis_pct(sg.centering_lr), worst_axis_pct(sg.centering_tb))
    back_worst = max(worst_axis_pct(sg.back_centering_lr), worst_axis_pct(sg.back_centering_tb))

    front_centering_grade = int(piecewise_centering_score(front_worst, FRONT_CENTERING_BREAKPOINTS, granularity=1))
    back_centering_grade = int(piecewise_centering_score(back_worst, BACK_CENTERING_BREAKPOINTS, granularity=1))
    centering_grade = min(front_centering_grade, back_centering_grade)

    corners_grade = int(round(clamp(sg.corners, 1, 10)))
    edges_grade = int(round(clamp(sg.edges, 1, 10)))
    surface_grade = int(round(clamp(sg.surface, 1, 10)))

    overall = min(centering_grade, corners_grade, edges_grade, surface_grade)
    overall = int(clamp(overall, 1, 10))

    notes = [
        f"Front centering measured at {front_worst:.1f}/{100 - front_worst:.1f} -> grade "
        f"{front_centering_grade}; back centering at {back_worst:.1f}/{100 - back_worst:.1f} -> grade "
        f"{back_centering_grade} (PSA grades both sides, back more leniently).",
        "PSA's published grade descriptions are dominated by the worst single "
        "attribute; overall grade here = min(centering, corners, edges, surface).",
        DISCLAIMER,
    ]

    return GradeResult(
        company="PSA",
        overall=float(overall),
        label=LABELS[overall],
        subgrades={
            "centering": centering_grade,
            "corners": corners_grade,
            "edges": edges_grade,
            "surface": surface_grade,
        },
        scale="1-10 (whole numbers)",
        notes=notes,
    )
