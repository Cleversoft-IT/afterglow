"""Tests for the English-only guardrail on the simulation script builder.

Speechmatics TTS preview voices are EN-only; if Gemini drops back into
the template's source language (e.g. an Italian business name pulls the
whole dialogue into Italian), the rendered MP3 is unintelligible and
the analyzer downstream gets nothing usable. `_validate_english_or_raise`
is the safety net.

We test the validator in isolation — building a real Gemini call from a
unit test is out of scope here.
"""
from __future__ import annotations

import pytest

from app.agents.simulation_script import (
    ScriptBuilderError,
    _ScriptResponse,
    _ScriptScenario,
    _ScriptTurn,
    _validate_english_or_raise,
)


def _turn(speaker: str, text: str) -> _ScriptTurn:
    """speaker→voice mapping mirrors how Gemini usually assigns them; the
    validator only inspects `text`, so any allowed voice is fine."""
    voice = "sarah" if speaker == "operator" else "theo"
    return _ScriptTurn(speaker=speaker, voice=voice, text=text)


def _scenario(turns: list[_ScriptTurn]) -> _ScriptScenario:
    return _ScriptScenario(
        caller_name="Test Caller",
        caller_phone_e164="+1 (555) 111-2222",
        turns=turns,
    )


def _response(existing: list[_ScriptTurn], new: list[_ScriptTurn]) -> _ScriptResponse:
    return _ScriptResponse(
        scenarios_existing=_scenario(existing),
        scenarios_new=_scenario(new),
    )


def test_english_script_passes():
    """A clean EN dialogue should not raise."""
    resp = _response(
        existing=[
            _turn("operator", "Good morning, Bella Vita restaurant, how can I help?"),
            _turn("caller", "Hi, it's Marco — I'd like the usual corner table for four."),
        ],
        new=[
            _turn("operator", "Good afternoon, this is Lumière dental office."),
            _turn("caller", "Hello, I'm calling to book a cleaning for next week."),
        ],
    )
    _validate_english_or_raise(resp)  # must not raise


def test_italian_greeting_is_rejected():
    """The canonical regression: business is an Italian restaurant and
    Gemini opens the operator turn with 'buongiorno'."""
    resp = _response(
        existing=[
            _turn("operator", "Buongiorno Trattoria Bella Vita, come posso aiutarla?"),
            _turn("caller", "Sono Marco, vorrei prenotare per quattro."),
        ],
        new=[
            _turn("operator", "Good afternoon, how can I help?"),
            _turn("caller", "Hello, I'd like to book a table."),
        ],
    )
    with pytest.raises(ScriptBuilderError, match="not English"):
        _validate_english_or_raise(resp)


def test_french_marker_is_rejected():
    """Same trap with a French dental office name pulling 'bonjour' /
    'merci' into the dialogue."""
    resp = _response(
        existing=[
            _turn("operator", "Hello, how can I help you today?"),
            _turn("caller", "Bonjour, je voudrais prendre rendez-vous merci."),
        ],
        new=[
            _turn("operator", "Hi, dental office speaking."),
            _turn("caller", "Hi, I'd like to book a cleaning."),
        ],
    )
    with pytest.raises(ScriptBuilderError, match="not English"):
        _validate_english_or_raise(resp)


def test_spanish_marker_is_rejected():
    resp = _response(
        existing=[
            _turn("operator", "Hola, body shop here. Hola again."),
            _turn("caller", "Hi, my car has a dent."),
        ],
        new=[
            _turn("operator", "Hi there."),
            _turn("caller", "Hi, I need a quote."),
        ],
    )
    with pytest.raises(ScriptBuilderError, match="not English"):
        _validate_english_or_raise(resp)


def test_proper_noun_in_english_dialogue_passes():
    """Edge case: keeping a non-English business name as a proper noun
    inside an otherwise English sentence is allowed (the validator only
    flags whole-word non-English markers, not character classes)."""
    resp = _response(
        existing=[
            _turn("operator", "Good morning, Café Lumière, how can I help?"),
            _turn("caller", "Hi, can I book a table near the window?"),
        ],
        new=[
            _turn("operator", "Hello, this is the Lumière hostess desk."),
            _turn("caller", "Hi, first time here — what's the wait like?"),
        ],
    )
    _validate_english_or_raise(resp)  # must not raise
