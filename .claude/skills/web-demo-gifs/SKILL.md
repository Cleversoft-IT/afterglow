---
name: web-demo-gifs
description: Use when producing an animated GIF (or smaller WebP/MP4 fallback) to demo a web app or PWA — README hero, landing page, marketing carousel, Slack/Linear/Discord share. Covers scripted Playwright recording, fake-cursor / tap-ripple injection, smooth scrolling, the two-pass palette pipeline (ffmpeg / gifski / ImageMagick / gifsicle), per-frame variable timing for narrative pacing, and format choice between GIF / WebP / MP4 with size budgets.
---

# Web Demo GIFs

## Overview

A good product GIF is **a directed film, not a screen recording.** Every frame is chosen, every pause is timed, no jitter, no cursor wander, no mid-transition smear. The default mistake is to start OBS and re-encode the video — that path is faster but loses 10x in quality and 3x in file size.

**Core principle:** for UI demos, **drive the app headlessly with Playwright, take one PNG per story beat, stitch with per-frame delays.** The browser is your camera; you control every frame.

Reserve video-capture → GIF only for things you can't script (real device, native app, hand-drawn input).

## Decision: which pipeline?

```
Is the target a web app you can drive with a URL + selectors?
├── YES  → Scripted screenshots (Playwright → magick / gifski).         [Approach A]
│         Deterministic, no jitter, smallest file at given quality.
└── NO   → Screen-record video, two-pass palette to GIF.                [Approach B]
          OBS / wf-recorder → ffmpeg palettegen+paletteuse → gifsicle.
```

Then choose **format** based on where it ships:

| Channel | Best format | Why |
|---|---|---|
| GitHub README, Slack, Linear, Discord, email | **GIF** | Renders inline everywhere, no JS required. Pay the size tax. |
| Landing page hero, docs site, marketing | **WebP animated** or **`<video autoplay loop muted playsinline>`** | 3–10x smaller, sharper, supports alpha. Falls back to a still `<img>` for OG/social cards. |
| GitHub issue/PR comment | **MP4 upload** (drag-drop) | GitHub re-hosts it, renders a player. 10MB limit on free, 100MB paid. **Cannot** be embedded from a relative repo path in README. |
| Twitter/X | **MP4** | GIFs over 5MB get auto-converted to MP4 anyway. |

**Rule of thumb:** export the source as a PNG sequence + MP4 + GIF + animated WebP from the same recording. Different surfaces want different files.

## Approach A — Scripted Playwright recording (recommended)

The shape, adapted from `scripts/record-demo.cjs`:

```js
const { chromium } = require('playwright');
const { execFileSync } = require('node:child_process');
const { join } = require('node:path');

const VIEWPORT = { width: 390, height: 845 };   // iPhone-ish aspect
const FRAMES_DIR = '/tmp/demo-frames';

// Centiseconds (1/100s). Long on "read" frames, short on motion micro-steps.
const FRAMES = [
  { name: '01-home',         delay: 350 },  // 3.5s — let the eye land
  { name: '02-tap',          delay: 80  },  // 0.8s — flash of the press
  { name: '03-transition-a', delay: 25  },  // 0.25s — motion
  { name: '04-transition-b', delay: 25  },  // 0.25s — motion
  { name: '05-detail',       delay: 400 },  // 4.0s — key read, the payoff
];

(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({
    viewport: VIEWPORT,
    deviceScaleFactor: 1,        // DPR=1 → no retina doubling, half the bytes
    isMobile: true, hasTouch: true,
    locale: 'en-US',
  });
  // Skip cold-start / onboarding by seeding state.
  await ctx.addInitScript(() => localStorage.setItem('demo.session', 'primed'));

  const page = await ctx.newPage();
  await page.goto('http://localhost:3000', { waitUntil: 'networkidle' });
  await page.evaluate(() => document.fonts.ready);   // wait for webfonts
  await page.waitForTimeout(400);                     // settle paint
  await page.screenshot({ path: join(FRAMES_DIR, '01-home.png') });

  // ... per-beat clicks/scrolls + screenshots ...

  await browser.close();

  // Stitch with variable per-frame delays (ImageMagick).
  const args = [];
  for (const { name, delay } of FRAMES) {
    args.push('-delay', String(delay), join(FRAMES_DIR, `${name}.png`));
  }
  args.push('-loop', '0', '-layers', 'OptimizePlus', 'demo.gif');
  execFileSync('magick', args, { stdio: 'inherit' });
})();
```

Why this beats video-capture-then-convert:
- **No jitter.** Each PNG is pixel-perfect; the GIF is exactly what the app rendered.
- **No compression blur.** No intermediate H.264 chroma subsampling.
- **Variable delays.** Long pauses on key frames, fast micro-frames on motion → narrative pacing, smaller file.
- **Deterministic.** Re-runs produce identical bytes (modulo timestamps).
- **Retina-clean.** `deviceScaleFactor: 1` keeps width at design size; no `scale=` downscale needed.

### Per-frame timing strategy

Constant FPS wastes bytes. Spend them where the eye lands:

| Beat type | Delay (cs) | Note |
|---|---|---|
| Hero/establishing frame | 300–400 | Reader's brain orients |
| Key read (the payoff) | 350–450 | The screenshot you'd put in the deck |
| Tap/press feedback | 60–120 | A flash, not a pose |
| Transition / scroll mid-step | 20–40 | Motion, deliberately blurred by short hold |
| End-of-loop hold | 500–700 | Pause before the loop restarts so it doesn't feel anxious |

Aim for a 15–25s total loop. Anything longer and viewers leave before the loop reveals.

### Fake cursor + tap ripples

Headless browsers don't render a system cursor and Paper-style ripples often fire only on real pointer events. Inject your own via `addInitScript`:

```js
await ctx.addInitScript(() => {
  // 1. CSS for cursor + ripple
  const style = document.createElement('style');
  style.textContent = `
    #demo-cursor {
      position: fixed; top: 0; left: 0; width: 22px; height: 22px;
      border-radius: 50%; background: rgba(0,0,0,0.55);
      box-shadow: 0 0 0 2px rgba(255,255,255,0.9);
      transform: translate(-50%, -50%); pointer-events: none;
      z-index: 2147483647; transition: transform 180ms cubic-bezier(.2,.7,.2,1);
    }
    .demo-ripple {
      position: fixed; width: 12px; height: 12px; border-radius: 50%;
      background: rgba(0,120,255,0.5); pointer-events: none;
      transform: translate(-50%, -50%); z-index: 2147483646;
      animation: demo-ripple 600ms ease-out forwards;
    }
    @keyframes demo-ripple {
      0%   { width: 12px;  height: 12px;  opacity: 0.6; }
      100% { width: 120px; height: 120px; opacity: 0;   }
    }
  `;
  document.documentElement.appendChild(style);

  const cursor = document.createElement('div');
  cursor.id = 'demo-cursor';
  document.documentElement.appendChild(cursor);

  // 2. Expose move + tap to the test runner
  window.__demoMove = (x, y) => {
    cursor.style.transform = `translate(${x}px, ${y}px) translate(-50%, -50%)`;
  };
  window.__demoTap = (x, y) => {
    const r = document.createElement('div');
    r.className = 'demo-ripple';
    r.style.left = x + 'px'; r.style.top = y + 'px';
    document.documentElement.appendChild(r);
    setTimeout(() => r.remove(), 700);
  };
});
```

Then in the recording flow, **move the cursor first, screenshot the move, fire the tap, screenshot the ripple, then the real click**:

```js
async function tapAt(page, selector) {
  const el = page.locator(selector);
  const box = await el.boundingBox();
  const x = box.x + box.width / 2, y = box.y + box.height / 2;

  await page.evaluate(([x, y]) => window.__demoMove(x, y), [x, y]);
  await page.waitForTimeout(160);     // let the cursor glide
  await page.screenshot({ path: 'frame-cursor.png' });

  await page.evaluate(([x, y]) => window.__demoTap(x, y), [x, y]);
  await page.waitForTimeout(120);     // catch the ripple mid-bloom
  await page.screenshot({ path: 'frame-ripple.png' });

  await el.click();                    // real click that drives navigation
}
```

### Smooth scrolling

A single `page.mouse.wheel(0, 800)` jumps. Break it into 2–3 increments with 200–300ms between and screenshot each — the GIF replays as a glide:

```js
for (const dy of [320, 320, 320]) {
  await page.mouse.wheel(0, dy);
  await page.waitForTimeout(280);
  await page.screenshot({ path: `scroll-${dy}.png` });
}
```

### Disabling app animations when you need crisp frames

If the app's own animations smear your captures, kill them via init script:

```js
await ctx.addInitScript(() => {
  const s = document.createElement('style');
  s.textContent = `*, *::before, *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }`;
  document.documentElement.appendChild(s);
});
```

This trades realism for crispness — use it when your story is about *what's on screen*, not *how it animates in*. Keep it off when the animation IS the story.

## Approach B — Video capture → GIF (fallback)

Use only when scripted screenshots aren't possible (real device mirroring, native app, hand-drawn input).

Record at 30fps then halve in conversion:

```bash
# 1. Trim and crop (frame-accurate; put -ss after -i for accuracy)
ffmpeg -i raw.mp4 -ss 00:00:02 -to 00:00:18 \
  -vf "crop=720:1560:0:0,scale=390:-1:flags=lanczos" trimmed.mp4

# 2. Generate a custom palette (huge quality win over default 256-color)
ffmpeg -i trimmed.mp4 -vf \
  "fps=15,scale=390:-1:flags=lanczos,palettegen=max_colors=128:stats_mode=diff" \
  palette.png

# 3. Apply palette with dithering
ffmpeg -i trimmed.mp4 -i palette.png -lavfi \
  "fps=15,scale=390:-1:flags=lanczos[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle" \
  out.gif
```

`stats_mode=diff` focuses palette on changing regions (UI demos have lots of static area). `diff_mode=rectangle` re-encodes only the changing rectangle per frame — significant size drop. `bayer:bayer_scale=5` compresses better than `sierra2_4a` on flat UI regions; switch to `sierra2_4a` if you see banding on gradients.

## Highest quality from a PNG sequence — `gifski`

For brand/landing-page work where quality matters more than the build pipeline:

```bash
gifski -o out.gif --fps 20 --quality 90 --width 390 frames/*.png
```

gifski uses pngquant's cross-frame palette and temporal dithering, breaking the 256-color-per-image GIF limit by varying palette per frame. The output is visibly cleaner than ffmpeg's palettegen on gradients and photographic content. Trade-off: no per-frame variable delay flag — pre-duplicate frames or stitch in two passes if you need long holds.

## Final squeeze with gifsicle

Always optimize the finished GIF:

```bash
gifsicle -O3 --lossy=80 out.gif -o final.gif
```

`-O3` is lossless layer-level optimization. `--lossy=80` (range 20–200) introduces controlled noise that makes LZW compress better — typical extra savings 30–50% at imperceptible quality loss. Push to `--lossy=120` for aggressive size cuts; visible banding starts around 160.

## File-size reduction sequence

Try in this order — each step is cheap and reversible:

1. **Trim the loop.** Cut every frame that isn't part of the story. A 12s loop beats a 22s loop every time.
2. **Drop the width.** 390 → 360 → 320. Linear file-size relationship.
3. **Drop FPS.** 20 → 15 → 12. UI demos look fine at 12fps; only motion-heavy content needs 20+.
4. **Drop palette colors.** `max_colors=128 → 96 → 64`. Watch for banding on gradients.
5. **gifsicle `--lossy=80 → 120`.**
6. **Switch format.** If you've squeezed past your budget, the answer is WebP or MP4.

Targets I aim for:
- README: ≤500 KB
- Landing hero (with `<img>` fallback): ≤800 KB
- Slack/Linear share: ≤1 MB
- Animated WebP equivalent: 30–40% of the GIF size

## Common pitfalls

| Pitfall | Fix |
|---|---|
| First and last frame don't match → loop "jumps" | End on the same screen as the start, or add a 500ms hold on the closing frame to soften the seam. |
| Mid-transition smear in screenshot | `await page.waitForSelector(...)` on the post-transition element, or kill animations via init script. |
| Webfonts not loaded → first-frame fallback font | `await page.evaluate(() => document.fonts.ready)` after `goto`. |
| Retina doubling → 4x file size | Set `deviceScaleFactor: 1` in the browser context. |
| Onboarding screen wastes 5s of the loop | Pre-seed `localStorage` / call the priming API before the recording starts. |
| Gradient banding | Switch dither: `bayer_scale=3` (more noise, less banding) or `sierra2_4a`. Or raise `max_colors` to 192. |
| File size still huge after palette | You're at retina. Check captured PNG dimensions before stitching. |
| `magick: command not found` | ImageMagick 7 binary is `magick`; v6 is `convert`. Install IMv7. |
| Ripple animation captured before it blooms | Add 80–150ms `waitForTimeout` between `__demoTap` and `screenshot`. |
| Mouse cursor visible in real OS recordings | Hide system cursor (`unclutter -idle 0.01`) or use Approach A. |

## Quick reference — commands

```bash
# Variable per-frame delay (ImageMagick — best for hand-paced demos)
magick -delay 350 01.png -delay 80 02.png -delay 25 03.png \
       -loop 0 -layers OptimizePlus demo.gif

# Constant FPS, two-pass palette (ffmpeg — best from video)
ffmpeg -i in.mp4 -vf "fps=15,scale=390:-1,palettegen=max_colors=128" palette.png
ffmpeg -i in.mp4 -i palette.png -lavfi \
  "fps=15,scale=390:-1[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=5" out.gif

# Highest quality from PNG sequence (gifski)
gifski -o out.gif --fps 20 --quality 90 --width 390 frames/*.png

# Final squeeze (gifsicle)
gifsicle -O3 --lossy=80 in.gif -o out.gif

# WebP animated alternative (cwebp from libwebp)
img2webp -loop 0 -d 67 -lossy -q 75 frames/*.png -o demo.webp

# MP4 alternative (h264, web-friendly)
ffmpeg -framerate 15 -pattern_type glob -i 'frames/*.png' \
  -c:v libx264 -pix_fmt yuv420p -movflags +faststart -crf 23 demo.mp4
```

## Reference implementation in this repo

[`scripts/record-demo.cjs`](../../scripts/record-demo.cjs) — drives the live app at 390×845 with Playwright, takes 9 PNGs with hand-tuned centisecond delays, stitches with `magick`. Output: 180 KB for a 21.7s loop with no jitter and no compression blur. Read it before writing a new recorder for a different screen.

## Hidden gems

- **`stats_mode=diff` + `diff_mode=rectangle`** in the ffmpeg palette pipeline drops UI-demo file size 20–40% by skipping unchanged regions. Almost no one uses these flags.
- **Two GIFs are sometimes smaller than one**: split a long loop into two GIFs in an HTML `<picture>` if a hero needs both phone and desktop demos — each is independently quantized.
- **GitHub renders animated WebP** in README via `<img src="demo.webp">` (Markdown image syntax also works). Browsers without animated-WebP support show the first frame as a still — graceful fallback for OG cards.
- **Apple devices auto-pause GIFs over ~5 MB** in some iOS WebKit contexts. Stay under it.
- **`puppeteer-screen-recorder` and `playwright-video`** exist but produce H.264 → you re-encode to GIF anyway. Skip them; PNG sequence is fewer moving parts.
- **`vhs` (charm.sh)** is the gold standard for terminal GIFs and the same idea applies to browsers: declarative script → deterministic output. If a teammate is building a CLI demo, point them there.
- **Add a 1-pixel border** with `magick -bordercolor "#000" -border 1` before final optimization — kills the imperceptible edge-bleeding LZW penalty on some viewers and forces a clean crop on dark-mode contexts.
