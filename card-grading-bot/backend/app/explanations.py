"""Turns the raw measurements into plain-English answers to "why didn't
this get a 10?" -- one explanation per attribute (centering, corners,
edges, surface), independent of any single company's grading rules. Each
company's own GradeResult.notes still explains how *that company's* math
turned these same measurements into its particular number.
"""

from typing import Dict

from .grading.base import SubGrades, worst_axis_pct
from .vision.surface import SurfaceResult

NEAR_PERFECT = 9.95
GOOD_THRESHOLD = 9.5
FAIR_THRESHOLD = 8.0

CORNER_NAMES = {
    "top_left": "top-left",
    "top_right": "top-right",
    "bottom_left": "bottom-left",
    "bottom_right": "bottom-right",
}
EDGE_NAMES = {
    "top": "top",
    "bottom": "bottom",
    "left": "left",
    "right": "right",
}


def _defect_phrase(score: float, kind: str) -> str:
    """kind is 'tip' for corners or 'side' for edges."""
    if score >= GOOD_THRESHOLD:
        return "just a shade off a perfect score -- nothing a grader would call a real defect"
    if score >= FAIR_THRESHOLD:
        return f"some whitening was detected at that {kind}"
    return f"noticeable whitening/wear was detected at that {kind}"


def _explain_centering(subgrades: SubGrades) -> str:
    lr_worst = worst_axis_pct(subgrades.centering_lr)
    tb_worst = worst_axis_pct(subgrades.centering_tb)
    lr_text = f"{subgrades.centering_lr[0]:.1f}/{subgrades.centering_lr[1]:.1f}"
    tb_text = f"{subgrades.centering_tb[0]:.1f}/{subgrades.centering_tb[1]:.1f}"

    if lr_worst <= 51 and tb_worst <= 51:
        return (f"Measured at {lr_text} left-right and {tb_text} top-bottom -- "
                f"essentially a perfect 50/50 split on both axes, so centering isn't costing this card anything.")

    worse_axis = "left-right" if lr_worst >= tb_worst else "top-bottom"
    worse_pct = max(lr_worst, tb_worst)
    return (f"Measured at {lr_text} left-right and {tb_text} top-bottom. A 50/50 split on "
            f"both axes scores a perfect 10 everywhere; every company here docks points as the "
            f"split moves away from 50/50, and the {worse_axis} split ({worse_pct:.1f}/"
            f"{100 - worse_pct:.1f}) is this card's limiting axis.")


def _explain_corners(subgrades: SubGrades) -> str:
    details = subgrades.corner_details or {}
    if not details:
        return f"Blended corner condition score: {subgrades.corners:.1f}/10."

    worst_key = min(details, key=details.get)
    worst_val = details[worst_key]
    if worst_val >= NEAR_PERFECT:
        return "All four corners came back essentially perfect -- no whitening or softness detected at any tip."

    others = [f"{CORNER_NAMES.get(k, k)} {v:.1f}" for k, v in details.items() if k != worst_key]
    return (f"The {CORNER_NAMES.get(worst_key, worst_key)} corner is the weakest at {worst_val:.1f}/10 "
            f"({_defect_phrase(worst_val, 'tip')}); the other corners scored {', '.join(others)}.")


def _explain_edges(subgrades: SubGrades) -> str:
    details = subgrades.edge_details or {}
    if not details:
        return f"Blended edge condition score: {subgrades.edges:.1f}/10."

    worst_key = min(details, key=details.get)
    worst_val = details[worst_key]
    if worst_val >= NEAR_PERFECT:
        return "All four edges came back essentially perfect -- no whitening or chipping detected along any side."

    others = [f"{EDGE_NAMES.get(k, k)} {v:.1f}" for k, v in details.items() if k != worst_key]
    return (f"The {EDGE_NAMES.get(worst_key, worst_key)} edge is the weakest at {worst_val:.1f}/10 "
            f"({_defect_phrase(worst_val, 'side')}); the other edges scored {', '.join(others)}.")


def _explain_surface(front_surface: SurfaceResult, back_surface: SurfaceResult) -> str:
    front_pct = front_surface.blemish_fraction * 100
    back_pct = back_surface.blemish_fraction * 100

    if front_pct < 0.5 and back_pct < 0.5:
        return "No meaningful scratches, print lines, or stains were detected on either side."

    worse_side = "back" if back_pct > front_pct else "front"
    worse_pct = max(front_pct, back_pct)
    return (f"Detected surface texture irregularities (scratches, print lines, or staining) covering "
            f"about {worse_pct:.1f}% of the {worse_side} of the card's interior -- that's what's "
            f"pulling the surface score down (front: {front_pct:.1f}%, back: {back_pct:.1f}%).")


def build_explanations(subgrades: SubGrades, front_surface: SurfaceResult,
                        back_surface: SurfaceResult) -> Dict[str, str]:
    return {
        "centering": _explain_centering(subgrades),
        "corners": _explain_corners(subgrades),
        "edges": _explain_edges(subgrades),
        "surface": _explain_surface(front_surface, back_surface),
    }
