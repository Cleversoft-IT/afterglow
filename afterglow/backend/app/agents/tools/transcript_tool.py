"""`search_transcript` + `read_transcript_segment` tools.

Both operate on the diarized transcript already loaded by the orchestrator
(`call.raw_transcript`). No external I/O, no LLM call — these are purely
mechanical helpers that let the agent re-read mirated chunks instead of
re-scanning the entire transcript on every turn.
"""
from __future__ import annotations

from typing import Any, Callable

from app.agents.tools.turn import bump_turn


_SNIPPET_RADIUS_WORDS = 12


def _words(transcript_text: str) -> list[str]:
    return transcript_text.split()


def _speaker_at(speakers: list[Any] | None, word_index: int) -> str:
    """Best-effort speaker resolution. Speechmatics emits per-word speaker
    tags but the orchestrator stores them as a list of segment dicts; we
    pick the segment that covers `word_index` (approximate)."""
    if not speakers:
        return "?"
    cursor = 0
    for seg in speakers:
        if not isinstance(seg, dict):
            continue
        seg_text = (seg.get("text") or "").strip()
        seg_len = len(seg_text.split())
        if cursor + seg_len > word_index:
            return str(seg.get("speaker") or "?")
        cursor += seg_len
    return "?"


def make_search_transcript(
    *, transcript_text: str, speakers: list[Any] | None
) -> Callable[..., Any]:
    """Return a `search_transcript(keyword)` callable bound to this call."""

    def search_transcript(
        keyword: str, tool_context: Any = None
    ) -> dict[str, Any]:
        """Case-insensitive substring search over the diarized transcript.

        Returns up to 8 matches with surrounding snippet, speaker label and
        the word index where the keyword starts. Use the word index with
        `read_transcript_segment` to expand the context.
        """
        bump_turn(tool_context)
        if not keyword or not keyword.strip():
            return {"matches": [], "count": 0}
        kw = keyword.lower().strip()
        words = _words(transcript_text)
        matches: list[dict[str, Any]] = []
        for idx, w in enumerate(words):
            if kw in w.lower():
                start = max(0, idx - _SNIPPET_RADIUS_WORDS)
                end = min(len(words), idx + _SNIPPET_RADIUS_WORDS + 1)
                snippet = " ".join(words[start:end])
                matches.append(
                    {
                        "speaker": _speaker_at(speakers, idx),
                        "snippet": snippet,
                        "word_index": idx,
                    }
                )
                if len(matches) >= 8:
                    break
        return {"matches": matches, "count": len(matches)}

    search_transcript.__annotations__ = {
        "keyword": str,
        "tool_context": Any,
        "return": dict,
    }
    return search_transcript


def make_read_segment(
    *, transcript_text: str, speakers: list[Any] | None
) -> Callable[..., Any]:
    """Return a `read_transcript_segment(start_word, end_word)` callable."""

    def read_transcript_segment(
        start_word: int, end_word: int, tool_context: Any = None
    ) -> dict[str, Any]:
        """Read a contiguous slice of the diarized transcript by word index.

        Bounds are clamped to [0, total_words]. Returns the slice text plus
        a coarse speaker hint for the first word.
        """
        bump_turn(tool_context)
        words = _words(transcript_text)
        total = len(words)
        s = max(0, int(start_word))
        e = min(total, max(s, int(end_word)))
        slice_words = words[s:e]
        return {
            "text": " ".join(slice_words),
            "word_count": len(slice_words),
            "start_speaker": _speaker_at(speakers, s),
        }

    read_transcript_segment.__annotations__ = {
        "start_word": int,
        "end_word": int,
        "tool_context": Any,
        "return": dict,
    }
    return read_transcript_segment
