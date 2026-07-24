"""SGC (Sportscard Guaranty) style grading approximation.

SGC is known for a numeric scale that runs from 10 up to 100 (10, 20, 30,
40, 50, 60, 70, 80, then finer 2-point steps near the top: 84, 86, 88, 90,
92, 94, 96, 98, 100), shown on its labels alongside a text description.
SGC's grading philosophy, like PSA's, is generally understood to be
dominated by the worst attribute rather than an average -- it has a
reputation among collectors for being conservative/strict on eye appeal.
We model that as a weakest-link lookup against the public number line.
"""

from .base import (
    GradeResult, SubGrades, clamp, centering_score_linear, worst_axis_pct,
    threshold_lookup, DISCLAIMER,
)

# (minimum continuous 0-10 score required across centering/corners/edges/surface, (grade, label))
GRADE_TABLE = [
    (10.0, (100, "Pristine")),
    (9.8, (98, "Gem Mint")),
    (9.6, (96, "Mint+")),
    (9.4, (94, "Mint")),
    (9.2, (92, "Mint-")),
    (9.0, (90, "NM/Mt+")),
    (8.8, (88, "NM/Mt+")),
    (8.6, (86, "NM/Mt")),
    (8.4, (84, "NM/Mt-")),
    (8.0, (80, "NM")),
    (7.0, (70, "EX/NM")),
    (6.0, (60, "EX")),
    (5.0, (50, "VG/EX")),
    (4.0, (40, "VG")),
    (3.0, (30, "Good+")),
    (2.0, (20, "Good")),
    (1.0, (10, "Poor")),
]


def grade_sgc(sg: SubGrades) -> GradeResult:
    worst_pct = max(worst_axis_pct(sg.centering_lr), worst_axis_pct(sg.centering_tb))
    centering = centering_score_linear(worst_pct, granularity=0.1)
    corners = clamp(sg.corners, 1, 10)
    edges = clamp(sg.edges, 1, 10)
    surface = clamp(sg.surface, 1, 10)

    weakest = min(centering, corners, edges, surface)
    overall, label = threshold_lookup(weakest, GRADE_TABLE)

    notes = [
        f"Worst-side centering measured at {worst_pct:.1f}/{100 - worst_pct:.1f} "
        f"-> centering component score {centering:.1f}.",
        "SGC's number line is dominated by the worst single attribute, similar "
        "to PSA's philosophy but expressed on SGC's 10-100 scale; overall = "
        "the SGC grade tier corresponding to min(centering, corners, edges, surface).",
        DISCLAIMER,
    ]

    return GradeResult(
        company="SGC",
        overall=float(overall),
        label=label,
        subgrades={
            "centering": round(centering, 1),
            "corners": round(corners, 1),
            "edges": round(edges, 1),
            "surface": round(surface, 1),
        },
        scale="10-100 (SGC number line)",
        notes=notes,
    )
