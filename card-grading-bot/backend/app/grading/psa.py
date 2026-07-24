"""PSA-style grading approximation.

PSA (Professional Sports Authenticator) grades on a 1-10 whole-number scale
and publicly describes its grades primarily in terms of centering ranges
(e.g. "55/45 or better" for Gem Mint 10) plus qualitative descriptions of
corners, edges, surface and print quality. PSA does not publish an exact
formula for combining these into one number; collector consensus, backed by
PSA's own grade descriptions, is that the grade is effectively capped by the
worst single attribute (a "weakest link" model) -- a single sharp corner
ding or off-white edge will cap an otherwise sharp card. That weakest-link
model is what we implement here.
"""

from .base import GradeResult, SubGrades, clamp, centering_score_linear, worst_axis_pct, DISCLAIMER

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


def grade_psa(sg: SubGrades) -> GradeResult:
    worst_lr = worst_axis_pct(sg.centering_lr)
    worst_tb = worst_axis_pct(sg.centering_tb)
    worst_pct = max(worst_lr, worst_tb)

    centering_grade = int(centering_score_linear(worst_pct, granularity=1))
    corners_grade = int(round(clamp(sg.corners, 1, 10)))
    edges_grade = int(round(clamp(sg.edges, 1, 10)))
    surface_grade = int(round(clamp(sg.surface, 1, 10)))

    overall = min(centering_grade, corners_grade, edges_grade, surface_grade)
    overall = int(clamp(overall, 1, 10))

    notes = [
        f"Worst-side centering measured at {worst_pct:.1f}/{100 - worst_pct:.1f} "
        f"-> centering component grade {centering_grade}.",
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
