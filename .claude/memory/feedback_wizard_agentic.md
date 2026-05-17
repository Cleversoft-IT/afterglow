---
name: feedback-wizard-agentic
description: Il Template Wizard è agentico (draft-first + budget 2-5 domande), NON un form a slot né uno script con singola domanda hard-coded
metadata:
  type: feedback
---

Il Template Wizard (`afterglow/backend/app/agents/wizard_chat.py`) deve comportarsi come un agente, non come un form a slot né come uno script con singola domanda hard-coded:

- **Draft-first**: se il primo messaggio utente è già ricco (business type + call flow), il modello emette subito `ready=True` con bozza completa, senza domande.
- **Budget agentico 2-5 domande**, hard ceiling 5: il modello decide turno per turno se chiedere ancora o fare il draft. Il server inietta nel prompt utente "Questions asked so far: N / 5"; al raggiungimento del budget, "BUDGET EXHAUSTED" forza il draft.
- **Mai chiedere**: nome del template (inferire da business context), schemi/payload, mock targets, classi PII, dictionary ASR, soglie di confidenza, internals del modello.
- **Drafts target**: 4-8 fields snake_case (string/integer/boolean/date/time/enum/string_list), 2-4 actions (solo `available_keys()` dell'action catalog), 1-3 prompt_hints.
- **Niente post-processing hard-coded** che forzi `ready=True/False` in base a soglie deterministiche. La logica vive nel prompt + meta-state passato al modello. Unica eccezione: `ready=True ∧ draft_partial is None` → safety net down-grade a `ready=False`.

**Why:** feedback utente esplicito durante refactor 2026-05-17 — "deve essere agentica questa cosa, non hard coded". La versione precedente slot-filling era percepita come noiosa e burocratica; un single-question forzato sarebbe stato l'opposto rigido. Tenersi nel mezzo, lasciando decidere il modello entro un budget.

**How to apply:** in ogni futura modifica a `wizard_chat.py`, `wizard.tsx`, o agli schema `TemplateWizardResponse` / `WizardChatRequest` / `WizardChatResponse`, preservare la filosofia agentica. Resistere alla tentazione di aggiungere checklist rigide o "una sola domanda per turno". Le regole comportamentali vanno nel prompt; il codice fa solo grounding del catalog (strip hallucinated actions) e safety net minimali. Vedi [[project-template-simplified-2026-05-17]] per il contesto sulla pulizia degli obsolete field.
