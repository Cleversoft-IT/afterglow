---
name: reference-hackathon-docs
description: Pointer alla knowledge base completa AI Agent Olympics Hackathon (Milan AI Week 2026) nel repo Afterglow.
metadata:
  type: reference
---

Knowledge base completa dell'hackathon (~22.900 parole, 14 file MD):

**Path:** `/home/sepa/cleversoft/hackaton/hackaton-lablab/hackathon-docs/`

| File | Quando aprirlo |
|---|---|
| `01-about.md` | Contesto Milan AI Week, date, format |
| `02-challenge.md` | Tesi sfida, 5 tracks |
| `03-technology-partners.md` | Vultr, Gemini, Kraken, Featherless, Speechmatics — quickstart, modelli, pricing, snippet |
| `04-prizes.md` | Prize pool, eligibility multi-categoria |
| `06-what-to-submit.md` | Checklist submission, vincoli MP4, track tagging |
| `07-judging-criteria.md` | 4 criteri ufficiali |
| `08-hackathon-details.md` | Regole, mentor tags, IP, payout |
| `09-event-schedule.md` | Timeline kick-off + judging window |
| `12-vultr-deep-dive.md` | ⭐ Architettura Vultr completa (Serverless Inference, Vector Store, Coolify, IAM). **Nota:** contiene warning box sulla differenza `VULTR_API_KEY` vs `INFERENCE_API_KEY` aggiunto 2026-05-15 |
| `13-gemini-deep-dive.md` | ⭐ Gemini function calling, grounding, structured output, ADK |
| `14-tutorial-gemini-vultr-document-agent.md` | 🚀 Baseline ufficiale lablab (FastAPI+ADK+Gemini+Vultr+Docker) |

**Source repos / URL pubblici di riferimento:**
- Baseline tutorial: https://github.com/Stephen-Kimoi/gemini-multimodal-document-agent
- Vultr Serverless Inference: https://api.vultrinference.com/v1 (OpenAI-compatible). Il modello usato sul nostro endpoint RAG è `MiniMaxAI/MiniMax-M2.7` (commit `d08912f` ha rimpiazzato il `kimi-k2-instruct` originale).
- Gemini API: https://ai.google.dev/
- Speechmatics Academy: https://github.com/speechmatics/speechmatics-academy
- Submission guidelines: https://lablab.ai/delivering-your-hackathon-solution

**Plan di implementazione:** `.claude/plans/` nel repo. I due plan file storici (`procedi-col-planning-reactive-cocke.md` e `revisione-architettura-single-tenant-app-demo.md`) sono ormai in larga parte eseguiti — vanno letti come storia, non come roadmap. Per lo stato corrente fai riferimento a [[project-afterglow-decisions]] (architettura) e [[reference-devops-pipeline]] (infra).

Aggiornata 2026-05-16.
