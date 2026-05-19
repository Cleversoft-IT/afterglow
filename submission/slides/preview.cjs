// Render each .slide to a PNG for visual review.
// Output: afterglow/submission/slides/_preview/slide-NN.png
//
// Run: NODE_PATH=$(npm root -g) node afterglow/submission/slides/preview.cjs

const { chromium } = require('playwright');
const { resolve } = require('node:path');
const { pathToFileURL } = require('node:url');
const { mkdirSync, rmSync, existsSync } = require('node:fs');

const HERE = resolve(__dirname);
const HTML = resolve(HERE, 'deck.html');
const OUT_DIR = resolve(HERE, '_preview');

(async () => {
  if (existsSync(OUT_DIR)) rmSync(OUT_DIR, { recursive: true, force: true });
  mkdirSync(OUT_DIR, { recursive: true });

  const browser = await chromium.launch();
  const ctx = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    deviceScaleFactor: 1,
  });
  const page = await ctx.newPage();
  await page.goto(pathToFileURL(HTML).href, { waitUntil: 'networkidle' });
  await page.waitForTimeout(300);

  const slideCount = await page.locator('.slide').count();
  for (let i = 0; i < slideCount; i++) {
    const el = page.locator('.slide').nth(i);
    const num = String(i + 1).padStart(2, '0');
    const path = resolve(OUT_DIR, `slide-${num}.png`);
    await el.screenshot({ path });
    console.log(`  ${path}`);
  }

  await browser.close();
  console.log(`\n✓ ${slideCount} slides rendered to ${OUT_DIR}`);
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
