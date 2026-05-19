---
name: feedback-production-equals-hackathon
description: Quando si parla di "produzione" in Afterglow, si intende la demo URL dell'hackathon. Post-hackathon è out of scope; può comparire solo nel pitch come "future ideas".
metadata:
  type: feedback
---

In Afterglow "**produzione**" = la demo URL pubblica dell'hackathon (https://app.afterglow.cleversoft.it e https://demo.afterglow.cleversoft.it) durante e per la judging window dell'AI Agent Olympics @ Milan AI Week 2026 (deadline 19 maggio 2026 17:00 CEST). **Tutto ciò che è "post-hackathon" è out of scope.**

**Why:** evitare scope creep travestito da "ma in produzione vera servirà…". Argomenti come "scaling multi-tenant", "audit retention 90 giorni", "Twilio integration vera al posto del MOCK_REGISTRY", "persistent audio volume", "k8s migration" sono **tutti tabù** come motivazione per cambiare codice ora. Sono buone idee, ma valgono **solo** come materiale di pitch ("future work").

**How to apply:**
- Quando una proposta di refactor/feature si giustifica con "ma se andiamo in produzione…" → respingerla o etichettarla come "future idea per il pitch", non come lavoro da fare.
- Quando si valuta se un'astrazione vale la pena: la domanda è "serve per la demo del 19 maggio?", non "scala bene?".
- Quando si scrive doc/memory che cita "produzione": chiarire che si intende lo stack hackathon attuale (Coolify + Vultr Managed Postgres + Vultr Vector Store + 2 Application su VM 95.179.245.107), non un sistema futuro generico.
- Il MOCK_REGISTRY (`backend/app/integrations/mocks/`) resta com'è: fake booking/whatsapp/email/CRM. Sostituirli con SDK veri è **future work**, non hackathon work. In compenso ogni payload mock include `"mock": true` e la UI lo mostra con un badge dedicato — onestà verso i giudici.
- Il `postgres` service nel `docker-compose.yml` è solo dev locale; produzione (= hackathon) gira sempre su Vultr Managed Postgres. Vedi [[reference-devops-pipeline]] per coordinate.

Related: [[project-afterglow-decisions]], [[project-afterglow-hackathon]], [[reference-devops-pipeline]]
