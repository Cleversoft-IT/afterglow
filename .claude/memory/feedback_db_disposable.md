---
name: feedback-db-disposable
description: In Afterglow i record nel DB sono usa-e-getta; niente backward-compat per la shape dei dati, niente reader retro-compat. Le migration possono cancellare/TRUNCATE liberamente.
metadata:
  type: feedback
---

In Afterglow tutto ciò che vive nel database (templates seed, customers demo, calls, extracted_fields, executed_actions, audit_log, customer_memory_chunks, demo_sessions) è **usa-e-getta**: viene rigenerato dal `seed.py` al primo `entrypoint.sh` del backend, o accumulato per sessione demo che ha una TTL di 24h con cleanup automatico (vedi `app/tasks/session_cleanup.py`). Non c'è una "produzione con clienti veri" il cui storico vada conservato — il progetto è un prototipo hackathon.

**Why:** durante l'audit del piano "Templates roadmap rev 2" (2026-05-16) ho rallentato il design proponendo reader Python retro-compat per la vecchia `prompt_hints: str` (verso la nuova `list[PromptHintRule]`) e migrazioni `ALTER COLUMN … USING` per preservare i dati. L'utente ha tagliato: *"i dati nel db non sono importanti, quindi non preoccupiamoci di migliorare o retro compatibilità. eliminiamo tutti i record senza problemi se serve"*. Tenere la retro-compat costa codice morto, casi-limite da testare, ambiguità in lettura, e prompt più lunghi per il Gemini — tutto sprecato in un progetto in cui possiamo riseminare il DB in 3 secondi.

**How to apply:**

- **Migrazioni distruttive sono ammesse.** `DELETE FROM …` (FK-ordered) o `TRUNCATE … RESTART IDENTITY CASCADE` su tabelle anche grandi è una scelta legittima quando semplifica lo schema change. Non serve preservare `templates`, `customers`, `calls`, ecc.
- **Niente reader legacy nel codice runtime.** Quando lo shape di una colonna JSONB cambia (es. `prompt_hints` da string a array, o `PlannedAction.payload_json: str` a `payload: dict`), si rinomina/riscrive direttamente. Non si scrive `if isinstance(x, str): wrap_in_legacy_shape(...)`. Il DB è già stato ripulito dalla migration; nessuna riga sopravvissuta ha la vecchia forma.
- **Drop & re-add column** è preferibile a `ALTER COLUMN … TYPE … USING …` quando le righe sono state svuotate dalla migration stessa: più leggibile, meno fragile rispetto a cast Postgres impliciti.
- **`seed.py` è la fonte di verità "fresca".** Riscrivere `seed.py` sulla nuova shape e lasciarlo idempotente (skip se popolato) è sufficiente: la migration azzera le tabelle, l'entrypoint richiama `seed.py`, il DB è coerente al primo boot.
- **Eccezioni esplicite.** Se in futuro arrivasse una vera produzione con dati di clienti reali (es. post-hackathon, contratto pilot), questa regola **decade** e va ridiscussa esplicitamente prima di toccare migrazioni. Marcare la transizione con una nuova memory (`feedback-db-production`) e segnalare nel commit message.
- **Non si applica al DB sviluppo dei colleghi.** Una migration distruttiva landed su `main` viene applicata anche su Vultr Managed Postgres e su qualunque DB locale di team-mate. Confermarlo a voce in Slack/chat prima di pushare quando il blast radius non è limitato alla mia macchina.

Questa regola compone con [[feedback-docs-freshness]]: quando una migration distruttiva cambia shape, **lo stesso commit** aggiorna i doc (ARCHITECTURE/README/memory) che descrivevano la vecchia shape, altrimenti chi rilegge i doc resta convinto della vecchia struttura.

Related: [[project-afterglow-decisions]], [[feedback-docs-freshness]], [[feedback-code-language]].
