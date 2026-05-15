---
name: feedback-docs-freshness
description: La documentazione e le memorie di Afterglow vanno tenute sincronizzate col codice nello stesso commit/PR di un cambiamento. Stale docs poisonano le decisioni future.
metadata:
  type: feedback
---

In Afterglow lavorano più persone (umani + sessioni Claude indipendenti). Tutto ciò che vive sotto `.claude/memory/`, `.claude/plans/`, `afterglow/README.md`, `afterglow/docs/**` e i prompt agent in `afterglow/backend/app/agents/prompts/` è **onboarding surface condiviso**: chiunque (umano o agente) lo legge per costruirsi il modello mentale del progetto. Se un MD è obsoleto, ogni decisione presa a valle parte da una mappa sbagliata.

**Why:** un audit del 2026-05-16 ha trovato decine di affermazioni obsolete (tabella `Business` "ancora presente" mentre era stata droppata da `0002_drop_business.py`, "single Gemini call" mentre `action_planner.py` con ADK era già rientrato, `afterglow/frontend/` citato come path mentre era stato spaccato in `app/` + `demo-site/`, env var `DEMO_MODE` citata mentre era stata rimossa, ecc.). La causa-radice è una: cambiamenti landed sul codice senza un parallelo update ai documenti che ne parlavano.

**How to apply:**

- **Stesso commit/PR.** Quando modifichi il codice o le decisioni di prodotto, l'update ai doc rilevanti **non è un follow-up** — sta nello stesso changeset. Se il tempo non c'è, almeno marca le sezioni obsolete con un disclaimer in cima ("⚠️ outdated — see commit `<sha>`") e apri un task. La cosa peggiore è lasciare il vecchio testo standing senza segnale.
- **Greppa il nome.** Prima di rimuovere/rinominare una env var, un endpoint, una tabella, un file top-level, un flag, un comando — grep su `**/*.md` per il vecchio nome. Se restituisce risultati, devi aggiornare anche quelli.
- **Cambi di scope → memory.** Cambiamenti che spostano un'invariante (single-tenant / multi-tenant, n. di chiamate AI, pin di versione critiche, nome del progetto, deadline, partner targeting) → `.claude/memory/project_afterglow_decisions.md` e/o `project_afterglow_hackathon.md` aggiornati prima del merge.
- **Cambi di infra → reference.** Cambi a Coolify, Vultr, DB, Postgres trusted-IPs, GitHub App, endpoint sslip.io, env vars di produzione → `reference_devops_pipeline.md` + `reference_coolify_api.md` + sezione "Production stack" del `README.md`.
- **Piani eseguiti → marker.** Quando un plan file in `.claude/plans/` viene eseguito (totalmente o in larga parte), aggiungi in cima un header `> **✅ COMPLETATO** — verificato YYYY-MM-DD.` o `> **⚠️ SUPERSEDED**` con elenco delle parti che il codice contraddice. Non cancellare il file (è storia preziosa) ma toglilo dal radar come "roadmap viva".
- **Conflitto memory vs codice → vince il codice.** Se durante una sessione una memory file contraddice quello che vedi nel codice, verifica nel codice e aggiorna la memory, non viceversa. Le memory sono snapshot temporali; il codice è lo stato attuale.
- **Tipi di memory** (riepilogo, dettagli in system prompt auto-memory):
  - `project` — fatti su progetto, decisioni di prodotto, milestone. Scadono velocemente, aggiorna spesso.
  - `feedback` — regole/policy del team (come questa). Scadono solo quando la policy cambia.
  - `reference` — pointer a sistemi esterni (Coolify, Vultr, GitHub). Aggiorna solo quando i coordinati cambiano.
  - `user` — info sulla persona con cui collabori. Aggiorna man mano che impari.
  Aggiungere un memory nuovo → crea file con frontmatter + slug, aggiungi una riga ≤150 chars in [[MEMORY]] index. Mai mettere contenuto direttamente in `MEMORY.md`.
- **Doc del prodotto (non memory).** `afterglow/README.md` e `afterglow/docs/**` sono lette anche dai giudici dell'hackathon — ogni claim concreto (path, comando, env, partner, score) deve essere verificato contro il codice prima di mergiare. Le `Award alignment` sections sono particolarmente sensibili: una linea obsoleta lì può costare punti.
- **Prompt degli agenti.** Quando modifichi un prompt agent in `backend/app/agents/*.py`, controlla se esiste un `.md` "documentazione" parallelo in `backend/app/agents/prompts/` e tienilo allineato (oggi il `.md` è doc-only, il runtime usa la stringa Python — è esplicito nel file).

Related: [[project-afterglow-decisions]], [[feedback-code-language]], [[feedback-plan-files-location]], [[feedback-plans-no-timing]].
