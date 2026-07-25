"""Shared data structures and helpers used by every company's grading module."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def worst_axis_pct(pair: Tuple[float, float]) -> float:
    """Given a (side_a, side_b) centering split that sums to ~100, return the
    larger (worse) side as a percentage, e.g. (60, 40) -> 60.0."""
    a, b = pair
    total = a + b
    if total <= 0:
        return 50.0
    return max(a, b) / total * 100.0


def round_to_granularity(value: float, granularity: float) -> float:
    """Round to the nearest step (1 for whole-number scales, 0.5, 0.1, ...)."""
    if granularity <= 0:
        return value
    steps = round(value / granularity)
    result = steps * granularity
    # avoid float noise like 8.999999999
    decimals = max(0, len(str(granularity).split(".")[-1])) if "." in str(granularity) else 0
    return round(result, decimals)


def centering_score_linear(worst_pct: float, granularity: float,
                            perfect_pct: float = 50.0, floor_pct: float = 95.0,
                            min_score: float = 1.0, max_score: float = 10.0) -> float:
    """Map a worst-side centering percentage to a 0-10 style score.

    50/50 (perfect_pct) maps to max_score; floor_pct or worse maps to min_score;
    everything between is a straight line. This linear model is our own
    approximation standing in for each company's undisclosed internal
    centering charts -- it is not a leaked or reverse-engineered formula.
    """
    pct = clamp(worst_pct, perfect_pct, floor_pct)
    span = floor_pct - perfect_pct
    if span <= 0:
        raw = max_score
    else:
        raw = max_score - (pct - perfect_pct) / span * (max_score - min_score)
    raw = clamp(raw, min_score, max_score)
    return round_to_granularity(raw, granularity)


def piecewise_centering_score(worst_pct: float, breakpoints: List[Tuple[float, float]],
                                granularity: float, min_score: float = 1.0) -> float:
    """Map a worst-side centering percentage to a score using anchor points
    grounded in a company's actual published centering requirements, e.g.
    PSA's public grading descriptions (55/45 -> 10, 60/40 -> 9, 65/35 -> 8,
    ...). `breakpoints` is a list of (worst_side_pct, score) pairs; we
    linearly interpolate between the two nearest published anchors and
    clamp to the end anchors outside the published range. The anchor
    points themselves come from public grading-standard descriptions; the
    linear interpolation between them is our own approximation for values
    a company doesn't explicitly publish a breakpoint for."""
    pts = sorted(breakpoints, key=lambda p: p[0])
    if not pts:
        return min_score
    if worst_pct <= pts[0][0]:
        return round_to_granularity(pts[0][1], granularity)
    if worst_pct >= pts[-1][0]:
        return round_to_granularity(pts[-1][1], granularity)
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if x0 <= worst_pct <= x1:
            raw = y0 if x1 == x0 else y0 + (worst_pct - x0) / (x1 - x0) * (y1 - y0)
            return round_to_granularity(raw, granularity)
    return round_to_granularity(pts[-1][1], granularity)


def threshold_lookup(value: float, table: List[Tuple[float, Any]]) -> Any:
    """table is a list of (minimum_value, payload) sorted descending by
    minimum_value. Returns the payload for the first entry whose minimum is
    at or below `value`; falls back to the lowest (last) entry otherwise."""
    for threshold, payload in table:
        if value >= threshold:
            return payload
    return table[-1][1]


@dataclass
class SubGrades:
    """Condition measurements feeding every company's grading logic.

    centering_lr / centering_tb are the FRONT card's (side_a, side_b)
    percentage splits, e.g. (58.0, 42.0) for a 58/42 left/right centering.
    back_centering_lr / back_centering_tb are the same, measured on the
    back -- every company's published standard grades back centering too,
    almost always with a looser tolerance than the front. corners/edges/
    surface are generic 0-10 condition scores (10 = flawless) produced by
    the vision pipeline (or entered manually).
    """

    centering_lr: Tuple[float, float]
    centering_tb: Tuple[float, float]
    corners: float
    edges: float
    surface: float
    back_centering_lr: Tuple[float, float] = (50.0, 50.0)
    back_centering_tb: Tuple[float, float] = (50.0, 50.0)
    corner_details: Optional[Dict[str, float]] = None
    edge_details: Optional[Dict[str, float]] = None
    notes: List[str] = field(default_factory=list)


@dataclass
class GradeResult:
    company: str
    overall: float
    label: str
    subgrades: Dict[str, float]
    scale: str
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "company": self.company,
            "overall": self.overall,
            "label": self.label,
            "subgrades": self.subgrades,
            "scale": self.scale,
            "notes": self.notes,
        }


DISCLAIMER = (
    "Independent, unofficial estimate based on publicly available grading "
    "guides. Not affiliated with, endorsed by, or a substitute for grading "
    "from PSA, Beckett Grading Services (BGS), CGC Cards, TAG Grading, "
    "Sportscard Guaranty (SGC), or HGA."
)
