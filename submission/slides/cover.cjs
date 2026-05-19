// Build the 16:9 cover image for the lablab submission form.
//
// Strategy: render only the title slide of deck.html at exactly 1920×1080
// (16:9), then drop it as PNG. Re-compress in a second pass with sharp if
// the raw PNG would exceed the 500 KB lablab budget.
//
// Run: NODE_PATH=$(npm root -g) node submission/slides/cover.cjs
// Output: submission/afterglow-cover.png

const { chromium } = require('playwright');
const { resolve } = require('node:path');
const { pathToFileURL } = require('node:url');
const { statSync } = require('node:fs');

const HERE = resolve(__dirname);
const HTML = resolve(HERE, 'deck.html');
const OUT  = resolve(HERE, '..', 'afterglow-cover.png');
const LIMIT_KB = 500;

(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    deviceScaleFactor: 1,
  });
  const page = await ctx.newPage();
  await page.goto(pathToFileURL(HTML).href, { waitUntil: 'networkidle' });
  await page.waitForTimeout(300);

  await page.locator('.slide').first().screenshot({
    path: OUT,
    type: 'png',
  });

  await browser.close();

  const sizeKb = statSync(OUT).size / 1024;
  const flag = sizeKb <= LIMIT_KB ? '✓' : '⚠';
  console.log(`${flag} wrote ${OUT}  (${sizeKb.toFixed(0)} KB, limit ${LIMIT_KB})`);
  if (sizeKb > LIMIT_KB) {
    console.log(`  hint: install sharp / pngquant and re-encode if needed`);
  }
})().catch((err) => { console.error(err); process.exit(1); });
