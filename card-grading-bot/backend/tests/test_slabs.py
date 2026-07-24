import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.rendering.slabs import (
    ACCENT_COLORS, format_grade, fake_cert_number, render_slab_png, _truncate_to_width,
)
from PIL import ImageDraw, ImageFont


def make_card(w=350, h=500):
    return np.full((h, w, 3), 200, dtype=np.uint8)


def test_format_grade_strips_trailing_zeros_but_keeps_precision():
    assert format_grade(10.0) == "10"
    assert format_grade(9.5) == "9.5"
    assert format_grade(9.97) == "9.97"
    assert format_grade(98.0) == "98"


def test_fake_cert_number_is_stable_and_nine_digits():
    a = fake_cert_number(b"same-photo-bytes", "psa")
    b = fake_cert_number(b"same-photo-bytes", "psa")
    c = fake_cert_number(b"same-photo-bytes", "bgs")
    assert a == b
    assert a != c
    assert len(a) == 9


def test_render_slab_png_produces_a_valid_png_at_expected_size():
    png_bytes = render_slab_png(make_card(), "psa", 10.0, "Gem Mint", cert_seed=b"seed")
    assert png_bytes[:8] == b"\x89PNG\r\n\x1a\n"
    img = Image.open(__import__("io").BytesIO(png_bytes))
    assert img.format == "PNG"
    assert img.size[0] > 0 and img.size[1] > 0


def test_render_slab_png_works_for_every_known_company():
    for key in ACCENT_COLORS:
        png_bytes = render_slab_png(make_card(), key, 9.5, "Gem Mint", cert_seed=b"seed")
        assert len(png_bytes) > 0


def test_render_slab_png_handles_unusually_long_names_without_crashing():
    png_bytes = render_slab_png(
        make_card(), "bgs", 10.0,
        "A Very Long Hypothetical Grade Label That Would Never Actually Fit",
        cert_seed=b"seed",
    )
    assert len(png_bytes) > 0


def test_truncate_to_width_never_exceeds_the_limit():
    img = Image.new("RGB", (10, 10))
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()
    long_text = "Pristine 10 (Black Label Edition Extended)"
    result = _truncate_to_width(draw, long_text, font, max_width=50)
    box = draw.textbbox((0, 0), result, font=font)
    assert (box[2] - box[0]) <= 50
