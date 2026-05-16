---
name: feedback-code-language
description: Tutto Afterglow (codice + dati di seed/demo) è in inglese. Solo la conversazione utente-Claude è in italiano. Aggiornato 2026-05-16 — rimossa eccezione seed italiani.
metadata:
  type: feedback
---

Tutto Afterglow è in **inglese**: codice (commenti, identificatori, stringhe user-facing in UI, label dei menu, prompt agenti, log, messaggi d'errore, valori enum intent/sentiment) **e dati di seed/demo** (transcript di esempio, custom_dictionary, memory_summary dei clienti seed, prompt_hints, nomi dei business demo, customer phone numbers).

**Why:** È un progetto da consegnare per l'AI Agent Olympics @ Milan AI Week 2026 — i giudici sono internazionali e valutano sia il codice che la demo. L'eccezione storica "seed in italiano perché è contenuto, non codice" creava incoerenza con i 3 MP3 demo che sono già in EN UK/US (vincolo Speechmatics TTS preview): un giudice che apriva il dialer sentiva audio EN ma vedeva customer profile / memory_summary in italiano. Tutto-EN risolve. L'utente parla italiano con Claude per comodità, ma il deliverable resta in inglese.

**How to apply:**
- Quando genero/modifico codice in `afterglow/backend/**`, `afterglow/app/**` (Expo) o `afterglow/demo-site/**` (Vite): scrivo in inglese (label, commenti, stringhe).
- **Anche i dati di seed/demo sono in inglese** (`app/db/seed.py`, demo template definitions, customer demo profiles, transcript stubs). Se trovi residui italiani in seed/fixture, è un retaggio: va anglicizzato.
- Eccezione singola: messaggi di output a un end-user *generati a runtime dall'LLM nella lingua rilevata dal transcript* (i18n dinamica) — non hardcodare nulla, ma puoi parametrizzare per lingua rilevata dall'audio.
- Conversazione utente-Claude resta in italiano (vedi system prompt).

Related: [[project-afterglow-decisions]], [[project-afterglow-hackathon]], [[feedback-production-equals-hackathon]]
