"""Draws a diagnostic overlay on a rectified card photo showing exactly
what the vision pipeline measured: the centering border lines it detected,
a bracket at each corner colored by that corner's score, a colored strip
along each edge, and a highlight over any surface area flagged as a
blemish. This is what lets the "why did this get a 9.5" answer point at a
specific spot on the photo instead of just a number.
"""

import io
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .centering import CenteringResult
from .corners import CornerResult, PATCH_FRACTION as CORNER_PATCH_FRACTION
from .edges import EdgeResult, STRIP_FRACTION, CORNER_MARGIN_FRACTION
from .surface import SurfaceResult

FONTS_DIR = Path(__file__).resolve().parent.parent / "fonts"

DISPLAY_MAX_W = 460

GOOD_COLOR = (58, 158, 108)      # score >= GOOD_THRESHOLD
FAIR_COLOR = (212, 158, 42)      # FAIR_THRESHOLD <= score < GOOD_THRESHOLD
POOR_COLOR = (206, 46, 66)       # score < FAIR_THRESHOLD
CENTERING_COLOR = (60, 140, 230)
BLEMISH_COLOR = (230, 90, 40)

GOOD_THRESHOLD = 9.5
FAIR_THRESHOLD = 8.0


def _font(name: str, size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(str(FONTS_DIR / name), size)
    except OSError:
        return ImageFont.load_default()


def _score_color(score: float):
    if score >= GOOD_THRESHOLD:
        return GOOD_COLOR
    if score >= FAIR_THRESHOLD:
        return FAIR_COLOR
    return POOR_COLOR


def _label_with_backdrop(draw: ImageDraw.ImageDraw, xy, text: str, font, fill) -> None:
    x, y = xy
    box = draw.textbbox((x, y), text, font=font)
    pad = 2
    draw.rectangle([box[0] - pad, box[1] - pad, box[2] + pad, box[3] + pad], fill=(255, 255, 255, 235))
    draw.text((x, y), text, font=font, fill=fill)


def render_annotated_photo(card_bgr: np.ndarray, corners: CornerResult, edges: EdgeResult,
                            surface: SurfaceResult, centering: Optional[CenteringResult] = None) -> bytes:
    card_rgb = cv2.cvtColor(card_bgr, cv2.COLOR_BGR2RGB)
    img = Image.fromarray(card_rgb).convert("RGBA")

    scale = min(1.0, DISPLAY_MAX_W / img.width)
    if scale < 1.0:
        img = img.resize((int(img.width * scale), int(img.height * scale)), Image.LANCZOS)
    w, h = img.size

    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    label_font = _font("DejaVuSans-Bold.ttf", 12)

    # Surface: tint any flagged blemish pixels directly on the photo.
    if surface.blemish_mask.size:
        mask_h, mask_w = surface.blemish_mask.shape
        tint = np.zeros((mask_h, mask_w, 4), dtype=np.uint8)
        tint[surface.blemish_mask] = (*BLEMISH_COLOR, 130)
        tint_img = Image.fromarray(tint, mode="RGBA")
        target_w = int(mask_w * scale)
        target_h = int(mask_h * scale)
        if target_w > 0 and target_h > 0:
            tint_img = tint_img.resize((target_w, target_h), Image.NEAREST)
            overlay.alpha_composite(tint_img, (int(surface.margin_x * scale), int(surface.margin_y * scale)))

    # Centering: dashed lines at the detected border offsets, each labeled
    # with the measured percentage split for that axis.
    if centering is not None:
        left_x = int(centering.left_px * scale)
        right_x = w - int(centering.right_px * scale)
        top_y = int(centering.top_px * scale)
        bottom_y = h - int(centering.bottom_px * scale)
        for x in (left_x, right_x):
            for y in range(0, h, 10):
                draw.line([(x, y), (x, min(y + 5, h))], fill=(*CENTERING_COLOR, 220), width=2)
        for y in (top_y, bottom_y):
            for x in range(0, w, 10):
                draw.line([(x, y), (min(x + 5, w), y)], fill=(*CENTERING_COLOR, 220), width=2)
        lr_text = f"{centering.lr[0]:.1f}/{centering.lr[1]:.1f}"
        tb_text = f"{centering.tb[0]:.1f}/{centering.tb[1]:.1f}"
        _label_with_backdrop(draw, (6, top_y + 4), f"L/R {lr_text}", label_font, CENTERING_COLOR)
        _label_with_backdrop(draw, (6, bottom_y - 18), f"T/B {tb_text}", label_font, CENTERING_COLOR)

    # Corners: a bracket at each corner, colored by that corner's score.
    corner_size = max(6, int(min(w, h) * CORNER_PATCH_FRACTION))
    corner_positions = {
        "top_left": (0, 0, 1, 1),
        "top_right": (w, 0, -1, 1),
        "bottom_left": (0, h, 1, -1),
        "bottom_right": (w, h, -1, -1),
    }
    for name, (cx, cy, dx, dy) in corner_positions.items():
        score = corners.per_corner.get(name, 10.0)
        color = _score_color(score)
        s = corner_size
        draw.line([(cx, cy + dy * s), (cx, cy), (cx + dx * s, cy)], fill=(*color, 255), width=3)
        label_x = cx + dx * (s + 6) - (30 if dx < 0 else 0)
        label_y = cy + dy * (s + 6) - (16 if dy < 0 else 0)
        _label_with_backdrop(draw, (label_x, label_y), f"{score:.1f}", label_font, color)

    # Edges: a colored strip along each side, matching the region the
    # pipeline actually sampled, labeled with that edge's score.
    strip_w = max(2, int(w * STRIP_FRACTION))
    strip_h = max(2, int(h * STRIP_FRACTION))
    margin_w = max(1, int(w * CORNER_MARGIN_FRACTION))
    margin_h = max(1, int(h * CORNER_MARGIN_FRACTION))
    edge_regions = {
        "top": (margin_w, 0, w - margin_w, strip_h),
        "bottom": (margin_w, h - strip_h, w - margin_w, h),
        "left": (0, margin_h, strip_w, h - margin_h),
        "right": (w - strip_w, margin_h, w, h - margin_h),
    }
    for name, box in edge_regions.items():
        score = edges.per_edge.get(name, 10.0)
        color = _score_color(score)
        draw.rectangle(box, outline=(*color, 255), width=2)

    mid_y = h // 2
    mid_x = w // 2
    left_score = edges.per_edge.get('left', 10.0)
    right_score = edges.per_edge.get('right', 10.0)
    top_score = edges.per_edge.get('top', 10.0)
    bottom_score = edges.per_edge.get('bottom', 10.0)
    _label_with_backdrop(draw, (4, mid_y), f"{left_score:.1f}", label_font, _score_color(left_score))
    _label_with_backdrop(draw, (w - 26, mid_y), f"{right_score:.1f}", label_font, _score_color(right_score))
    _label_with_backdrop(draw, (mid_x - 12, strip_h + 4), f"{top_score:.1f}", label_font, _score_color(top_score))
    _label_with_backdrop(draw, (mid_x - 12, h - strip_h - 18), f"{bottom_score:.1f}", label_font,
                          _score_color(bottom_score))

    composed = Image.alpha_composite(img, overlay).convert("RGB")
    buf = io.BytesIO()
    composed.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
