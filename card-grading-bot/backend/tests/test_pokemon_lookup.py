import shutil
import sys
import types
from pathlib import Path

import cv2
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import pokemon_lookup
from app.pokemon_lookup import (
    _candidate_names, _card_to_identification, identify_pokemon_card,
)


def _make_card_jpeg_bytes(w=200, h=280):
    img = np.full((h, w, 3), 200, dtype=np.uint8)
    ok, buf = cv2.imencode(".jpg", img)
    return buf.tobytes()


def _ocr_data(rows):
    """rows: list of (text, conf, top, left, block, par, line)"""
    keys = ["text", "conf", "top", "left", "block_num", "par_num", "line_num"]
    data = {k: [] for k in keys}
    for row in rows:
        for k, v in zip(keys, row):
            data[k].append(v)
    return data


NAME_BAND_OCR = _ocr_data([
    ("CHARCADET", 95, 10, 5, 1, 1, 1),
    ("HP", 90, 12, 60, 1, 1, 2),
    ("80", 88, 12, 90, 1, 1, 2),
    ("BASIC", 92, 200, 5, 1, 1, 3),  # well below the name band
])

NO_CANDIDATE_OCR = _ocr_data([
    ("HP", 90, 10, 5, 1, 1, 1),
    ("80", 88, 10, 60, 1, 1, 1),
    ("BASIC", 92, 12, 5, 1, 1, 2),
])


def _make_fake_pytesseract_module(ocr_data=None, raise_exc=None):
    class _Output:
        DICT = "dict"

    def _image_to_data(image, output_type=None):
        if raise_exc:
            raise raise_exc
        return ocr_data

    return types.SimpleNamespace(Output=_Output, image_to_data=_image_to_data)


def _make_fake_httpx_module(cards_by_name=None, raise_exc=None):
    class _FakeResponse:
        def __init__(self, data):
            self._data = data

        def raise_for_status(self):
            pass

        def json(self):
            return self._data

    class _FakeAsyncClient:
        def __init__(self, timeout=None):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc_info):
            return False

        async def get(self, url, params=None):
            if raise_exc:
                raise raise_exc
            name = params["q"].split('"')[1]
            lookup = {k.upper(): v for k, v in (cards_by_name or {}).items()}
            card = lookup.get(name.upper())
            return _FakeResponse({"data": [card] if card else []})

    return types.SimpleNamespace(AsyncClient=_FakeAsyncClient)


CHARCADET_CARD = {
    "name": "Charcadet",
    "number": "67",
    "rarity": "Common",
    "set": {"name": "Scarlet & Violet", "releaseDate": "2023/03/31", "printedTotal": "198"},
}

HOLO_RARE_CARD = {
    "name": "Charizard",
    "number": "4",
    "rarity": "Rare Holo",
    "set": {"name": "Base Set", "releaseDate": "1999/01/09", "printedTotal": "102"},
}


def test_candidate_names_picks_up_the_top_band_and_skips_stopwords_and_stats():
    candidates = _candidate_names(NAME_BAND_OCR, image_height=280)
    assert candidates == ["CHARCADET"]


def test_candidate_names_returns_empty_when_only_stopwords_in_band():
    candidates = _candidate_names(NO_CANDIDATE_OCR, image_height=280)
    assert candidates == []


def test_card_to_identification_formats_number_and_drops_plain_rarity():
    ci = _card_to_identification(CHARCADET_CARD)
    assert ci.identified is True
    assert ci.year == "2023"
    assert ci.set_name == "Scarlet & Violet"
    assert ci.subject_name == "Charcadet"
    assert ci.card_number == "#67/198"
    assert ci.variation == ""  # "Common" is filtered out as uninteresting
    assert ci.confidence == "medium"


def test_card_to_identification_keeps_notable_rarity_as_variation():
    ci = _card_to_identification(HOLO_RARE_CARD)
    assert ci.variation == "Rare Holo"


async def test_identify_pokemon_card_returns_none_without_pytesseract(monkeypatch):
    monkeypatch.setitem(sys.modules, "pytesseract", None)
    result = await identify_pokemon_card(_make_card_jpeg_bytes())
    assert result is None


async def test_identify_pokemon_card_returns_none_on_bad_image_bytes(monkeypatch):
    monkeypatch.setitem(sys.modules, "pytesseract", _make_fake_pytesseract_module(NAME_BAND_OCR))
    result = await identify_pokemon_card(b"not an image")
    assert result is None


async def test_identify_pokemon_card_fails_soft_on_ocr_error(monkeypatch):
    fake_module = _make_fake_pytesseract_module(raise_exc=RuntimeError("tesseract not found"))
    monkeypatch.setitem(sys.modules, "pytesseract", fake_module)
    result = await identify_pokemon_card(_make_card_jpeg_bytes())
    assert result is None


async def test_identify_pokemon_card_returns_unidentified_with_no_candidates(monkeypatch):
    monkeypatch.setitem(sys.modules, "pytesseract", _make_fake_pytesseract_module(NO_CANDIDATE_OCR))
    result = await identify_pokemon_card(_make_card_jpeg_bytes())
    assert result is not None
    assert result.identified is False


async def test_identify_pokemon_card_matches_via_pokemontcg(monkeypatch):
    monkeypatch.setitem(sys.modules, "pytesseract", _make_fake_pytesseract_module(NAME_BAND_OCR))
    monkeypatch.setattr(
        pokemon_lookup, "httpx",
        _make_fake_httpx_module(cards_by_name={"CHARCADET": CHARCADET_CARD}),
    )
    result = await identify_pokemon_card(_make_card_jpeg_bytes())
    assert result is not None
    assert result.identified is True
    assert result.subject_name == "Charcadet"
    assert result.label_line == "2023 SCARLET & VIOLET CHARCADET #67/198"


async def test_identify_pokemon_card_returns_unidentified_when_no_match_found(monkeypatch):
    monkeypatch.setitem(sys.modules, "pytesseract", _make_fake_pytesseract_module(NAME_BAND_OCR))
    monkeypatch.setattr(pokemon_lookup, "httpx", _make_fake_httpx_module(cards_by_name={}))
    result = await identify_pokemon_card(_make_card_jpeg_bytes())
    assert result is not None
    assert result.identified is False


async def test_identify_pokemon_card_fails_soft_on_network_error(monkeypatch):
    monkeypatch.setitem(sys.modules, "pytesseract", _make_fake_pytesseract_module(NAME_BAND_OCR))
    monkeypatch.setattr(
        pokemon_lookup, "httpx",
        _make_fake_httpx_module(raise_exc=RuntimeError("connection refused")),
    )
    result = await identify_pokemon_card(_make_card_jpeg_bytes())
    assert result is not None
    assert result.identified is False


@pytest.mark.skipif(shutil.which("tesseract") is None, reason="tesseract binary not installed")
async def test_identify_pokemon_card_real_ocr_reads_a_synthetic_name(monkeypatch):
    """Runs the real pytesseract/Tesseract binary (no mocking of the OCR
    step) against a synthetic card image with a name drawn near the top,
    to confirm the OCR integration itself works end-to-end -- separate
    from the mocked-pytesseract unit tests above. Only the network call
    is mocked, since we can't reach pokemontcg.io in a sandboxed test run.

    Uses a real TTF at a normal card-name size (PIL's tiny default bitmap
    font produces OCR confidence too low/flaky to assert on reliably).
    """
    from PIL import Image, ImageDraw, ImageFont

    font_path = str(Path(__file__).resolve().parents[1] / "app" / "fonts" / "DejaVuSans-Bold.ttf")
    name_font = ImageFont.truetype(font_path, 30)
    small_font = ImageFont.truetype(font_path, 18)

    img = Image.new("RGB", (500, 700), (250, 240, 210))
    draw = ImageDraw.Draw(img)
    draw.text((30, 25), "Charcadet", fill=(15, 15, 15), font=name_font)
    draw.text((380, 30), "HP80", fill=(15, 15, 15), font=small_font)
    draw.text((30, 90), "Basic", fill=(15, 15, 15), font=small_font)
    arr = np.array(img)[:, :, ::-1]
    ok, buf = cv2.imencode(".jpg", arr)

    seen_queries = []

    class _RecordingClient(_make_fake_httpx_module(cards_by_name={"CHARCADET": CHARCADET_CARD}).AsyncClient):
        async def get(self, url, params=None):
            seen_queries.append(params["q"])
            return await super().get(url, params=params)

    monkeypatch.setattr(pokemon_lookup, "httpx", types.SimpleNamespace(AsyncClient=_RecordingClient))

    result = await identify_pokemon_card(buf.tobytes())
    assert result is not None
    assert result.identified is True
    assert result.subject_name == "Charcadet"
    assert any("charcadet" in q.lower() for q in seen_queries)
