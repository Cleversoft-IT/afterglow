---
name: project-template-validator-deterministic
description: Il template_validator è deterministico puro dal 2026-05-17 (zero LLM call); chi consuma lo schema del Template e come.
metadata:
  type: project
---

## Stato 2026-05-17

`backend/app/agents/template_validator.py` è **deterministico puro**: zero LLM call, niente network. La funzione pubblica `validate_template(template) -> ValidationReport` è **sincrona** e ritorna `ValidationReport(issues=validate_template_deterministic(template))`.

Rimossi nello stesso commit: `_semantic_review`, `_SEMANTIC_INSTRUCTION`, `ProposedMock`, il campo `ValidationReport.proposed_mocks`, il prompt `backend/app/agents/prompts/template_validator.md` (cartella `prompts/` ora vuota), e i tipi TS `ProposedMock` + `ValidationReport.proposed_mocks` in `app/lib/types.ts`.

Vive in `agents/` per ragione storica — non è più un agente. Non contarlo come sub-agent quando si discute della pipeline post-call (vedi [[project-afterglow-decisions]] sez. "Decision 1.ter / 1.quattro").

**Why:** L'output di `_semantic_review.issues` veniva già loggato-e-droppato in produzione (commento al codice: "useful for telemetry but confusing for an operator"). L'output `proposed_mocks` era duplicativo: `wizard_chat.run_wizard_chat` strippa già le action key fuori catalogo dal `draft_partial` e le espone via `proposed_actions_from_catalog` (riga 286-300 in `wizard_chat.py`). La Gemini call costava latenza + token per ogni turno finale del wizard senza output visibile all'operatore.

**How to apply:**

- Se trovi PR/proposte che reintroducono LLM dentro il validator, rifiuta: la decisione 2026-05-17 è che il validator è guardrail deterministico, non agente.
- Se il `then` di un `prompt_hints` rule sembra "ambiguo" o un `label` non matcha la `key`, NON è compito del validator catturarlo. Quei segnali soft erano la metà semantica e sono fuori scope. Il validator cattura solo invarianti hard (crash a runtime).
- Per il caso "operatore ha scritto una action key inventata": il path corretto è `proposed_actions_from_catalog` nel `WizardChatResponse`, popolato da `wizard_chat.run_wizard_chat` mentre filtra le key invalide dal draft. Non reintrodurre `proposed_mocks`.
- Test contract: `test_template_validator.py::test_validate_template_is_synchronous` blocca regressioni async sul punto pubblico.

## Cosa cattura il validator (oggi)

Tutti hard, tutti deterministici, tutte cose che senza il validator esploderebbero a runtime in silenzio:

| Check | Conseguenza se manca |
|---|---|
| field keys snake_case + non duplicati | `_coerce_extractions` non riconosce la key, valore scartato |
| `depends_on` referenzia field esistenti, niente cicli | orchestrator's coercer looperebbe |
| action keys dot.namespaced + non duplicate | catalog lookup fallisce |
| action keys ∈ `action_catalog.available_keys()` (warning) | `action_executor` rifiuta l'azione |
| `preconditions` referenzia field in `fields_schema` | planner skippa sempre l'azione in silenzio |
| `payload_schema` è JSONSchema valido | `jsonschema.validate` in executor crasha |
| `prompt_hints[].when` matcha la mini-grammatica di `prompt_hint_eval.py` | regola silenziosamente ignorata a runtime |

## I tre consumatori dello schema del Template

Il `Template` (record Postgres + classi Pydantic in `schemas/templates.py`) è la lingua franca tra tre componenti:

1. **`agents/wizard_chat.py` — emettitore.** Lo schema Pydantic (`TemplateWizardResponse`, `FieldDefinition`, `ActionDefinitionDraft`, `PromptHintRule`) viene passato a Gemini come `response_schema` di structured-output. Il wizard è forzato a emettere JSON che rispetta la forma. Nota: usa `ActionDefinitionDraft` (= `ActionDefinition` senza `payload_schema`) perché Gemini structured-output rifiuta `additionalProperties` che Pydantic emette per `dict[str, Any]`. Il `payload_schema` viene riempito al persistence boundary in `api/templates.py` dal `default_payload_schema` dell'entry catalog corrispondente.

2. **`agents/call_analyzer.py` — consumatore.** Riceve il template **istanziato** (record DB) serializzato in JSON dentro il prompt di Gemini, sezione `=== DOMAIN & TEMPLATE ===`. `fields_schema` e `action_types` diventano il contratto di estrazione (verbatim evidence, rispetto di `type`/`options`/`extractor_hint`/`confidence_threshold`/`depends_on`/`preconditions`/`execution_mode`). I `prompt_hints` vengono filtrati prima: solo i `then` delle regole il cui `when` matcha i prior facts del chiamante (vedi `agents/prompt_hint_eval.py`) finiscono nel prompt come bullet list.

3. **`agents/template_validator.py` — guardrail.** Deterministico, sincrono. Validato sia dal wizard quando `ready=True`, sia dall'endpoint `POST /api/v1/templates/validate` per la Refine UI post-persistence. Il `ValidationReport` viene messo nel campo `validation` di `WizardChatResponse` / `TemplateWizardResponse`, mostrato inline dalla wizard UI (`app/templates/wizard.tsx`).

Cosa **non** decide il template: integration_kind (`mock_external` vs `internal_real`), `mock_target`, `internal_handler`, `can_undo`, `mutates`. Tutto questo vive in `integrations/action_catalog.py`, ed è la trust boundary.

Related: [[project-afterglow-decisions]], [[project-template-simplified-2026-05-17]]
