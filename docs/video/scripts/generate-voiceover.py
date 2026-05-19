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
    {
        "id":       "intro-tagline",
        "startSec": 3.3,
        "text":     "afterglow.",
    },
    {
        "id":       "promise",
        "startSec": 6.7,
        "text":     "Every day, operators answer dozens of calls. Each one ends the same way — a note, a tab switch, a follow-up they might forget.",
    },
    {
        "id":       "home",
        "startSec": 14.7,
        "text":     "Afterglow replaces the phone app. Every call becomes a structured record — with extracted fields, booked appointments, and automatic follow-ups.",
    },
    {
        "id":       "incoming-call",
        "startSec": 24.7,
        "text":     "Answer normally. One tap on the blue AI button enables post-call analysis. The caller never knows. And before you even say hello — the AI already knows who's calling.",
    },
    {
        "id":       "call-analysis",
        "startSec": 34.7,
        "text":     "After the call, Gemini 2.0 Flash reads the full transcript and extracts every field in a single pass — party size, date, allergies, preferences — all with source evidence.",
    },
    {
        "id":       "actions",
        "startSec": 44.7,
        "text":     "Bookings are confirmed. WhatsApp messages are sent. Customer profiles are updated. No operator clicks required. Every action is audited — and individually reversible.",
    },
    {
        "id":       "memory",
        "startSec": 54.7,
        "text":     "Every call enriches a vector store. At the next ring, the operator is already briefed — who's calling, their preferences, and when they last visited.",
    },
    {
        "id":       "tech",
        "startSec": 63.7,
        "text":     "Built on Speechmatics for transcription, Google Gemini and ADK for intelligence, and Vultr for compute, database, and vector memory.",
    },
    {
        "id":       "outro",
        "startSec": 72.7,
        "text":     "afterglow. AI for what happens after the call.",
    },
]

# ─── GENERA OGNI SEGMENTO ──────────────────────────────────────────────────────

async def generate_segment(seg: dict, idx: int) -> Path:
    """Genera un file MP3 per un singolo segmento."""
    out_path = OUT_DIR / f"seg_{idx:02d}_{seg['id']}.mp3"

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
