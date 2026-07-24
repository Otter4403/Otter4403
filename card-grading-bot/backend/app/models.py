from typing import Dict, List

from pydantic import BaseModel


class GradeResultOut(BaseModel):
    company: str
    overall: float
    label: str
    subgrades: Dict[str, float]
    scale: str
    notes: List[str]
    slab_image_base64: str


class MeasurementsOut(BaseModel):
    centering_lr: List[float]
    centering_tb: List[float]
    corners: float
    edges: float
    surface: float
    corner_details: Dict[str, float]
    edge_details: Dict[str, float]
    explanations: Dict[str, str]
    annotated_front_base64: str
    annotated_back_base64: str


class QualityWarningOut(BaseModel):
    side: str
    code: str
    message: str


class GradeResponse(BaseModel):
    measurements: MeasurementsOut
    results: List[GradeResultOut]
    quality_warnings: List[QualityWarningOut] = []
