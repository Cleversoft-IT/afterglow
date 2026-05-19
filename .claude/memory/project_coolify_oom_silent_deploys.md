---
name: project-coolify-oom-silent-deploys
description: La VM Coolify (4 GB RAM) muore SIGKILL durante cache-miss builds e Coolify tiene il container vecchio in piedi senza segnalare errore — il codice non arriva in prod e GH non vede fail.
metadata:
  type: project
---

La VM Vultr che ospita Coolify ha 4 GB di RAM. Builds Docker pesanti (in particolare `apt-get install` di pacchetti con dipendenze grosse — `ffmpeg` su Debian trixie tira giù ~200 pacchetti) saturano la RAM e il kernel SIGKILL-a il processo di build.

**Sintomo subdolo:** Coolify NON marca la build come `failed` in modo evidente; mantiene online il container precedente, l'auto-deploy GitHub vede il push come gestito, e dall'esterno sembra che "il codice non si vede in prod" senza alcun errore visibile.

**Why:** la build muore prima che Coolify riesca a propagare lo stato dell'errore al webhook GitHub; il rollback automatico al container precedente fa sembrare tutto verde mentre in realtà il deploy del nuovo codice è fallito.

**How to apply:**
1. Dopo un push, controlla SEMPRE Coolify dashboard → Deployments della specifica app, non fidarti del checkmark verde GitHub.
2. Se devi installare pacchetti via `apt-get` in un Dockerfile, scegli il pacchetto più piccolo possibile (es. `lame` invece di `ffmpeg` per MP3 encoding mono — 2 MB vs ~500 MB di deps, vedi `backend/Dockerfile` e `backend/app/integrations/speechmatics_tts.py`).
3. Prima di mergiare un Dockerfile che cambia base image o tira deps nuove, considera un test build su VM locale per stimare il picco RAM.
4. Se vedi "deploy non si vede in prod", controlla anche `dmesg` su VM Coolify (`oom-killer`) — non solo i log Coolify.

Collegato a [[reference-devops-pipeline]] e [[reference-coolify-api]].
