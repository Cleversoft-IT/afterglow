# Afterglow

> **What remains after the call.**
>
> Human-first AI dialer that turns booking phone calls into structured data, customer memory, and autonomously executed actions — every action is revertible, every decision is traceable.

Built for the **AI Agent Olympics Hackathon @ Milan AI Week 2026** — targeting Best use of Vultr, Best use of Gemini, and bonus integration with Speechmatics.

## The problem

Small appointment-driven businesses (restaurants, dental clinics, body shops) still take bookings on the phone. Every call carries data that is easily lost: a name, a date, an allergy, a callback request. Post-its and memory don't scale. AI receptionists that talk *instead of* the human kill the relationship.

## The approach

The human keeps talking. The AI listens (opt-in via the **blue phone button**), transcribes with diarization, retrieves customer memory from prior calls, structures the conversation, and **autonomously executes the follow-up actions** (booking, WhatsApp confirmation, CRM update). Every action lands on the post-call screen with a **Revert** button. Every step is logged in a production-shape audit log.

The autonomy is the whole point: the hackathon brief calls for *autonomous decision-making systems*, not copilots. The revert button + audit + confidence/evidence are the trust net that justifies the autonomy.

## Architecture

```
Frontend PWA (Next.js)
       │ POST /api/v1/calls/audio
       ▼
FastAPI (Vultr Coolify) ──► Speechmatics batch (diarization + lang detect + custom dict)
       │
       ├─► Memory Retrieval Agent ──► Vultr /v1/chat/completions/RAG (kimi-k2-instruct)
       │                              └─► Vector Store collection per business
       │
       ├─► Orchestrator (Gemini ADK) ──► sub-agents (function calling, tool-state pattern):
       │                                   • Extraction Agent (Gemini, audio multimodal + transcript)
       │                                   • Classification Agent (Vultr Kimi-K2, intent/sentiment/lang)
       │                                   • Action Planner Agent (Gemini)
       │
       ├─► Action Executor (Python deterministic) ──► mocks + Postgres + audit_log
       │
       └─► Memory Updater (Gemini summarize) ──► Vultr Vector Store push
                                                  └─► customer_memory_chunks (Postgres link)
```

System of record: **Vultr Managed Postgres**. Deploy: **Vultr Cloud Compute + Coolify**. IAM: Service User minimal-privilege + OIDC GitHub Actions.

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full diagram.

## Award alignment

### Best use of Vultr
- `POST /v1/chat/completions/RAG` is the killer endpoint for cross-call customer memory retrieval
- Vector Store collection per business, populated by every completed call
- Kimi-K2 used as a real second model for Classification + Memory Retrieval — not decorative
- Vultr Managed Postgres as the system of record (every call, customer, action, audit row)
- IAM Service User with resource-scoped policy + OIDC GitHub Actions deploy
- Coolify auto-deploy with HTTPS via Traefik + Let's Encrypt

### Best use of Gemini
- Multi-agent architecture on **Google ADK 1.18**
- Function calling with the tool-state pattern (no JSON prompt hacks)
- **Multimodal audio**: raw WAV/MP3 passed as `Part.from_bytes` alongside the Speechmatics transcript, so Gemini grounds on lexicon *and* picks up tone/pauses for sentiment
- Structured Output (Pydantic schema) on the prompt-to-template wizard
- Gemini 3 Flash Preview selectively on the wizard agent (Originality bonus)

### Speechmatics
- `speechmatics-batch` SDK with diarization always on (massive bonus)
- Custom dictionary per template (food, dental, automotive)
- Multilingual demo (IT, EN, ES) with language detection auto
- Sample audio dataset generated with Speechmatics TTS, burning the hackathon credit

## Stack

| Layer | Tech |
|---|---|
| Frontend | Next.js 14 App Router · React 18 · Tailwind · shadcn/ui · next-pwa |
| Backend | Python 3.11 · FastAPI · Google ADK 1.18 · SQLAlchemy 2.0 async · Alembic |
| Speech | Speechmatics batch SDK |
| LLM | Gemini 2.5 Flash (default) · Gemini 3 Flash Preview (template wizard) · Kimi-K2-instruct (Vultr) |
| Storage | Vultr Managed Postgres · Vultr Vector Store |
| Deploy | Docker Compose · Vultr Cloud Compute HP · Coolify |

## Local development

```bash
cp .env.example .env       # fill in API keys
docker compose up -d postgres
cd backend && pip install -r requirements.txt && alembic upgrade head
python -m app.db.seed
uvicorn app.main:app --reload
# in another shell
cd frontend && pnpm install && pnpm dev
```

Open http://localhost:3000 → Dialer / Dashboard.

## Demo

Public URL: _coming soon (Day 1–2)_.

## License

MIT — see [LICENSE](LICENSE).

---

🤖 Built for [AI Agent Olympics @ Milan AI Week 2026](https://lablab.ai/ai-hackathons/milan-ai-week-hackathon).
