// Cattura screenshot fullPage con la sessione del browser live
// Usa i cookie del browser per mantenere la sessione
import { chromium } from 'playwright-chromium';
import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.join(__dirname, '..', 'public', 'screenshots');
const APP = 'https://app.95-179-245-107.sslip.io';

fs.mkdirSync(OUT, { recursive: true });

async function shot(page, name, fullPage = false) {
  const p = path.join(OUT, `${name}.png`);
  await page.screenshot({ path: p, fullPage });
  console.log(`  ✓ ${name}.png`);
}

async function run() {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 430, height: 932 }, deviceScaleFactor: 2 });
  const page = await ctx.newPage();

  // ─── Attiva template prima di tutto ────────────────────
  await page.goto(APP + '/templates', { waitUntil: 'networkidle' });
  await page.waitForTimeout(3000);
  await shot(page, 'templates', false);
  try {
    await page.locator('text=Activate').first().click({ timeout: 5000 });
    await page.waitForTimeout(2000);
  } catch {/* già attivo */}

  // ─── Home ───────────────────────────────────────────────
  await page.goto(APP + '/', { waitUntil: 'networkidle' });
  await page.waitForTimeout(3500);
  await shot(page, 'home', false);
  // Full-page per avere la lista completa
  await shot(page, 'home-full', true);

  // Recupera callId dalla API
  let callId = null;
  let customerId = null;
  const resp = await page.waitForResponse(
    r => r.url().includes('/calls') && r.status() === 200,
    { timeout: 0 }
  ).then(r => r.json()).catch(() => null);

  if (!resp) {
    // Forza reload per intercettare
    const [r2] = await Promise.all([
      page.waitForResponse(r => r.url().includes('/calls') && r.status() === 200, { timeout: 8000 }).catch(() => null),
      page.reload({ waitUntil: 'networkidle' }),
    ]);
    const body = r2 ? await r2.json().catch(() => null) : null;
    if (body) {
      const c = body.find(c => c.status === 'completed' && c.analyzed_at);
      callId = c?.id;
      customerId = c?.customer_id;
    }
  } else if (Array.isArray(resp)) {
    const c = resp.find(c => c.status === 'completed' && c.analyzed_at);
    callId = c?.id;
    customerId = c?.customer_id;
  }

  console.log('callId:', callId, 'customerId:', customerId);

  // ─── Call detail — fullPage (fields + actions + transcript) ─
  if (callId) {
    await page.goto(`${APP}/call/${callId}`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(3500);
    // Viewport screenshot (fields visibili)
    await shot(page, 'call-detail-fields', false);
    // Full page (fields + actions + transcript tutto)
    await shot(page, 'call-detail-full', true);

    // Espandi transcript e rifai fullPage
    try {
      await page.locator('text=View turns').first().click({ timeout: 4000 });
      await page.waitForTimeout(800);
      await shot(page, 'call-detail-transcript-full', true);
    } catch {/* */}

    // ─── Customer detail ─────────────────────────────────
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.waitForTimeout(400);
    try {
      await page.locator('text=Open contact').click({ timeout: 5000 });
      await page.waitForTimeout(3000);
      await shot(page, 'customer-detail', false);
      await shot(page, 'customer-detail-full', true);
    } catch {
      if (customerId) {
        await page.goto(`${APP}/customer/${customerId}`, { waitUntil: 'networkidle' });
        await page.waitForTimeout(3000);
        await shot(page, 'customer-detail', false);
      }
    }
  }

  // ─── Audit log ──────────────────────────────────────────
  await page.goto(APP + '/audit', { waitUntil: 'networkidle' });
  await page.waitForTimeout(3500);
  await shot(page, 'audit-log', false);
  await shot(page, 'audit-log-full', true);

  // ─── Simulator ──────────────────────────────────────────
  await page.goto(APP + '/simulator', { waitUntil: 'networkidle' });
  await page.waitForTimeout(3000);
  await shot(page, 'simulator', false);

  // ─── Incoming call ──────────────────────────────────────
  try {
    await page.locator('text=Call from existing customer').click({ timeout: 6000 });
    await page.waitForURL(`**\/incoming-call*`, { timeout: 10000 });
    await page.waitForTimeout(2000);
    await shot(page, 'incoming-call', false);
  } catch (e) {
    console.log('  incoming-call via direct URL...');
    await page.goto(`${APP}/incoming-call?caller=existing`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(3000);
    await shot(page, 'incoming-call', false);
  }

  // ─── Contacts ───────────────────────────────────────────
  await page.goto(APP + '/contacts', { waitUntil: 'networkidle' });
  await page.waitForTimeout(3000);
  await shot(page, 'contacts', false);

  await browser.close();
  const files = fs.readdirSync(OUT).filter(f => f.endsWith('.png'));
  console.log(`\n✅ ${files.length} screenshot in ${OUT}`);
  files.forEach(f => console.log('   ' + f));
}

run().catch(e => { console.error(e); process.exit(1); });
