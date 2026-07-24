"""Generates a stylized 'slab' mockup for each grading company: the
submitted card shown inside a plastic-holder-style graphic with that
company's estimated grade on the label.

This is purely illustrative. It does not reproduce any company's actual
holder design, logo, hologram, barcode, or other security feature -- it's a
generic rounded-rectangle case with a colored label band and text, clearly
marked as an unofficial estimate, meant only to make the six results easier
to compare side by side.
"""

import hashlib
import io
from pathlib import Path
from typing import Tuple

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

FONTS_DIR = Path(__file__).resolve().parent / "fonts"

CANVAS_W = 340
CANVAS_H = 560
MARGIN = 14
LABEL_H = 100
FOOTER_H = 34
OUTER_RADIUS = 20
CAVITY_RADIUS = 10

CASE_BG = (240, 239, 235)
CASE_BORDER = (196, 194, 188)
CASE_SHADOW = (208, 206, 200)
CAVITY_BG = (26, 26, 24)
CARD_BORDER = (60, 60, 58)
FOOTER_TEXT = (110, 108, 102)

# Matches the frontend's per-company accent colors (frontend/style.css).
ACCENT_COLORS = {
    "psa": "#d21f3c",
    "bgs": "#d4af37",
    "cgc": "#2e6bd6",
    "tag": "#8a4fd6",
    "sgc": "#2f8f5b",
    "hga": "#e0457b",
}

DISPLAY_NAMES = {
    "psa": "PSA",
    "bgs": "Beckett (BGS)",
    "cgc": "CGC",
    "tag": "TAG",
    "sgc": "SGC",
    "hga": "HGA",
}


def _font(name: str, size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(str(FONTS_DIR / name), size)
    except OSError:
        return ImageFont.load_default()


def _hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))


def _readable_text_color(bg: Tuple[int, int, int]) -> Tuple[int, int, int]:
    luminance = 0.299 * bg[0] + 0.587 * bg[1] + 0.114 * bg[2]
    return (24, 22, 18) if luminance > 150 else (250, 248, 244)


def _text_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont) -> float:
    box = draw.textbbox((0, 0), text, font=font)
    return box[2] - box[0]


def _truncate_to_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont,
                        max_width: float) -> str:
    """Shorten `text` with a trailing ellipsis until it fits max_width, so
    long company names or grade labels never overlap neighboring text."""
    if max_width <= 0:
        return ""
    if _text_width(draw, text, font) <= max_width:
        return text
    truncated = text
    while truncated and _text_width(draw, truncated + "…", font) > max_width:
        truncated = truncated[:-1]
    return (truncated.rstrip() + "…") if truncated else text[:1]


def format_grade(overall: float) -> str:
    """10.0 -> '10', 9.5 -> '9.5', 9.97 -> '9.97', 98.0 -> '98'."""
    return f"{overall:g}"


def fake_cert_number(seed: bytes, key: str) -> str:
    """Deterministic 9-digit placeholder cert number, stable for a given
    card photo + company so re-rendering the same result looks the same."""
    digest = hashlib.sha256(seed + key.encode("utf-8")).hexdigest()
    return str(int(digest[:12], 16) % 900_000_000 + 100_000_000)


def render_slab_png(card_bgr: np.ndarray, company_key: str, overall: float,
                     grade_label: str, cert_seed: bytes) -> bytes:
    accent = _hex_to_rgb(ACCENT_COLORS.get(company_key, "#5b8cff"))
    text_on_accent = _readable_text_color(accent)
    company_name = DISPLAY_NAMES.get(company_key, company_key.upper())
    grade_text = format_grade(overall)
    cert_number = fake_cert_number(cert_seed, company_key)

    canvas = Image.new("RGBA", (CANVAS_W, CANVAS_H), (255, 255, 255, 0))
    draw = ImageDraw.Draw(canvas)

    shadow_box = [MARGIN + 4, MARGIN + 6, CANVAS_W - MARGIN + 4, CANVAS_H - MARGIN + 6]
    draw.rounded_rectangle(shadow_box, radius=OUTER_RADIUS, fill=(*CASE_SHADOW, 160))

    case_box = [MARGIN, MARGIN, CANVAS_W - MARGIN, CANVAS_H - MARGIN]
    draw.rounded_rectangle(case_box, radius=OUTER_RADIUS, fill=(*CASE_BG, 255), outline=(*CASE_BORDER, 255), width=2)

    label_box = [MARGIN + 4, MARGIN + 4, CANVAS_W - MARGIN - 4, MARGIN + LABEL_H]
    draw.rounded_rectangle(label_box, radius=OUTER_RADIUS - 4, fill=(*accent, 255))
    draw.rectangle([MARGIN + 4, MARGIN + LABEL_H - (OUTER_RADIUS - 4), CANVAS_W - MARGIN - 4, MARGIN + LABEL_H],
                    fill=(*accent, 255))

    company_font = _font("DejaVuSans-Bold.ttf", 21)
    sub_font = _font("DejaVuSans.ttf", 11)
    grade_font = _font("DejaVuSans-Bold.ttf", 32)
    label_font = _font("DejaVuSans.ttf", 12)
    footer_font = _font("DejaVuSans.ttf", 9)

    left_x = MARGIN + 16
    right_edge = CANVAS_W - MARGIN - 16
    gap = 10

    # Row 1: company name (left, truncated so it never runs into the grade
    # number) and the overall grade (right).
    grade_w = _text_width(draw, grade_text, grade_font)
    company_text = _truncate_to_width(draw, company_name.upper(), company_font,
                                       right_edge - grade_w - gap - left_x)
    draw.text((left_x, MARGIN + 14), company_text, font=company_font, fill=text_on_accent)
    draw.text((right_edge - grade_w, MARGIN + 10), grade_text, font=grade_font, fill=text_on_accent)

    # Row 2: "ESTIMATED GRADE" (left) and the grade's text label (right,
    # truncated so a long label like a Black Label name never collides).
    sub_text = "ESTIMATED GRADE"
    sub_w = _text_width(draw, sub_text, sub_font)
    draw.text((left_x, MARGIN + 56), sub_text, font=sub_font, fill=text_on_accent)
    label_text = _truncate_to_width(draw, grade_label, label_font,
                                     right_edge - left_x - sub_w - gap)
    label_w = _text_width(draw, label_text, label_font)
    draw.text((right_edge - label_w, MARGIN + 54), label_text, font=label_font, fill=text_on_accent)

    cavity_top = MARGIN + LABEL_H + 12
    cavity_box = [MARGIN + 14, cavity_top, CANVAS_W - MARGIN - 14, CANVAS_H - MARGIN - FOOTER_H - 8]
    draw.rounded_rectangle(cavity_box, radius=CAVITY_RADIUS, fill=(*CAVITY_BG, 255))

    cavity_w = (cavity_box[2] - cavity_box[0]) - 20
    cavity_h = (cavity_box[3] - cavity_box[1]) - 20
    card_rgb = cv2.cvtColor(card_bgr, cv2.COLOR_BGR2RGB)
    card_img = Image.fromarray(card_rgb)
    scale = min(cavity_w / card_img.width, cavity_h / card_img.height)
    new_w = max(1, int(card_img.width * scale))
    new_h = max(1, int(card_img.height * scale))
    card_img = card_img.resize((new_w, new_h), Image.LANCZOS)

    paste_x = cavity_box[0] + (cavity_box[2] - cavity_box[0] - new_w) // 2
    paste_y = cavity_box[1] + (cavity_box[3] - cavity_box[1] - new_h) // 2
    canvas.paste(card_img, (paste_x, paste_y))
    draw.rectangle([paste_x - 1, paste_y - 1, paste_x + new_w, paste_y + new_h], outline=(*CARD_BORDER, 255), width=1)

    footer_y = CANVAS_H - MARGIN - FOOTER_H + 9
    draw.text((MARGIN + 16, footer_y), f"EST-{cert_number}", font=footer_font, fill=(*FOOTER_TEXT, 255))
    reminder = "UNOFFICIAL · for reference only"
    reminder_w = _text_width(draw, reminder, footer_font)
    draw.text((CANVAS_W - MARGIN - 16 - reminder_w, footer_y), reminder, font=footer_font, fill=(*FOOTER_TEXT, 255))

    # Subtle diagonal glare, like light catching the plastic case.
    glare = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    glare_draw = ImageDraw.Draw(glare)
    glare_draw.polygon([(0, 0), (95, 0), (35, CANVAS_H), (-60, CANVAS_H)], fill=(255, 255, 255, 22))
    canvas = Image.alpha_composite(canvas, glare)

    flattened = Image.new("RGB", canvas.size, (250, 249, 246))
    flattened.paste(canvas, (0, 0), canvas)

    buf = io.BytesIO()
    flattened.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
