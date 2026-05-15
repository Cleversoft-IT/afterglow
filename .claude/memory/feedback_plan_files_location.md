---
name: feedback-plan-files-location
description: Plan files vanno in .claude/plans/ della repo, non nella dir globale ~/.claude/plans/
metadata:
  type: feedback
---

I plan file generati in plan mode vanno salvati in `.claude/plans/` dentro la repo Afterglow, non in `~/.claude/plans/` (dir globale user-level).

**Why:** I piani sono artefatti versionati condivisi col team (esattamente come `.claude/memory/`). Il piano precedente `procedi-col-planning-reactive-cocke.md` vive già lì ed è la single source of truth sulla roadmap del progetto. Tenerli in user-dir li nasconde dal team e li separa dal codice che descrivono.

**How to apply:** Quando entri in plan mode su Afterglow, scrivi il plan file in `/home/sepa/cleversoft/hackaton/hackaton-lablab/.claude/plans/<slug>.md` invece di accettare il path user-level proposto dal system reminder. Se accidentalmente lo crei in user-dir, spostalo prima di chiamare ExitPlanMode.

Collegato a [[feedback-plans-no-timing]].
