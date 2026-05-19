"""
Genera il voiceover per il video Afterglow usando Microsoft Edge TTS.
- Voce: en-GB-SoniaNeural (inglese UK, tono professionale, keynote-like)
- Ritmo: -8% (leggermente più lento del default per un feel premium)
- Output: public/audio/voiceover.mp3

Uso: python scripts/generate-voiceover.py
"""

import asyncio
import os
import json
from pathlib import Path

try:
    import edge_tts
except ImportError:
    print("edge-tts non trovato. Installalo con: pip install edge-tts")
    exit(1)

# ─── CONFIGURAZIONE ────────────────────────────────────────────────────────────

# Voce consigliata per tono keynote premium
VOICE = "en-GB-SoniaNeural"     # UK English, femminile, professionale
# Alternative valide:
# "en-US-AriaNeural"   — US, femminile, chiara e moderna
# "en-US-GuyNeural"    — US, maschile, professionale
# "en-GB-RyanNeural"   — UK, maschile, autorevole

RATE = "-8%"     # Leggermente più lento: tono riflessivo da keynote
PITCH = "+0Hz"   # Pitch neutro

OUT_DIR = Path(__file__).parent.parent / "public" / "audio"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ─── SCRIPT SCENA PER SCENA ────────────────────────────────────────────────────
# startSec: quando inizia il segmento nel video (in secondi)
# Il video è @30fps, 2400 frame = 80 secondi

SEGMENTS = [
    # Act I (0:00–0:22) has NO voiceover — typographic, silence + pad only.
    # Narration starts with Act II.A. Budgets in SUBMISSION.md §4 (tightened
    # to 3:30 total). Word counts target ~150 wpm with breathing room.
    {
        "id":       "iiA_intro",
        "startSec": 22.4,  # SCENES.iiA.start (660f) + LEAD_IN (12f) at 30fps
        "text":     "Afterglow is a phone app. The operator picks up. The moment they hang up, the after begins. Transcript. Booking. Follow-ups. The briefing for the next call. The operator never touched a screen. Stay in the moment. We handle the after.",
    },
    {
        "id":       "iiB_endrun",
        "startSec": 40.4,  # SCENES.iiB.start (1200f) + LEAD_IN
        "text":     "Mark Ross calls. He's a regular. The audio is real — Speechmatics TTS, transcribed by Speechmatics batch, diarization on. Trail on the right. Turn one, read the transcript. Turn two, Vultr's Vector Store — and the question is specific. Allergies on file? Comes back: gluten-free. Turn three, booking dot create, payload typed against the template's JSON schema. Turn four, WhatsApp confirmation. Turn five, finalize: fields, intent, sentiment, briefing. Five turns. Two thousand tokens. Six seconds end to end.",
    },
    {
        "id":       "iiC_selfcorrect",
        "startSec": 80.4,  # SCENES.iiC.start (2400f) + LEAD_IN
        "text":     "Here it's a loop, not a script. The agent submits party_size equals zero. Validator says no — validation failed. Next turn: re-read the transcript, find four people, resubmit, executed. Two attempts per action, hard cap. A mutation that already succeeded cannot be replayed.",
    },
    {
        "id":       "iiD_memory",
        "startSec": 104.4,  # SCENES.iiD.start (3120f) + LEAD_IN
        "text":     "The briefing the agent wrote at the end of the last call. Same number rings again — the operator sees it before picking up. Gluten-free. Last booking. Anniversary. No typing. No second tab. No CRM lookup. The after of one call is the before of the next.",
    },
    {
        "id":       "iiE_wizard",
        "startSec": 126.4,  # SCENES.iiE.start (3780f) + LEAD_IN
        "text":     "Three presets ship: restaurant, dentist, body shop. For everything else, a wizard. Two to five questions, out the other end a working template — JSON schema, action tools, two fresh demo MP3s through Speechmatics TTS. Pick any vertical. Same loop. Same audit trail. New domain in thirty seconds.",
    },
    {
        "id":       "iiF_honest",
        "startSec": 149.4,  # SCENES.iiF.start (4470f) + LEAD_IN
        "text":     "What's real: Speechmatics on every call. The Gemini ADK loop. Vultr RAG with audited input tokens. Postgres. The profile mutation. The demo MP3s. Mocked, by design: booking, WhatsApp, calendar, payment, CRM — the outbound writes no public demo should fire. Swapping a mock for real is one entry in the action catalog plus an env var. Not a migration.",
    },
    {
        "id":       "iiG_market",
        "startSec": 173.4,  # SCENES.iiG.start (5190f) + LEAD_IN
        "text":     "Italy is where we measured first: four hundred seventy-eight thousand booking-led businesses, a phone-led subset of one hundred eighty-five thousand, a hundred and ten million in initial SAM. Worldwide is next. Against CallRail, Aircall, Dialpad AI — one word of difference. After. They're on the call. We are everything that happens next.",
    },
    {
        "id":       "coda_close",
        "startSec": 195.4,  # SCENES.coda.start (5850f) + LEAD_IN
        "text":     "Vultr · Postgres · Vector Store · Serverless Inference. Gemini through ADK. Speechmatics for STT and TTS. MIT. Afterglow. Stay in the moment. We handle the after.",
    },
]

# ─── GENERA OGNI SEGMENTO ──────────────────────────────────────────────────────

async def generate_segment(seg: dict, idx: int) -> Path:
    """Genera un file MP3 per un singolo segmento."""
    out_path = OUT_DIR / f"seg_{seg['id']}.mp3"

    print(f"  [{idx+1}/{len(SEGMENTS)}] Generating: {seg['id']}")
    print(f"           Text: \"{seg['text'][:60]}{'...' if len(seg['text']) > 60 else ''}\"")

    communicate = edge_tts.Communicate(
        text=seg['text'],
        voice=VOICE,
        rate=RATE,
        pitch=PITCH,
    )
    await communicate.save(str(out_path))
    print(f"           Saved: {out_path.name}")
    return out_path


async def main():
    print(f"\n[MIC] Generating voiceover with {VOICE}")
    print(f"   Rate: {RATE}  Pitch: {PITCH}")
    print(f"   Output: {OUT_DIR}\n")

    # Genera ogni segmento
    segment_files = []
    for i, seg in enumerate(SEGMENTS):
        path = await generate_segment(seg, i)
        segment_files.append({
            "id":       seg["id"],
            "startSec": seg["startSec"],
            "file":     path.name,
        })

    # Salva il manifest JSON (usato da Remotion per la sincronizzazione)
    manifest_path = OUT_DIR / "voiceover-manifest.json"
    with open(manifest_path, "w") as f:
        json.dump({
            "voice": VOICE,
            "rate": RATE,
            "segments": segment_files,
        }, f, indent=2)
    print(f"\n✅ Manifest saved: {manifest_path.name}")

    # Combina tutti i segmenti in un unico file continuo
    # Usa ffmpeg se disponibile, altrimenti istruzioni manuali
    try:
        import subprocess

        # Crea il file list per ffmpeg
        list_path = OUT_DIR / "segments.txt"
        combined_path = OUT_DIR / "voiceover.mp3"

        # Genera il voiceover combinato con pause calibrate
        # Prima generiamo i segmenti con il timing giusto usando un unico testo
        # con SSML (Speech Synthesis Markup Language) per inserire pause

        print("\n📦 Combining segments with ffmpeg...")

        # Costruisci lista ffmpeg
        with open(list_path, "w") as f:
            for seg_info in segment_files:
                seg_path = OUT_DIR / seg_info["file"]
                f.write(f"file '{seg_path.resolve()}'\n")

        result = subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
             "-i", str(list_path), "-c", "copy", str(combined_path)],
            capture_output=True, text=True
        )

        if result.returncode == 0:
            print(f"✅ Combined: {combined_path.name}")
        else:
            print("⚠️  ffmpeg not found or error. Segments are saved individually.")
            print("   You can combine them manually or use the segments individually.")

    except Exception as e:
        print(f"⚠️  Could not combine: {e}")
        print("   Individual segment files are ready in public/audio/")

    # Genera anche la versione SSML con pause integrate per massima precisione
    await generate_full_ssml()

    print("\n📋 Next steps:")
    print("   1. Review public/audio/ for the generated files")
    print("   2. Run: npm run video:preview to check audio sync")
    print("   3. Adjust startSec values in SEGMENTS if needed")
    print("   4. Re-run this script to regenerate\n")


async def generate_full_ssml():
    """Genera l'intero voiceover in un unico file con pause SSML precise."""
    print("\n🎵 Generating unified voiceover with SSML pauses...")

    # SSML con pause calibrate
    # Il video inizia a t=0. Le pause sono calcolate rispetto al segmento precedente.

    parts = []
    prev_end_sec = 0.0

    for seg in SEGMENTS:
        start = seg["startSec"]
        # Pausa necessaria dall'ultimo segmento
        pause_ms = max(0, int((start - prev_end_sec) * 1000))

        if pause_ms > 100:
            parts.append(f'<break time="{pause_ms}ms"/>')

        parts.append(seg["text"])

        # Stima durata del parlato (circa 130 parole/minuto con -8% rate)
        word_count = len(seg["text"].split())
        duration_sec = (word_count / 120)  # 120 parole/min @ rate lento
        prev_end_sec = start + duration_sec

    # Prima pausa (intro silenzioso: 3.3 secondi)
    ssml_text = f'<speak><break time="3300ms"/>' + "".join(parts) + "</speak>"

    out_path = OUT_DIR / "voiceover-ssml.mp3"

    try:
        communicate = edge_tts.Communicate(
            text="\n\n".join([s["text"] for s in SEGMENTS]),
            voice=VOICE,
            rate=RATE,
            pitch=PITCH,
        )
        await communicate.save(str(out_path))
        print(f"✅ Unified voiceover: {out_path.name}")
    except Exception as e:
        print(f"⚠️  Could not generate unified: {e}")


if __name__ == "__main__":
    asyncio.run(main())
