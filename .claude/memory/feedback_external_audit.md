---
name: feedback-external-audit
description: L'utente porta audit di collaboratori esterni sui piani prima dell'esecuzione; non sono verità assolute ma vanno verificati contro i contratti reali della codebase
metadata:
  type: feedback
---

L'utente porta occasionalmente un "audit di un collaboratore esterno" sui piani che hai appena scritto, prima di approvarli. Esempio durante il round 5 (2026-05-17): dopo aver scritto `.claude/plans/il-tuo-obiettivo-curried-lemur.md`, l'utente ha condiviso una recensione tecnica del piano con 6 correzioni puntuali (`failure_kind` non `error is None`, `payload_schema` enrichment al persistence boundary non nel wizard, validation source-based non severity-based, `action_catalog.get` da verificare, uniqueness scope template rename, wizard `_user_prompt` da chiarire per il caso budget+canali).

**Il framing è esplicito:** "non considerarlo verità assoluta, ma usalo per migliorare il piano, se serve".

**How to apply:**

1. **Non accettare l'audit alla cieca.** Verifica ogni claim contro il codice reale: leggi i file citati, controlla le firme delle funzioni, conferma gli error code, controlla se l'helper esiste davvero. Esempi di assunzioni dell'audit che sono risultate corrette nel round 5: `_MISSED_ERROR_CODES = {"empty_or_noise_audio"}`, `ActionDefinitionDraft` senza `payload_schema`, `UpdateTemplateRequest` senza `name`. Esempi di assunzioni da verificare comunque: l'audit suggeriva `action_catalog.get_entry()` ma in realtà il metodo si chiama `get()` (verificato in `action_catalog.py:188`).

2. **Non rifare il piano da zero.** Patch chirurgico delle sezioni interessate, mantenendo struttura e scelte già confermate via `AskUserQuestion`. Il piano è il prodotto della conversazione precedente, l'audit è un secondo passaggio di QA.

3. **Tieni traccia esplicita.** Nel piano aggiungi un blocco "**Audit di un collaboratore esterno applicato**: ho ricontrollato i contratti reali della codebase. Alcune assunzioni del primo draft erano sbagliate. Correzioni principali: …". Questo è feedback diretto all'utente che hai trattato il suggerimento con rigore.

4. **Verifica con il codice, non con la memoria.** Le memory possono essere stale (vedi [[feedback-docs-freshness]]). Quando l'audit dice "verifica che `X` esista", apri `X` e leggi.

5. **Resta agentico nei punti di stile.** Se l'audit suggerisce "preferire `Optional[dict]` ai mutable defaults", applicalo se è effettivamente meglio (lo era), ma se l'audit propone una refactor che renderebbe il fix più complicato senza beneficio chiaro (es. introdurre un `failure_kind` enum a DB invece di computed field per il demo hackathon), spiega perché stai scegliendo la versione più leggera.

6. **L'audit può essere multi-round.** Durante il round 5 sono arrivati DUE audit successivi sullo stesso piano. Tratta ogni round con lo stesso rigore: ri-verifica i contratti, patch le sezioni, documenta le correzioni.

**Why:** l'utente preferisce un piano che sopravvive a un secondo paio d'occhi tecnici piuttosto che uno che "sembra ok al primo passaggio". È un metodo di lavoro, non un'eccezione una tantum.
