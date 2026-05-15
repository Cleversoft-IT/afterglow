---
name: feedback-code-language
description: Tutto il codice del progetto Afterglow (backend Python + frontend TS) deve essere in inglese. Solo la conversazione utente-Claude è in italiano.
metadata:
  type: feedback
---

Tutto il codice di Afterglow (commenti, identificatori, stringhe user-facing in UI, label dei menu, prompt agenti, log, messaggi d'errore, valori enum intent/sentiment) deve essere in **inglese**.

**Why:** È un progetto da consegnare per l'AI Agent Olympics @ Milan AI Week 2026 — i giudici e l'audience internazionale valutano il codice. L'utente parla italiano con Claude per comodità, ma il deliverable resta in inglese.

**How to apply:**
- Quando genero/modifico codice in `afterglow/backend/**` o `afterglow/frontend/**`: scrivo in inglese (label, commenti, stringhe).
- Eccezione: **dati di seed/demo** che simulano una trattoria italiana possono restare in italiano (transcript di esempio, custom_dictionary `["celiachia","glutine",...]`, memory_summary dei clienti seed, prompt_hints riferiti al dominio italiano). Sono dati di scena, non codice di prodotto.
- Eccezione: messaggi di output a un end-user italiano *generati a runtime dall'LLM nella lingua rilevata dal transcript* (i18n dinamica) — non hardcodare italiano, ma puoi parametrizzare per lingua.
- Conversazione utente-Claude resta in italiano (vedi system prompt).

Related: [[project-afterglow-decisions]], [[project-afterglow-hackathon]]
