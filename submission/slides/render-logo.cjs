// Render the Afterglow wordmark as a standalone PNG for use as a logo
// asset in the slide deck and the README. Brand colors mirror styles.css
// (--brand-deep = #1d4ed8) to match the deck's title slide.
//
// Output: submission/screenshots/logo.png (and logo-dark.png on dark bg).
//
// Run: NODE_PATH=$(npm root -g) node submission/slides/render-logo.cjs

const { chromium } = require('playwright');
const { resolve } = require('node:path');
const { mkdirSync, existsSync } = require('node:fs');

const OUT_DIR = resolve(__dirname, '../screenshots');

const HTML = ({ bg, ink, accent }) => `
<!doctype html>
<html><head><meta charset="utf-8" /><style>
  html, body { margin: 0; padding: 0; background: ${bg}; }
  .wm {
    display: inline-block;
    padding: 48px 80px;
    font-family: "Inter", system-ui, -apple-system, "Segoe UI", sans-serif;
    font-weight: 800;
    font-size: 220px;
    letter-spacing: -0.02em;
    line-height: 1;
    color: ${ink};
  }
  .wm .accent { color: ${accent}; }
  .wm .dot {
    display: inline-block;
    width: 36px;
    height: 36px;
    border-radius: 50%;
    background: ${accent};
    margin-left: 16px;
    transform: translateY(-110px);
  }
</style></head>
<body>
  <span class="wm">after<span class="accent">glow</span><span class="dot"></span></span>
</body></html>`;

(async () => {
  if (!existsSync(OUT_DIR)) mkdirSync(OUT_DIR, { recursive: true });
  const browser = await chromium.launch();
  const ctx = await browser.newContext({
    viewport: { width: 1600, height: 360 },
    deviceScaleFactor: 2,
  });
  const page = await ctx.newPage();

  // Light variant — for README + slide 1 footer/header.
  await page.setContent(HTML({ bg: '#ffffff', ink: '#0F172A', accent: '#1d4ed8' }));
  const light = page.locator('.wm').first();
  await light.screenshot({ path: resolve(OUT_DIR, 'logo.png'), omitBackground: false });

  // Dark variant — for the dark-themed pitch slides.
  await page.setContent(HTML({ bg: '#0B0D12', ink: '#ECEEF2', accent: '#60a5fa' }));
  const dark = page.locator('.wm').first();
  await dark.screenshot({ path: resolve(OUT_DIR, 'logo-dark.png'), omitBackground: false });

  await browser.close();
  console.log(`✓ ${OUT_DIR}/logo.png + logo-dark.png`);
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
