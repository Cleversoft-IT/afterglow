---
name: feedback-demo-scripts-quality
description: Regola di qualità per ogni script demo Afterglow (seed e wizard-generated) — devono essere arguti, distinctive per dominio, esercitare 2-3 action del catalog, niente filler.
metadata:
  type: feedback
---

Ogni script demo che finisce in front del giudice — sia i 6 seed in `scripts/generate_demo_audio.py` (mirrored in `db/seed.py::_bundled_simulation_configs`) sia gli script wizard-generated in `agents/simulation_script.py` — DEVE rispettare questa barra di qualità prima di essere committato o renderizzato in audio.

**Why:** richiesta esplicita dell'utente 2026-05-18 quando abbiamo allargato il marketplace: *"tutti gli script, sia i 6 di mock (che generano gli mp3) sia quelli che devono essere generati devono essere script arguti e belli"*. Gli script triviali ("test test test", "I want to book a table") sprecano l'opportunità di demo: il post-call pipeline ha azioni nuove (payment/calendar/review/sms) che vanno **esercitate** dal caller in modo naturale, non lasciate inutilizzate.

**How to apply:**

1. **Esercitare 2-3 action del catalog naturalmente.** Lo script non deve recitare i nomi delle action; deve far emergere, attraverso la conversazione, i field e gli intent che permettono al post-call planner di pianificarle. Esempio buono (restaurant_new): party di 7 + occasione speciale → emerge naturalmente la richiesta di deposito (`payment.request_deposit`) + conferma WhatsApp + booking.create. Esempio cattivo: "I want to book a table for 4 at 8pm. Goodbye."

2. **Allineamento template ↔ script (NON NEGOZIABILE).** Ogni action_key che lo script suggerisce deve essere presente negli `action_types` del template (seed o wizard-built). Senza l'entry il post-call pipeline NON può pianificare l'azione anche se il caller la chiede letteralmente. Quando si tocca uno script seed, controllare il corrispondente `<DOMAIN>_TEMPLATE["action_types"]` in `db/seed.py`; aggiungere l'entry se manca.

3. **Voce distintiva per dominio.** Restaurant = warm hospitality, dettagli sensoriali (il dolce, il tavolo). Dentist = clinico-empatico, restraint sulla descrizione del dolore. Bodyshop = pragmatico-tecnico, targhe + codici di danno. Hotel = concierge tone. Salon = chatty, mention dello stylist. Clinic = calmo, attento ai sintomi. Legal = formale ma umano. Realestate = mention del riferimento immobiliare. Gym = casual e motivante. Events = high-energy, occasion + headcount. Vivono come `_DOMAIN_VOICE_HINTS` in `agents/simulation_script.py`.

4. **Caller è una persona, non un form.** Mini-arco di 1-2 dettagli specifici. `existing` riferisce almeno un fatto storico ("come l'ultima volta", "la prenotazione di marzo", "il Fiat Panda di nuovo"). `new` ha una complicazione fresca + nome completo + un ID realistico (targa, numero pratica assicurazione, e-mail).

5. **No filler, no trivia.** Mai "test test test", "demo demo demo", "lorem ipsum", "this is a demo call". Se un giudice riproduce lo script in live demo, deve potere senza imbarazzo.

6. **Turni brevi e realistici.** 1-2 frasi per turno, esitazioni naturali sono benvenute ("hmm", "let me think"). Tra 6 e 12 turni per scenario.

7. **Channel actions solo se confermate dal contesto.** Le action channel-dependent (`whatsapp.*`, `sms.*`, `email.*`, `calendar.*`, `payment.*`, `review.*`) compaiono solo se il contesto del business le giustifica. Non default sistematico a WhatsApp.

**Where to check:**
- Seed scripts: `scripts/generate_demo_audio.py:75-160` (e mirror in `backend/app/db/seed.py::_bundled_simulation_configs`).
- Wizard generator: `backend/app/agents/simulation_script.py:SYSTEM_INSTRUCTION` + `_build_user_prompt`.
- Template ↔ script alignment lock: TBD test `test_seed_script_action_alignment.py` (issue noto, da scrivere).

Related: [[project-afterglow-decisions]] §E "Marketplace expansion 2026-05-18".
