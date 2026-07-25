import sys
import types
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.identification import (
    CardIdentification, _guess_media_type, _parse_response, identify_card,
)

JPEG_HEADER = b"\xff\xd8\xff\xe0" + b"\x00" * 20
PNG_HEADER = b"\x89PNG\r\n\x1a\n" + b"\x00" * 20


class _FakeToolUseBlock:
    def __init__(self, name, input_data):
        self.type = "tool_use"
        self.name = name
        self.input = input_data


class _FakeResponse:
    def __init__(self, content):
        self.content = content


def _make_fake_anthropic_module(tool_input=None, raise_exc=None):
    class _FakeAsyncAnthropic:
        def __init__(self, api_key=None, timeout=None):
            self.messages = self

        async def create(self, **kwargs):
            if raise_exc:
                raise raise_exc
            return _FakeResponse([_FakeToolUseBlock("report_card_identification", tool_input)])

    return types.SimpleNamespace(AsyncAnthropic=_FakeAsyncAnthropic)


def test_guess_media_type():
    assert _guess_media_type(JPEG_HEADER) == "image/jpeg"
    assert _guess_media_type(PNG_HEADER) == "image/png"
    assert _guess_media_type(b"unknown-bytes") == "image/jpeg"


def test_parse_response_builds_card_identification():
    ci = _parse_response({
        "identified": True, "year": "2023", "set_name": "Topps Chrome",
        "subject_name": "Shohei Ohtani", "card_number": "#27",
        "variation": "Refractor", "confidence": "high",
    })
    assert ci == CardIdentification(
        identified=True, year="2023", set_name="Topps Chrome",
        subject_name="Shohei Ohtani", card_number="#27",
        variation="Refractor", confidence="high",
    )


def test_parse_response_handles_missing_fields_with_empty_strings():
    ci = _parse_response({"identified": False})
    assert ci.year == ""
    assert ci.confidence == "low"


def test_label_line_joins_nonempty_parts_uppercase():
    ci = CardIdentification(identified=True, year="2023", set_name="Topps Chrome",
                             subject_name="Shohei Ohtani", card_number="#27",
                             variation="Refractor", confidence="high")
    assert ci.label_line == "2023 TOPPS CHROME SHOHEI OHTANI #27 REFRACTOR"


def test_label_line_skips_empty_fields():
    ci = CardIdentification(identified=True, year="2023", set_name="Topps Chrome",
                             subject_name="Shohei Ohtani", card_number="", variation="",
                             confidence="medium")
    assert ci.label_line == "2023 TOPPS CHROME SHOHEI OHTANI"


async def test_identify_card_returns_none_without_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    result = await identify_card(JPEG_HEADER)
    assert result is None


async def test_identify_card_returns_none_when_anthropic_not_installed(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setitem(sys.modules, "anthropic", None)
    result = await identify_card(JPEG_HEADER)
    assert result is None


async def test_identify_card_parses_successful_tool_use_response(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    fake_module = _make_fake_anthropic_module(tool_input={
        "identified": True, "year": "2023", "set_name": "Topps Chrome",
        "subject_name": "Shohei Ohtani", "card_number": "#27",
        "variation": "Refractor", "confidence": "high",
    })
    monkeypatch.setitem(sys.modules, "anthropic", fake_module)
    result = await identify_card(JPEG_HEADER)
    assert result is not None
    assert result.identified is True
    assert result.label_line == "2023 TOPPS CHROME SHOHEI OHTANI #27 REFRACTOR"


async def test_identify_card_fails_soft_on_api_error(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    fake_module = _make_fake_anthropic_module(raise_exc=RuntimeError("rate limited"))
    monkeypatch.setitem(sys.modules, "anthropic", fake_module)
    result = await identify_card(JPEG_HEADER)
    assert result is None
