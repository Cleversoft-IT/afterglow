// Server HTTP locale che riceve screenshot in base64 e li salva su disco
// Uso: node scripts/screenshot-server.mjs

import http from 'http';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const OUT_DIR = path.join(__dirname, '..', 'public', 'screenshots');
fs.mkdirSync(OUT_DIR, { recursive: true });

const server = http.createServer((req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') { res.writeHead(204); res.end(); return; }
  if (req.method !== 'POST') { res.writeHead(405); res.end(); return; }

  let body = '';
  req.on('data', chunk => { body += chunk; });
  req.on('end', () => {
    try {
      const { name, data } = JSON.parse(body);
      const base64 = data.replace(/^data:image\/png;base64,/, '');
      const filePath = path.join(OUT_DIR, `${name}.png`);
      fs.writeFileSync(filePath, Buffer.from(base64, 'base64'));
      console.log(`✓ Saved: ${name}.png`);
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ ok: true, path: filePath }));
    } catch (e) {
      console.error('Error:', e.message);
      res.writeHead(500);
      res.end(JSON.stringify({ error: e.message }));
    }
  });
});

server.listen(19999, () => {
  console.log('Screenshot server listening on http://localhost:19999');
  console.log('POST { name: "filename", data: "data:image/png;base64,..." }');
});
