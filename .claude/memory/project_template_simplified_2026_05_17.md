---
name: project-template-simplified-2026-05-17
description: 2026-05-17 — Template model ridotto al solo product surface (fields_schema/action_types/prompt_hints). PII/custom_dictionary/mock_target/mutates rimossi dal template e da editor/wizard. mock_target e mutates ora vivono in ActionCatalogEntry; pii_sanitizer.py cancellato.
metadata:
  type: project
---

> ⚠️ Round-10 (2026-05-18) ha rimosso `action_planner.py` integralmente e ridotto `call_analyzer.py` ai soli schemi. Le menzioni qui sotto a "`agents/action_planner.py`" e ai "4 step (call_analyzer → action_planner → action_executor → _persist_memory)" descrivono lo stato a 2026-05-17. La pipeline live è descritta in [[project-agentic-pipeline]] (unico agente ADK multi-turn). Il resto del file resta valido come riferimento sulla forma del `Template` (fields_schema / action_types / prompt_hints).

Il modello `Template` è stato semplificato per riallinearsi con lo scope hackathon: un template descrive il prodotto (cosa estrarre + cosa fare dopo), non il sistema (routing mock, classificazione PII, dizionario ASR).

**Cosa è stato rimosso dal template (Pydantic + TS + UI + seed + LLM prompt):**

- `FieldDefinition.pii_class`
- `FieldDefinition.sensitive`
- `ActionDefinition.mock_target` → ora vive in `ActionCatalogEntry.mock_target` (era già lì, ma il template lo trasportava in parallelo)
- `ActionDefinition.mutates` → spostato in **nuovo** campo `ActionCatalogEntry.mutates`; `action_executor` e `action_planner` lo leggono via `action_catalog.mutates(key)`
- `Template.custom_dictionary` → colonna ARRAY droppata con migration `0012_drop_template_custom_dictionary.py`; Speechmatics gira senza `additional_vocab`

**Cosa è stato eliminato dal backend:**

- `backend/app/agents/pii_sanitizer.py` (file cancellato)
- `backend/app/agents/pii_policy.py` (file cancellato — `redact_for_briefing`, `hash_for_audit`, `PII_THRESHOLDS`, `threshold_for` tutti gone)
- `backend/tests/test_pii_sanitizer.py` (cancellato)
- `backend/tests/test_pii_policy.py` (cancellato)
- Step audit `pii_policy_applied` non viene più emesso; `orchestrator.run_pipeline` ha ora 4 step (call_analyzer → action_planner → action_executor → _persist_memory)
- `customer_profile.apply_customer_update` non setta più `mock`/`mutates` nel result dict — li stampa il catalog tramite `_run_internal_real`

**Cosa è cambiato in `ActionCatalogEntry`:**

```python
@dataclass(frozen=True)
class ActionCatalogEntry:
    ...
    mock_target: Optional[str] = None        # già esistente
    mutates: bool = False                    # nuovo (popolato per ogni entry)
```

Helper `action_catalog.mutates(action_key) -> bool` è la single source of truth.

**Cosa resta nel template:**

- `fields_schema`: `key`, `label`, `type`, `required`, `options`, `description`, `confidence_threshold`, `extractor_hint`, `depends_on`
- `action_types`: `key`, `label`, `description`, `execution_mode`, `preconditions`, `confidence_threshold`, `evidence_required`, `payload_schema`
- `prompt_hints`: `[{when, then}]`
- `simulation_config`: interno/demo only — non esposto nel template editor

**File modificati (per ricostruire la storia):**

- Backend: `schemas/templates.py`, `db/models.py`, `db/seed.py`, `executors/action_executor.py`, `agents/{action_planner,call_analyzer,orchestrator,template_builder,template_validator,wizard_chat}.py`, `agents/prompts/{template_builder,template_validator}.md`, `api/{templates,calls}.py`, `schemas/calls.py`, `integrations/{action_catalog,speechmatics}.py`, `integrations/internal/customer_profile.py`
- Migration: `alembic/versions/0012_drop_template_custom_dictionary.py`
- Frontend: `app/lib/{types,auditLabels}.ts`, `app/app/templates/[id].tsx`
- Docs: `CLAUDE.md`, `README.md`, `docs/ARCHITECTURE.md`, `docs/future-ideas.md`
- Memory: [[project-afterglow-decisions]] (sezione 1.nove), [[feedback-code-language]] (rimossa menzione custom_dictionary)

**Why:** ticket "simplify template model and template editor surface" — il template editor era un wizard tecnico (PII + ASR + mock routing); il valore di hackathon è la pipeline post-call + esecuzione tipata. PII gating è esplicitamente "future work" per `docs/future-ideas.md`.

**How to apply:**

- Prima di rimettere uno dei campi rimossi nel template Pydantic: leggere il ticket. Il piano corretto è arricchire `ActionCatalogEntry` o aggiungere uno step esterno al template, non il template stesso.
- Quando aggiungi una nuova action al catalog, ricordati di settare `mutates: bool` esplicitamente — il default è `False` ma cambia la docstring del tool Gemini e l'audit row.
- Quando vedi un seed/test/file che cita ancora `pii_class` o `custom_dictionary`, è un leftover: cancellarlo.
- `payload_schema` resta sul template (è product-level: cosa il business vuole che venga validato).

Related: [[project-afterglow-decisions]], [[feedback-db-disposable]], [[project-wizard-template-new-only]]
