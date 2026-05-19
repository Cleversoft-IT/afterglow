// Capture live screenshots of the operator app for the slide deck.
// Output: submission/screenshots/<name>.png
//
// Pre-reqs: an active *seed* template (so the incoming-call mode works for an
// existing caller). The script flips the visitor session to dark/light via
// localStorage so we can shoot both modes without manual UI clicks.
//
// Run: NODE_PATH=$(npm root -g) node submission/slides/capture-app-screenshots.cjs

const { chromium } = require('playwright');
const { resolve } = require('node:path');
const { mkdirSync, existsSync } = require('node:fs');

const APP_URL = process.env.APP_URL || 'https://app.afterglow.cleversoft.it';
const OUT_DIR = resolve(__dirname, '../screenshots');

const VIEWPORT = { width: 410, height: 835 }; // phone-frame logical size
const THEME_KEY = 'afterglow.theme_mode';

async function setTheme(page, mode) {
  await page.evaluate(
    ({ key, mode }) => {
      try { localStorage.setItem(key, mode); } catch {}
    },
    { key: THEME_KEY, mode },
  );
}

async function dismissDialogs(page) {
  // Welcome on a fresh sandbox session, plus "Template activated" after we
  // tap an Activate button. Both are Paper Dialogs with text buttons — we
  // scan visible buttons by accessible name and click the right one if
  // present. Done in JS to avoid react-native-web role flakiness.
  await page.evaluate(() => {
    const wanted = ['pick a preset', 'stay on templates'];
    const buttons = Array.from(document.querySelectorAll('[role="button"], button'));
    for (const b of buttons) {
      const t = (b.textContent || '').trim().toLowerCase();
      if (wanted.includes(t)) (b).click();
    }
  });
}

async function activatePreset(page, presetName) {
  await page.goto(`${APP_URL}/templates`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(1200);
  await dismissDialogs(page);
  await page.waitForTimeout(500);
  // Find the "Standard booking" row and the sibling Activate button. We
  // can't trust getByRole on RN-web, so we scan the DOM directly.
  const activated = await page.evaluate((name) => {
    const all = Array.from(document.querySelectorAll('*'));
    const titleEl = all.find((el) => el.textContent?.trim() === name);
    if (!titleEl) return 'no-title';
    // Walk up to the surface card, then look for an "Activate" or "Active"
    // descendant.
    let card = titleEl;
    for (let i = 0; i < 8 && card.parentElement; i++) {
      card = card.parentElement;
      const buttons = Array.from(card.querySelectorAll('[role="button"], button'));
      const active = buttons.find((b) => (b.textContent || '').trim() === 'Active');
      if (active) return 'already-active';
      const activate = buttons.find((b) => (b.textContent || '').trim() === 'Activate');
      if (activate) {
        (activate).click();
        return 'clicked';
      }
    }
    return 'no-button';
  }, presetName);
  console.log(`  activate(${presetName}): ${activated}`);
  await page.waitForTimeout(1200);
  await dismissDialogs(page);
  await page.waitForTimeout(500);
}

async function shotAt(page, url, name) {
  await page.goto(url, { waitUntil: 'networkidle' });
  await page.waitForTimeout(1500);
  await dismissDialogs(page);
  await page.waitForTimeout(400);
  const out = resolve(OUT_DIR, `${name}.png`);
  await page.screenshot({ path: out, clip: { x: 0, y: 0, ...VIEWPORT } });
  console.log(`  ${out}`);
}

(async () => {
  if (!existsSync(OUT_DIR)) mkdirSync(OUT_DIR, { recursive: true });

  const browser = await chromium.launch();
  const ctx = await browser.newContext({
    viewport: VIEWPORT,
    deviceScaleFactor: 2,
  });
  const page = await ctx.newPage();

  // First nav so localStorage gets a real origin (and so the demo session
  // gets minted — every reload after this reuses the same X-Demo-Session
  // header, which is what keeps the activated template alive across navs).
  await page.goto(APP_URL, { waitUntil: 'networkidle' });
  await setTheme(page, 'dark');
  await activatePreset(page, 'Standard booking');

  // Dark shots — Templates page (showing the AI sparkle button + the
  // "Active" Standard booking row) + the incoming-call screen.
  await shotAt(page, `${APP_URL}/templates`, 'templates-dark');
  await shotAt(page, `${APP_URL}/incoming-call?caller=existing`, 'incoming-dark');

  // Light shots — Home + Simulator. Switch the theme in place (no reload,
  // so we keep the session) by writing localStorage and toggling the
  // <html> data attribute the theme provider listens to.
  await setTheme(page, 'light');
  // Force a soft refresh of the next page so the ThemeContext re-reads
  // localStorage. We do this by navigating away then back.
  await page.goto(`${APP_URL}/templates`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(500);
  await shotAt(page, `${APP_URL}/`, 'home-light');
  await shotAt(page, `${APP_URL}/simulator`, 'simulator-light');

  await browser.close();
  console.log(`\n✓ screenshots written to ${OUT_DIR}`);
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
