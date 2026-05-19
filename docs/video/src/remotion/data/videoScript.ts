// Central source of truth for all copy, timing, and scene metadata.

export const COLORS = {
  bg: '#0B0D12',
  bgAlt: '#0F1118',
  surface: '#161922',
  surfaceElevated: '#1A1F2B',
  surfaceVariant: '#1F2330',
  primary: '#3b82f6',
  primaryMid: 'rgba(59,130,246,0.3)',
  primaryDim: 'rgba(59,130,246,0.12)',
  primaryGlow: 'rgba(59,130,246,0.06)',
  onSurface: '#ECEEF2',
  onSurfaceVariant: '#A5A9B3',
  success: '#86D8A2',
  successDim: 'rgba(134,216,162,0.15)',
  successSolid: '#26B31E',
  error: '#B3261E',
  errorDim: 'rgba(179,38,30,0.15)',
  border: '#3A3F4E',
  borderDim: '#262B3A',
  white: '#FFFFFF',
};

export const EASING = {
  // Spring-like ease-out — Apple HIG feel
  spring: [0.16, 1, 0.3, 1] as [number, number, number, number],
  // Smooth ease-in-out — Material Design standard
  standard: [0.4, 0, 0.2, 1] as [number, number, number, number],
  // Decelerate — elements arriving on screen
  decelerate: [0, 0, 0.2, 1] as [number, number, number, number],
};

// Scene durations in frames (@30fps)
// Calibrated on the real voiceover audio durations + 0.7s lead-in + 1.8s trail-out.
// Total video: 113.5s = 3405 frames.
export const SCENES = {
  intro:        { start: 0,    duration: 150  },  // 0–5s
  promise:      { start: 150,  duration: 375  },  // 5–17.5s
  pipeline:     { start: 525,  duration: 405  },  // 17.5–31s   (HomeReveal)
  incomingCall: { start: 930,  duration: 1020 },  // 31–65s     (estesa: 31s audio)
  callAnalysis: { start: 1950, duration: 465  },  // 65–80.5s
  actions:      { start: 2415, duration: 510  },  // 80.5–97.5s
  memory:       { start: 2925, duration: 405  },  // 97.5–111s
  techStack:    { start: 3330, duration: 390  },  // 111–124s
  outro:        { start: 3720, duration: 210  },  // 124–131s
} as const;

export const TOTAL_FRAMES = 3930; // 131.0 seconds

export const VIDEO_CONFIG = {
  fps: 30,
  width: 1920,
  height: 1080,
};

// Demo data from seed — restaurant scenario
export const DEMO_CALL = {
  caller: 'Sarah Mitchell',
  phone: '+44 7700 900789',
  time: '2 min ago',
  duration: '3m 42s',
  domain: 'restaurant',
  intent: 'Booking request',
  sentiment: 'Positive',
  transcript: [
    { speaker: 'Caller', text: "Hi, I'd like to book a table for four, this Friday at 8 PM." },
    { speaker: 'Operator', text: "Of course! Could I get your name, please?" },
    { speaker: 'Caller', text: "Sure, it's Sarah Mitchell. Oh, and we have one gluten allergy in the group." },
    { speaker: 'Operator', text: "Perfect, noted. We'll see you Friday at 8 — shall I send a WhatsApp confirmation?" },
    { speaker: 'Caller', text: "Yes please, that'd be great. Thank you!" },
  ],
  fields: [
    { key: 'party_size', label: 'Party size', value: '4', confidence: 97, evidence: '"a table for four"' },
    { key: 'booking_date', label: 'Date', value: 'Friday, 23 May', confidence: 95, evidence: '"this Friday"' },
    { key: 'booking_time', label: 'Time', value: '8:00 PM', confidence: 98, evidence: '"at 8 PM"' },
    { key: 'customer_name', label: 'Name', value: 'Sarah Mitchell', confidence: 99, evidence: '"it\'s Sarah Mitchell"' },
    { key: 'allergies', label: 'Allergies', value: 'Gluten', confidence: 94, evidence: '"one gluten allergy"' },
  ],
  actions: [
    { type: 'booking.create', label: 'Create booking', status: 'completed', mock: true },
    { type: 'whatsapp.send_confirmation', label: 'Send WhatsApp confirmation', status: 'completed', mock: true },
    { type: 'customer.update_profile', label: 'Update customer profile', status: 'completed', mock: false },
  ],
  briefing: 'Returning caller, prefers window seating. Booked for 4 this Friday at 8 PM; gluten allergy noted.',
};

export const PIPELINE_STEPS = [
  {
    n: '01',
    icon: '🎙️',
    label: 'Speechmatics',
    sublabel: 'Transcription + Diarization',
    description: 'Speaker-labelled transcript in seconds',
  },
  {
    n: '02',
    icon: '✦',
    label: 'Gemini 2.0 Flash',
    sublabel: 'Structured extraction',
    description: 'Fields, intent, sentiment — one pass',
  },
  {
    n: '03',
    icon: '⚡',
    label: 'ADK Agent',
    sublabel: 'Action planning',
    description: 'Typed tool calls with evidence gates',
  },
  {
    n: '04',
    icon: '🗄️',
    label: 'Vultr Postgres',
    sublabel: 'Audit + Memory',
    description: 'Every action logged, caller memory updated',
  },
];

export const FEATURES = [
  {
    icon: '⚡',
    title: 'Autonomous, not a copilot',
    body: 'Bookings confirmed. WhatsApp sent. Profile updated. Every action logged and individually reversible.',
  },
  {
    icon: '🔇',
    title: 'Zero AI in the live call',
    body: 'The pipeline runs post-call. The screen updates while the operator is still saying goodbye.',
  },
  {
    icon: '🧠',
    title: 'Caller memory',
    body: 'Every call enriches a Vector Store. At the next ring, prior history arrives before the caller speaks.',
  },
  {
    icon: '🔧',
    title: 'Any vertical in minutes',
    body: 'A 4-step wizard turns a plain-language description into a typed extraction schema — no code required.',
  },
];
