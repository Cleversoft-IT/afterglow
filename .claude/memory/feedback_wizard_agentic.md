---
name: feedback-wizard-agentic
description: Il Template Wizard è agentico (draft-first + budget 2-5 domande), NON un form a slot né uno script con singola domanda hard-coded
metadata:
  type: feedback
---

Il Template Wizard (`backend/app/agents/wizard_chat.py`) deve comportarsi come un agente, non come un form a slot né come uno script con singola domanda hard-coded:

- **Draft-first per i campi neutri**: business type, fields_schema, prompt_hints, action keys non-canale. Se il primo messaggio utente è già ricco, il modello può proporre subito i campi/azioni "safe" e farlo presente.
- **Integration discovery HARD RULE (2026-05-17 round 5)**: prima di committare azioni che dipendono da canali esterni (`whatsapp.*`, `sms.*`, `email.*`, `case.open_insurance`), il wizard DEVE confermare quali canali l'utente usa. Se il primo messaggio non li menziona esplicitamente, il turno 1 è una domanda di clarification (`"Do you reach customers via WhatsApp, SMS, email, or only on the phone?"`) e `ready=False`. Mai default a WhatsApp / SMS / email. Se BUDGET_EXHAUSTED e canali ancora ignoti → drafta omettendo le azioni canale-dipendenti.
- **Budget agentico 2-5 domande**, hard ceiling 5: il modello decide turno per turno se chiedere ancora o fare il draft. Il server inietta nel prompt utente "Questions asked so far: N / 5"; al raggiungimento del budget, "BUDGET EXHAUSTED" forza il draft (con la regola Integration discovery sopra ancora attiva).
- **Mai chiedere**: nome del template (inferire da business context), schemi/payload, mock targets, classi PII, dictionary ASR, soglie di confidenza, internals del modello.
- **Drafts target**: 4-8 fields snake_case (string/integer/boolean/date/time/enum/string_list), 2-4 actions (solo `available_keys()` dell'action catalog), 1-3 prompt_hints.
- **Niente post-processing hard-coded** che forzi `ready=True/False` in base a soglie deterministiche. La logica vive nel prompt + meta-state passato al modello. Unica eccezione: `ready=True ∧ draft_partial is None` → safety net down-grade a `ready=False`.
- **`payload_schema` NON è responsabilità del wizard**: `ActionDefinitionDraft` non porta quel campo (Gemini structured-output rifiuta `additionalProperties`). L'arricchimento avviene al persistence boundary in `backend/app/api/templates.py` (helper `_enrich_action_types_with_catalog_schemas`) leggendo `ActionCatalogEntry.default_payload_schema`. Vedi sub-decisione 1.dieci in [[project-afterglow-decisions]].

**Why:** feedback utente esplicito durante refactor 2026-05-17 — "deve essere agentica questa cosa, non hard coded". La versione precedente slot-filling era percepita come noiosa e burocratica; un single-question forzato sarebbe stato l'opposto rigido. Tenersi nel mezzo, lasciando decidere il modello entro un budget. La Integration discovery rule (round 5, pomeriggio) nasce dal feedback "draft un'azione WhatsApp senza chiedermi se uso WhatsApp" — l'agente era troppo eager.

**How to apply:** in ogni futura modifica a `wizard_chat.py`, `wizard.tsx`, o agli schema `TemplateWizardResponse` / `WizardChatRequest` / `WizardChatResponse`, preservare la filosofia agentica + la Integration discovery rule. Resistere alla tentazione di rimuovere la clarification "per snellire il turno 1" o di aggiungere checklist rigide. Le regole comportamentali vanno nel prompt; il codice fa solo grounding del catalog (strip hallucinated actions), safety net minimali, e l'arricchimento `payload_schema` al persistence boundary. Vedi [[project-template-simplified-2026-05-17]] per il contesto sulla pulizia degli obsolete field.
