from typing import Dict, List

from pydantic import BaseModel


class GradeResultOut(BaseModel):
    company: str
    overall: float
    label: str
    subgrades: Dict[str, float]
    scale: str
    notes: List[str]


class MeasurementsOut(BaseModel):
    centering_lr: List[float]
    centering_tb: List[float]
    corners: float
    edges: float
    surface: float
    corner_details: Dict[str, float]
    edge_details: Dict[str, float]


class GradeResponse(BaseModel):
    measurements: MeasurementsOut
    results: List[GradeResultOut]
