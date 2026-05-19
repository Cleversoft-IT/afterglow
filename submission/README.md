# Afterglow — submission artifacts

Built deliverables for the AI Agent Olympics (Milan AI Week 2026) lablab.ai
submission form. All copy and structure are sourced from
[`docs/SUBMISSION.md`](../docs/SUBMISSION.md) — that is the
single source of truth; this directory is the rendered output.

## Files

| File | Purpose | lablab field | Spec |
|---|---|---|---|
| `afterglow-pitch.mp4` | 3:32 video pitch (live product demo + Coda — no opening cinematic) | **Video Presentation** | MP4, ≤5:00, ≤300 MB |
| `afterglow-slides.pdf` | 10-slide pitch deck (16:9, 1920×1080 per page) | **Slide Presentation** | PDF, ≤5 MB |
| `afterglow-cover.png` | Title-slide capture, used as the cover hero | **Cover Image** | PNG, 16:9, ≤500 KB |
| `slides/deck.html` + `slides/styles.css` | Source for the deck — Pixel-style Material aesthetic, brand seed `#3b82f6` mirrored from `app/lib/paperTheme.ts` | — | — |
| `slides/build.cjs` | Playwright PDF export | — | — |
| `slides/cover.cjs` | Playwright PNG export of slide 1 | — | — |
| `slides/preview.cjs` | Renders every slide as an individual PNG into `slides/_preview/` for visual review | — | — |

The MP4 is rendered from the Remotion project under
[`docs/video/`](../docs/video/) — see "Rebuilding the video" below.

## Rebuilding

Requires `playwright` installed globally (`sudo npm install -g playwright`
+ `playwright install chromium`).

```bash
# from repo root
NODE_PATH=$(npm root -g) node submission/slides/build.cjs    # → afterglow-slides.pdf
NODE_PATH=$(npm root -g) node submission/slides/cover.cjs    # → afterglow-cover.png
NODE_PATH=$(npm root -g) node submission/slides/preview.cjs  # → slides/_preview/slide-NN.png
```

Current build sizes: PDF ~1.4 MB · cover ~290 KB · video ~15 MB (3:32)
— all well under the respective lablab caps (5 MB · 500 KB · 300 MB).

## Rebuilding the video

The pitch MP4 is rendered from a Remotion project at
[`docs/video/`](../docs/video/). One-shot regen from scratch:

```bash
cd docs/video

# 1. install deps (once)
npm install
python3 -m venv .venv && .venv/bin/pip install edge-tts

# 2. capture fresh app screenshots (against the live app)
node scripts/capture-screenshots.mjs

# 3. regenerate voice-over (edits in scripts/generate-voiceover.py)
.venv/bin/python -X utf8 scripts/generate-voiceover.py

# 4. render the MP4
npm run video:render        # → out/afterglow-final.mp4

# 5. promote to submission/
cp out/afterglow-final.mp4 ../../submission/afterglow-pitch.mp4
```

Source of truth for narration + timings: [`docs/SUBMISSION.md §4`](../docs/SUBMISSION.md#4-video-pitch-script--5-minutes-scene-by-scene).
Composition wiring + scene structure: [`docs/video/src/Composition.tsx`](../docs/video/src/Composition.tsx)
and [`docs/video/src/remotion/data/videoScript.ts`](../docs/video/src/remotion/data/videoScript.ts).

## Slide map

| # | Title | Source in SUBMISSION.md |
|---|---|---|
| 1 | Title — wordmark + tagline + partner pills + URL | §1 + §5 |
| 2 | The problem — 60s + AI-receptionist counter | §2 + §5 |
| 3 | The product — Extract · Execute · Remember | §2 + §5 |
| 4 | How it works — pipeline diagram with agent loop | §7 + §5 |
| 5 | Why it's agentic — 4 differentiators | §9 + §5 |
| 6 | Partner integration depth — Vultr · Google · Speechmatics | §8 + §5 |
| 7 | Business value — TAM/SAM + USP table | §3 long description + §5 |
| 8 | Real-vs-mocked — the honest table | §11 (added vs §5 outline) |
| 9 | Live demo + click path | §6 + §5 |
| 10 | Future work + close | §14 + §5 |

Slide 8 ("Real-vs-mocked") was added to the §5 outline because it earns
trust the moment a judge wonders "is this thing real?" — leading with the
honest table is faster than waiting for the question.

## Editing the deck

Slides live in [`slides/deck.html`](slides/deck.html) — one `<section
class="slide">…</section>` per page. Each slide is 1920×1080 with
`page-break-after: always`, so adding a section adds a PDF page.

Color and typography variables are at the top of
[`slides/styles.css`](slides/styles.css) (`--brand`, `--ink`, etc.); they
mirror the operator-app Paper theme (`app/lib/paperTheme.ts`) so the deck
reads as the same product.

After any edit:
1. Rebuild PNG previews and inspect them.
2. Rebuild the PDF.
3. (Optional) re-export the cover if slide 1 changed.

## What is NOT in this directory

* **Deep-research market report** (`tmp/deep-research-report (2).md`) —
  source for the TAM/SAM figures on slide 7. Quoted but not bundled.
