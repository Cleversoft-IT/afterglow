// Cattura screenshot delle pagine reali dell'app Afterglow
// Uso: node scripts/capture-screenshots.mjs

import { chromium } from 'playwright-chromium';
import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const OUT_DIR = path.join(__dirname, '..', 'public', 'screenshots');
const APP = 'https://app.95-179-245-107.sslip.io';
const API = 'https://api.95-179-245-107.sslip.io';

fs.mkdirSync(OUT_DIR, { recursive: true });

async function shot(page, name) {
  const p = path.join(OUT_DIR, `${name}.png`);
  await page.screenshot({ path: p });
  console.log(`  ✓ ${name}.png`);
}

async function run() {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({
    viewport: { width: 430, height: 932 },
    deviceScaleFactor: 2,
  });
  const page = await ctx.newPage();

  // ─── STEP 0: Inizializza — visita l'app e attiva template ──
  console.log('0. Activating template...');
  await page.goto(APP + '/templates', { waitUntil: 'networkidle' });
  await page.waitForTimeout(3000);

  // Screenshot della pagina templates (utile per il video)
  await shot(page, 'templates');

  // Clicca "Activate" sul primo template (Standard booking)
  try {
    const activateBtn = page.locator('text=Activate').first();
    await activateBtn.waitFor({ timeout: 8000 });
    await activateBtn.click();
    await page.waitForTimeout(3000);
    console.log('  Template activated');
  } catch (e) {
    console.log('  ⚠ Could not activate template:', e.message);
  }

  // ─── Leggi la sessione demo per usarla nelle API calls ──
  // Recupera i cookies per estrarre il demo session ID
  const cookies = await ctx.cookies();
  const sessionCookie = cookies.find(c => c.name === 'demo_session' || c.name.includes('session'));

  // Intercetta il header X-Demo-Session dalle richieste
  let demoSession = null;
  await page.route('**/*', route => {
    const req = route.request();
    const h = req.headers()['x-demo-session'];
    if (h && !demoSession) {
      demoSession = h;
      console.log('  Session ID:', demoSession);
    }
    route.continue();
  });

  // ─── 1. HOME ───────────────────────────────────────────
  console.log('1. Home...');
  await page.goto(APP + '/', { waitUntil: 'networkidle' });
  await page.waitForTimeout(3500);
  await shot(page, 'home');

  // Scroll per vedere chiamate con booking badge
  await page.evaluate(() => window.scrollBy(0, 700));
  await page.waitForTimeout(800);
  await shot(page, 'home-scrolled');
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForTimeout(400);

  // ─── Recupera ID chiamate via API ──────────────────────
  let callId = null;
  let customerId = null;

  try {
    // Leggi il localStorage per trovare il demo session
    const ls = await page.evaluate(() => {
      const keys = Object.keys(localStorage);
      const result = {};
      keys.forEach(k => { result[k] = localStorage.getItem(k); });
      return result;
    });
    console.log('  localStorage keys:', Object.keys(ls).join(', '));
  } catch {/* */}

  // Intercetta la risposta dalla API delle calls
  const callsResponse = await page.waitForResponse(
    r => r.url().includes('/calls') && r.status() === 200,
    { timeout: 5000 }
  ).then(r => r.json()).catch(() => null);

  if (callsResponse && Array.isArray(callsResponse)) {
    const completed = callsResponse.find(c => c.status === 'completed');
    if (completed) {
      callId = completed.id;
      customerId = completed.customer_id;
      console.log('  Call ID:', callId);
      console.log('  Customer ID:', customerId);
    }
  }

  if (!callId) {
    // Ricarica e intercetta
    const [callsResp] = await Promise.all([
      page.waitForResponse(r => r.url().includes('/calls') && r.status() === 200, { timeout: 8000 }).catch(() => null),
      page.reload({ waitUntil: 'networkidle' }),
    ]);
    if (callsResp) {
      const body = await callsResp.json().catch(() => null);
      if (body && Array.isArray(body)) {
        const completed = body.find(c => c.status === 'completed');
        if (completed) {
          callId = completed.id;
          customerId = completed.customer_id;
        }
      }
    }
  }

  console.log('  Final callId:', callId, 'customerId:', customerId);

  // ─── 2. CALL DETAIL ────────────────────────────────────
  if (callId) {
    console.log('2. Call detail...');
    await page.goto(`${APP}/call/${callId}`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(3500);
    await shot(page, 'call-detail-fields');

    await page.evaluate(() => window.scrollBy(0, 500));
    await page.waitForTimeout(600);
    await shot(page, 'call-detail-actions');

    // Transcript
    try {
      await page.evaluate(() => window.scrollTo(0, 0));
      await page.waitForTimeout(400);
      await page.locator('text=View turns').first().click({ timeout: 4000 });
      await page.waitForTimeout(700);
      await page.evaluate(() => window.scrollBy(0, 400));
      await page.waitForTimeout(400);
      await shot(page, 'call-detail-transcript');
    } catch { console.log('  ⚠ transcript expand failed'); }

    // ─── 3. CUSTOMER DETAIL ──────────────────────────────
    console.log('3. Customer detail...');
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.waitForTimeout(400);
    try {
      await page.locator('text=Open contact').click({ timeout: 5000 });
      await page.waitForTimeout(3000);
      await shot(page, 'customer-detail');
    } catch {
      if (customerId) {
        await page.goto(`${APP}/customer/${customerId}`, { waitUntil: 'networkidle' });
        await page.waitForTimeout(3000);
        await shot(page, 'customer-detail');
      } else {
        console.log('  ⚠ No customer ID, skipping');
      }
    }
  } else {
    console.log('  ⚠ No call ID found, skipping call/customer detail');
  }

  // ─── 4. AUDIT LOG ──────────────────────────────────────
  console.log('4. Audit log...');
  await page.goto(APP + '/audit', { waitUntil: 'networkidle' });
  await page.waitForTimeout(3500);
  await shot(page, 'audit-log');

  // ─── 5. SIMULATOR ──────────────────────────────────────
  console.log('5. Simulator...');
  await page.goto(APP + '/simulator', { waitUntil: 'networkidle' });
  await page.waitForTimeout(3000);
  await shot(page, 'simulator');

  // ─── 6. INCOMING CALL ──────────────────────────────────
  console.log('6. Incoming call...');
  try {
    await page.locator('text=Call from existing customer').click({ timeout: 8000 });
    // Aspetta la navigazione a incoming-call
    await page.waitForURL(`**\/incoming-call*`, { timeout: 10000 });
    await page.waitForTimeout(2000);
    await shot(page, 'incoming-call');
  } catch (e) {
    console.log('  ⚠', e.message);
    // Naviga direttamente
    await page.goto(`${APP}/incoming-call?caller=existing`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(3000);
    await shot(page, 'incoming-call');
  }

  // ─── 7. CONTACTS ───────────────────────────────────────
  console.log('7. Contacts...');
  await page.goto(APP + '/contacts', { waitUntil: 'networkidle' });
  await page.waitForTimeout(3000);
  await shot(page, 'contacts');

  await browser.close();

  const files = fs.readdirSync(OUT_DIR).filter(f => f.endsWith('.png'));
  console.log(`\n✅ ${files.length} screenshots catturati:`);
  files.forEach(f => console.log('   ' + f));
}

run().catch((err) => { console.error(err); process.exit(1); });
