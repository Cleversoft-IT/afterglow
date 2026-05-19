// Render the demo-site favicon + mobile icon set from a single SVG source.
//
// Source:   demo-site/public/icon-source.svg
// Output:   demo-site/public/{favicon-16.png, favicon-32.png,
//                             apple-touch-icon.png (180),
//                             icon-192.png, icon-512.png,
//                             favicon.ico (32x32 PNG-in-ICO)}
//
// We render the SVG via headless Chromium so font fallback + gradient
// rasterise identically to what a browser would do at runtime — no
// surprises when the icon shows up in tabs or on a home-screen install.

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..', '..');
const SVG_PATH = path.join(ROOT, 'demo-site', 'public', 'icon-source.svg');
const OUT_DIR = path.join(ROOT, 'demo-site', 'public');

const targets = [
  { size: 16,  out: 'favicon-16.png' },
  { size: 32,  out: 'favicon-32.png' },
  { size: 180, out: 'apple-touch-icon.png' },
  { size: 192, out: 'icon-192.png' },
  { size: 512, out: 'icon-512.png' },
];

async function renderOne(page, svg, size, outPath) {
  const html = `<!doctype html><meta charset="utf-8"><style>
    html,body{margin:0;padding:0;background:transparent}
    .stage{width:${size}px;height:${size}px}
    .stage svg{width:100%;height:100%;display:block}
  </style><div class="stage">${svg}</div>`;
  await page.setViewportSize({ width: size, height: size });
  await page.setContent(html, { waitUntil: 'load' });
  const handle = await page.$('.stage');
  await handle.screenshot({ path: outPath, omitBackground: true });
  console.log(`✓ ${path.relative(ROOT, outPath)} (${size}×${size})`);
}

(async () => {
  const svg = fs.readFileSync(SVG_PATH, 'utf8');
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ deviceScaleFactor: 1 });
  const page = await ctx.newPage();
  for (const t of targets) {
    await renderOne(page, svg, t.size, path.join(OUT_DIR, t.out));
  }
  await browser.close();

  // ICO file: minimum-viable single-image ICO containing the 32×32 PNG.
  // Browsers (Chrome, Firefox, Safari) all accept PNG-encoded ICO frames,
  // so we wrap favicon-32.png in an ICONDIR + ICONDIRENTRY header instead
  // of going to native BMP encoding.
  const png32 = fs.readFileSync(path.join(OUT_DIR, 'favicon-32.png'));
  const ico = Buffer.alloc(6 + 16 + png32.length);
  // ICONDIR
  ico.writeUInt16LE(0, 0);      // reserved
  ico.writeUInt16LE(1, 2);      // type: 1 = ICO
  ico.writeUInt16LE(1, 4);      // image count
  // ICONDIRENTRY (1 entry)
  ico.writeUInt8(32, 6);        // width (0 = 256)
  ico.writeUInt8(32, 7);        // height
  ico.writeUInt8(0, 8);         // colour palette (0 = none)
  ico.writeUInt8(0, 9);         // reserved
  ico.writeUInt16LE(1, 10);     // colour planes
  ico.writeUInt16LE(32, 12);    // bits per pixel
  ico.writeUInt32LE(png32.length, 14); // image data size
  ico.writeUInt32LE(22, 18);    // image data offset (6 + 16)
  png32.copy(ico, 22);
  fs.writeFileSync(path.join(OUT_DIR, 'favicon.ico'), ico);
  console.log(`✓ ${path.relative(ROOT, path.join(OUT_DIR, 'favicon.ico'))} (32×32 PNG)`);
})();
