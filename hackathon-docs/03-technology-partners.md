# Technology Partners & Workshops — AI Agent Olympics Hackathon

> Fonte principale: https://lablab.ai/ai-hackathons/milan-ai-week-hackathon
> Documentazione arricchita: vedi link sorgente in fondo a ogni sezione.

I 5 partner tecnologici dell'hackathon offrono **crediti / accesso gratuito** e ciascuno propone una **sfida specifica** con premi dedicati (vedi `04-prizes.md`). Le sfide sono indipendenti: un progetto può potenzialmente concorrere su più tracce.

---

## ☁️ 1. Vultr — Web-Based Enterprise Agent

Vultr fornisce **l'infrastruttura backend** dell'hackathon. I team che fanno **deploy su Vultr** e lo usano come **system of record** per planning, coordination ed esecuzione sono eleggibili per i Vultr Awards.

### La sfida

**Build a Web-Based Enterprise Agent Deployed on Vultr**

Progettare un agente AI **web-based** per workflow enterprise reali su:

- Operations
- Sales / Marketing
- Customer Support
- HR
- e qualsiasi altro dominio business

I progetti devono dimostrare:

- **Multi-step agentic workflows**
- **Realistic future-of-work use cases**
- **Production-style web application**

### Cosa deve consegnare ogni team

- ✅ **GitHub repository** con setup e documentazione
- ✅ **Vultr VM backend deployment**
- ✅ **Public demo URL**
- ✅ **Recorded demo video**
- ✅ Spiegazione chiara di architettura e use case

### Stack tecnologico ammesso

- Qualsiasi linguaggio / framework
- LLM **open-source** e workflow di **RAG (retrieval-augmented generation)**
- **Vultr Serverless Inference** disponibile per progetti eleggibili
- ⚠️ **Vultr GPUs NON disponibili** per questo evento

### Risorse Vultr

#### Product overview

L'ecosistema Vultr per un AI agent in hackathon include:

| Categoria | Servizi rilevanti |
|---|---|
| **Compute** | VX1 Cloud Compute, Optimized Cloud Compute, Cloud Compute, Bare Metal, Clusters (no GPU per l'hackathon) |
| **Storage** | Block Storage, Object Storage (S3-compatibile), File System, Storage Gateway |
| **Kubernetes** | VKE — provisioning e management |
| **Serverless Inference** | Endpoint LLM gestiti, no ops |
| **Vector Store** | DB gestito per embedding (RAG / memoria agenti) |
| **Container Registry** | Registry, repo, Docker Hub Proxy |
| **Managed DB** | MySQL, PostgreSQL, **Valkey** (Redis-compatible), Apache Kafka |
| **Network** | BGP, DNS, Firewall, VPC 2.0, Reserved IP |
| **Orchestration** | Backup, ISO, Snapshot, Startup Scripts |

#### Platform / IAM

- **Service User** dedicato per credenziali API-only (machine-to-machine) → ideale per dare a un agente accesso minimal-privilege
- IAM con Organizations, Policies (allow/deny), Groups, Roles assignable/assumable, **OIDC** per federated auth
- Best practices di sicurezza per Instances, VKE, Object Storage, Block/File Storage

#### Reference (CLI + Terraform)

- **Vultr CLI:** 30+ sotto-comandi per Account, Apps, Backups, Bare Metal, Billing, Block Storage, ecc.
- **Terraform Provider:** Resources (provisioning dichiarativo) + Data Sources

#### Serverless Inference — l'asset chiave

| Feature | Note |
|---|---|
| Endpoint base | `https://api.vultrinference.com/v1/chat/completions` |
| Auth | `Authorization: Bearer $VULTR_INFERENCE_API_KEY` |
| Modello citato | **`kimi-k2-instruct`** (supporta **tool calling** / function calling) |
| Vector Store | DB gestito per embedding — abilita RAG |

##### Tool calling minimo (cURL)

```bash
curl --location "https://api.vultrinference.com/v1/chat/completions" \
  --header "Content-Type: application/json" \
  --header "Authorization: Bearer ${VULTR_INFERENCE_API_KEY}" \
  --data '{
    "model": "kimi-k2-instruct",
    "messages": [{"role":"user","content":"..."}],
    "tools": [{
      "type":"function",
      "function":{"name":"get_horoscope","description":"...","parameters":{...}}
    }],
    "tool_choice":"auto"
  }'
```

Il flusso è a 2 chiamate: il modello risponde `finish_reason: "tool_calls"` con `name` + `arguments` JSON; il client esegue la funzione e rispedisce un messaggio `role: "tool"` con `tool_call_id` + `content` → il modello produce la risposta finale.

Esempio Python ufficiale: `vultr-marketing/code-samples` → `tool-calling-weather.py`.

#### Deployment con Coolify (Marketplace app)

[How to Deploy Claude Code Projects on Vultr Using Coolify](https://docs.vultr.com/how-to-deploy-claude-code-projects-on-vultr-using-coolify) — guida completa step-by-step:

- **Prerequisiti:** Anthropic API key, GitHub, istanza Marketplace Coolify (min. 2 GB RAM / 1 CPU), dominio puntato all'IP
- **Flusso:** Claude Code genera app full-stack con `Dockerfile` → `git push` → Coolify Sources → Add Project → Deploy → routing Traefik + TLS Let's Encrypt automatici (3-5 min)
- **CI/CD:** webhook GitHub → auto-deploy on push
- **DB aggiuntivo:** Add Resource → PostgreSQL → connection string in `DATABASE_URL`

### Workshops Vultr (registrati, on-demand)

Speaker: **Sanskriti Harmukh** — **Associate Developer Relations Advocate**

- 🎓 **Tech talk** — *Vultr Serverless Inference*
- 🎓 **Workshop** — *Supabase*
- 🎓 **Workshop** — *Coolify*

> 💡 *"Se costruisci con Vultr, questi tre sono must-watch"* — confermato da Joan al kick-off.

### 📘 Link sorgente

- Product Documentation — https://docs.vultr.com/products
- Platform Documentation — https://docs.vultr.com/platform
- Support Documentation — https://docs.vultr.com/support
- Reference Documentation — https://docs.vultr.com/reference
- Vultr Serverless Inference Documentation — https://docs.vultr.com/products/serverless
- How to Deploy Claude Code Projects on Vultr Using Coolify — https://docs.vultr.com/how-to-deploy-claude-code-projects-on-vultr-using-coolify
- How to Use Tool Calling with Vultr Serverless Inference — https://docs.vultr.com/how-to-use-tool-calling-with-vultr-serverless-inference
- Vultr API Endpoints — https://www.vultr.com/api/

### ⚠️ Note credits — CHIARIMENTO Q&A

> *"For Vultr we don't have extra credits. But maybe Steve you could explain how to deploy on Vultr without the extra credits."* — Sophia al Q&A live

**Significa:**

- ❌ **NESSUN coupon code dedicato all'hackathon** per Vultr (a differenza di Featherless e Speechmatics)
- ✅ **Usa il free trial standard di Vultr: $250 credit per 30 giorni** (newly registered accounts)
- ✅ Tutorial dedicato condiviso da Steve (lablab DevRel) su Discord
- ✅ I credit Vultr citati nei Prizes (es. $1.000 ai vincitori) sono **post-evento**, non disponibili in fase di build
- 📩 Per continuare oltre i credit → linkare un metodo di pagamento valido

---

## 🧠 2. Google — Gemini & Google AI Studio (Google DeepMind)

**Gemini** è la famiglia di modelli AI multimodali di **Google DeepMind** (testo, immagini, codice, video, audio). **Google AI Studio** è l'ambiente browser-based per prototipare con Gemini prima di passare alla Gemini API in produzione.

> 🎙️ Quote dal kick-off (Amit Vadi, Head of Community for Google DeepMind Developer Experience):
> *"Gemini 3 shifted to an era of action. As builders, we're the first generation that can create tools for a world where anyone can build anything. There's never been a better time to be a builder. Get started at ai.studio/build."*

### La sfida

**Build intelligent agents or applications using Gemini models and Google AI Studio.**

Il progetto deve:

- Usare Gemini via **Google AI Studio** o **Gemini API** per reasoning, chat, multimodal understanding
- Implementare workflow agentici / automation che rispondano a input, dati, contesto
- Dimostrare valore pratico tramite prototipo o sistema funzionante

### Modelli raccomandati

| Modello | Posizionamento |
|---|---|
| **Gemini Flash** | Speed + bassa latenza — real-time, chat, responsive agents |
| **Gemini Pro** | Reasoning avanzato — multi-step workflows, decision-making, enterprise |

### Famiglia modelli aggiornata (ai.google.dev/gemini-api/docs/models)

- **Gemini 3.1 Pro** (anteprima) — reasoning avanzato, agentic, vibe coding
- **Gemini 3 Flash** (anteprima) — "Frontier performance a frazione di costo"
- **Gemini 3.1 Flash-Lite** (stable + preview) — efficienza, alto volume
- **Gemini 3.1 Flash Live / Flash TTS** — voce e dialogo real-time
- **Gemini 2.5 Pro / Flash / Flash-Lite** — generazione precedente, equilibrio prezzo/performance
- **Nano Banana 2 / Pro** — generazione/editing immagini
- **Veo 3.1** — video · **Imagen 4** — immagini · **Lyria 3** — musica
- **Gemini Embedding 2** · **Gemini Robotics-ER 1.6** · **Computer Use** · **Deep Research**
- ⚠️ **Gemini 2.0 Flash / Flash-Lite** deprecati — switch off **1 giugno 2026**

### Esempi di use case (dalla pagina hackathon)

- AI copiloti e assistenti enterprise
- Agentic commerce e workflow automation
- App multimodali con text/image/audio/video understanding
- Research, analisi, decision-support
- Customer support e conversational AI

### Accesso & pricing

#### Free tier

| Risorsa | Cosa offre |
|---|---|
| **Google AI Studio** | Gratis in tutte le regioni (anche per Gemini 3.1 Pro) — prototipazione senza API key |
| **Gemini API free tier** | Allowance mensile gratuita di token per text & multimodal IO. Free per `gemini-3-flash-preview` e `gemini-3.1-flash-lite`. Pro non disponibile in free su API |
| **Google Cloud free tier** | **$300 di credit** per 90 giorni per nuovi account |

#### Paid tier (per 1M token, alcuni esempi chiave)

| Modello | Input | Output |
|---|---|---|
| **Gemini 3.1 Flash-Lite** | $0.25 (text/img/video) · $0.50 (audio) | $1.50 |
| **Gemini 3 Flash** | $0.50 | $3 |
| **Gemini 3.1 Pro** (≤200K) | $2 | $12 |
| **Gemini 3.1 Pro** (>200K) | $4 | $18 |
| **Imagen 4** | — | $0.02 Fast / $0.04 Std / $0.06 Ultra per immagine |
| **Veo 3.1** | — | $0.40/sec std, $0.60/sec 4K |

> **Batch API:** sconto 50%.
> **Tool pricing:** Google Search 500 RPD free (Flash/Flash-Lite); Gemini 3: 5000 prompt/mese gratis poi $14 / 1000 query.

#### Rate limits (4 tier)

| Tier | Requisito | Spend cap |
|---|---|---|
| **Free** | Progetto attivo o trial | — |
| **Tier 1** | Account fatturazione attivo | $250 |
| **Tier 2** | $100+ spesi + 3gg dal primo pagamento | $2.000 |
| **Tier 3** | $1.000+ spesi + 30gg | $20-100K+ |

> Limiti per-model esposti in AI Studio. **Batch:** max 100 richieste concorrenti, file input 2 GB, storage 20 GB.

### Quickstart

1. Visit https://ai.google.dev/
2. Crea API key in **Google AI Studio** (gratis)
3. Installa l'SDK Google GenAI
4. Prima richiesta — due opzioni:
   - **Interactions API** (raccomandata): supporta tool use multi-step, orchestrazione, reasoning, nuove capability agentiche
   - **`generateContent`** (stateless, semplice)
5. Variabile `GEMINI_API_KEY` rilevata automaticamente

### Novità API Gemini 3

- `thinking_level`: minimal / low / medium / high
- `media_resolution`: low / medium / high / ultra_high
- Temperatura **raccomandata = 1.0**
- **Thought signatures** per mantenere contesto di reasoning tra chiamate
- **Tool integrati:** Google Search, URL context, File Search, Maps, Code Execution

### Google Cloud free tier (oltre i $300 credit)

20+ prodotti always-free, rilevanti per hackathon:

- Compute Engine: 1 istanza e2-micro/mese
- Cloud Run: 2M richieste/mese
- BigQuery: 1 TB query/mese
- Vision AI: 1000 unità/mese
- Speech-to-Text: 60 min/mese
- Firestore: 1 GB · Pub/Sub: 10 GB

> **Per startup:** Google for Startups Cloud Program fino a **$200K** in credit ($350K per AI startup).

### 📘 Link sorgente

- Gemini API home — https://ai.google.dev/
- Quickstart Guide — https://ai.google.dev/gemini-api/docs/quickstart
- Gemini API models — https://ai.google.dev/gemini-api/docs/models
- Gemini 3 Developer Guide — https://ai.google.dev/gemini-api/docs/gemini-3
- Pricing — https://ai.google.dev/pricing
- Rate limits — https://ai.google.dev/gemini-api/docs/rate-limits
- Google AI Studio Build — https://ai.studio/build
- Google Cloud free tier — https://cloud.google.com/free
- Antigravity — https://antigravity.dev/ *(al momento della consultazione mostra solo la pagina default nginx — verificare dominio corretto)*

### ⚠️ Note credits

- Dopo l'expiration del free credit, l'uso continuato richiede billing abilitato su Google Cloud
- Addebiti solo se si sceglie di continuare con servizi paid

---

## 🥷 3. Kraken — AI Trading su xStocks via Kraken CLI

**Kraken** è uno dei crypto exchange più consolidati al mondo (**since 2011**). Per questo hackathon, partecipano con due prodotti:

> 🎙️ Quote dal kick-off (Lorenzo Capone, Head of Regional Growth — Southern Europe):
> *"If you were part of our first challenge with Lab Lab, you already know the vibe. We saw people building full YouTube channels around the AI agents — that blew our mind. You handled crypto splendidly last time. Now, let's see what you can do with traditional assets."*

- **Kraken CLI** — la prima CLI AI-native per il trading di crypto, azioni, forex e derivati su Kraken. Gestisce autenticazione, rate limiting, order management → il team si concentra sulla **strategia dell'agente**
- **xStocks** — azioni ed ETF statunitensi tokenizzati 1:1, tradeable 24/7 on-chain

### La sfida

**Build an autonomous AI agent that trades xStocks using the Kraken CLI as its execution layer.**

L'agente deve:

- Analizzare segnali di mercato
- Formulare una strategia
- Eseguire trade **programmaticamente senza intervento manuale**

Esempi di use case suggeriti:

- Momentum-based stock picker
- Portfolio rebalancer
- Event-driven trading system

### Scoring — due categorie indipendenti

#### 1️⃣ Trading Performance (PnL)

| Step | Dettagli |
|---|---|
| **Submission** | Read-only Kraken API key linkata al proprio account (permette a lablab.ai e Kraken di vedere la trade history, **no execution**, **no withdrawal**) |
| **Audit** | Kraken esegue un audit finale sui top agent prima della distribuzione premi |
| **Ranking** | Net PnL (realized + unrealized) al termine della finestra |

**Requisiti:**

- Agente deve usare **Kraken CLI come execution layer**
- Una sola submission per team / partecipante

#### 2️⃣ Social Engagement (30 giorni)

Build in public. Score puramente quantitativo su:

- Impression, like, share, reach
- Piattaforme: X / Twitter, YouTube, blog, IG, LinkedIn

**Account da taggare:** vedi `05-community-and-social-channels.md`.

### Kraken CLI — cosa offre

> First AI-native CLI per trading di crypto, equity, forex e derivati su Kraken — Single binary, no runtime dependencies, integrated MCP server, live + paper trading. **Licenza MIT**.

**Compatibile con:** Cursor, Claude, Codex, Copilot, Gemini, Goose, OpenClaw.

#### Asset class supportate (6)

| Asset | Universo | Leverage |
|---|---|---|
| **Crypto spot** | 1.400+ coppie (BTC, ETH, SOL, …) | fino a **10x** su major |
| **xStocks tokenizzate** | **79 asset** (AAPL, NVDA, TSLA, GOOGL, AMZN, MSFT, SPY, QQQ, …) | fino a **3x** su top 10 — **non in USA** |
| **Forex** | 11 coppie fiat (EUR/USD, GBP/USD, USD/JPY, AUD/USD, …) | — |
| **Perpetual futures** | 317 contratti | fino a **50x** |
| **Inverse/fixed-date futures** | 20 contratti | — |
| **Earn / staking** | strategie flexible e bonded | — |

#### Installazione

One-liner curl per macOS (Apple Silicon/Intel), Linux (x86_64/ARM64). Windows via WSL. Binari firmati **minisign**. Build da sorgente con `cargo build`.

#### Autenticazione (read-only consigliata per hackathon)

- Market data pubblici → no credenziali
- Per comandi autenticati: API key Kraken (Spot: Settings → API; Futures: Settings → Create Key)
- **Per monitoring read-only basta:** permessi `Query Funds` + `Query Open Orders & Trades` (principio minimi privilegi)
- **Precedence credenziali:** flag CLI > env vars > `~/.config/kraken/config.toml` (permessi 0600)
- Env vars supportate: `KRAKEN_API_KEY`, `KRAKEN_API_SECRET`, `KRAKEN_FUTURES_API_KEY`, `KRAKEN_FUTURES_API_SECRET`
- Per evitare leak in process listing: `--api-secret-stdin` o `--api-secret-file`
- **I segreti non sono mai loggati o stampati**

#### Comandi base (selezione)

```
kraken status
kraken ticker BTCUSD -o json
kraken orderbook BTCUSD --count 10 -o json
kraken ohlc BTCUSD --interval 60 -o json
kraken balance -o json
kraken open-orders -o json
kraken order buy BTCUSD 0.001 --type limit --price 50000 -o json
kraken setup        # wizard interattivo
kraken shell        # REPL
```

#### Topologia comandi

**151 comandi** in 13 gruppi: market (10, no auth), account (18), trade (9), funding (10), earn (6), subaccount (2), futures (39), futures-paper (17), futures-ws (9), websocket (15), paper (10), auth (4), utility (2). 34 comandi marcati `dangerous`.

#### MCP Server integrato

`kraken mcp` espone gli stessi command path via stdio. Modalità default `market,account,paper` (read-only). Chiamate dangerous richiedono `acknowledged=true` (guarded mode) o `--allow-dangerous`. Avvertenza esplicita: **local-first, non esporre il server fuori dalla propria macchina**.

#### Pattern agent-first

`kraken <cmd> [args...] -o json 2>/dev/null` — stdout sempre JSON valido, exit 0 = success, stderr solo diagnostica con `-v`.

**Risorse dedicate nel repo:**

- `CONTEXT.md`, `AGENTS.md`, `CLAUDE.md`
- `agents/tool-catalog.json` — 151 comandi con schema
- `agents/error-catalog.json` — 9 categorie di errore con retry guidance
- `skills/` — 50+ `SKILL.md` goal-oriented

#### Paper Trading

Sandbox con prezzi live, **senza API key**:

- **Spot paper:** solo market e limit, fee taker 0.26% (Kraken Starter), no modeling slippage/partial fill
- **Futures paper:** 8 tipi di ordine, leva e margine simulati, liquidazione e funding rate accrual
- Output etichettato `[PAPER]` o `mode: "paper"` in JSON

#### Esempi agent (README)

- Morning market brief automatico
- Watch ETH/SOL/BTC ogni 30 secondi
- Lookup AAPLx / TSLAx / SPYx su xStocks
- Paper trade BTC con P&L tracking
- Long 10x su BTC futures paper con $5.000 collateral e trailing stop 3%
- Conditional order su prezzo live (jq)
- Portfolio rebalance
- Streaming WS multi-ticker
- **Dead man's switch** con `kraken order cancel-after 60`

### xStocks — come funzionano

- **Tokenizzate 1:1** dall'asset sottostante presso un custode regolamentato
- Emesse tramite struttura legale conforme — strumenti blockchain-native
- **Reti supportate:** Ethereum, Solana, Mantle, TON, Ink + altre EVM-compatibili (nativamente)
- **Trading 24/7** su exchange supportati e venue DeFi
- Emissione/redemption tramite issuer 24/5 (allineate al mercato U.S.)
- **Self-custodial** (withdraw a proprio wallet)
- **DeFi composable** (collateral, lending, liquidity pool, prodotti strutturati)
- **Frazionabili**
- **Protezioni investitore:** SPV bankruptcy-remote, 1:1 senza commingling, custodia segregata con Account Control Agreement a tre parti, Security Agent indipendente, **proof of reserves pubblicamente verificabile**, smart contract auditati
- **True to price:** dividendi, stock split e reverse split riflessi via rebasing on-chain (no azione richiesta agli holder)

### xStocks Alliance

Alleanza di exchange, chain e protocolli DeFi per:

- Interoperabilità
- Standard di integrazione comuni
- Liquidità cross-venue
- Standard equity tokenizzate

### ⚠️ Disclaimer

xStocks **non distribuibili negli USA**, a US person o in altre giurisdizioni proibite. Non costituisce consulenza finanziaria.

### Quickstart Kraken

1. Installare Kraken CLI dal repo ufficiale
2. Configurare l'accesso API e collegarlo all'agente
3. Verificare l'accesso al mercato xStocks
4. Costruire l'agente autonomo (signal → strategy → execute)
5. **Condividere i progressi pubblicamente** (Social Engagement track)

### 📘 Link sorgente

- Kraken CLI GitHub Repository — https://github.com/krakenfx/kraken-cli
- xStocks Documentation — https://docs.xstocks.fi/docs
- xStocks su Kraken — https://www.kraken.com/xstocks *(non accessibile dal browser dei sub-agenti per safety restriction)*

---

## ⚡ 4. Featherless — Domain-Specialized Open-Source Agent

**Featherless** è una piattaforma di **serverless inference** per **30.000+ modelli open-source** tramite **una singola API key OpenAI-compatibile**. Niente gestione GPU, deploy istantaneo.

### La sfida

**Build a domain-specialized, open-source AI agent using models from the Featherless catalog.**

Invece di costruire un assistente general-purpose, l'obiettivo è un agente che **fa una cosa eccezionalmente bene** in un dominio specifico.

### Cosa cercano i giudici

- **Domain-Specialized, NOT Generalist** — legal, medical, logistics, finance, research, code review, content moderation, localization, …
- **Async-First Architecture** — agenti che operano in background: scheduled workflow, document pipelines, monitoring systems, event-driven task
- **Fully Open-Source** — licenza permissiva **MIT o Apache 2.0**, prompt + orchestrazione + deployment riproducibili
- **Production-Shaped** — deployabile, ben documentato, usabile oltre l'hackathon

### Accesso & credit

- **$25 di credit per partecipante**
- **Primi 1.000 partecipanti**, first-come first-served
- ⭐ **Premium plan con TOKEN ILLIMITATI per 1 mese** — confermato da Isaac Gemal (Developer Relations Manager) al kick-off: *"Everyone at the Lab Lab hackathon will have access to our premium plan for one month, which features unlimited tokens, so you can focus on building something people want and not get bogged down on price"*
- Dettagli e setup guide condivisi durante il kick-off stream
- Supporto: **Discord Featherless** (canale community) — Isaac contattabile per problemi specifici

### Quickstart

1. Aprire il setup guide
2. Scansionare QR code o link signup nel guide
3. Creare account → attivare free Premium
4. Generare API key dal dashboard
5. Scegliere un modello dal catalogo e iniziare a costruire

### Piattaforma Featherless — overview

> *"Featherless AI is a serverless AI inference platform."*

Headline ufficiale: *"One API key. Instant access. Freedom to reliably deploy any open model effortlessly."*

- **30.000+ modelli** open-weight della community
- API **OpenAI-compatible** — qualsiasi client OpenAI funziona riconfigurando `base_url`
- Esperienza chat: **Phoenix**
- Lancio agenti one-click: **OpenClaw** + **NemoClaw Agent**
- Series A da 20M$, radici in **RWKV** (Linux Foundation project)
- Modello proprietario: **QRWKV** (linear-transformer)

### Catalogo modelli (categorie)

Most Popular · Trending · Top Reasoning · Top Small Models · Top RP & Creative Writing · Top Language Specific · Creative Writing.

Famiglie principali:

- Mistral 3 / 3.1 (es. `Mistral-Small-3.2-24B`)
- DeepSeek V3 / V3.2 / R1
- GLM 4.6 / 5
- Llama 2 / 3 / 3.1
- Qwen 2 / 2.5 / 3 (incluso `Qwen3-Coder-30B`)
- Kimi K2.5
- GPT-OSS 120B
- Gemma 3
- TinyLlama, Nanbeige, Ling-1T
- Language-specific: swahili, coreano, thai, arabo, giapponese, russo, svedese

### Pricing (piani flat con token illimitati)

| Piano | Prezzo | Caratteristiche |
|---|---|---|
| **Basic** | $10 / mese | Modelli ≤15B, 2 connessioni concorrenti, 16K context |
| **Premium** | $25 / mese | DeepSeek / Kimi / GLM, qualunque size, 4 conn., 32K context |
| **Agent Standard** | $100 / mese | Modelli ≤229B, 8 conn., 256K context, **1 agent runtime**, sandbox standard, persistent storage (trial 3gg) |
| **Agent Pro** | $200 / mese | Qualunque modello, 8 conn., 256K context, agent runtime, sandbox più ampia, persistent storage |

### Quickstart API

- **Endpoint base:** `https://api.featherless.ai/v1`
- **Auth:** `Authorization: Bearer FEATHERLESS_API_KEY`
- **Endpoint:** `/completions`, `/chat/completions`
- **Naming modelli:** identifier in formato Hugging Face (es. `Qwen/Qwen2.5-7B-Instruct`)

#### Snippet Python (OpenAI SDK)

```python
client = OpenAI(
    base_url="https://api.featherless.ai/v1",
    api_key="FEATHERLESS_API_KEY"
)
client.chat.completions.create(
    model='Qwen/Qwen2.5-7B-Instruct',
    messages=[...]
)
```

### 📘 Link sorgente

- Featherless Platform Overview — https://featherless.ai/
- Featherless Documentation — https://featherless.ai/docs/overview
- Featherless Quickstart — https://featherless.ai/docs/quickstart-guide

### ⚠️ Note credits

- Feather Premium valido **1 mese** dall'attivazione
- Provvisto direttamente da Featherless, soggetto ai loro termini

---

## 🎙️ 5. Speechmatics — Voice-First / Real-Time Speech AI

**Speechmatics** fornisce STT (speech-to-text) ad alta accuratezza e tecnologia conversational AI per voice apps, assistants, real-time workflows. **15+ anni** sul problema, **55+ lingue**, **100+ voice AI startup** già in scaling.

> 🎙️ Quote dal kick-off (Edgars Adamovics, Developer Relations Lead):
> *"Real world means messy. Real world means accents, background noise, people talking over each other, two humans on one microphone, three different languages on one call. This is where most speech APIs fall apart. This is where Speechmatics is miles ahead."*

### La sfida (ridefinita al kick-off)

**Build the most AMBITIOUS voice-first autonomous agent we have ever seen.**

Pattern richiesto: **Voice in → reasoning / planning / tool calling → Voice out**

- Agent che parlano la lingua dell'utente
- Agent che gestiscono conversazioni reali, **non toy demo**
- **Multispeaker · Multilingual · Production-shaped**
- Pick a vertical: healthcare triage · field service support · multilingual customer ops · accessibility per utenti non-verbal · qualunque cosa ti accenda

### Categorie di progetto incoraggiate

- Real-time conversational AI agents
- Voice-powered copilots e assistants
- AI meeting / interview / call summarization tools
- Speaker diarization e multi-speaker workflows
- Accessibility e transcription platforms
- Voice interface integrate dentro AI agent

### Capability tecniche chiave

- **Real-time STT** in <1 secondo dichiarato
- **Speaker diarization** best-in-class per conversazioni multi-speaker
- **Adaptive turn detection** che riduce **falsi interrupt 3.5x** vs alternative
- **Batch transcription** per audio registrati
- **55+ lingue** supportate
- **Voice SDK** = high-level Python SDK che nasconde *"all the websocket plumbing, all the JSON parsing, all the streaming infrastructure that usually eats your first three days of any voice project"*
- **Text-to-Speech API**
- **Voice agents (Flow API)**
- **Integrazioni native production-tested:** LiveKit · Pipecat · **Vapi** (drop-in dal day one)
- Deploy flessibile: **cloud, on-prem, on-device** (caso Adobe Premiere)
- Default: **No data logging**

### 🎯 Pro tips ufficiali dal kick-off (Edgars Adamovics)

| # | Tip | Perché |
|---|-----|--------|
| 1 | **Usa i preset, non tunare da zero** | Voice agent config external per Pipecat · smart turn per LiveKit. *"The presets exist because we already did the tuning for you"* |
| 2 | **Turn on diarization** | È gratis e *"a massive differentiator. Your agents will know who is talking every single time"* — la maggior parte dei team se la dimentica |
| 3 | **Custom dictionary** | Nomi prodotto, gergo verticale, acronimi interni → *"watch your accuracy jump"* |

### 🏆 Bonus score Speechmatics (dichiarati dal kick-off)

- ✅ Usare **direttamente il Voice SDK** → "bonus love"
- ✅ **Multilingual** (più di una lingua nel flusso) → **"massive bonus love"**
- ✅ **Speaker diarization usata in modo creativo** → **"massive bonus love"**

### Sicurezza & compliance

- ISO/IEC 27001:2022
- GDPR
- HIPAA
- SOC 2 Type II

### Casi d'uso (homepage)

Medical/healthcare (Medical Model, -50% errori su termini chiave dichiarato), voice agents, live captioning, contact center, legal, meeting platforms.

### Accesso & credit

- **$200 di credit API per partecipante**
- **Primi 200 partecipanti**, first-come first-served
- Validità: **1 mese**
- 🎟️ **COUPON CODE: `AI WEEK 200`** ← rivelato al kick-off del 13 maggio

### Quickstart

1. Creare account su **portal.speechmatics.com** (free API key)
2. Aggiungere una carta di pagamento per attivare l'account
3. Riscattare il **coupon `AI WEEK 200`**
4. Generare API key
5. Andare diretti su **Speechmatics Academy** (GitHub) → esempi pronti per **LiveKit · Pipecat · Vapi · Voice SDK** — "zero to voice agents in minutes, not days"
6. Supporto: il team Speechmatics è on-call sul **Discord Speechmatics** tutta la settimana

📹 Tutorial step-by-step di credit redemption condiviso durante il kick-off.

### Quickstart paths (docs)

- Transcribe in real-time
- Transcribe a file (batch)
- Build a voice agent (Flow)
- Generate speech from text (TTS)
- Guida "Realtime transcription with NextJS" (Coming soon)

### SDK Python (Academy)

Pacchetti SDK Python richiamati:

- `speechmatics-batch` — batch async
- `speechmatics-rt` — streaming real-time
- `speechmatics-voice` — voice agent con gestione conversazione
- `speechmatics-tts` — TTS

### Repository GitHub principali

| Repo | Tech |
|---|---|
| `speechmatics-academy` (MIT) | Python — esempi e tutorial |
| `speechmatics-python-sdk` | Python — SDK ufficiali |
| `speechmatics-dotnet` | C# — client .NET per Real-Time API |
| `speechmatics-js-sdk` | TypeScript — SDK JS/TS |
| `community` | Area pubblica utenti |
| `docs` (MIT) | TypeScript — sito documentazione |
| `speechmatics-python` (MIT) | Python — libreria e CLI storica |
| `livekit-agents` (fork) | Python — framework voice AI realtime |
| `pipecat` (fork) | Python — framework AI conversazionale voce/multimodale |

### Esempi dall'Academy

- **Fundamentals:** Hello World, Batch vs Real-time, Configuration Guide, TTS, Channel Diarization, Audio Intelligence, Multilingual & Translation, Turn Detection (Basic/Intelligent), Speaker ID & Speaker Focus, Voice API Explorer
- **Integrations:** LiveKit · Pipecat · Twilio (SIP, Media Streams, outbound dialer) · VAPI · Krisp · ElevenLabs
- **Use cases:** Medical Transcription · Video Captioning (SRT) · Call Analytics · AI Receptionist · Santa Voice Agent · Medical Assistant (AR+EN, GPT-4o, SOAP/ICD-10) · Medical Microbatching (HIPAA on-prem) · Alphanumerics Form Filler

### Migration guides

- ✅ Deepgram disponibile
- ⏳ In arrivo: AssemblyAI, Google Cloud Speech, AWS Transcribe, Azure Speech

### 📘 Link sorgente

- Speechmatics Platform — https://www.speechmatics.com/
- Speechmatics Documentation — https://docs.speechmatics.com/
- Speechmatics GitHub — https://github.com/speechmatics
- Speechmatics Academy — https://github.com/speechmatics/speechmatics-academy

### ⚠️ Note credits

- Credits forniti direttamente da Speechmatics
- ❗ **Eliminare le API key inutilizzate dopo l'hackathon** per evitare addebiti accidentali

---

## 🎓 Workshops (registrati, on-demand)

> *"Get inspired and boost your skills with exclusive sessions from our partners and experts. Watch them anytime!"*

| Sponsor | Speaker | Topic |
|---|---|---|
| **Vultr** | Sanskriti Harmukh — Junior Developer Relations | Vultr Serverless Inference |
| **Vultr** | Sanskriti Harmukh | Supabase |
| **Vultr** | Sanskriti Harmukh | Coolify |

> Altri workshop / sessioni opening da parte di Google, Kraken, Featherless, Speechmatics si svolgono durante il **kick-off del 13 maggio** (vedi `09-event-schedule.md`).

---

## ⚠️ Riepilogo Access & Usage Notes (ufficiali)

| Sponsor | Credit | Validità | Cosa fare per continuare |
|---|---|---|---|
| **Vultr** | Credit (importo ufficiale durante kick-off) | 30 giorni | Linkare metodo di pagamento valido |
| **Google Cloud** | $300 per nuovi account | 90 giorni | Abilitare billing per servizi paid |
| **Featherless** | $25 + Feather Premium | 1 mese | Provvisto da Featherless |
| **Speechmatics** | $200 (primi 200) | 1 mese | Eliminare API key inutilizzate post-hackathon |

> ⚠️ **General:** lablab.ai **non è responsabile** di provisioning, billing o limitazioni delle piattaforme terze.
