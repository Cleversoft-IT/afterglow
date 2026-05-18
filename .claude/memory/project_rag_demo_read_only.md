---
name: project-rag-demo-read-only
description: Round-9 demo RAG semantics — read attivo on pre-seeded collection, write skipped, idempotency per-call.
metadata:
  type: project
---

**Decision (2026-05-18, round-9 parte 2):** in demo mode il **read** della
Vultr Vector Store è **attivo** su una collection pre-seedata; lo
**scrittura (write-back)** resta **skipped**. La scelta sostituisce la
prima decisione di [[project-afterglow-decisions]] §1.quater ("Vultr
Vector Store skipato in demo mode" — sia read che write).

**Why:** alza il segnale Vultr Award per i giudici dell'hackathon lablab
(deadline 19 mag 2026). Con il preseed, il primo tap del giudice su
"Call from existing customer" già produce un audit row
`memory_lookup status=success step_type=rag_semantic` con
`prior_facts_preview` reale, invece di mostrare uno `status=skipped` con
la nota "in produzione funzionerebbe davvero". I tre problemi storici
che giustificavano lo skip iniziale (SDK Vultr senza metadata filter,
no cleanup multi-session, valore marginale al primo round) sono ora
mitigati: la collection condivisa resta a singletask, l'idempotency
per-call evita duplicati, e il valore è dimostrato dal primo squillo.

**How to apply:**

- Il preseed gira in lifespan via `backend/app/tasks/vector_preseed.py.preseed_demo_collection(session)`,
  chiamato dopo `recover_orphans()` e dopo `refresh_seed_dates_if_needed`
  (l'ordine è critico — il preseed deve vedere date già shiftate).
- **Idempotency per-call**: il task calcola
  `expected_call_ids = SELECT id FROM calls WHERE is_seed AND raw_transcript IS NOT NULL`
  e
  `already_preseeded_call_ids = SELECT call_id FROM customer_memory_chunks WHERE chunk_metadata @> '{"preseed": true}'::jsonb`,
  poi inserisce solo `expected - already`. Sopravvive a partial failures
  (Vultr 500 a metà push → restart riprende dai mancanti) e a evoluzioni
  del dataset.
- **Aggiungere una nuova seed call** è automatico: al prossimo boot il
  preseed inserisce il chunk mancante. Nessun reset richiesto.
- **Rimuovere una seed call** lascia il chunk orphan (`call_id` finisce
  a `NULL` via FK SET NULL). Cleanup manuale:
  `DELETE FROM customer_memory_chunks WHERE chunk_metadata @> '{"preseed":true}'`
  + svuotare la collection dal dashboard Vultr (l'SDK non espone un list
  endpoint, quindi non c'è automation possibile senza endpoint REST
  custom). Trade-off accettato per la demo.
- **Read gate** centralizzato in
  `backend/app/agents/memory_retrieval.retrieve_customer_context(preseed_available: bool)`:
  skip solo se `not collection_id` o se `is_demo and not preseed_available`.
  L'orchestrator (`backend/app/agents/orchestrator.py`) calcola
  `demo_can_rag = is_demo and collection_id and (customer.is_seed or await _seed_exists_for_phone(session, customer.phone_e164))`
  e passa `preseed_available=True` quando entra nel ramo RAG. Per gli
  unknown phone in demo (cold call sconosciuta) → continua structured-empty,
  NESSUNA call Vultr (cost-aware).
- **Write-back** resta invariato: `_persist_memory` continua a emettere
  `memory_updater status=skipped reason=demo_sandbox_vector_store_disabled`,
  così il giudice vede esplicitamente che la sua call non sta inquinando
  la collection condivisa. La row è visibile nel nuovo audit drawer
  overview (vedi [[feedback-audit-collapse-pattern]]).
- **Coesistenza prod + preseed nella stessa collection**: i chunk
  prod (write-back) non hanno il marker `preseed`; quelli preseed sì.
  Il calcolo `already_preseeded_call_ids` filtra esplicitamente per
  `chunk_metadata @> '{"preseed": true}'`, quindi i chunk prod
  vengono ignorati e non bloccano l'inserimento dei preseed mancanti.

**Coordinate file:**

- BE preseed: `backend/app/tasks/vector_preseed.py`,
  `backend/app/agents/orchestrator.py._format_briefing_chunk` (helper
  estratto per non duplicare il template del chunk content tra preseed
  e write-back).
- BE read gate: `backend/app/agents/memory_retrieval.py`
  (`preseed_available`), `backend/app/agents/orchestrator.py`
  (`_seed_exists_for_phone`).
- Lifespan: `backend/app/main.py` (try/except separati: refresh ERROR +
  skip preseed; preseed WARNING + continue).
- Audit visibility: `memory_lookup` row con `payload.prior_facts_preview`
  (primi 1000 char), `memory_updater` row con `status=skipped
  reason=demo_sandbox_vector_store_disabled`.

**Pitch coverage:** [[project-afterglow-decisions]] §1.quater (rewrite)
+ §1.quindici (round-9 parte 2). README `Best use of Vultr` + Demo
isolation policy. `afterglow/docs/ARCHITECTURE.md` "Vultr Vector Store
— read-only on pre-seeded collection in demo".
