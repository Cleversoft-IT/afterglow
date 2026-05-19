// Script voiceover sincronizzato con le scene del video Afterglow
// Ogni segment ha: startFrame, endFrame, text
// @30fps — il video dura 2400 frame (80 secondi)

export interface VoiceSegment {
  id: string;
  startFrame: number;
  endFrame: number;
  startSec: number;
  endSec: number;
  text: string;
}

// ─── VOICE SEGMENTS ────────────────────────────────────────────────────────
// Calibrati sulle scene del video:
//   IntroScene:        0–180   (0–6s)     — silenzio, il logo rivela
//   PromiseScene:    180–420   (6–14s)
//   HomeReveal:      420–720  (14–24s)
//   IncomingCall:    720–1020  (24–34s)
//   CallAnalysis:   1020–1320  (34–44s)
//   Actions:        1320–1620  (44–54s)
//   Memory:         1620–1890  (54–63s)
//   TechStack:      1890–2160  (63–72s)
//   Outro:          2160–2400  (72–80s)

export const VOICE_SEGMENTS: VoiceSegment[] = [
  // Intro — nessun testo (lascia respirare il logo)
  // Inizia a parlare leggermente dopo il reveal del logo

  {
    id: 'intro-tagline',
    startFrame: 100,
    endFrame: 180,
    startSec: 3.3,
    endSec: 6,
    text: 'afterglow.',
  },
  {
    id: 'promise',
    startFrame: 200,
    endFrame: 420,
    startSec: 6.7,
    endSec: 14,
    text: 'Every day, operators answer dozens of calls. Each one ends the same way — a note, a tab switch, a follow-up they might forget.',
  },
  {
    id: 'home',
    startFrame: 440,
    endFrame: 700,
    startSec: 14.7,
    endSec: 23.3,
    text: "Afterglow replaces the phone app. Every call becomes a structured record — with extracted fields, booked appointments, and automatic follow-ups.",
  },
  {
    id: 'incoming-call',
    startFrame: 740,
    endFrame: 1000,
    startSec: 24.7,
    endSec: 33.3,
    text: "Answer normally. One tap on the blue AI button enables post-call analysis. The caller never knows. And before you even say hello — the AI already knows who's calling.",
  },
  {
    id: 'call-analysis',
    startFrame: 1040,
    endFrame: 1300,
    startSec: 34.7,
    endSec: 43.3,
    text: "After the call, Gemini 2.0 Flash reads the full transcript and extracts every field in a single structured pass — party size, date, allergies, preferences — all with source evidence.",
  },
  {
    id: 'actions',
    startFrame: 1340,
    endFrame: 1600,
    startSec: 44.7,
    endSec: 53.3,
    text: "Bookings are confirmed. WhatsApp messages are sent. Customer profiles are updated. No operator clicks required. Every action is audited — and individually reversible.",
  },
  {
    id: 'memory',
    startFrame: 1640,
    endFrame: 1870,
    startSec: 54.7,
    endSec: 62.3,
    text: "Every call enriches a vector store. At the next ring, the operator is already briefed — who's calling, their preferences, and when they last visited.",
  },
  {
    id: 'tech',
    startFrame: 1910,
    endFrame: 2140,
    startSec: 63.7,
    endSec: 71.3,
    text: "Built on Speechmatics for transcription and diarization, Google Gemini and ADK for intelligence, and Vultr for compute, database, and vector memory.",
  },
  {
    id: 'outro',
    startFrame: 2180,
    endFrame: 2380,
    startSec: 72.7,
    endSec: 79.3,
    text: "afterglow. AI for what happens after the call.",
  },
];

// Testo concatenato per la generazione TTS (con pause [silence] tra i segmenti)
export const FULL_SCRIPT = VOICE_SEGMENTS.map(s => s.text).join('\n\n');
