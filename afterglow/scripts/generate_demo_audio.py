"""Generate the three demo MP3s (restaurant / dentist / bodyshop) using
Speechmatics Text-to-Speech.

The Speechmatics TTS preview currently exposes only English voices (UK and US),
so the conversations below are EN UK/US. The audio is the *only* thing the
demo simulator plays back; the rest of the seed data (business names,
customer phone numbers) stays Italian by design.

Pipeline per file:
  1. Render each speaker line as WAV via POST /generate/<voice>?output_format=wav_16000
  2. Concatenate with 250ms of silence in between using ffmpeg's concat demuxer
  3. Encode to MP3 (96 kbps mono 22.05 kHz) to match the previous placeholders
  4. Write the result to both:
        afterglow/app/assets/audio/<domain>.mp3      (bundled by Expo)
        afterglow/backend/sample_audio/<domain>.mp3  (used by backend smoke tests)

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

import httpx

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


# Two distinct voices per scenario so Speechmatics' diarization can split them.
# Each conversation opens with the operator picking up the phone — that's the
# bit that was missing in the first cut and made the scripts feel out of context.
SCENARIOS: dict[str, list[Turn]] = {
    "restaurant": [
        Turn("operator", "sarah", "Good evening, La Trattoria. How may I help you?"),
        Turn("caller",   "theo",  "Hi, I'd like to book a table for Friday evening."),
        Turn("operator", "sarah", "Of course. How many people?"),
        Turn("caller",   "theo",  "Four of us, around eight thirty. My name is Mark."),
        Turn("caller",   "theo",  "One person is gluten intolerant. Can you handle that?"),
        Turn("operator", "sarah", "Absolutely, the kitchen has a dedicated gluten free menu."),
        Turn("caller",   "theo",  "Could you confirm by WhatsApp?"),
    ],
    "dentist": [
        Turn("operator", "jack",  "Greenwood Dental, this is the front desk. How can I help you?"),
        Turn("caller",   "megan", "Hi, I urgently need an appointment. My filling came off and I have severe pain in my lower right molar."),
        Turn("operator", "jack",  "I'm sorry to hear that. We can fit you in tomorrow morning. What's your name?"),
        Turn("caller",   "megan", "I'm Laura Bennett, you already have my chart on file."),
        Turn("operator", "jack",  "Perfect Laura. Do you have insurance coverage?"),
        Turn("caller",   "megan", "Yes, BlueCross. I'll send the policy number on WhatsApp."),
        Turn("operator", "jack",  "Good, I'll text you the confirmation with the time and directions."),
    ],
    "bodyshop": [
        Turn("operator", "megan", "Greenline Auto Body, good afternoon. How can I help?"),
        Turn("caller",   "jack",  "Hello, I backed into a pole and need to fix the rear bumper of a 2019 Fiat Panda."),
        Turn("operator", "megan", "Have you already opened an insurance claim?"),
        Turn("caller",   "jack",  "No, I'm not filing one. I'm paying out of pocket — I just need a quote."),
        Turn("operator", "megan", "Got it. When can you come in for the inspection?"),
        Turn("caller",   "jack",  "I'm free Thursday afternoon. My name is Andrew Green."),
        Turn("operator", "megan", "I'll text you the appointment confirmation."),
    ],
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

        for domain, turns in SCENARIOS.items():
            print(f"[tts] {domain}: rendering {len(turns)} turn(s)")
            wav_paths: list[Path] = []
            for idx, turn in enumerate(turns):
                wav = tmp_dir / f"{domain}_{idx:02d}_{turn.voice}.wav"
                _render_turn(client, turn, wav)
                wav_paths.append(wav)

            merged = tmp_dir / f"{domain}.wav"
            _concat_wavs(ffmpeg, wav_paths, silence_path, merged)

            for target_dir in (APP_AUDIO_DIR, BACKEND_AUDIO_DIR):
                target = target_dir / f"{domain}.mp3"
                _wav_to_mp3(ffmpeg, merged, target)
                size_kb = target.stat().st_size / 1024
                print(f"[tts] wrote {target.relative_to(REPO_ROOT)}  ({size_kb:.1f} KB)")


if __name__ == "__main__":
    main()
