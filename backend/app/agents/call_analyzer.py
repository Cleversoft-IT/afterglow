"""Schemas + token-usage helper shared across the agentic post-call stack.

As of round-10 the legacy single-shot `analyze_call` function and its prompt
have been removed: the analysis is now produced turn-by-turn by the
multi-turn agent in `agents/call_agent.py`. This module retains only the
Pydantic shapes that downstream consumers (orchestrator, finalize_call tool,
briefing_regenerator) still use:

  - `FieldExtraction`: one extracted field + confidence + verbatim evidence.
    The agent emits a `list[FieldExtraction]` inside `FinalizeCallPayload`.
  - `TokenUsage`: thin wrapper over Gemini's `usage_metadata` so audit rows
    can carry `input_tokens` / `output_tokens` consistently.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from pydantic import BaseModel, Field


class FieldExtraction(BaseModel):
    key: str = Field(description="Field key from the template's fields_schema.")
    value: str = Field(
        description=(
            "Extracted value as a string. For lists (e.g. allergies) use a "
            "JSON array literal like '[\"glutine\"]'. Use ISO formats for "
            "dates/times when applicable."
        )
    )
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: str = Field(description="Verbatim transcript span supporting the extraction.")


@dataclass
class TokenUsage:
    """Token-count snapshot extracted from a Gemini response's usage_metadata.

    Both fields are Optional[int] because the Gemini SDK does not always
    populate them (e.g. cached responses).
    """

    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None

    @classmethod
    def from_gemini(cls, resp: Any) -> "TokenUsage":
        usage = getattr(resp, "usage_metadata", None)
        if usage is None:
            return cls()
        return cls(
            input_tokens=getattr(usage, "prompt_token_count", None),
            output_tokens=getattr(usage, "candidates_token_count", None),
        )
