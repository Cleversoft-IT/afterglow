# Afterglow — submission artifacts

Built deliverables for the AI Agent Olympics (Milan AI Week 2026) lablab.ai
submission form. All copy and structure are sourced from
[`afterglow/docs/SUBMISSION.md`](../docs/SUBMISSION.md) — that is the
single source of truth; this directory is the rendered output.

## Files

| File | Purpose | lablab field | Spec |
|---|---|---|---|
| `afterglow-slides.pdf` | 10-slide pitch deck (16:9, 1920×1080 per page) | **Slide Presentation** | PDF, ≤5 MB |
| `afterglow-cover.png` | Title-slide capture, used as the cover hero | **Cover Image** | PNG, 16:9, ≤500 KB |
| `slides/deck.html` + `slides/styles.css` | Source for the deck — Pixel-style Material aesthetic, brand seed `#3b82f6` mirrored from `app/lib/paperTheme.ts` | — | — |
| `slides/build.cjs` | Playwright PDF export | — | — |
| `slides/cover.cjs` | Playwright PNG export of slide 1 | — | — |
| `slides/preview.cjs` | Renders every slide as an individual PNG into `slides/_preview/` for visual review | — | — |

The video pitch MP4 is NOT versioned here — recorded on demand from the
script in [`SUBMISSION.md §4`](../docs/SUBMISSION.md#4-video-pitch-script--5-minutes-scene-by-scene).

## Rebuilding

Requires `playwright` installed globally (`sudo npm install -g playwright`
+ `playwright install chromium`) — same toolchain as
[`afterglow/scripts/record-demo.cjs`](../scripts/record-demo.cjs).

```bash
# from repo root
NODE_PATH=$(npm root -g) node afterglow/submission/slides/build.cjs    # → afterglow-slides.pdf
NODE_PATH=$(npm root -g) node afterglow/submission/slides/cover.cjs    # → afterglow-cover.png
NODE_PATH=$(npm root -g) node afterglow/submission/slides/preview.cjs  # → slides/_preview/slide-NN.png
```

Current build sizes: PDF ~1.9 MB · cover ~320 KB (both well under lablab caps).

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

* **Video pitch MP4** — record per [§4 script](../docs/SUBMISSION.md#4-video-pitch-script--5-minutes-scene-by-scene).
  Spec filename: `afterglow-pitch.mp4`. Direct upload to lablab (not YouTube/Drive).
* **Deep-research market report** (`tmp/deep-research-report (2).md`) —
  source for the TAM/SAM figures on slide 7. Quoted but not bundled.
