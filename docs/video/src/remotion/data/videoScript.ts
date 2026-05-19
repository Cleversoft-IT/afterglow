// Central source of truth for all copy, timing, and scene metadata.
//
// Structure mirrors SUBMISSION.md §4 (Act I 0:30 typographic + Act II 4:00
// live demo + Coda 0:30 close = 5:00 total). Each scene's duration is the
// exact §4 budget rounded to whole seconds; voice-over MP3s are sized to
// fit those budgets at ~150 wpm. See docs/SUBMISSION.md §4 for the
// authoritative pace and narration.

export const COLORS = {
  bg: '#0B0D12',
  bgAlt: '#0F1118',
  surface: '#161922',
  surfaceElevated: '#1A1F2B',
  surfaceVariant: '#1F2330',
  primary: '#3b82f6',
  primaryDeep: '#1d4ed8',
  primaryMid: 'rgba(59,130,246,0.3)',
  primaryDim: 'rgba(59,130,246,0.12)',
  primaryGlow: 'rgba(59,130,246,0.06)',
  primarySoft: '#7DA9FF',
  onSurface: '#ECEEF2',
  onSurfaceVariant: '#A5A9B3',
  muted: '#94A3B8',
  success: '#86D8A2',
  successDim: 'rgba(134,216,162,0.15)',
  successSolid: '#26B31E',
  successDeep: '#1F7A3D',
  amber: '#FBBF24',
  amberDim: 'rgba(251,191,36,0.15)',
  amberDeep: '#B98412',
  error: '#B3261E',
  errorDim: 'rgba(179,38,30,0.15)',
  border: '#3A3F4E',
  borderDim: '#262B3A',
  white: '#FFFFFF',
};

export const EASING = {
  spring: [0.16, 1, 0.3, 1] as [number, number, number, number],
  standard: [0.4, 0, 0.2, 1] as [number, number, number, number],
  decelerate: [0, 0, 0.2, 1] as [number, number, number, number],
};

// ─── Scene timing — sized to fit the actual TTS-generated voice-overs ──
// 30 fps. Total: 212.5 s ≈ 3:32 (well under lablab's 5:00 cap).
// Act I (typographic spot) was dropped on purpose: we open straight on
// the product, no opening cinematic. Each scene = one MP3 + breathing
// room.
//
//   Act II.A    0:00–0:20  product in one sentence     615 f  (~20.5s)
//   Act II.B    0:20–1:06  end-to-end run + Trail     1380 f  (~46s)
//   Act II.C    1:06–1:30  self-correction             720 f  (~24s)
//   Act II.D    1:30–1:52  memory across calls         660 f  (~22s)
//   Act II.E    1:52–2:18  wizard / any vertical       780 f  (~26s)
//   Act II.F    2:18–2:50  real-vs-mocked              960 f  (~32s)
//   Act II.G    2:50–3:15  market & USP                750 f  (~25s)
//   Coda        3:15–3:32  partners + close            510 f  (~17s)

export const SCENES = {
  iiA:         { start: 0,    duration: 615  },
  iiB:         { start: 615,  duration: 1380 },
  iiC:         { start: 1995, duration: 720  },
  iiD:         { start: 2715, duration: 660  },
  iiE:         { start: 3375, duration: 780  },
  iiF:         { start: 4155, duration: 960  },
  iiG:         { start: 5115, duration: 750  },
  coda:        { start: 5865, duration: 510  },
} as const;

export const TOTAL_FRAMES = 6375; // 212.5 s · 3:32

export const VIDEO_CONFIG = {
  fps: 30,
  width: 1920,
  height: 1080,
};

// ─── Act I — typographic beats (no VO) ─────────────────────────────────
// Scene total: 660 f (22s). Beats:
//   0–60   held black + silence
//   60–240 "A call ends."             (~6s)
//   240–420 "Something else begins."  (~6s)
//   420–540 4 proof points stack      (~4s)
//   540–660 the claim                 (~4s)

export const ACT_I_BEATS = [
  { text: 'A call ends.',            start: 60,  duration: 180 },
  { text: 'Something else\nbegins.', start: 240, duration: 180 },
] as const;

// Beat 16–22s: four proof points stack in (one every ~10 frames / 0.33s)
export const ACT_I_PROOFS = [
  'Booking to enter.',
  'Confirmation to send.',
  'Allergy to remember.',
  'Briefing to write.',
] as const;

// Beat 22–27s: the claim (centred)
export const CLAIM = {
  wordmark: 'afterglow',
  line1: 'Stay in the moment.',
  line2: 'We handle the after.',
} as const;

// ─── Demo call data (Mark Ross — the §4 hero) ──────────────────────────

export const DEMO_CALL = {
  caller: 'Mark Ross',
  phone: '+44 7700 900123',
  time: 'just now',
  duration: '0:42',
  domain: 'restaurant',
  intent: 'Booking request',
  sentiment: 'Positive',
  language: 'en-GB',
  transcript: [
    { speaker: 'S1', text: "Hi, it's Mark Ross. I'd like to book a table for four, this Friday at 8 PM." },
    { speaker: 'S2', text: "Hi Mark — sure. Four people, Friday 8 PM. Anything we should know?" },
    { speaker: 'S1', text: "Still gluten-free here. Window table if you have one." },
    { speaker: 'S2', text: "Of course. I'll WhatsApp the confirmation in a minute." },
    { speaker: 'S1', text: "Perfect, thanks." },
  ],
  fields: [
    { key: 'party_size',    label: 'Party size', value: '4',               confidence: 97, evidence: '"a table for four"' },
    { key: 'booking_date',  label: 'Date',       value: 'Friday, 23 May',  confidence: 95, evidence: '"this Friday"' },
    { key: 'booking_time',  label: 'Time',       value: '8:00 PM',         confidence: 98, evidence: '"at 8 PM"' },
    { key: 'customer_name', label: 'Name',       value: 'Mark Ross',       confidence: 99, evidence: '"it\'s Mark Ross"' },
    { key: 'allergies',     label: 'Allergies',  value: 'Gluten-free',     confidence: 96, evidence: '"still gluten-free"' },
  ],
  actions: [
    { type: 'booking.create',            label: 'Create booking',           status: 'completed', mock: true  },
    { type: 'whatsapp.send_confirmation',label: 'Send WhatsApp confirmation', status: 'completed', mock: true  },
    { type: 'customer.update_profile',   label: 'Update customer profile',  status: 'completed', mock: false },
  ],
  briefing: 'Returning customer · gluten-free · prefers window seating. Booked 4 for Friday 8 PM; WhatsApp confirmation sent.',
};

// ─── Act II.B — the 5-turn agent trail (Mark Ross run) ─────────────────
// Each turn is one row in the Agent Reasoning Trail panel.

export const AGENT_TURNS = [
  {
    n: 1,
    title: 'Read transcript',
    tool: 'transcript',
    summary: 'Diarized · 5 utterances · S1 / S2 · 42s · language=en-GB',
    status: 'ok' as const,
  },
  {
    n: 2,
    title: 'lookup_customer_memory',
    tool: 'memory',
    summary: 'Vultr RAG · "allergies on file for Mark Ross?" → gluten-free · ~840 in / 92 out tokens',
    status: 'ok' as const,
  },
  {
    n: 3,
    title: 'booking.create',
    tool: 'action',
    summary: 'party_size=4 · date=2026-05-23 · time=20:00 · notes="gluten-free, window if available"',
    status: 'ok' as const,
  },
  {
    n: 4,
    title: 'whatsapp.send_confirmation',
    tool: 'action',
    summary: 'phone=+44…900123 · template=booking_confirm_en · vars={date, time, party_size}',
    status: 'ok' as const,
  },
  {
    n: 5,
    title: 'finalize_call',
    tool: 'finalize',
    summary: 'intent=booking · sentiment=positive · urgency=low · briefing written · status=completed',
    status: 'ok' as const,
  },
] as const;

// ─── Act II.C — the self-correction example ────────────────────────────
// Same caller, party_size mis-extracted on first attempt.

export const SELF_CORRECTION_TURNS = [
  {
    n: 6,
    title: 'booking.create — attempt 1',
    summary: 'party_size=0 · validator: required, > 0 ',
    status: 'failed' as const,
    badge: 'validation_failed',
  },
  {
    n: 7,
    title: 'read_transcript_segment',
    summary: 'Re-read 00:08–00:14 · "a table for four"',
    status: 'ok' as const,
    badge: null,
  },
  {
    n: 8,
    title: 'booking.create — attempt 2',
    summary: 'party_size=4 · date=2026-05-23 · 20:00',
    status: 'ok' as const,
    badge: 'executed',
  },
] as const;

// ─── Act II.F — Real-vs-mocked card ────────────────────────────────────

export const REAL_PROOFS = [
  { n: 1, head: 'Speechmatics',  body: 'Batch STT on every call · diarization on · language=auto.' },
  { n: 2, head: 'Gemini · ADK',  body: 'Multi-turn agent loop on every analyzed call. No offline stub.' },
  { n: 3, head: 'Vultr RAG',     body: 'Non-zero input_tokens per query — verifiable via /admin/rag-probe.' },
] as const;

export const REAL_AND_MORE = 'Plus Vultr Vector Store · Managed Postgres · customer.update_profile row mutation · TTS Preview for every demo MP3.';

export const MOCKED_TAGS = [
  'booking.*', 'whatsapp.*', 'sms.*', 'email.*',
  'calendar.*', 'payment.*', 'crm.*', 'review.*',
  'RAG write-back in demo',
] as const;

export const MOCK_SUMMARY = "The outbound write-side integrations a multi-judge public demo cannot safely fire.";

export const MOCK_SWAP_NOTE = 'Swap a mock for real = one entry in action_catalog.py + an env var. Not an architecture migration.';

// ─── Act II.G — Market & USP ───────────────────────────────────────────

export const MARKET_METRICS = [
  { num: '478k', label: 'booking-led IT businesses' },
  { num: '185k', label: 'phone-led subset (SAM)' },
  { num: '€110M', label: 'initial IT SAM / year (€50 / seat)' },
] as const;

export const MARKET_NOTE = 'Sized sector by sector from first-party Italian sources (FIPE · ISTAT · FNOMCeO · Key-Stone · Confartigianato · AGCOM · UPB). Same product, same wizard, expansion next: France · Germany · UK · Spain · US service economy.';

export const USP_ROWS = [
  { label: 'Where the AI lives',         them: 'On the call',       us: 'After the call' },
  { label: 'Who picks up',               them: 'AI voice agent',    us: 'The human' },
  { label: 'Memory across calls',        them: 'Transcript log',    us: 'Briefing + RAG' },
  { label: 'Auditable agent reasoning',  them: '—',                 us: 'First-class UI' },
  { label: 'Vertical adaptation',        them: 'Reseller config',   us: '2-min wizard' },
  { label: 'Geo model',                  them: 'Country-specific',  us: 'Single-tenant · worldwide' },
] as const;

export const REVENUE_STRIP = 'SaaS per seat · SMB owner/operator buyer · expansion by vertical template';

// ─── Coda — partners, stack, close ─────────────────────────────────────

export const STACK = {
  vultr: 'Cloud Compute · Managed Postgres · Vector Store · Serverless Inference',
  google: 'Gemini 3.1 Flash Lite via Google ADK 1.18',
  speechmatics: 'Batch STT · diarization · TTS Preview',
  deploy: 'Coolify · auto-deploy on push to main · MIT licensed',
};

export const URLS = {
  demo: 'demo.afterglow.cleversoft.it',
  app:  'app.afterglow.cleversoft.it',
  api:  'api.afterglow.cleversoft.it',
  repo: 'github.com/Cleversoft-IT/afterglow',
};

// ─── Wizard scene data (II.E) ──────────────────────────────────────────
// Live build of a dog-groomer template through wizard chat.

export const WIZARD_CHAT = [
  { from: 'user',   text: 'I run a small dog grooming studio.' },
  { from: 'wizard', text: 'Got it. Same-day bookings, or scheduled?' },
  { from: 'user',   text: 'Mostly same-day. Lots of repeat customers — allergies and breed-specific notes matter.' },
  { from: 'wizard', text: 'Building: 6 fields (breed, allergies, last_visit, …), 4 action tools (booking, sms_reminder, customer.update_profile, review.request_feedback). Generating two demo MP3s now.' },
] as const;

export const WIZARD_OUTPUT_FIELDS = [
  'breed', 'temperament', 'allergies', 'last_visit_notes', 'preferred_groomer', 'follow_up_window',
] as const;
