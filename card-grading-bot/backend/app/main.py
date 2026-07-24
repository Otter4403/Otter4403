from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .grading import grade_all
from .models import GradeResponse, MeasurementsOut
from .vision import analyze_card, decode_image

MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB per image

app = FastAPI(title="Otter Grading", description=(
    "Unofficial, best-effort card condition estimator inspired by the "
    "publicly described grading approaches of PSA, Beckett (BGS), CGC, "
    "TAG, SGC, and HGA. Not affiliated with any of those companies."
))

FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"


async def _read_upload(upload: UploadFile) -> bytes:
    data = await upload.read()
    if not data:
        raise HTTPException(status_code=400, detail=f"'{upload.filename}' is empty")
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail=f"'{upload.filename}' exceeds the 10MB upload limit")
    return data


@app.post("/api/grade", response_model=GradeResponse)
async def grade_card(front: UploadFile = File(...), back: UploadFile = File(...)):
    front_bytes = await _read_upload(front)
    back_bytes = await _read_upload(back)

    try:
        front_img = decode_image(front_bytes)
        back_img = decode_image(back_bytes)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    try:
        subgrades = analyze_card(front_img, back_img)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Could not analyze card images: {exc}")

    results = grade_all(subgrades)

    measurements = MeasurementsOut(
        centering_lr=list(subgrades.centering_lr),
        centering_tb=list(subgrades.centering_tb),
        corners=round(subgrades.corners, 2),
        edges=round(subgrades.edges, 2),
        surface=round(subgrades.surface, 2),
        corner_details={k: round(v, 2) for k, v in (subgrades.corner_details or {}).items()},
        edge_details={k: round(v, 2) for k, v in (subgrades.edge_details or {}).items()},
    )

    return GradeResponse(
        measurements=measurements,
        results=[r.to_dict() for r in results.values()],
    )


@app.get("/api/health")
async def health():
    return {"status": "ok"}


if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

    @app.get("/")
    async def index():
        return FileResponse(str(FRONTEND_DIR / "index.html"))
