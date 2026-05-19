"""
Generate the voice-over MP3s for the Afterglow pitch video.

Voice: en-US-AriaNeural — US English, female, modern "tech narrator".
Rate:  +0% (neutral, agile — no keynote drag).
Pitch: +0Hz.

Output: docs/video/public/audio/seg_<scene>.mp3, one MP3 per scene.

Composition.tsx loads each MP3 via staticFile() at
SCENES.<scene>.start + LEAD_IN — no manifest / SSML / concat helpers
needed. Keep this script narrow: one MP3 per scene, nothing else.

Usage:  python -X utf8 scripts/generate-voiceover.py
"""

import asyncio
from pathlib import Path

try:
    import edge_tts
except ImportError:
    print("edge-tts not found. Install with: pip install edge-tts")
    raise SystemExit(1)

# ─── CONFIG ────────────────────────────────────────────────────────────

VOICE = "en-US-AriaNeural"
RATE  = "+0%"
PITCH = "+0Hz"

OUT_DIR = Path(__file__).parent.parent / "public" / "audio"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ─── SCENE SCRIPTS ─────────────────────────────────────────────────────
#
# Principle: the voice-over does NOT read the slide. It supplies the
# context, the why, the framing — things the viewer cannot read from
# the screen. Frame budgets are per docs/video/src/remotion/data/videoScript.ts:
#
#   iiA  615f  / 20.5s   ProductIntro
#   iiB  1380f / 46s     EndToEndRun
#   iiC  720f  / 24s     SelfCorrection
#   iiD  660f  / 22s     Memory
#   iiE  780f  / 26s     Wizard
#   iiF  960f  / 32s     RealVsMocked
#   iiG  750f  / 25s     Market (two-beat: number + USP cards)
#   coda 510f  / 17s     Coda
#
# Word counts target ~155 wpm at +0% with ~1s breathing per scene.

SEGMENTS = [
    {
        "id": "iiA_intro",
        "text": (
            "Operators have great tools for the call itself. "
            "The moment they hang up, the tooling stops — "
            "the booking, the follow-up, the next caller's history. "
            "All of it has to happen in their heads. "
            "That gap is where Afterglow lives."
        ),
    },
    {
        "id": "iiB_endrun",
        "text": (
            "When Mark hangs up, an agent loop starts. "
            "Not a fixed pipeline — the model picks its own next step. "
            "Read the transcript. Ask the memory store a specific question "
            "rather than a catch-all. Submit the booking with a payload "
            "the schema actually accepts. Send the confirmation. Then "
            "finalize. Every turn is logged and replayable — there is no "
            "black box here. The whole sequence costs less than the change "
            "in your operator's pocket."
        ),
    },
    {
        "id": "iiC_selfcorrect",
        "text": (
            "Models hallucinate. We don't pretend otherwise. "
            "Here the first booking attempt is wrong, the validator catches "
            "it before anything mutates, and the agent gets one chance to "
            "re-read the transcript and try again. Two attempts, then a "
            "human looks at it. The wrong call never becomes a wrong booking."
        ),
    },
    {
        "id": "iiD_memory",
        "text": (
            "The second call from the same number is cheaper, faster, "
            "and warmer — because we wrote a briefing at the end of the "
            "first one. The operator sees it before saying hello. "
            "That's the compound effect: every after becomes the next before."
        ),
    },
    {
        "id": "iiE_wizard",
        "text": (
            "Three verticals ship as presets, but the interesting part is "
            "what happens for the fourth. A short chat with a wizard, and "
            "Afterglow generates the fields, the action tools, and the "
            "demo audio. We didn't write a template per industry. "
            "We wrote the thing that writes templates."
        ),
    },
    {
        "id": "iiF_honest",
        "text": (
            "Some of these integrations are real, some are deliberately "
            "mocked. The transcription, the agent reasoning, the memory "
            "lookup — all real, on every call. The outbound side — "
            "the actual WhatsApp, the actual payment — stays mocked "
            "because a public demo shouldn't be texting real customers. "
            "Swapping a mock for a live integration is one entry in a "
            "config file. Not a rewrite."
        ),
    },
    {
        "id": "iiG_market",
        "text": (
            "We sized this from the ground up in Italy because that's "
            "where we sell. A hundred and ten million in annual spend — "
            "at fifty euros per seat, just the businesses where a phone "
            "leads a booking. France, Germany, the UK — same wizard, "
            "same loop. What CallRail and Dialpad sell is the call. "
            "We sell the after."
        ),
    },
    {
        "id": "coda_close",
        "text": (
            "Built in five days on Vultr. One agent, one model, one loop. "
            "Open source, MIT. The demo URL is below. "
            "Operators stay in the moment. The system handles the after."
        ),
    },
]

# ─── GENERATE ──────────────────────────────────────────────────────────

async def generate_segment(seg: dict, idx: int, total: int) -> Path:
    out_path = OUT_DIR / f"seg_{seg['id']}.mp3"
    preview = seg["text"].replace("\n", " ")
    if len(preview) > 70:
        preview = preview[:70] + "..."
    print(f"  [{idx + 1}/{total}] {seg['id']:<22} {preview}")

    communicate = edge_tts.Communicate(
        text=seg["text"],
        voice=VOICE,
        rate=RATE,
        pitch=PITCH,
    )
    await communicate.save(str(out_path))
    return out_path


async def main():
    print(f"\n[edge-tts] voice={VOICE} rate={RATE} pitch={PITCH}")
    print(f"           output={OUT_DIR}\n")

    for i, seg in enumerate(SEGMENTS):
        await generate_segment(seg, i, len(SEGMENTS))

    print(f"\nDone. {len(SEGMENTS)} MP3 written.\n")


if __name__ == "__main__":
    asyncio.run(main())
