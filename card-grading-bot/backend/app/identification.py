"""Optional card identification: reads the player/character, set, year,
and card number off the front photo using Claude's vision API, the way a
real grading company's label would show it (e.g. "2023 TOPPS CHROME
SHOHEI OHTANI #27 REFRACTOR").

This is entirely optional and fails soft: if ANTHROPIC_API_KEY isn't set,
the `anthropic` package isn't installed, or the API call errors out for
any reason (rate limit, timeout, bad image), identify_card returns None
and grading proceeds exactly as it would without this feature -- nothing
else in the app depends on it.
"""

import base64
import os
from dataclasses import dataclass
from typing import Optional

MODEL = os.environ.get("CARD_ID_MODEL", "claude-haiku-4-5-20251001")
REQUEST_TIMEOUT_SECONDS = 30

IDENTIFY_TOOL = {
    "name": "report_card_identification",
    "description": "Report what trading card is shown in the photo, formatted the way a grading company's label would show it.",
    "input_schema": {
        "type": "object",
        "properties": {
            "identified": {
                "type": "boolean",
                "description": "False if too little of the card is legible to identify anything at all.",
            },
            "year": {"type": "string", "description": "Card year, e.g. '2023'. Empty string if unknown."},
            "set_name": {"type": "string", "description": "Set/brand name, e.g. 'Topps Chrome'. Empty string if unknown."},
            "subject_name": {"type": "string", "description": "Player, character, or subject name. Empty string if unknown."},
            "card_number": {"type": "string", "description": "Card number as printed, e.g. '#27'. Empty string if unknown."},
            "variation": {"type": "string", "description": "Parallel/insert/variation name if any, e.g. 'Refractor'. Empty string if none/unknown."},
            "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
        },
        "required": ["identified", "year", "set_name", "subject_name", "card_number", "variation", "confidence"],
    },
}

IDENTIFY_PROMPT = (
    "This is the front of a trading card. Identify it the way a grading company's "
    "label would: year, set/brand, player or character name, card number, and any "
    "parallel/variation. Leave a field as an empty string if you can't confidently "
    "tell. Set identified=false only if too little of the card is legible to "
    "identify anything at all."
)


@dataclass
class CardIdentification:
    identified: bool
    year: str
    set_name: str
    subject_name: str
    card_number: str
    variation: str
    confidence: str

    @property
    def label_line(self) -> str:
        """A single line formatted like a real grading label, e.g.
        '2023 TOPPS CHROME SHOHEI OHTANI #27 REFRACTOR'."""
        parts = [self.year, self.set_name, self.subject_name, self.card_number, self.variation]
        return " ".join(p for p in parts if p).upper()


def _guess_media_type(data: bytes) -> str:
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return "image/jpeg"


def _parse_response(data: dict) -> CardIdentification:
    return CardIdentification(
        identified=bool(data.get("identified", False)),
        year=str(data.get("year") or ""),
        set_name=str(data.get("set_name") or ""),
        subject_name=str(data.get("subject_name") or ""),
        card_number=str(data.get("card_number") or ""),
        variation=str(data.get("variation") or ""),
        confidence=str(data.get("confidence") or "low"),
    )


async def identify_card(front_image_bytes: bytes) -> Optional[CardIdentification]:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None

    try:
        import anthropic
    except ImportError:
        return None

    try:
        client = anthropic.AsyncAnthropic(api_key=api_key, timeout=REQUEST_TIMEOUT_SECONDS)
        b64 = base64.b64encode(front_image_bytes).decode("ascii")
        media_type = _guess_media_type(front_image_bytes)
        response = await client.messages.create(
            model=MODEL,
            max_tokens=500,
            tools=[IDENTIFY_TOOL],
            tool_choice={"type": "tool", "name": "report_card_identification"},
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": b64}},
                    {"type": "text", "text": IDENTIFY_PROMPT},
                ],
            }],
        )
        for block in response.content:
            if getattr(block, "type", None) == "tool_use" and block.name == "report_card_identification":
                return _parse_response(block.input)
    except Exception as exc:
        print(f"[identification] card identification skipped: {exc}")
        return None
    return None
