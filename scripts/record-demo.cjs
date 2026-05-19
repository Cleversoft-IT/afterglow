// Build the demo GIF that sits in the demo-site hero.
//
// Strategy (see .claude/skills/web-demo-gifs/SKILL.md):
//   - drive the live app in a phone-sized headless Chromium (Playwright),
//   - take one PNG per "story beat" with hand-tuned per-frame delays,
//   - inject a faux cursor + tap ripple so the click on the AI FAB is
//     legible instead of a hard cut between "ringing" and "answering",
//   - stitch with ImageMagick (variable -delay per frame),
//   - optionally squeeze with gifsicle if installed.
//
// Output: demo-site/public/afterglow-demo.gif
//
// Re-run after frontend changes:
//   NODE_PATH=$(npm root -g) node scripts/record-demo.cjs
//
// Requirements:
//   - Node + global `playwright` (sudo npm install -g playwright)
//   - Chromium browser (playwright install chromium)
//   - `magick` on PATH (ImageMagick 7, already on Fedora)
//   - Optional: `gifsicle` for the final lossy squeeze
//     (sudo dnf install -y gifsicle)

const { chromium, request } = require('playwright');
const { mkdirSync, rmSync, existsSync, statSync } = require('node:fs');
const { resolve, join } = require('node:path');
const { execFileSync, spawnSync } = require('node:child_process');

// ─── Config ──────────────────────────────────────────────────────────────

const APP_URL = process.env.APP_URL || 'https://app.afterglow.cleversoft.it';
const API_URL = process.env.API_URL || 'https://api.afterglow.cleversoft.it';

// 390 × 845 = the viewport we drive the app at. React-native-web's mobile
// layout has a ~30 px top padding before the search bar (status-bar safe
// area). We clip that strip from each screenshot below — the bezel of the
// phone-frame in the demo-site would otherwise sit on top of a light-grey
// gap, which reads as "wrong margin".
const VIEWPORT = { width: 390, height: 845 };
const APP_TOP_PADDING = 15; // px to clip off the top of each screenshot
const FRAME_W = VIEWPORT.width;
const FRAME_H = VIEWPORT.height - APP_TOP_PADDING; // 830

// Centre of the blue (AI) FAB on the incoming-call screen. RN Paper renders
// the 3 FABs (Decline / AI / Accept) as 64-px circles centred horizontally
// on the bottom of the viewport.
const AI_FAB = { x: VIEWPORT.width / 2, y: 770 };
// Centre of the red hangup pill on the in-call screen (single FAB centred
// below the Keypad/Mute/Speaker/More control row).
const HANGUP = { x: VIEWPORT.width / 2, y: 780 };

const FRAMES_DIR = '/tmp/afterglow-demo-frames';
const OUT_DIR = resolve(__dirname, '../demo-site/public');
const OUT_GIF = join(OUT_DIR, 'afterglow-demo.gif');

const DEMO_SESSION_KEY = 'afterglow.demo_session_id';
const LOCALE_KEY = 'afterglow.locale';
const DEMO_SESSION_HEADER = 'X-Demo-Session';

// Per-frame display time in centiseconds (1/100s).
// Long on "read" frames, short on motion micro-steps. Spend bytes where
// the eye lands. See SKILL.md → "Per-frame timing strategy".
//
// Every click in the flow gets a single combined "tap" frame (cursor
// pinned on the target + ripple captured mid-bloom). Showing a cursor
// only on one tap and skipping the others felt incoherent.
// Special frame: `*-white` is synthesised at compose time by magick
// (xc:white), it doesn't come from a screenshot. Used as a brief fade
// between "Afterglow listening" and the later in-call frame to suggest
// time passing during the call.
const FRAMES = [
  { name: '01-home',          delay: 320 }, // 3.2s — read the call list
  { name: '02-tap-bookings',  delay: 80  }, // 0.8s — tap on Bookings tab
  { name: '03-bookings',      delay: 270 }, // 2.7s — filtered subset
  { name: '04-incoming',      delay: 380 }, // 3.8s — caller + briefing (key)
  { name: '05-tap-blue',      delay: 90  }, // 0.9s — tap on AI FAB
  { name: '06-answering',     delay: 160 }, // 1.6s — "Afterglow listening"
  { name: '07-white',         delay: 35,  synth: 'white' }, // 0.35s fade
  { name: '08-call-later',    delay: 180 }, // 1.8s — call still in progress
  { name: '09-tap-red',       delay: 90  }, // 0.9s — tap on hangup pill
  { name: '10-calls',         delay: 230 }, // 2.3s — back to call list
  { name: '11-tap-mark',      delay: 80  }, // 0.8s — tap on Mark Ross row
  { name: '12-detail-top',    delay: 240 }, // 2.4s — call detail header
  { name: '13-detail-mid',    delay: 30  }, // 0.3s — scroll motion
  { name: '14-detail-mid2',   delay: 30  }, // 0.3s — scroll motion
  { name: '15-detail-bottom', delay: 400 }, // 4.0s — final read (key)
];
// Total ≈ 25.0s loop.

// ─── Init scripts injected into every page in the context ───────────────

// Pre-seed the demo session id + locale so the app skips its boot handshake
// and the seeded restaurant template is already active.
function buildSessionInit(sessionId) {
  return [
    ({ sessionKey, sessionVal, localeKey, localeVal }) => {
      try {
        localStorage.setItem(sessionKey, sessionVal);
        localStorage.setItem(localeKey, localeVal);
      } catch { /* ignore */ }
    },
    {
      sessionKey: DEMO_SESSION_KEY, sessionVal: sessionId,
      localeKey: LOCALE_KEY, localeVal: 'en',
    },
  ];
}

// Kill app animations so transitions don't smear into screenshots (the
// story here is *what's on screen*, not *how it animates in*). Per SKILL.md.
const killAnimationsInit = () => {
  const s = document.createElement('style');
  s.textContent = `*, *::before, *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }`;
  document.documentElement.appendChild(s);
};

// Faux cursor + tap-ripple helpers. Headless Chromium has no system
// cursor, and RN Paper's ripple needs a real pointer event we don't
// fire here. We inject the cursor lazily via page.evaluate on first
// use — addInitScript would do this too, but proved fragile across the
// Expo Router SPA navigations.
async function ensureCursorOverlay(page) {
  await page.evaluate(() => {
    if (document.getElementById('demo-cursor')) return;
    const style = document.createElement('style');
    style.id = 'demo-cursor-style';
    style.textContent = `
      #demo-cursor {
        position: fixed; top: 0; left: 0; width: 24px; height: 24px;
        border-radius: 50%;
        background: rgba(0, 0, 0, 0.45);
        box-shadow: 0 0 0 2px rgba(255, 255, 255, 0.95),
                    0 2px 6px rgba(0, 0, 0, 0.25);
        transform: translate(-50%, -50%);
        pointer-events: none;
        z-index: 2147483647;
        opacity: 0;
        transition: transform 220ms cubic-bezier(.2,.7,.2,1),
                    opacity 120ms ease;
      }
      .demo-ripple {
        position: fixed; width: 14px; height: 14px; border-radius: 50%;
        background: rgba(56, 116, 240, 0.55);
        pointer-events: none;
        transform: translate(-50%, -50%);
        z-index: 2147483646;
        animation: demo-ripple 700ms ease-out forwards;
      }
      @keyframes demo-ripple {
        0%   { width: 14px;  height: 14px;  opacity: 0.7; }
        100% { width: 160px; height: 160px; opacity: 0;   }
      }
    `;
    document.documentElement.appendChild(style);
    const cursor = document.createElement('div');
    cursor.id = 'demo-cursor';
    document.documentElement.appendChild(cursor);
  });
}

async function showCursor(page, x, y) {
  await ensureCursorOverlay(page);
  await page.evaluate(([x, y]) => {
    const c = document.getElementById('demo-cursor');
    c.style.transform = `translate(${x}px, ${y}px) translate(-50%, -50%)`;
    c.style.opacity = '1';
  }, [x, y]);
}

async function hideCursor(page) {
  await page.evaluate(() => {
    const c = document.getElementById('demo-cursor');
    if (c) c.style.opacity = '0';
  });
}

async function fireTap(page, x, y) {
  await page.evaluate(([x, y]) => {
    const r = document.createElement('div');
    r.className = 'demo-ripple';
    r.style.left = x + 'px';
    r.style.top = y + 'px';
    document.documentElement.appendChild(r);
    setTimeout(() => r.remove(), 800);
  }, [x, y]);
}

// One frame per tap: cursor pinned on the target + ripple captured
// mid-bloom (~25 % into its 700 ms animation). Then the real interaction
// is fired (either page.mouse.click on coordinates or .click() on a
// Playwright locator).
async function tapAndCapture(page, { x, y, name, fire }) {
  await showCursor(page, x, y);
  await page.waitForTimeout(220);   // let the cursor glide settle
  await fireTap(page, x, y);
  await page.waitForTimeout(180);   // catch ripple mid-bloom
  await shot(page, name);
  await hideCursor(page);
  await fire();
}

// ─── Helpers ─────────────────────────────────────────────────────────────

async function callsList(api, sessionId) {
  const r = await api.get(`${API_URL}/api/v1/calls?limit=10`, {
    headers: { [DEMO_SESSION_HEADER]: sessionId, Accept: 'application/json' },
  });
  if (!r.ok()) throw new Error(`calls list failed: ${r.status()} ${await r.text()}`);
  return r.json();
}

// After hang-up the new call enters Speechmatics + Gemini analysis in the
// background. It only appears at the top of the call list once status
// reaches "completed". The mock audio is ~1 min, plus a few seconds of
// model latency, so 2 minutes is a safe ceiling.
async function waitForNewCall(api, sessionId, preTopId, timeoutMs = 150000) {
  const start = Date.now();
  let lastStatus = null;
  while (Date.now() - start < timeoutMs) {
    const list = await callsList(api, sessionId);
    const top = list[0];
    if (top && top.id !== preTopId) {
      if (top.status === 'completed') return top;
      if (top.status !== lastStatus) {
        console.log(`  new call status: ${top.status}`);
        lastStatus = top.status;
      }
    }
    await new Promise((res) => setTimeout(res, 2000));
  }
  throw new Error(`timed out (${timeoutMs}ms) waiting for new-call analysis`);
}

async function provisionSession() {
  const api = await request.newContext();

  const res = await api.get(`${API_URL}/api/v1/templates`, {
    headers: { [DEMO_SESSION_HEADER]: 'new', Accept: 'application/json' },
  });
  if (!res.ok()) {
    throw new Error(`templates list failed: ${res.status()} ${await res.text()}`);
  }
  const headers = res.headers();
  const sessionId =
    headers[DEMO_SESSION_HEADER.toLowerCase()] || headers[DEMO_SESSION_HEADER];
  if (!sessionId || sessionId === 'new') {
    throw new Error(`server did not mint a demo session — got: ${sessionId}`);
  }
  const templates = await res.json();

  const restaurant = templates.find(
    (t) =>
      (t.domain_hint && t.domain_hint.toLowerCase() === 'restaurant') ||
      (t.name && t.name.toLowerCase().includes('standard booking')),
  );
  if (!restaurant) {
    throw new Error(
      `restaurant template not found among: ${templates.map((t) => t.name).join(', ')}`,
    );
  }

  const activate = await api.put(`${API_URL}/api/v1/templates/active`, {
    headers: { [DEMO_SESSION_HEADER]: sessionId, 'Content-Type': 'application/json' },
    data: { template_id: restaurant.id },
  });
  if (!activate.ok()) {
    throw new Error(`activate failed: ${activate.status()} ${await activate.text()}`);
  }

  await api.dispose();
  return { sessionId };
}

function shot(page, name) {
  return page.screenshot({
    path: join(FRAMES_DIR, `${name}.png`),
    clip: { x: 0, y: APP_TOP_PADDING, width: FRAME_W, height: FRAME_H },
  });
}

// Wait for webfonts + paint settle before snapping. Without this, the
// first frame of a navigation can capture the system-font fallback.
async function settle(page, extra = 300) {
  await page.evaluate(() => document.fonts && document.fonts.ready);
  await page.waitForTimeout(extra);
}

// ─── Recording flow ──────────────────────────────────────────────────────

async function record() {
  rmSync(FRAMES_DIR, { recursive: true, force: true });
  mkdirSync(FRAMES_DIR, { recursive: true });
  mkdirSync(OUT_DIR, { recursive: true });

  const { sessionId } = await provisionSession();
  console.log(`session: ${sessionId}`);

  // Persistent API context for polling the call list throughout the run
  // (used to detect when the freshly-handled call finishes analysis).
  const api = await request.newContext();

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: VIEWPORT,
    deviceScaleFactor: 1,
    isMobile: true,
    hasTouch: true,
    locale: 'en-US',
  });

  const [seedFn, seedArg] = buildSessionInit(sessionId);
  await context.addInitScript(seedFn, seedArg);
  await context.addInitScript(killAnimationsInit);

  const page = await context.newPage();

  // ── Frame 01: Home ─────────────────────────────────────────────────────
  await page.goto(`${APP_URL}/`, { waitUntil: 'networkidle' });
  await settle(page, 1200);
  await shot(page, '01-home');

  // ── Frame 02: tap the Bookings tab ────────────────────────────────────
  const bookingsTab = page.getByText('Bookings', { exact: true }).first();
  const bb = await bookingsTab.boundingBox();
  await tapAndCapture(page, {
    x: bb.x + bb.width / 2,
    y: bb.y + bb.height / 2,
    name: '02-tap-bookings',
    fire: () => bookingsTab.click(),
  });

  // ── Frame 03: Bookings filtered subset ────────────────────────────────
  await settle(page, 700);
  await shot(page, '03-bookings');

  // Snapshot of the current top-of-list id before we trigger the incoming
  // call. We'll wait until a *new* id surfaces at the top with status
  // "completed" — that's the one whose detail the GIF should land on.
  const preTopId = (await callsList(api, sessionId))[0]?.id ?? null;

  // ── Frame 04: Incoming call (Mark Ross + briefing) ────────────────────
  await page.goto(`${APP_URL}/incoming-call?caller=existing`, {
    waitUntil: 'networkidle',
  });
  await settle(page, 1500);
  await shot(page, '04-incoming');

  // ── Frame 05: tap the blue (AI) FAB ───────────────────────────────────
  await tapAndCapture(page, {
    x: AI_FAB.x,
    y: AI_FAB.y,
    name: '05-tap-blue',
    fire: () => page.mouse.click(AI_FAB.x, AI_FAB.y),
  });

  // ── Frame 06: "Afterglow listening" — call just answered ──────────────
  await page.waitForTimeout(1300);  // ringing → in-call transition
  await shot(page, '06-answering');

  // ── Frame 07 (synth): white fade card. Generated by magick later.
  // It bridges the real-world ~minute of call between answering and hang
  // up; without it the cut from 00:01 to a later state reads as a jump.

  // ── Frame 08: in-call screen later — timer has advanced ──────────────
  // Wait long enough for the in-call timer to tick a few times. We are
  // not chasing a specific "01:00" — any visibly higher number sells the
  // "time passed during the call" beat.
  await page.waitForTimeout(15000);
  await shot(page, '08-call-later');

  // ── Frame 09: tap the red hangup pill — VISUAL ONLY ──────────────────
  // The app's real hangUp() handler stops the audio and goes back, which
  // skips the submit. The submit only happens when acceptAi's audio
  // playback ends naturally (~30-40 s of recording) and submitAndClose
  // POSTs the blob to /api/v1/calls. So we render the cursor + ripple on
  // the hangup pill for narrative beat, but we don't fire a real click.
  await tapAndCapture(page, {
    x: HANGUP.x,
    y: HANGUP.y,
    name: '09-tap-red',
    fire: () => Promise.resolve(),
  });

  // ── Wait for the audio to finish playing and the app to auto-submit ──
  // submitAndClose() runs router.replace('/(drawer)/(tabs)') after the
  // POST returns. We wait for the navigation away from /incoming-call.
  console.log('waiting for audio playback to end and the call to submit…');
  await page.waitForFunction(
    () => !window.location.pathname.includes('incoming-call'),
    null,
    { timeout: 90000 },
  );

  // ── Now wait for Speechmatics + Gemini + ADK to finish the analysis ──
  // Only when that pipeline finishes does the new call surface at the
  // top of /api/v1/calls with status=completed. The GIF should land on
  // the detail of *that* call, not a seeded one.
  console.log('waiting for the new call to finish analysis…');
  const newCall = await waitForNewCall(api, sessionId, preTopId);
  console.log(`new call ready: ${newCall.id}`);

  // ── Frame 10: back to Calls list — new call is now at the top ────────
  await page.goto(`${APP_URL}/`, { waitUntil: 'networkidle' });
  await settle(page, 1200);
  await shot(page, '10-calls');

  // ── Frame 11: tap the top Mark Ross row (= the new call) ─────────────
  // getByText('Mark Ross').first() resolves to the topmost occurrence,
  // which is the call we just recorded (sorted by date desc).
  const markRow = page.getByText('Mark Ross').first();
  const mb = await markRow.boundingBox();
  await tapAndCapture(page, {
    x: mb.x + mb.width / 2,
    y: mb.y + mb.height / 2,
    name: '11-tap-mark',
    fire: () => page.goto(`${APP_URL}/call/${newCall.id}`, { waitUntil: 'networkidle' }),
  });

  // ── Frame 12: Call detail header (the new call) ──────────────────────
  await settle(page, 900);
  await shot(page, '12-detail-top');

  // ── Frame 13-15: smooth-ish scroll through the detail ────────────────
  await page.mouse.wheel(0, 320);
  await page.waitForTimeout(280);
  await shot(page, '13-detail-mid');

  await page.mouse.wheel(0, 320);
  await page.waitForTimeout(280);
  await shot(page, '14-detail-mid2');

  await page.mouse.wheel(0, 320);
  await page.waitForTimeout(700);
  await shot(page, '15-detail-bottom');

  await browser.close();
  await api.dispose();
}

// ─── GIF compose (ImageMagick) + optional gifsicle squeeze ──────────────

function composeGif() {
  // Synthesise any frames flagged with `synth` (currently only the white
  // fade frame) so the recorder doesn't have to capture them.
  for (const f of FRAMES) {
    if (f.synth !== 'white') continue;
    const path = join(FRAMES_DIR, `${f.name}.png`);
    execFileSync('magick', [
      '-size', `${FRAME_W}x${FRAME_H}`,
      'xc:white',
      path,
    ]);
  }

  const args = [];
  for (const { name, delay } of FRAMES) {
    const path = join(FRAMES_DIR, `${name}.png`);
    if (!existsSync(path)) {
      throw new Error(`missing frame: ${path}`);
    }
    args.push('-delay', String(delay), path);
  }
  args.push('-loop', '0', '-layers', 'OptimizePlus', OUT_GIF);

  console.log('composing GIF with magick…');
  execFileSync('magick', args, { stdio: 'inherit' });

  const beforeSqueeze = statSync(OUT_GIF).size;

  // Optional final squeeze. gifsicle -O3 + --lossy compresses LZW by 30-50%
  // at imperceptible quality loss for UI demos. If it's not installed, skip.
  const hasGifsicle = spawnSync('which', ['gifsicle']).status === 0;
  if (hasGifsicle) {
    console.log('squeezing with gifsicle…');
    // --colors 256 collapses magick's per-frame local palettes into a
    // single global one (kills the "too many colors" warning and unlocks
    // real LZW savings). --lossy=80 introduces controlled noise that
    // compresses better — invisible on UI demos, ~30-50% extra savings.
    execFileSync(
      'gifsicle',
      ['-O3', '--colors', '256', '--lossy=80', OUT_GIF, '-o', OUT_GIF],
      { stdio: 'inherit' },
    );
    const after = statSync(OUT_GIF).size;
    const saved = ((1 - after / beforeSqueeze) * 100).toFixed(0);
    console.log(
      `saved ${OUT_GIF}  (${(after / 1024).toFixed(0)} KB, -${saved}% vs magick-only)`,
    );
  } else {
    console.log(
      `saved ${OUT_GIF}  (${(beforeSqueeze / 1024).toFixed(0)} KB) — install gifsicle for an extra 30-50% squeeze`,
    );
  }
}

// ─── Main ────────────────────────────────────────────────────────────────

(async () => {
  try {
    await record();
    composeGif();
  } catch (err) {
    console.error('record-demo failed:', err);
    process.exit(1);
  }
})();
