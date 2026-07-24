"""Generates a stylized 'slab' mockup for each grading company: the
submitted card shown inside a plastic-holder-style graphic with that
company's estimated grade on the label.

This is original artwork, not a reproduction of any company's actual
holder. It borrows only industry-wide *conventions* that aren't anyone's
exclusive property -- e.g. "red label" / "black label with a subgrade
grid" / "grade shown in a bordered badge" are broad stylistic ideas used
across the hobby, not a specific company's protected logo, wordmark, or
label artwork. No real logos, hologram, or barcode graphics are drawn, and
every slab is watermarked "UNOFFICIAL" with an obviously placeholder cert
number.
"""

import hashlib
import io
from pathlib import Path
from typing import Dict, Optional, Tuple

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

FONTS_DIR = Path(__file__).resolve().parent.parent / "fonts"

CANVAS_W = 340
CANVAS_H = 560
MARGIN = 14
LABEL_H = 96
GRID_H = 46
FOOTER_H = 34
OUTER_RADIUS = 20
CAVITY_RADIUS = 10

CASE_BG = (240, 239, 235)
CASE_BORDER = (196, 194, 188)
CASE_SHADOW = (208, 206, 200)
CAVITY_BG = (26, 26, 24)
CARD_BORDER = (60, 60, 58)
FOOTER_TEXT = (110, 108, 102)
GRID_LABEL_COLOR = (120, 118, 112)
GRID_VALUE_COLOR = (28, 26, 22)

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

# Broad, unprotectable stylistic conventions per company: whether the grade
# reads as a bordered "badge" (PSA/CGC-style) vs. a plain banner number
# (SGC-style), and whether a 4-box subgrade strip is shown beneath the
# card (Beckett/TAG/HGA-style, since those companies are known for
# publishing per-attribute subgrades).
LAYOUTS = {
    "psa": "badge",
    "cgc": "badge",
    "sgc": "banner",
    "bgs": "grid",
    "tag": "grid",
    "hga": "grid",
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


def _summarize_subgrades(subgrades: Optional[Dict[str, float]]) -> "list[Tuple[str, Optional[float]]]":
    """Collapse whatever subgrade keys a company produced (plain
    corners/edges, or per-corner/per-edge detail like TAG/HGA) down to the
    four attributes every company publicly grades on."""
    subgrades = subgrades or {}

    def avg_matching(prefix: str, fallback_key: str) -> Optional[float]:
        matches = [v for k, v in subgrades.items() if k.startswith(prefix)]
        if matches:
            return sum(matches) / len(matches)
        return subgrades.get(fallback_key)

    return [
        ("CENT", subgrades.get("centering")),
        ("CORN", avg_matching("corner_", "corners")),
        ("EDGE", avg_matching("edge_", "edges")),
        ("SURF", subgrades.get("surface")),
    ]


def _draw_grade_badge(draw: ImageDraw.ImageDraw, x: float, y: float, grade_text: str,
                       font: ImageFont.FreeTypeFont, border_color: Tuple[int, int, int]) -> float:
    """A bordered white badge holding the grade number, evoking the
    grade-in-a-box convention several companies use, without copying any
    specific company's badge artwork. Returns the badge's width."""
    pad_x, pad_y = 12, 8
    text_w = _text_width(draw, grade_text, font)
    ascent, descent = font.getmetrics()
    text_h = ascent + descent
    box = [x - text_w - pad_x * 2, y, x, y + text_h + pad_y * 2]
    draw.rounded_rectangle(box, radius=8, fill=(255, 255, 255, 235), outline=(*border_color, 255), width=2)
    draw.text((box[0] + pad_x, y + pad_y - 2), grade_text, font=font, fill=(*border_color, 255))
    return box[2] - box[0]


def _draw_subgrade_grid(draw: ImageDraw.ImageDraw, box, entries, label_font, value_font) -> None:
    x0, y0, x1, y1 = box
    n = len(entries)
    cell_w = (x1 - x0) / n
    for i, (key, value) in enumerate(entries):
        cx0 = x0 + i * cell_w
        cx1 = cx0 + cell_w
        if i > 0:
            draw.line([(cx0, y0 + 4), (cx0, y1 - 4)], fill=(*CASE_BORDER, 255), width=1)
        label_w = _text_width(draw, key, label_font)
        draw.text((cx0 + (cell_w - label_w) / 2, y0 + 4), key, font=label_font, fill=(*GRID_LABEL_COLOR, 255))
        value_text = f"{value:g}" if value is not None else "–"
        value_w = _text_width(draw, value_text, value_font)
        draw.text((cx0 + (cell_w - value_w) / 2, y0 + 20), value_text, font=value_font, fill=(*GRID_VALUE_COLOR, 255))


def render_slab_png(card_bgr: np.ndarray, company_key: str, overall: float,
                     grade_label: str, cert_seed: bytes,
                     subgrades: Optional[Dict[str, float]] = None) -> bytes:
    accent = _hex_to_rgb(ACCENT_COLORS.get(company_key, "#5b8cff"))
    text_on_accent = _readable_text_color(accent)
    company_name = DISPLAY_NAMES.get(company_key, company_key.upper())
    grade_text = format_grade(overall)
    cert_number = fake_cert_number(cert_seed, company_key)
    layout = LAYOUTS.get(company_key, "banner")
    show_grid = layout == "grid"

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
    # A thin inner hairline near the top of the band, evoking the
    # double-rule look a lot of labels use, without copying any one design.
    draw.line([(MARGIN + 4, MARGIN + 30), (CANVAS_W - MARGIN - 4, MARGIN + 30)],
               fill=(*text_on_accent, 60), width=1)

    company_font = _font("DejaVuSans-Bold.ttf", 20)
    sub_font = _font("DejaVuSans.ttf", 11)
    grade_font = _font("DejaVuSans-Bold.ttf", 30)
    badge_font = _font("DejaVuSans-Bold.ttf", 26)
    label_font = _font("DejaVuSans.ttf", 12)
    footer_font = _font("DejaVuSans.ttf", 9)
    grid_label_font = _font("DejaVuSans-Bold.ttf", 9)
    grid_value_font = _font("DejaVuSans-Bold.ttf", 13)

    left_x = MARGIN + 16
    right_edge = CANVAS_W - MARGIN - 16
    gap = 10

    if layout == "badge":
        # PSA/CGC-style: company name top-left, grade in a bordered white
        # badge top-right (evokes a "grade slot" without copying one).
        badge_w = _draw_grade_badge(draw, right_edge, MARGIN + 8, grade_text, badge_font, accent)
        company_text = _truncate_to_width(draw, company_name.upper(), company_font,
                                           right_edge - badge_w - gap - left_x)
        draw.text((left_x, MARGIN + 14), company_text, font=company_font, fill=text_on_accent)
    else:
        # Beckett/TAG/HGA/SGC-style: plain banner with the grade as a big
        # number at top-right.
        grade_w = _text_width(draw, grade_text, grade_font)
        company_text = _truncate_to_width(draw, company_name.upper(), company_font,
                                           right_edge - grade_w - gap - left_x)
        draw.text((left_x, MARGIN + 14), company_text, font=company_font, fill=text_on_accent)
        draw.text((right_edge - grade_w, MARGIN + 8), grade_text, font=grade_font, fill=text_on_accent)

    sub_text = "ESTIMATED GRADE"
    sub_w = _text_width(draw, sub_text, sub_font)
    draw.text((left_x, MARGIN + 58), sub_text, font=sub_font, fill=text_on_accent)
    label_text = _truncate_to_width(draw, grade_label, label_font,
                                     right_edge - left_x - sub_w - gap)
    label_w = _text_width(draw, label_text, label_font)
    draw.text((right_edge - label_w, MARGIN + 56), label_text, font=label_font, fill=text_on_accent)

    cavity_top = MARGIN + LABEL_H + 12
    cavity_bottom = CANVAS_H - MARGIN - FOOTER_H - 8 - (GRID_H if show_grid else 0)
    cavity_box = [MARGIN + 14, cavity_top, CANVAS_W - MARGIN - 14, cavity_bottom]
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

    if show_grid:
        grid_box = [MARGIN + 14, cavity_bottom + 8, CANVAS_W - MARGIN - 14, cavity_bottom + 8 + GRID_H - 8]
        draw.rounded_rectangle(grid_box, radius=6, outline=(*CASE_BORDER, 255), width=1, fill=(*CASE_BG, 255))
        entries = _summarize_subgrades(subgrades)
        _draw_subgrade_grid(draw, grid_box, entries, grid_label_font, grid_value_font)

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
