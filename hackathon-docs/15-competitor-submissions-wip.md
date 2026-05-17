# Competitor submissions snapshot — WIP

> **Status:** Work-in-progress, snapshot at 2026-05-18 ~00:30 CEST (~41h before deadline).
> **Source:** [lablab.ai live dashboard](https://lablab.ai/ai-hackathons/milan-ai-week-hackathon/live) + per-submission pages + **repo-level deep dive on 5 competitors** (see new section below).
> **Purpose:** situational awareness only — *how do other teams look?* — **not** a checklist
> for our submission and **not** a "best practices" guide. The state changes every hour;
> re-pull before treating any number as fresh.
>
> **What to read across the file:**
> - The dashboard counts are a moving target (54 submissions tonight, ~150–200 likely by deadline).
> - Community vote totals are tiny (top entry has 13 votes) → the leaderboard is not yet a signal of quality, it's a signal of *who shared the link first on Discord*.
> - Many submissions are clearly still rough — boilerplate copy, missing demo link, repos created hours ago. Don't be intimidated by the absolute count.
>
> **Why this matters for Afterglow:**
> - There is **at least one direct competitor on our exact tech stack** (Vultr + Gemini + Speechmatics + Featherless) → see `Patiently`. Worth understanding their angle.
> - Several teams used Veea Lobster Trap as a differentiator on the "enterprise utility" track — we don't, and we should be ready to explain why our angle (post-call memory, not in-flight guardrails) is different.
> - "Multi-agent that debates / argues / has 5 personas" is the dominant pattern (AXIOM, VendorIQ, agentSpam, Boardroom Agents, Diligence, Project Doomsday…). Our differentiator is **temporal memory across calls**, not in-call deliberation — keep that framing crisp.

---

## Live dashboard snapshot (2026-05-17 21:30 CEST)

| Metric | Value |
| --- | --- |
| Participants | 2,281 (+39 today) |
| Teams | 648 (+27 today) |
| **Submissions** | **54** (+26 today) |
| Drafts in progress | 33 (+7 today) |

Most-used tech (top of the list): Gemini AI (42 submissions), AI Studio (33), Gemini 3 Flash (25), Gemini 3 Pro (24), **Vultr (21)**, Anthropic Claude (20), Claude Code (19), AI/ML API (14), ChatGPT (12), Antigravity (12), Vercel (11), Codex (10), **Featherless (9)**, OpenAI (9), **Speechmatics (7)**, LangChain (7), AgentOps (6), Streamlit (5), Lobster Trap (5).

Submissions per track (multiple tracks per submission allowed):
- Agentic Workflows: 58
- Google Track: 45
- Intelligent Reasoning: 44
- Enterprise Utility: 40
- Multimodal Intelligence: 35
- Collaborative Systems: 35
- **Vultr: 26**
- **Featherless AI: 19**
- **Speechmatics: 16**
- Kraken: 9

---

## Repo-level deep dive (2026-05-18 ~00:30 CEST)

Six competitors were selected for a code-level review (cloning the GitHub repo, reading the actual sources, checking commit history). One ranking dimension: **claimed stack vs implemented stack**. Most of the community-vote leaderboard collapses under this lens.

| Repo | Community vote | Verdict vs Afterglow | Bottom line |
| --- | :---: | --- | --- |
| **Patiently** ([0xNoramiya/patiently](https://github.com/0xNoramiya/patiently)) | 0 | **Comparabili** — leggero vantaggio loro su demo polish, leggero vantaggio nostro su Vultr depth | 36+ commit oggi, FastAPI+Next.js, 3 agenti Gemini in `asyncio.gather`, Speechmatics + Featherless reali, PWA bilingue installabile. **Ma Vultr = solo VM** (no Inference, no Vector Store) e nessuna memoria temporale cross-call. Vertical clinico (red-flag triage) molto narrabile. |
| **RevAgent** ([fozagtx/Revagent](https://github.com/fozagtx/Revagent)) | 0 | **Comparabili** — leggero vantaggio nostro per coerenza | Monorepo Bun + Hono + Next 16. Integrazioni vere e cablate: Speechmatics RT, Featherless 4 modelli OSS distinti, Gemini 2.5 Pro, Vultr Object Storage via AWS SDK, Resend. **Ma 1 solo commit** (storia riscritta), scope-spread su 3 prodotti shallow, niente memoria, niente test, smell di generazione AI massiva. |
| **Vela** ([proresin382-cpu/vela](https://github.com/proresin382-cpu/vela)) | 13 (#1) | **Afterglow nettamente più forte** | **Single-file Flask** `app.py` 21KB + 5 dipendenze (`flask, flask-sqlalchemy, werkzeug, openai, markdown`). 1 commit. "Veea Lobster Trap" = `open('/root/lobstertrap/audit.log')`. Una sola `chat.completions.create` per generare un report markdown. Vultr = solo hosting. Demo `tryvela.io` è una landing carina sopra CRUD. |
| **Ghost Board** ([vidwansai66/Ghost-Board](https://github.com/vidwansai66/Ghost-Board)) | 12 (#2) | **Afterglow nettamente più forte** | Next.js shell **senza un solo SDK AI** nel `package.json` (no `openai`, no `@google/generative-ai`, no `langchain`). Le "C-suite AIs" sono label in `mock-data.ts` (252 righe di hard-coded). Tutto l'intelligenza è delegata a workflow n8n privati non versionati. UI cinematic-dashboard ben fatta su Framer Motion + Tailwind 4 — wow visivo che spiega i 12 voti. |
| **Mixer** ([Nadhila-dot/Mixer](https://github.com/Nadhila-dot/Mixer)) | 4 (#4) | **Afterglow nettamente più forte** | Rust reale (Monoio + httparse + rusqlite + rust-embed), single-binary che inglobba il frontend. **Ma il "sandbox Linux" promesso è 2 chiamate `Command::new` sull'host VM** — niente Docker/Firecracker/nsjail. "NVIDIA" nello stack è l'hardware Vultr sotto. Install via startup-script Vultr copia-incollato — fragile. |
| **Vultr Atlas** (org `qubitpage`) | 3 (#5) | **Non valutabile** — no repo pubblico | Nessun repo nell'org [qubitpage](https://github.com/qubitpage) corrisponde ad "Atlas". I giudici tecnici non vedono codice; valuteranno solo la demo a `atlas.qubitpage.com`. Probabilmente il più rifinito visivamente sul track Vultr — rischio reale per il Vultr Award perché Vultr ama le demo "letteralmente brandizzate". |

### Take-away dai deep dive

1. **La leaderboard community è ingannevole.** I due top spot (Vela, Ghost Board, 25 voti combinati) sono UI shell con codice tecnico minimo. La barriera per entrare in top-10 è bassa: serve solo postare il link su Discord.
2. **I due competitor seri sul nostro stack quartetto (Patiently, RevAgent) non hanno la memoria cross-call.** Le loro pipeline sono one-shot per sessione. **Questa è la nostra trincea da difendere a tutti i costi.**
3. **Vultr depth è oggettivamente nostro.** Patiently/Mixer/Vela usano Vultr solo come hosting. RevAgent usa Vultr Object Storage via AWS SDK. Vultr Atlas mostra l'API Vultr ma non ha sorgente. **Nessuno usa Vultr Inference + Vector Store nativi come noi.** Pitch slide diretta: "We use Vultr like a partner, not like a VPS."
4. **Featherless è il nostro buco da turare.** RevAgent ha 4 modelli OSS differenziati per task. Noi siamo parziali. Vale la pena cablare uno-due use-case Featherless visibili (anche solo per il bilingual chunk EN-summarizer) prima del deadline per non perdere il prize per default.
5. **Speechmatics è contendibile.** Patiently e RevAgent hanno Speechmatics live in-call con effetto wow. Noi siamo post-call. Difendibile dicendo "usiamo Speechmatics per generare la materia prima della memoria persistente" — ma il Speechmatics Award rischia di andare a chi mostra il transcript scrollare a schermo.

### Cosa nessun competitor nel campione fa (e noi sì)

1. Memoria temporale cross-call con Vultr Vector Store (chunk bilingue native+EN).
2. Audit log con `input_tokens`/`output_tokens` per step.
3. Action executor con `jsonschema.validate` + `evidence_required=True` + badge "Simulated" automatico per `integration_kind="mock_external"`.
4. Pipeline post-call a 3 stadi *strutturalmente separati* (Gemini structured-output → Google ADK typed tool calls → executor) con fail-fast e zero stub deterministico.

Sono i 4 punti da mettere al centro della narrativa pitch.

---

## Direct-competitor watchlist (read first)

Submissions that overlap meaningfully with Afterglow's tech stack *or* product angle. These are the ones worth re-checking close to the deadline.

### 🔴 Patiently — closest stack overlap
- **URL:** https://lablab.ai/ai-hackathons/milan-ai-week-hackathon/muhammad-rifqi-haikal/patiently
- **Repo:** https://github.com/0xNoramiya/patiently
- **Live demo:** https://patiently.kudaliar.id/
- **Stack:** Vultr + Gemini + **Speechmatics** + **Featherless** (same four as us)
- **Tracks:** Vultr, Speechmatics, Google, Featherless AI, Agentic Workflows, Collaborative Systems, Intelligent Reasoning, Multimodal, Enterprise Utility (basically every applicable track — kitchen-sink submission)
- **What it does:** clinic waiting-room copilot. Patient scans a QR on arrival → bilingual voice + photo intake from the patient's phone. Three Gemini agents in parallel: Intake (OPQRST history extraction), Triage (continuous red-flag screening for cardiac/stroke/sepsis with live priority score), Summarizer (SOAP note draft on Featherless). Speechmatics transcribes the in-room consultation. Clinician dashboard ties live queue + vitals + drug-interaction checks + printable prescriptions.
- **Why it matters for us:** *exactly* our recipe — voice intake, multi-agent post-processing, Vultr inference, Speechmatics, bilingual. Different vertical (clinic intake vs. SMB phone calls) and different temporal angle (real-time triage during a wait vs. memory across future calls). Team is one person (a medical doctor) which gives them a credibility angle we can't match on healthcare.
- **Quality read:** the description is well-structured and clinically literate. The live demo URL works (kudaliar.id is the doctor's personal domain). Created **today** (2026-05-17), so the implementation depth is unknown — could be impressive, could be hand-wavy.
- **Differentiator angle for our pitch:** Patiently is *in-session* assistance for a queued waiting room; Afterglow is *across-session* memory for whoever picks up the phone next. Same partner toolbox, orthogonal problem.

### 🟡 RevAgent
- **URL:** https://lablab.ai/ai-hackathons/milan-ai-week-hackathon/kaizenv2/revagent
- **Stack:** Speechmatics + Vultr + Gemini + **Featherless** (same four as us)
- **Tracks:** Featherless AI, Google, Speechmatics, Vultr
- **What it does:** three-agent sales-coaching tool. Pitch Surgeon (rewrites weakest slide of a deck, generates 30-sec narrated pitch with Gemini 3 Pro), Discovery Co-Pilot (live call diarization with Speechmatics RT + Gemini Flash, JTBD switch chart and mid-call nudges), Win-Loss Auditor (uses 4 specialized OSS models on Featherless to produce a PDF debrief).
- **Why it matters for us:** also uses Speechmatics RT for live call transcription + Gemini, but as a **live in-call coach**, not as post-call memory. Their "Win-Loss Auditor" is the closest piece to our analyzer — except it's one-shot, no memory continuity. **0 community votes**, no demo URL visible.

### 🟡 VoiceBroker AI
- **URL:** https://lablab.ai/ai-hackathons/milan-ai-week-hackathon/team-believer/voicebroker-ai-autonomous-voice-trading-agent
- **Stack:** Speechmatics + Gemini + Kraken + Supabase + AI Studio + Codex + Mistral AI
- **Tracks:** Featherless AI, Google, Vultr, Speechmatics, Agentic Workflows, Enterprise Utility, Intelligent Reasoning
- **What it does:** voice-driven simulated trading desk. Speechmatics RT → Gemini intent parsing → Kraken market data + Supabase portfolio.
- **Why it matters for us:** confirms the "Speechmatics RT + Gemini intent extraction" pattern is well-trodden tonight. Vertical is totally different (crypto trading) so not a direct competitor, but a benchmark for how clean the voice-to-action loop looks.

### 🟡 Mythos.OS
- **URL:** https://lablab.ai/ai-hackathons/milan-ai-week-hackathon/kim-seok-jin/mythosos
- **Stack:** Gemini 3 Flash + Gemini 3 Pro + **Speechmatics Flow** + rest API + Streamlit
- **Tracks:** Speechmatics, Google, Agentic Workflows, Collaborative Systems, Enterprise Utility, Multimodal
- **What it does:** stateful simulation sandbox where a multi-agent swarm (Universe Generator + others) collaborates with the user via Speechmatics real-time voice dictation to build "laws" and a living narrative universe.
- **Why it matters for us:** uses **Speechmatics Flow** specifically (the streaming product) — worth checking their submission video to see what Flow looks like in production. Otherwise: completely different product (fiction/worldbuilding playground).

### 🟢 Vultr Atlas (top-5 community vote)
- **URL:** https://lablab.ai/ai-hackathons/milan-ai-week-hackathon/cybertron/vultr-atlas
- **Votes:** 3
- **Stack:** Vultr + AI/ML API + Claude Code + Gemini 3 Pro + NVIDIA
- **Tracks:** Vultr, Featherless AI, Google, Speechmatics, Kraken, plus most general tracks
- **What it does:** 3D rotating globe showing every Vultr region with live instance/service/status data from `/v2` and Vultr Status. Right-rail Gemini 2.0 Flash copilot that can "fly to Frankfurt, compare two plans, find the cheapest GPU in Europe."
- **Why it matters for us:** **most polished Vultr-track demo right now** (top-5 by community vote). It's a Vultr admin UI more than an autonomous agent — judges on the Vultr track are clearly rewarding "looks great + lives on Vultr + uses the Vultr API meaningfully." Our Vultr usage is inference + vector store, not the management API, so we're not competing on that axis — but we should make sure the Vultr usage is *visible* in our pitch.

---

## Community-vote leaderboard (top 10)

Vote counts are tiny — the highest score is **13**. Treat the leaderboard as "who told their Discord first," not as a quality ranking.

| # | Submission | Team | Votes | Notes |
| -- | --- | --- | --- | --- |
| 1 | [Vela — AI Agency Command Center](https://lablab.ai/ai-hackathons/milan-ai-week-hackathon/vela/vela-ai-agency-command-center) | Vela | 13 | Flask + Gemini 2.5 Flash + Lobster Trap on Vultr. Webhook monitor for *other* people's deployed agents (n8n, Vapi, Voiceflow, Make). Live at `tryvela.io`. Solo dev (Ali Mehdi). Tracks: Enterprise Utility, Agentic Workflows, Vultr. Repo: `proresin382-cpu/vela`. |
| 2 | [GHOST BOARD](https://lablab.ai/ai-hackathons/milan-ai-week-hackathon/neural-forge/ghost-board-autonomous-ai-command-center) | Neural Forge | 12 | Multi-agent "C-suite simulator" (CEO/CTO/Security/Ops/HR/Marketing AIs) coordinating during simulated cyberattacks. Stack: Gemini + OpenAI + DALL-E-2 + n8n + Vercel + Antigravity. Heavy on theatre, light on the operational use case. |
| 3 | [Execution Enforcer](https://lablab.ai/ai-hackathons/milan-ai-week-hackathon/apex-media/execution-enforcer-the-autonomous-protocol-agent) | Apex media | 6 | Single-purpose: Gemini 3 Flash agent that audits cloud infra configs against protocol policies. Clean scope. |
| 4 | [Mixer](https://lablab.ai/ai-hackathons/milan-ai-week-hackathon/calabasas/mixer-ai-that-builds-for-the-enterprise) | Calabasas | 4 | Agent with a sandboxed Linux workspace it can write into & stream back live. On Vultr + NVIDIA. "Devin-clone" angle. |
| 5 | [Vultr Atlas](https://lablab.ai/ai-hackathons/milan-ai-week-hackathon/cybertron/vultr-atlas) | CYBERTRON | 3 | See above (direct-competitor watchlist). |
| 6 | [Evia AI](https://lablab.ai/ai-hackathons/milan-ai-week-hackathon/evia-ai/evia-ai-personalized-luxury-jewelry-with-ai) | Evia AI | 3 | AI agent that designs jewelry live with the customer then routes to manufacturing. Only "AI Studio" tag — implementation looks thin. |
| 7 | [ReelSights AI](https://lablab.ai/ai-hackathons/milan-ai-week-hackathon/reelsights-ai/reelsights-ai-autonomous-revenue-os) | ReelSights AI | 3 | "Sales clones" fleet for autonomous prospecting. AI/ML API + AI Studio + AWS. Buzzword-dense copy. |
| 8 | [Psychotherapy Orientation Agent](https://lablab.ai/ai-hackathons/milan-ai-week-hackathon/vector-minds/psychotherapy-orientation-agent) | Vector Minds | 2 | Structured conversational profiler that matches users to a psychotherapy orientation. Gemini 3 Flash + LangChain + Streamlit. |
| 9 | [agentSpam](https://lablab.ai/ai-hackathons/milan-ai-week-hackathon/unfixed-chunk/agentspam) | Unfixed Chunk | 2 | Spawns up to 90 specialist agents in a recursive tree, then two debate across 3 rounds + a Judge — spoken aloud. Only "Claude Code" tagged. Comedy/joke entry vibes. |
| 10 | [AcademiaGenie](https://lablab.ai/ai-hackathons/milan-ai-week-hackathon/fastend-team/academiagenie-ai-graduate-admission-assistant) | FastEnd Team | 2 | CV → matched professors globally + cold-email drafts + roadmap to fill profile gaps. AI Studio + Gemini Flash. |

---

## Full submission list (54)

Brief one-liners for situational awareness. Submissions are grouped by **dominant pattern** to make patterns visible — not by ranking.

### Multi-agent debate / boardroom (the dominant cliché tonight)
- **AXIOM — The Business Brain That Improves Itself** (The Orchestrators) — 5 agents argue, output a binding decision in <30s, self-improve every run. Claude Code + Anthropic Claude + Gemini + LangChain + Vultr.
- **VendorIQ** (Devil Eaters) — 13 specialized agents debate vendor proposals across multiple rounds, evidence-based recommendation.
- **Boardroom Agents** (merolav) — Researcher/Analyst/Red Team/Synthesizer/Verifier/Orchestrator for M&A due diligence. AI Studio + Claude Code + ElevenLabs.
- **agentSpam** (Unfixed Chunk) — see top 10.
- **SINTHER** (doracake) — 6 named agents (Chanky/Vizi/Kavi/Sri/Jupi/Mars) for decision intelligence.
- **NEXUS — Enterprise AI Command Center** (Agentic developers) — 6 agents (Scout/Analyst/Strategist/Communicator/Guardian/Orchestrator) + Lobster Trap.
- **OlympusAI** (Devidivya146) — "elite multi-agent platform that plans, reasons, collaborates, executes." Generic copy.
- **Project Doomsday** (Shinsengumi) — adversarial Bear/Bull/Judge stress-testing stock valuations against Black Swan events.
- **Sentinel: Autonomous Enterprise Situation Room** (Loosely_Coupled) — 4 Gemini agents pipeline: anomaly → root cause → escalation draft → leadership brief.

### Financial / trading / equity
- **Diligence — Adversarial AI Equity Research** (enso) — bull/bear/reconciler agents read 10-K/10-Q/earnings calls, cite to primary sources. **Stack: AI/ML API + Anthropic Claude + Claude Code + Gemini + Qwen3 + Speechmatics + Vultr + Featherless** — biggest stack overlap with us after Patiently. Submission page currently rendering as 404 (page hydration bug on lablab).
- **VoiceBroker AI** (Team believer) — see direct-competitor watchlist.
- **AutoResearch Strategic Stock Orchestration** (Quant Hunters) — Claude iteratively self-improves a trading strategy, kept only if held-out Sharpe improves. Anthropic Claude + Antigravity + Vercel.
- **Project Doomsday** (Shinsengumi) — see above.
- **VORTEX | Multi-Agent Cross-Asset Intelligence** (MAITS-VORTEX) — multi-agent trading on Kraken (xStocks + crypto). AWS + Gemini 3 Pro + Replit.
- **InvoiceLeak** (InvoiceOps AI) — autonomous finance audit agent (duplicate bills, overcharged seats, unused subs). Gemini + Codex + ChatGPT.

### Sales / GTM / agencies
- **Vela — AI Agency Command Center** (Vela) — see top 10.
- **Apex.** (apex) — autonomous multi-agent sales pipeline for US markets.
- **ReelSights AI** (ReelSights AI) — see top 10.
- **RevAgent** (Kaizenv2) — see direct-competitor watchlist.

### Voice / dictation / patient-facing
- **Patiently** (Muhammad Rifqi Haikal) — see direct-competitor watchlist.
- **Mythos.OS** (Kim Seok Jin) — see direct-competitor watchlist.
- **AURA (Adaptive Unified Response Agent)** (Dexter AI) — generic copy, unclear vertical.

### Healthcare / public sector
- **TELMED AI DOCTOR** (Pegasus).
- **Pusdatin AI Agents: Public Health Intelligence** (Pusdatin Dinkes DKI Jakarta) — public health data workflow with redaction + risk indicators.
- **Culltron CivicOps AI** (Culltron CivicOps AI) — civic incident intake/routing.
- **CityMind Crisis Command Center** (asystqa) — crisis-room dashboard.

### Procurement / compliance / supply chain
- **TenderMind AI** (TechNova) — sovereign procurement platform for EU market. Qwen + LangGraph + **Featherless** + MongoDB + Next.js.
- **TariffGuard AI** (TariffGuard AI) — multi-agent tariff classification with claim of 94%+ accuracy. CrewAI + Gemini + Antigravity.
- **SmartCharter** (Vultron) — legal document intelligence. Gemini 3 Pro + Vultr.
- **Execution Enforcer** (Apex media) — see top 10.

### Dev tools / agent runtimes
- **Mixer** (Calabasas) — see top 10.
- **Ghost Chimera** (INAN) — natural-language → task compiler with resource-control layer. AI Studio + Claude Code + Anthropic Claude.
- **NeYO Terminal CLI** (Dina) — agentic CLI for ERP/CRM + full-stack app generation. Gemini 3 Pro + Flash.
- **Privai — One Agent, Three Workspaces** (Pheonix) — desktop AI workspace (Coding/Learning/Business). Gemini + Anthropic Claude.
- **Lobasters: Enterprise Agent Proving Ground** (lobasters) — adversarial testing + automated grading harness for enterprise agents. AI/ML API + AgentOps + Antigravity.
- **GIT ArcheType Platform** (Ajaykumar Yavagal) — GitHub repos as living systems, contributor archetypes, collaboration dashboards.
- **KintsugiOps AI: Green Software Repair** (fovea) — autonomous code repair targeting energy efficiency.
- **Memory Core: Role-Aware Memory for Agent Teams** (Memory Core) — *interesting overlap with our memory angle but for multi-agent teams, not for human-facing CRMs.*
- **XIO ProofOps Agent** (xio-ai) — turns decks/contracts/policies/transcripts into structured proofs.

### Education
- **EduNex** (The Innovators) — autonomous AI tutor K-12 + college. Gemini 3 Pro + Anthropic Claude.
- **QuestXP** (Parth Patidar) — YouTube playlists → structured gamified curricula.
- **AI DSA Coach** (O(1) Innovations) — multi-agent DSA mentor with Web3 token/NFT rewards. AgentOps + AI Studio + Antigravity.
- **AcademiaGenie** (FastEnd Team) — see top 10.
- **bilimhack / BilimForAll** (Aftereffects) — "Duolingo for professions" with voice roleplays + context caching.

### "Operations cockpit" / dashboards
- **GHOST BOARD** (Neural Forge) — see top 10.
- **Vultr Atlas** (CYBERTRON) — see direct-competitor watchlist.
- **Manthan** (Miny Labs) — agentic business analyst, click-to-audit answers. Vultr only.
- **Themis — AI Advisor for Business** (RITeam) — 3-min closed-option chat → typed/costed/carbon-rated AI adoption plan with EU-style A-E rating. Anthropic + Gemini + Vultr.
- **InsightForge** (TeamMaet) — competitor research → boardroom-ready SWOT. Streamlit + Gemini.
- **Friday - Autonomous Cognitive AI OS** (nearx) — persistent memory + multi-agent orchestration + voice + 30+ agents. AI/ML API + Gemini.
- **AI Daily Life Optimizer** (Oreo) — Streamlit dashboard: focus detection + activity forecast + weather + Google Fit.

### Security / honeypot / guardrails
- **MIRAGE — AI Honeypot Defense for LLM Agents** (the best team ever) — silent switch to honeypot feeding attackers fake data. Redis + Lobster Trap + Gemini + OpenAI.
- **AdAudit: Guarded AI Media Buyer** (adaudit) — guarded media-buying agent with research loop.

### Misc / niche
- **Evia AI** (Evia AI) — see top 10. Jewelry concierge.
- **Psychotherapy Orientation Agent** (Vector Minds) — see top 10.
- **SimuChem_Enterprise Agentic R&D Simulation** (qu4ntum_quest) — computational chemistry → validated enterprise strategy.
- **The Trust Layer for AI Claims Resolution** (Duan and AI buddy) — 7 Gemini specialist agents resolve e-commerce damage claims in <10 min.
- **VEIN — Autonomous Market Intelligence Agent** (Vein).

---

## Quick takeaways for our pitch (subjective, May 17 evening)

1. **"Multi-agent debate" is fully saturated** — at least 9 submissions lean on it as their core mechanic. A pitch that opens with "5 agents argue…" sounds generic now. Our framing should emphasize the *timeline* (memory across past calls feeding the next one) rather than the *team* (how many agents talk to each other in one call).
2. **There's a Vultr+Gemini+Speechmatics+Featherless quartet that other teams are also playing** — at least Patiently, RevAgent, Diligence/enso. We are not the only ones who'll show all four logos on the same slide. Make sure our usage of each is *actually integrated* (we already are — voice via Speechmatics in the simulator, Gemini for analysis, Vultr for inference + vector store, Featherless if/when we wire it).
3. **The top community-vote spots have small absolute counts (≤13 votes)**. Sharing our submission early on the lablab Discord could push us into the top-N visibility band cheaply. Worth a 30-min "post-link" pass once submitted.
4. **No competitor is doing "vertical SMB phone-line memory"** yet. The closest adjacent vertical (Patiently) is healthcare waiting room. Our restaurant/dentist/bodyshop demo presets remain distinctive.
5. **The Lobster Trap angle is being aggressively played** (Vela, Mirage, NEXUS, Ghost Board reference it). We don't, and we shouldn't pivot to it 46h before deadline. If a judge asks, the answer is: "Our threat model is not in-call prompt injection — it's the operator pasting a fake summary. Audit log + evidence-required actions cover that."

---

## How to refresh this file

```bash
# open the live page
xdg-open https://lablab.ai/ai-hackathons/milan-ai-week-hackathon/live
# or just visit it in a chrome session and re-pull the submissions tab
```

When refreshing:
- Bump the timestamp at the top.
- Re-pull the dashboard counts (participants / teams / submissions / drafts).
- Diff the top-10 community vote list (link slugs).
- Check the **direct-competitor watchlist** in particular — that's the bit that decays fastest.
- Append new direct-competitor entries to the watchlist; do not bother rewriting the full 54-row list each time (just append new slugs at the bottom).
