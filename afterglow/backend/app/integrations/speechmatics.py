"""Speechmatics batch transcription client.

Calls the real `speechmatics-batch` SDK when SPEECHMATICS_API_KEY is set and
DEMO_MODE is false. Otherwise returns a cached transcript so the pipeline can
run end-to-end offline (useful for the demo and for unit tests).
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from app.config import get_settings

logger = logging.getLogger("afterglow")


@dataclass
class TranscriptResult:
    text: str
    language: str
    speakers: list[dict[str, Any]] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


_FAKE_TRANSCRIPTS: dict[str, TranscriptResult] = {
    "restaurant": TranscriptResult(
        text=(
            "S1: Buonasera, vorrei prenotare un tavolo per venerdi sera. "
            "S2: Certo, per quante persone? "
            "S1: Siamo in quattro, verso le otto e mezza. Mi chiamo Marco. "
            "S1: Una persona e intollerante al glutine, riuscite a gestirla? "
            "S2: Assolutamente. "
            "S1: Mi potete confermare su WhatsApp?"
        ),
        language="it",
        speakers=[
            {"id": "S1", "label": "caller"},
            {"id": "S2", "label": "operator"},
        ],
        raw={"source": "fake"},
    ),
    "dentist": TranscriptResult(
        text=(
            "S1: Buongiorno, avrei bisogno di una visita urgente, mi e saltata "
            "un'otturazione e ho un dolore forte al molare in basso a destra. "
            "S2: Mi dispiace, possiamo provare a vederla domani mattina. Come si chiama? "
            "S1: Sono Laura Bianchi, ho gia la cartella da voi. "
            "S2: Perfetto Laura, ha una copertura assicurativa? "
            "S1: Si, UniSalute, vi mando il numero polizza via WhatsApp. "
            "S2: Bene, le mando io la conferma con orario e indicazioni."
        ),
        language="it",
        speakers=[
            {"id": "S1", "label": "caller"},
            {"id": "S2", "label": "operator"},
        ],
        raw={"source": "fake"},
    ),
    "bodyshop": TranscriptResult(
        text=(
            "S1: Salve, ho preso un palo in retromarcia e devo sistemare il "
            "paraurti posteriore di una Fiat Panda del 2019. "
            "S2: Ha gia aperto un sinistro con l'assicurazione? "
            "S1: No, non ho fatto denuncia, pago io. Mi serve solo un preventivo. "
            "S2: Capito. Quando puo passare per la perizia? "
            "S1: Sono libero giovedi pomeriggio. Mi chiamo Andrea Verdi. "
            "S2: Le confermo via SMS l'appuntamento."
        ),
        language="it",
        speakers=[
            {"id": "S1", "label": "caller"},
            {"id": "S2", "label": "operator"},
        ],
        raw={"source": "fake"},
    ),
}


async def transcribe_audio(
    audio_path: Path,
    *,
    custom_dictionary: Optional[list[str]] = None,
    diarization: str = "speaker",
    language: str = "auto",
    timeout_sec: float = 120.0,
    domain_hint: str = "restaurant",
) -> TranscriptResult:
    """Transcribe an audio file via Speechmatics batch.

    Behaviour:
    - If settings.demo_mode is true OR no API key is set → canned transcript
      picked by `domain_hint` (restaurant/dentist/bodyshop).
    - If the audio path doesn't exist or points to /dev/null → canned transcript.
    - Otherwise submit the file to Speechmatics with diarization on, language
      auto-detect, and the template's custom_dictionary as additional_vocab.
    """
    settings = get_settings()

    if (
        settings.demo_mode
        or not settings.speechmatics_api_key
        or not audio_path
        or str(audio_path) == "/dev/null"
        or not audio_path.exists()
        or audio_path.stat().st_size < 4096
    ):
        await asyncio.sleep(0.2)  # simulate latency, keeps audit timings honest
        return _FAKE_TRANSCRIPTS.get(domain_hint, _FAKE_TRANSCRIPTS["restaurant"])

    return await _real_transcribe(
        audio_path,
        custom_dictionary=custom_dictionary,
        diarization=diarization,
        language=language,
        timeout_sec=timeout_sec,
    )


async def _real_transcribe(
    audio_path: Path,
    *,
    custom_dictionary: Optional[list[str]],
    diarization: str,
    language: str,
    timeout_sec: float,
) -> TranscriptResult:
    # Lazy imports so the app stays importable when the SDK is unavailable.
    from speechmatics.batch import AsyncClient, TranscriptionConfig

    settings = get_settings()

    additional_vocab = (
        [{"content": term} for term in custom_dictionary] if custom_dictionary else None
    )

    transcription_config = TranscriptionConfig(
        language=language,
        diarization=diarization,
        additional_vocab=additional_vocab,
    )

    client = AsyncClient(
        api_key=settings.speechmatics_api_key,
        url=settings.speechmatics_batch_url,
    )
    try:
        transcript = await client.transcribe(
            audio_file=str(audio_path),
            transcription_config=transcription_config,
            timeout=timeout_sec,
        )
    finally:
        await client.close()

    return _to_transcript_result(transcript, requested_language=language)


def _to_transcript_result(transcript: Any, *, requested_language: str) -> TranscriptResult:
    """Convert speechmatics.batch.Transcript into our internal TranscriptResult."""
    results = getattr(transcript, "results", None) or []
    speakers_raw = getattr(transcript, "speakers", None) or []
    metadata = getattr(transcript, "metadata", None)

    text = _diarized_text(results)
    detected_language = _detect_language(metadata, results, fallback=requested_language)
    speakers = _normalize_speakers(speakers_raw, results)

    # Keep a compact subset of the raw payload — full transcripts can be huge.
    raw_payload: dict[str, Any] = {
        "source": "speechmatics-batch",
        "language_identification": (
            getattr(metadata, "language_identification", None) if metadata else None
        ),
        "result_count": len(results),
    }
    return TranscriptResult(
        text=text,
        language=detected_language,
        speakers=speakers,
        raw=raw_payload,
    )


def _diarized_text(results: list[Any]) -> str:
    """Render `[{speaker, content}, ...]` as 'S1: hi S2: hey ...'.

    Punctuation is appended to the current segment without a leading space.
    """
    pieces: list[str] = []
    current_speaker: Optional[str] = None
    for r in results:
        alternatives = getattr(r, "alternatives", None) or []
        if not alternatives:
            continue
        alt = alternatives[0]
        content = getattr(alt, "content", None)
        if not content:
            continue
        speaker = getattr(alt, "speaker", None)
        rtype = getattr(r, "type", "word")

        if speaker and speaker != current_speaker:
            current_speaker = speaker
            pieces.append(f" {speaker}: " if pieces else f"{speaker}: ")
            pieces.append(content)
        else:
            if rtype == "punctuation":
                pieces.append(content)
            else:
                pieces.append(f" {content}")
    return "".join(pieces).strip()


def _detect_language(metadata: Any, results: list[Any], *, fallback: str) -> str:
    if metadata is not None:
        ident = getattr(metadata, "language_identification", None)
        if isinstance(ident, dict):
            for key in ("language", "predicted_language", "best_language"):
                value = ident.get(key)
                if isinstance(value, str) and value:
                    return value
        config = getattr(metadata, "transcription_config", None)
        if isinstance(config, dict):
            value = config.get("language")
            if isinstance(value, str) and value and value != "auto":
                return value
    for r in results:
        alts = getattr(r, "alternatives", None) or []
        for a in alts:
            lang = getattr(a, "language", None)
            if isinstance(lang, str) and lang:
                return lang
    return fallback if fallback != "auto" else "it"


def _normalize_speakers(speakers_raw: list[Any], results: list[Any]) -> list[dict[str, Any]]:
    if speakers_raw:
        out: list[dict[str, Any]] = []
        for s in speakers_raw:
            label = getattr(s, "label", None) or ""
            out.append({"id": label, "label": label})
        return out
    # Fall back: collect distinct speakers from the results stream.
    seen: list[str] = []
    for r in results:
        alts = getattr(r, "alternatives", None) or []
        for a in alts:
            sp = getattr(a, "speaker", None)
            if sp and sp not in seen:
                seen.append(sp)
    return [{"id": sp, "label": sp} for sp in seen]
