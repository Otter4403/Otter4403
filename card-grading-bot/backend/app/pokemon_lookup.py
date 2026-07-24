"""Free, Pokemon-only card identification: OCR the front photo with
Tesseract and match the likely name text against the public pokemontcg.io
database. Unlike identification.py's Claude vision path, this needs no API
key or paid service -- but it only recognizes Pokemon cards, and match
quality depends entirely on how cleanly OCR reads the printed name.

Fails soft everywhere: a missing `pytesseract`/Tesseract binary, a network
error, or no confident match all just return None or an "identified: false"
result, and grading proceeds exactly as it would without this feature.
"""

import asyncio
import re
from typing import Optional

import cv2
import httpx
import numpy as np

from .identification import CardIdentification

POKEMONTCG_API = "https://api.pokemontcg.io/v2/cards"
REQUEST_TIMEOUT_SECONDS = 10
MAX_CANDIDATES_TRIED = 5
MIN_WORD_CONFIDENCE = 40.0
NAME_BAND_FRACTION = 0.35  # a Pokemon's name is printed in the top ~35% of the card

# Words OCR reliably picks up on a Pokemon card that are never the name itself.
_STOPWORDS = {
    "HP", "BASIC", "STAGE", "EVOLVES", "FROM", "POKEMON", "POKÉMON", "EX",
    "GX", "VMAX", "VSTAR", "V", "ILLUSTRATION", "RARE", "ENERGY", "TRAINER",
    "ABILITY", "ATTACK", "WEAKNESS", "RESISTANCE", "RETREAT", "COST", "ITEM",
    "SUPPORTER", "STADIUM",
}

_PLAIN_RARITIES = {"common", "uncommon", "rare"}

# A plausible name token/phrase: letters plus the punctuation real Pokemon
# names use (Mr. Mime, Ho-Oh, Farfetch'd, Tapu Koko), nothing else.
_NAME_LINE_RE = re.compile(r"^[A-Za-zÀ-ÖØ-öø-ÿ][A-Za-zÀ-ÖØ-öø-ÿ' .-]{1,22}$")

_UNIDENTIFIED = CardIdentification(
    identified=False, year="", set_name="", subject_name="",
    card_number="", variation="", confidence="low",
)


def _clean_candidate(phrase: str) -> Optional[str]:
    phrase = phrase.strip()
    cleaned = phrase.strip(".,:;!?").upper()
    if not phrase or cleaned in _STOPWORDS or not _NAME_LINE_RE.match(phrase):
        return None
    return phrase


def _candidate_names(ocr_data: dict, image_height: int) -> "list[str]":
    """Group OCR words into lines within the card's name band, and return
    plausible name phrases, longest (most specific) first.

    Tesseract often puts the name and the HP number on the same detected
    line since they sit at the same height (e.g. "Charcadet ... HP80") --
    joining the whole line would then fail to match (it contains a digit)
    and lose the name entirely. So each line contributes both the full
    joined phrase (for real multi-word names like "Mr. Mime") and each
    individual word, and everything gets a chance to survive filtering.
    """
    lines: "dict[tuple, list[tuple[int, str]]]" = {}
    n = len(ocr_data.get("text", []))
    for i in range(n):
        text = ocr_data["text"][i].strip()
        if not text:
            continue
        try:
            conf = float(ocr_data["conf"][i])
        except (TypeError, ValueError):
            conf = -1
        if conf < MIN_WORD_CONFIDENCE:
            continue
        if ocr_data["top"][i] > image_height * NAME_BAND_FRACTION:
            continue
        key = (ocr_data["block_num"][i], ocr_data["par_num"][i], ocr_data["line_num"][i])
        lines.setdefault(key, []).append((ocr_data["left"][i], text))

    candidates = []
    seen = set()
    for words in lines.values():
        words.sort(key=lambda w: w[0])
        options = [" ".join(w for _, w in words)] + [w for _, w in words]
        for option in options:
            cleaned = _clean_candidate(option)
            if cleaned and cleaned not in seen:
                seen.add(cleaned)
                candidates.append(cleaned)

    candidates.sort(key=len, reverse=True)
    return candidates


async def _search_pokemontcg(client: httpx.AsyncClient, name: str) -> Optional[dict]:
    try:
        resp = await client.get(POKEMONTCG_API, params={"q": f'name:"{name}"', "pageSize": 1})
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return None
    cards = data.get("data") or []
    return cards[0] if cards else None


def _card_to_identification(card: dict) -> CardIdentification:
    set_info = card.get("set") or {}
    year = (set_info.get("releaseDate") or "")[:4]
    number = card.get("number") or ""
    total = set_info.get("printedTotal") or set_info.get("total") or ""
    card_number = f"#{number}/{total}" if number and total else (f"#{number}" if number else "")
    rarity = card.get("rarity") or ""
    variation = "" if rarity.lower() in _PLAIN_RARITIES else rarity
    return CardIdentification(
        identified=True,
        year=year,
        set_name=set_info.get("name") or "",
        subject_name=card.get("name") or "",
        card_number=card_number,
        variation=variation,
        confidence="medium",
    )


async def identify_pokemon_card(front_image_bytes: bytes) -> Optional[CardIdentification]:
    try:
        import pytesseract
    except ImportError:
        return None

    try:
        arr = np.frombuffer(front_image_bytes, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            return None
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        ocr_data = await asyncio.to_thread(
            pytesseract.image_to_data, gray, output_type=pytesseract.Output.DICT
        )
    except Exception as exc:
        print(f"[pokemon_lookup] OCR skipped: {exc}")
        return None

    candidates = _candidate_names(ocr_data, gray.shape[0])
    if not candidates:
        return _UNIDENTIFIED

    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS) as client:
            for name in candidates[:MAX_CANDIDATES_TRIED]:
                card = await _search_pokemontcg(client, name)
                if card:
                    return _card_to_identification(card)
    except Exception as exc:
        print(f"[pokemon_lookup] lookup skipped: {exc}")
        return None

    return _UNIDENTIFIED
