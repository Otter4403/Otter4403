"""Shared data structures and helpers used by every company's grading module."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


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


@dataclass
class SubGrades:
    """Condition measurements feeding every company's grading logic.

    centering_lr / centering_tb are (side_a, side_b) percentage splits, e.g.
    (58.0, 42.0) for a 58/42 left/right centering. corners/edges/surface are
    generic 0-10 condition scores (10 = flawless) produced by the vision
    pipeline (or entered manually).
    """

    centering_lr: Tuple[float, float]
    centering_tb: Tuple[float, float]
    corners: float
    edges: float
    surface: float
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
    "from PSA, Beckett Grading Services (BGS), CGC Cards, or TAG Grading."
)
