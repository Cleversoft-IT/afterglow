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
# different people on the line.
#
# Quality bar (apply when rewriting any scenario — must clear before
# regenerating audio):
# - Each conversation exercises 2-3 actions the seed template ships
#   (see `app/db/seed.py` *_TEMPLATE.action_types`). The mapping is
#   asserted in `tests/test_seed_script_action_alignment.py`.
# - Domain voice is distinctive: restaurant = warm hospitality with
#   sensory detail; dentist = clinical-empathetic, restraint on pain
#   description; bodyshop = pragmatic-technical, plates and damage codes.
# - The caller is a person, not a form-filler: at least one specific
#   biographical detail (a memory for `existing`, a fresh complication
#   for `new`), short turns, natural hesitations are welcome.
# - No filler ("test test test", "demo demo demo", "lorem ipsum"). If a
#   judge listens live, it must not embarrass anyone.
# - Existing-mode callers reference shared history ("the Friday booking",
#   "the crown Dr. Patel fitted last month", "the Fiat Panda again");
#   new-mode callers self-introduce with a full name and the operator
#   collects every required field from scratch.
SCENARIOS: dict[str, dict[CallerMode, list[Turn]]] = {
    "restaurant": {
        # Surfaces: booking.reschedule + review.request_feedback
        "existing": [
            Turn("operator", "sarah", "La Trattoria, good evening, this is Sarah."),
            Turn("caller",   "theo",  "Hi Sarah, it's Mark Ross. The Friday eight thirty for four — any chance we move it?"),
            Turn("operator", "sarah", "Hi Mark, of course. Same week or a different one?"),
            Turn("caller",   "theo",  "Same week. Saturday at eight would be better. My in-laws are flying in late."),
            Turn("operator", "sarah", "Saturday at eight, party of four, gluten free menu and the quiet table by the window — like last time?"),
            Turn("caller",   "theo",  "You remembered. Yes, identical setup."),
            Turn("operator", "sarah", "Done. After dinner I'll send a short note asking for a Google review — only if you enjoyed it."),
            Turn("caller",   "theo",  "Happy to leave one if the tiramisù is on form."),
            Turn("operator", "sarah", "I'll have a word with the kitchen. See you Saturday, Mark."),
            Turn("caller",   "theo",  "Thanks Sarah, see you then."),
        ],
        # Surfaces: booking.create + whatsapp.send_confirmation
        #           + payment.request_deposit
        "new": [
            Turn("operator", "sarah", "La Trattoria, good evening, this is Sarah. How can I help?"),
            Turn("caller",   "megan", "Hi, first time calling. I'd like to book Saturday evening — it's my mother's seventieth."),
            Turn("operator", "sarah", "Lovely. Could I have your name and how many guests?"),
            Turn("caller",   "megan", "Hannah Clarke. Seven of us, around eight."),
            Turn("operator", "sarah", "Seven for a celebration on Saturday at eight. Any allergies or dietary needs in the group?"),
            Turn("caller",   "megan", "My sister is lactose intolerant, and Mum wants the chef's tasting menu if you do it."),
            Turn("operator", "sarah", "We do, it's a fixed five courses. For parties of six or more we ask for a small deposit by card — fifty euro per guest, refundable up to forty-eight hours before."),
            Turn("caller",   "megan", "That's fair, go ahead."),
            Turn("operator", "sarah", "I'll send the deposit link by WhatsApp along with the booking confirmation. Anything else, Hannah?"),
            Turn("caller",   "megan", "A little something on the table for her would be magical. No singing though."),
            Turn("operator", "sarah", "Discreet candle, no singing — noted. See you Saturday."),
            Turn("caller",   "megan", "Thank you so much. Goodbye."),
        ],
    },
    "dentist": {
        # Surfaces: appointment.create + sms.send_reminder (now on the
        # dedicated sms bucket, not whatsapp) + calendar.send_invite.
        "existing": [
            Turn("operator", "jack",  "Greenwood Dental, this is Jack at the front desk."),
            Turn("caller",   "megan", "Hi Jack, it's Laura Bennett. The crown Dr. Patel fitted last month is feeling a touch loose when I bite on the left."),
            Turn("operator", "jack",  "I'm sorry, Laura. No pain, just movement?"),
            Turn("caller",   "megan", "No pain. More like the surface shifted half a millimetre."),
            Turn("operator", "jack",  "Let's not wait. Dr. Patel has tomorrow at ten fifteen — does that work?"),
            Turn("caller",   "megan", "Tomorrow at ten fifteen is fine."),
            Turn("operator", "jack",  "I'll text the SMS reminder the morning of, and I'll drop the appointment on your Google calendar as an invite — same e-mail as last time?"),
            Turn("caller",   "megan", "Same one, yes. Thanks for syncing it, I keep missing the wall calendar at home."),
            Turn("operator", "jack",  "See you tomorrow, Laura."),
            Turn("caller",   "megan", "Thanks Jack."),
        ],
        # Surfaces: appointment.create (urgent) + calendar.block_slot
        # + email.send (welcome packet with new patient form).
        "new": [
            Turn("operator", "jack",  "Greenwood Dental, this is Jack. How can I help?"),
            Turn("caller",   "sarah", "Hi, I'm a new patient. I cracked a molar on a hard candy about an hour ago."),
            Turn("operator", "jack",  "I'm sorry to hear that. May I have your name?"),
            Turn("caller",   "sarah", "Sophie Turner. The pain is sharp, lower right, when air hits it."),
            Turn("operator", "jack",  "Understood. Any bleeding or fever?"),
            Turn("caller",   "sarah", "No bleeding, no fever — just the pain."),
            Turn("operator", "jack",  "I'll block the three thirty slot today and hold it for you with Dr. Patel. Could you come in then?"),
            Turn("caller",   "sarah", "Yes, three thirty works."),
            Turn("operator", "jack",  "Good. I'll e-mail you a welcome packet — the new patient form, our address, parking instructions. What's the best e-mail?"),
            Turn("caller",   "sarah", "sophie dot turner at fast-mail dot com."),
            Turn("operator", "jack",  "Got it. Fill the form before you arrive if you can, it saves us ten minutes."),
            Turn("caller",   "sarah", "Will do. Thank you so much. Goodbye."),
        ],
    },
    "bodyshop": {
        # Surfaces: appointment.create_inspection + payment.request_deposit
        # (parts deposit for the bumper paint colour code).
        "existing": [
            Turn("operator", "megan", "Greenline Auto Body, good afternoon, this is Megan."),
            Turn("caller",   "jack",  "Hey Megan, it's Andrew Green. The Fiat Panda, plate Bravo Romeo six six four Charlie Yankee — clipped a bollard outside Lidl this morning."),
            Turn("operator", "megan", "Hi Andrew, ouch. Bumper again?"),
            Turn("caller",   "jack",  "Front bumper, dent and a long scratch down the wing. No mechanical issue, still drives clean."),
            Turn("operator", "megan", "Out of pocket like the last two times?"),
            Turn("caller",   "jack",  "Out of pocket. Just need a quick estimate."),
            Turn("operator", "megan", "Thursday afternoon at two for the inspection, same bay as before — works?"),
            Turn("caller",   "jack",  "Thursday at two is good."),
            Turn("operator", "megan", "If the colour code matches what's already on the shelf we can start straight away. Otherwise we order it in — and for that I'd ask a hundred-and-fifty deposit on the paint by Friday."),
            Turn("caller",   "jack",  "Understood. Send me the deposit link if it comes to that."),
            Turn("operator", "megan", "Will do. See you Thursday, Andrew."),
            Turn("caller",   "jack",  "Thanks Megan."),
        ],
        # Surfaces: appointment.create_inspection + case.open_insurance
        # (manual-only) + payment.send_invoice (formal PDF quote for the
        # insurer's claim file).
        "new": [
            Turn("operator", "megan", "Greenline Auto Body, good afternoon, this is Megan. How can I help?"),
            Turn("caller",   "theo",  "Hi, first time calling you. I was rear-ended at a roundabout this morning — fault is the other driver."),
            Turn("operator", "megan", "Sorry to hear that. May I have your name and the vehicle?"),
            Turn("caller",   "theo",  "Daniel Reed. Twenty twenty Toyota Corolla, plate Bravo Mike six four Lima Whisky."),
            Turn("operator", "megan", "Got it. What's the damage, and is the car drivable?"),
            Turn("caller",   "theo",  "Rear quarter panel is dented, the taillight is cracked. Drivable, lights still work."),
            Turn("operator", "megan", "Are you opening an insurance claim?"),
            Turn("caller",   "theo",  "Yes — Allianz, claim number TC twelve forty-five oh nine."),
            Turn("operator", "megan", "Thanks. I'll have my colleague open the file on our side after the call. Could you come in Friday at ten for the inspection?"),
            Turn("caller",   "theo",  "Friday at ten is fine."),
            Turn("operator", "megan", "After the inspection I'll e-mail a formal quote — they'll need it as a PDF invoice for the claim. What's your e-mail?"),
            Turn("caller",   "theo",  "Daniel dot reed at proton mail dot com."),
            Turn("operator", "megan", "Got it. We'll see you Friday."),
            Turn("caller",   "theo",  "Thanks. Goodbye."),
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
