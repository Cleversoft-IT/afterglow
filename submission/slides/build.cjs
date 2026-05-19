// Build the submission slide deck PDF.
//
// Run from anywhere:
//   NODE_PATH=$(npm root -g) node afterglow/submission/slides/build.cjs
//
// Output: afterglow/submission/afterglow-slides.pdf
//
// Strategy: render afterglow/submission/slides/deck.html in headless Chromium
// at exactly 1920×1080 per slide, then print to PDF with page format matched
// to those dimensions (16:9). Each .slide in the HTML carries
// `page-break-after: always` so one .slide becomes one PDF page.

const { chromium } = require('playwright');
const { resolve } = require('node:path');
const { pathToFileURL } = require('node:url');
const { existsSync, statSync } = require('node:fs');

const HERE = resolve(__dirname);
const HTML = resolve(HERE, 'deck.html');
const OUT  = resolve(HERE, '..', 'afterglow-slides.pdf');

// 1920×1080 px at 96 dpi = 20in × 11.25in.
const PAGE_WIDTH_IN  = 1920 / 96;
const PAGE_HEIGHT_IN = 1080 / 96;

(async () => {
  if (!existsSync(HTML)) {
    console.error(`deck.html missing at ${HTML}`);
    process.exit(1);
  }

  const browser = await chromium.launch();
  const ctx = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    deviceScaleFactor: 2,
  });
  const page = await ctx.newPage();

  await page.goto(pathToFileURL(HTML).href, { waitUntil: 'networkidle' });
  // Give webfonts / layout a beat.
  await page.waitForTimeout(300);

  await page.pdf({
    path: OUT,
    width:  `${PAGE_WIDTH_IN}in`,
    height: `${PAGE_HEIGHT_IN}in`,
    printBackground: true,
    margin: { top: 0, right: 0, bottom: 0, left: 0 },
    preferCSSPageSize: false,
  });

  await browser.close();

  const sizeKb = (statSync(OUT).size / 1024).toFixed(0);
  console.log(`✓ wrote ${OUT}  (${sizeKb} KB)`);
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
