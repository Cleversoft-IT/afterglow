"""Generate the six demo MP3s (three domains × two caller modes) using
Speechmatics Text-to-Speech.

Each domain (restaurant / dentist / bodyshop) ships TWO recordings — one
for the "existing customer" simulator button (caller already known by phone,
references shared history, doesn't re-introduce themselves) and one for the
"new customer" button (first-time caller, full self-introduction). The
operator voice stays constant per domain so the front-desk identity is
stable; the caller voice flips between modes so the two recordings sound
like different people on the line.

The Speechmatics TTS preview currently exposes only English voices (UK and
US), so the conversations below are EN UK/US. The audio is the *only*
thing the demo simulator plays back; the rest of the seed data (business
names, customer phone numbers) stays Italian by design.

Pipeline per file:
  1. Render each speaker line as WAV via POST /generate/<voice>?output_format=wav_16000
  2. Concatenate with 250ms of silence in between using ffmpeg's concat demuxer
  3. Encode to MP3 (96 kbps mono 22.05 kHz) to match the previous placeholders
  4. Write the result to both:
        afterglow/app/assets/audio/<domain>_<mode>.mp3      (bundled by Expo)
        afterglow/backend/sample_audio/<domain>_<mode>.mp3  (used by backend smoke tests)

Usage:
    python afterglow/scripts/generate_demo_audio.py

Requires:
  - SPEECHMATICS_API_KEY in env (or in afterglow/.env, auto-loaded)
  - ffmpeg on PATH
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import httpx

CallerMode = Literal["existing", "new"]

REPO_ROOT = Path(__file__).resolve().parents[2]
AFTERGLOW_DIR = REPO_ROOT / "afterglow"
APP_AUDIO_DIR = AFTERGLOW_DIR / "app" / "assets" / "audio"
BACKEND_AUDIO_DIR = AFTERGLOW_DIR / "backend" / "sample_audio"

TTS_BASE = "https://preview.tts.speechmatics.com/generate"
TTS_OUTPUT_FORMAT = "wav_16000"

INTER_LINE_SILENCE_SEC = 0.25
FINAL_MP3_BITRATE = "96k"
FINAL_MP3_SAMPLE_RATE = "22050"


@dataclass(frozen=True)
class Turn:
    speaker: str  # logical label (caller / operator) — for debug only
    voice: str    # Speechmatics voice id: sarah | theo | megan | jack
    text: str


# Per-domain, per-mode dialogues. Operator voice is held constant within a
# domain so it sounds like the same front-desk person; the caller voice
# flips between existing and new so the two recordings sound like
# different people on the line. Existing-mode callers do not re-introduce
# themselves ("It's Mark"), reference shared history, and ask for the
# usual setup. New-mode callers self-introduce with a full name and let
# the operator collect every required field from scratch.
SCENARIOS: dict[str, dict[CallerMode, list[Turn]]] = {
    "restaurant": {
        "existing": [
            Turn("operator", "sarah", "La Trattoria, good evening, this is Sarah."),
            Turn("caller",   "theo",  "Hi Sarah, it's Mark."),
            Turn("operator", "sarah", "Hi Mark, lovely to hear you. The usual Friday booking?"),
            Turn("caller",   "theo",  "Yes please, party of four, around eight thirty."),
            Turn("operator", "sarah", "Quiet table and gluten free menu, like last time?"),
            Turn("caller",   "theo",  "Exactly, same setup. Could you confirm on WhatsApp?"),
            Turn("operator", "sarah", "Of course, I'll send it over in a minute. See you Friday."),
            Turn("caller",   "theo",  "Thanks Sarah, see you Friday."),
        ],
        "new": [
            Turn("operator", "sarah", "La Trattoria, good evening, this is Sarah. How can I help?"),
            Turn("caller",   "megan", "Hi, I've never booked with you before. I'd like a table for Saturday evening."),
            Turn("operator", "sarah", "Of course. Could I have your name please?"),
            Turn("caller",   "megan", "It's Hannah Clarke."),
            Turn("operator", "sarah", "Thanks Hannah. How many guests, and what time?"),
            Turn("caller",   "megan", "Three of us, around seven forty five."),
            Turn("operator", "sarah", "Noted. Any allergies or special requests we should know about?"),
            Turn("caller",   "megan", "Yes, one of us is lactose intolerant. Window table if you have one."),
            Turn("operator", "sarah", "All set. I'll text you the confirmation by SMS. See you Saturday."),
            Turn("caller",   "megan", "Perfect, thank you. Goodbye."),
        ],
    },
    "dentist": {
        "existing": [
            Turn("operator", "jack",  "Greenwood Dental, this is Jack at the front desk."),
            Turn("caller",   "megan", "Hi Jack, it's Laura."),
            Turn("operator", "jack",  "Hi Laura, good to hear from you. What can we do today?"),
            Turn("caller",   "megan", "The crown you fitted last month is feeling a little loose, I'd like it checked."),
            Turn("operator", "jack",  "I'm sorry to hear that. Same chair as last time, with Dr. Patel?"),
            Turn("caller",   "megan", "Yes please, if she has space."),
            Turn("operator", "jack",  "She has a slot tomorrow at ten fifteen. Does that work?"),
            Turn("caller",   "megan", "Tomorrow at ten fifteen is fine."),
            Turn("operator", "jack",  "Booked. I'll WhatsApp you the reminder on your usual number. Take care."),
            Turn("caller",   "megan", "Thanks Jack, see you tomorrow."),
        ],
        "new": [
            Turn("operator", "jack",  "Greenwood Dental, this is Jack. How can I help?"),
            Turn("caller",   "sarah", "Hi, I'm not a patient here yet. I need an urgent appointment."),
            Turn("operator", "jack",  "I'm sorry to hear that. May I have your name?"),
            Turn("caller",   "sarah", "Sophie Turner. I cracked a molar this morning eating a hard candy."),
            Turn("operator", "jack",  "Painful. We can fit you in this afternoon. Is the tooth bleeding?"),
            Turn("caller",   "sarah", "No bleeding, but it's very sharp pain on the lower right."),
            Turn("operator", "jack",  "Understood. Three thirty today with Dr. Patel — does that work?"),
            Turn("caller",   "sarah", "Yes, three thirty is perfect."),
            Turn("operator", "jack",  "I'll text you the address and the new patient form. See you later."),
            Turn("caller",   "sarah", "Thank you so much, goodbye."),
        ],
    },
    "bodyshop": {
        "existing": [
            Turn("operator", "megan", "Greenline Auto Body, good afternoon, this is Megan."),
            Turn("caller",   "jack",  "Hey Megan, it's Andrew."),
            Turn("operator", "megan", "Hi Andrew. Is it the Fiat Panda again?"),
            Turn("caller",   "jack",  "Same car, yeah. I clipped a bollard, the front bumper has a dent and a long scratch."),
            Turn("operator", "megan", "Out of pocket like last time, or going through insurance this round?"),
            Turn("caller",   "jack",  "Out of pocket, same as before. Just need a quick quote."),
            Turn("operator", "megan", "Thursday afternoon at two works, same bay?"),
            Turn("caller",   "jack",  "Thursday at two is good. Thanks Megan."),
            Turn("operator", "megan", "See you Thursday, Andrew."),
        ],
        "new": [
            Turn("operator", "megan", "Greenline Auto Body, good afternoon, this is Megan. How can I help?"),
            Turn("caller",   "theo",  "Hi, first time calling you. I had a small fender-bender this morning."),
            Turn("operator", "megan", "Sorry to hear that. May I have your name and the vehicle?"),
            Turn("caller",   "theo",  "It's Daniel Reed. Twenty twenty Toyota Corolla, plate Bravo Mike six four Lima Whisky."),
            Turn("operator", "megan", "Got it. What's the damage, and is the car drivable?"),
            Turn("caller",   "theo",  "Rear quarter panel is dented, taillight is cracked. It's drivable, lights still work."),
            Turn("operator", "megan", "Are you opening an insurance claim?"),
            Turn("caller",   "theo",  "Yes, I've already filed with my insurer."),
            Turn("operator", "megan", "Understood. Could you come in Friday morning at ten for an inspection?"),
            Turn("caller",   "theo",  "Friday at ten is fine, thank you."),
            Turn("operator", "megan", "Great, I'll text you the address. See you Friday."),
            Turn("caller",   "theo",  "Thanks, goodbye."),
        ],
    },
}


def _load_dotenv(path: Path) -> None:
    """Tiny .env loader so the script can run without pip-installing python-dotenv."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        # Strip trailing inline comments (`KEY=value  # comment`)
        if "  #" in value:
            value = value.split("  #", 1)[0].rstrip()
        os.environ.setdefault(key, value)


def _require_api_key() -> str:
    key = os.environ.get("SPEECHMATICS_API_KEY", "").strip()
    if not key:
        sys.exit("error: SPEECHMATICS_API_KEY is not set (check afterglow/.env)")
    return key


def _require_ffmpeg() -> str:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        sys.exit("error: ffmpeg not found on PATH")
    return ffmpeg


def _render_turn(client: httpx.Client, turn: Turn, out_path: Path) -> None:
    url = f"{TTS_BASE}/{turn.voice}"
    params = {"output_format": TTS_OUTPUT_FORMAT}
    resp = client.post(url, params=params, json={"text": turn.text}, timeout=60.0)
    if resp.status_code >= 400:
        snippet = resp.text[:300].replace("\n", " ")
        sys.exit(
            f"error: Speechmatics TTS {resp.status_code} for voice={turn.voice!r} "
            f"text={turn.text[:60]!r}...: {snippet}"
        )
    out_path.write_bytes(resp.content)


def _make_silence(ffmpeg: str, out_path: Path, seconds: float) -> None:
    subprocess.run(
        [
            ffmpeg, "-y", "-loglevel", "error",
            "-f", "lavfi",
            "-i", f"anullsrc=r=16000:cl=mono",
            "-t", f"{seconds}",
            "-acodec", "pcm_s16le",
            str(out_path),
        ],
        check=True,
    )


def _concat_wavs(ffmpeg: str, wavs: list[Path], silence: Path, out_wav: Path) -> None:
    """Concat using the ffmpeg concat demuxer (works because every input is the
    same codec / sample rate / channel layout)."""
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        for idx, w in enumerate(wavs):
            f.write(f"file '{w.as_posix()}'\n")
            if idx < len(wavs) - 1:
                f.write(f"file '{silence.as_posix()}'\n")
        list_file = Path(f.name)
    try:
        subprocess.run(
            [
                ffmpeg, "-y", "-loglevel", "error",
                "-f", "concat", "-safe", "0",
                "-i", str(list_file),
                "-c", "copy",
                str(out_wav),
            ],
            check=True,
        )
    finally:
        list_file.unlink(missing_ok=True)


def _wav_to_mp3(ffmpeg: str, wav: Path, mp3: Path) -> None:
    subprocess.run(
        [
            ffmpeg, "-y", "-loglevel", "error",
            "-i", str(wav),
            "-ac", "1",
            "-ar", FINAL_MP3_SAMPLE_RATE,
            "-b:a", FINAL_MP3_BITRATE,
            str(mp3),
        ],
        check=True,
    )


def main() -> None:
    _load_dotenv(AFTERGLOW_DIR / ".env")
    api_key = _require_api_key()
    ffmpeg = _require_ffmpeg()

    APP_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    BACKEND_AUDIO_DIR.mkdir(parents=True, exist_ok=True)

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    with httpx.Client(headers=headers) as client, tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        silence_path = tmp_dir / "silence.wav"
        _make_silence(ffmpeg, silence_path, INTER_LINE_SILENCE_SEC)

        for domain, modes in SCENARIOS.items():
            for mode, turns in modes.items():
                slug = f"{domain}_{mode}"
                print(f"[tts] {slug}: rendering {len(turns)} turn(s)")
                wav_paths: list[Path] = []
                for idx, turn in enumerate(turns):
                    wav = tmp_dir / f"{slug}_{idx:02d}_{turn.voice}.wav"
                    _render_turn(client, turn, wav)
                    wav_paths.append(wav)

                merged = tmp_dir / f"{slug}.wav"
                _concat_wavs(ffmpeg, wav_paths, silence_path, merged)

                for target_dir in (APP_AUDIO_DIR, BACKEND_AUDIO_DIR):
                    target = target_dir / f"{slug}.mp3"
                    _wav_to_mp3(ffmpeg, merged, target)
                    size_kb = target.stat().st_size / 1024
                    print(f"[tts] wrote {target.relative_to(REPO_ROOT)}  ({size_kb:.1f} KB)")


if __name__ == "__main__":
    main()
