import base64
from pathlib import Path

import cv2
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .explanations import build_explanations
from .grading import grade_all
from .identification import identify_card
from .models import GradeResponse, MeasurementsOut
from .rendering import render_slab_png
from .vision import analyze_card, decode_image, has_blocking_issue
from .vision.annotate import render_annotated_photo

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
        analysis = analyze_card(front_img, back_img)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Could not analyze card images: {exc}")

    if has_blocking_issue(analysis.quality_issues):
        blocking = [i for i in analysis.quality_issues if i.severity == "blocking"]
        raise HTTPException(status_code=422, detail={
            "type": "photo_quality",
            "message": "One or more photos aren't clear enough to grade reliably. Please retake and resubmit.",
            "issues": [{"side": i.side, "code": i.code, "message": i.message} for i in blocking],
        })

    subgrades = analysis.subgrades
    results = grade_all(subgrades)

    _, front_card_buf = cv2.imencode(".jpg", analysis.front_card)
    identification = await identify_card(front_card_buf.tobytes())
    card_label = identification.label_line if identification and identification.identified else None

    explanations = build_explanations(subgrades, analysis.front_surface, analysis.back_surface)
    annotated_front = render_annotated_photo(
        analysis.front_card, analysis.front_corners, analysis.front_edges,
        analysis.front_surface, centering=analysis.front_centering,
    )
    annotated_back = render_annotated_photo(
        analysis.back_card, analysis.back_corners, analysis.back_edges, analysis.back_surface,
        centering=analysis.back_centering,
    )

    measurements = MeasurementsOut(
        centering_lr=list(subgrades.centering_lr),
        centering_tb=list(subgrades.centering_tb),
        back_centering_lr=list(subgrades.back_centering_lr),
        back_centering_tb=list(subgrades.back_centering_tb),
        corners=round(subgrades.corners, 2),
        edges=round(subgrades.edges, 2),
        surface=round(subgrades.surface, 2),
        corner_details={k: round(v, 2) for k, v in (subgrades.corner_details or {}).items()},
        edge_details={k: round(v, 2) for k, v in (subgrades.edge_details or {}).items()},
        explanations=explanations,
        annotated_front_base64=base64.b64encode(annotated_front).decode("ascii"),
        annotated_back_base64=base64.b64encode(annotated_back).decode("ascii"),
    )

    results_out = []
    for company_key, result in results.items():
        slab_png = render_slab_png(
            analysis.front_card, company_key, result.overall, result.label,
            cert_seed=front_bytes, subgrades=result.subgrades, card_label=card_label,
        )
        results_out.append({
            **result.to_dict(),
            "slab_image_base64": base64.b64encode(slab_png).decode("ascii"),
        })

    warnings = [i for i in analysis.quality_issues if i.severity == "warning"]

    return GradeResponse(
        measurements=measurements,
        results=results_out,
        quality_warnings=[{"side": i.side, "code": i.code, "message": i.message} for i in warnings],
        card_identification=identification.__dict__ | {"label_line": identification.label_line}
        if identification else None,
    )


@app.get("/api/health")
async def health():
    return {"status": "ok"}


if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

    @app.get("/")
    async def index():
        return FileResponse(str(FRONTEND_DIR / "index.html"))
