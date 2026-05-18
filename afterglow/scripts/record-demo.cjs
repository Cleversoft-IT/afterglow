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
// Output: afterglow/demo-site/public/afterglow-demo.gif
//
// Re-run after frontend changes:
//   NODE_PATH=$(npm root -g) node afterglow/scripts/record-demo.cjs
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

const APP_URL = process.env.APP_URL || 'https://app.95-179-245-107.sslip.io';
const API_URL = process.env.API_URL || 'https://api.95-179-245-107.sslip.io';

// 390 × 845 = same aspect ratio as the .phone-frame in the demo-site hero.
// DPR=1 → no upscale needed, the captured pixels drop straight into a 390-wide frame.
const VIEWPORT = { width: 390, height: 845 };

// Centre of the blue (AI) FAB on the incoming-call screen. RN Paper renders
// the 3 FABs (Decline / AI / Accept) as 64-px circles centred horizontally
// on the bottom of the viewport.
const AI_FAB = { x: VIEWPORT.width / 2, y: 770 };

const FRAMES_DIR = '/tmp/afterglow-demo-frames';
const OUT_DIR = resolve(__dirname, '../demo-site/public');
const OUT_GIF = join(OUT_DIR, 'afterglow-demo.gif');

const DEMO_SESSION_KEY = 'afterglow.demo_session_id';
const LOCALE_KEY = 'afterglow.locale';
const DEMO_SESSION_HEADER = 'X-Demo-Session';

// Per-frame display time in centiseconds (1/100s).
// Long on "read" frames, short on motion micro-steps. Spend bytes where
// the eye lands. See SKILL.md → "Per-frame timing strategy".
const FRAMES = [
  { name: '01-home',          delay: 350 }, // 3.5s — read the call list
  { name: '02-bookings',      delay: 280 }, // 2.8s — filtered subset
  { name: '03-incoming',      delay: 380 }, // 3.8s — caller + briefing (key)
  { name: '04-cursor-blue',   delay: 50  }, // 0.5s — cursor glides onto blue FAB
  { name: '05-blue-ripple',   delay: 100 }, // 1.0s — tap ripple mid-bloom
  { name: '06-answering',     delay: 200 }, // 2.0s — "Afterglow listening" badge
  { name: '07-calls',         delay: 280 }, // 2.8s — back to call list
  { name: '08-detail-top',    delay: 250 }, // 2.5s — call detail header
  { name: '09-detail-mid',    delay: 30  }, // 0.3s — scroll motion
  { name: '10-detail-mid2',   delay: 30  }, // 0.3s — scroll motion
  { name: '11-detail-bottom', delay: 450 }, // 4.5s — final read (key)
];
// Total ≈ 22.7s loop.

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

// ─── Helpers ─────────────────────────────────────────────────────────────

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
  return page.screenshot({ path: join(FRAMES_DIR, `${name}.png`) });
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

  // ── Frame 02: Bookings tab ────────────────────────────────────────────
  await page.getByText('Bookings', { exact: true }).first().click();
  await settle(page, 700);
  await shot(page, '02-bookings');

  // ── Frame 03: Incoming call (Mark Ross + briefing) ────────────────────
  await page.goto(`${APP_URL}/incoming-call?caller=existing`, {
    waitUntil: 'networkidle',
  });
  await settle(page, 1500);
  await shot(page, '03-incoming');

  // ── Frame 04: cursor lands on the blue (AI) FAB ───────────────────────
  // Show the cursor, then snap. The CSS transition on #demo-cursor makes
  // this read as a glide when sequenced with frame 03 (which had no cursor).
  await showCursor(page, AI_FAB.x, AI_FAB.y);
  await page.waitForTimeout(250);   // let the cursor glide animation finish
  await shot(page, '04-cursor-blue');

  // ── Frame 05: tap ripple mid-bloom on the blue FAB ────────────────────
  await fireTap(page, AI_FAB.x, AI_FAB.y);
  await page.waitForTimeout(180);   // catch the ripple mid-bloom (~25% into 700ms)
  await shot(page, '05-blue-ripple');

  // Fire the real click that drives the state change, then hide the cursor
  // so the next frame is a clean "On call" screen.
  await hideCursor(page);
  await page.mouse.click(AI_FAB.x, AI_FAB.y);

  // ── Frame 06: "Afterglow listening" — call in progress ────────────────
  await page.waitForTimeout(1300);  // ringing → in-call transition
  await shot(page, '06-answering');

  // ── Frame 07: back to Calls list ──────────────────────────────────────
  // Skip the live-call timer screen entirely — narratively the user has
  // answered, Afterglow is recording, and now we review the call list.
  // The seeded Mark Ross row reads as "the call we just handled".
  await page.goto(`${APP_URL}/`, { waitUntil: 'networkidle' });
  await settle(page, 1200);
  await shot(page, '07-calls');

  // ── Frame 08: Call detail header ──────────────────────────────────────
  await page.getByText('Mark Ross').first().click();
  await page.waitForLoadState('networkidle');
  await settle(page, 900);
  await shot(page, '08-detail-top');

  // ── Frame 09-11: smooth-ish scroll through the detail ─────────────────
  await page.mouse.wheel(0, 320);
  await page.waitForTimeout(280);
  await shot(page, '09-detail-mid');

  await page.mouse.wheel(0, 320);
  await page.waitForTimeout(280);
  await shot(page, '10-detail-mid2');

  await page.mouse.wheel(0, 320);
  await page.waitForTimeout(700);
  await shot(page, '11-detail-bottom');

  await browser.close();
}

// ─── GIF compose (ImageMagick) + optional gifsicle squeeze ──────────────

function composeGif() {
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
