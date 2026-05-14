# Vultr — Deep Dive per "Best use of Vultr"

> Approfondimento dedicato al premio **Vultr** (1° $5K + $1K credit, 2° $3K + $1K, 3° $1K + $1K) dell'AI Agent Olympics Hackathon.
> Sfida: **Build a Web-Based Enterprise Agent Deployed on Vultr**.
> Vincolo: **niente GPU**. Tutto il compute AI deve passare da **Vultr Serverless Inference** o offload esterno.

> 📚 **Vedi anche** [`14-tutorial-gemini-vultr-document-agent.md`](./14-tutorial-gemini-vultr-document-agent.md) — tutorial ufficiale lablab.ai pubblicato l'8 maggio 2026 con stack completo Gemini + Vultr (FastAPI + ADK + Docker) e GitHub repo riusabile come baseline.

## 🏗️ Architettura consigliata end-to-end

Per minimizzare ops e massimizzare lo score "Application of Technology + Business Value":

```
                    ┌─────────────────────────────────────┐
                    │  Vultr Cloud Compute HP 2vCPU/4GB   │
                    │  ($24/mese · Coolify Marketplace)   │
                    │  • Next.js front-end                │
                    │  • API gateway (FastAPI / Hono)     │
                    │  • Webhook handlers                 │
                    │  • Background workers               │
                    └─────────────────────────────────────┘
                                  │
                ┌─────────────────┴───────────────────────┐
                │                                         │
                ▼                                         ▼
┌──────────────────────────────────┐    ┌───────────────────────────────────┐
│  Vultr Managed PostgreSQL HP     │    │  Vultr Serverless Inference       │
│  4GB/2vCPU + 1 replica           │    │  (api.vultrinference.com)         │
│  ($120/mese, HA)                 │    │  + Vector Store collection        │
│  • conversation history          │    │  • LLM tool calling (Kimi K2)     │
│  • users · auth · audit log      │    │  • RAG chat completion endpoint   │
│  • feature flags                 │    │  • Embeddings auto (no charge)    │
└──────────────────────────────────┘    └───────────────────────────────────┘
                ▲                                         ▲
                │                                         │
                ┌─────────────────────────────────────────┐
                │  IAM Service User (API-only)            │
                │  con policy resource-scoped             │
                │  (subscription Inference + DB only)     │
                │  + OIDC per GitHub Actions deploy       │
                └─────────────────────────────────────────┘
```

**Costo stimato mensile demo:** ~$190 (compute + DB + LB), coperto dal free trial $250 / 30gg.
**Costo token Serverless Inference:** $0.15 / 1M input · $0.60 / 1M output per `kimi-k2-instruct` → ~$1-3 per intera demo.

---

## 1. ☁️ Vultr Serverless Inference — la chiave del progetto

### Endpoint e API key

| | |
|---|---|
| **Base URL** | `https://api.vultrinference.com/v1` |
| **Auth header** | `Authorization: Bearer $INFERENCE_API_KEY` |
| **Compatibilità** | **OpenAI-compatible** (drop-in: basta cambiare `base_url`) |
| **Management API** | `https://api.vultr.com/v2/inference` (con `VULTR_API_KEY`) — gestisce subscription, restituisce `inference-id` + `INFERENCE_API_KEY` |
| **Sicurezza** | *"All data transmitted to and from Vultr Serverless Inference is encrypted"* |
| **Test interattivo** | Console Vultr → tab **Prompt** (prima di scalare) |

### Endpoint disponibili

| Endpoint | Scopo |
|---|---|
| `GET /v1/models` | Lista modelli |
| `POST /v1/chat/completions` | Chat completion classica (OpenAI-style) |
| `POST /v1/chat/completions/RAG` | **Chat + retrieval in una sola call** ⭐ |
| `POST /v1/vector_store` | Crea collection |
| `POST /v1/vector_store/{id}/items` | Aggiunge item (embedding auto-calcolato) |

### Modelli LLM + pricing (per 1M token, input / output)

| Modello | Input | Output | Note hackathon |
|---|---|---|---|
| `nvidia/Llama-3.1-Nemotron-Safety-Guard-8B-v3` | $0.01 | $0.01 | Safety / moderation |
| `nvidia/Nemotron-3-Nano-Omni-30B-A3B-Reasoning-BF16` | $0.13 | $0.38 | Reasoning ottimizzato |
| `nvidia/Nemotron-Cascade-2-30B-A3B` | $0.15 | $0.60 | Multi-step reasoning |
| **`moonshotai/Kimi-K2.6`** | **$0.15** | **$0.60** | ⭐ **Unico con tool calling RAG** |
| `Qwen/Qwen3.5-397B-A17B-FP8` | $0.30 | $1.20 | Frontier general purpose |
| `MiniMaxAI/MiniMax-M2.7` | $0.30 | $1.20 | Long-context |
| `nvidia/DeepSeek-V3.2-NVFP4` | $0.55 | $1.65 | High quality |
| `deepseek-ai/DeepSeek-V4-Pro` | $0.55 | $1.65 | Top quality |
| `zai-org/GLM-5.1-FP8` | $0.85 | $3.10 | Premium |

### Modelli image generation (solo via API)

| Modello | Pricing |
|---|---|
| `stable-diffusion-3.5-medium` | $0.01 / MP |
| `flux.1-schnell` | $0.01 / MP |
| `stable-diffusion-3.5-large-turbo` | $0.02 / MP |
| `flux.1-dev` | $0.02 / MP |

### Tool calling — esempio Python

```python
from openai import OpenAI

client = OpenAI(
    base_url="https://api.vultrinference.com/v1",
    api_key=os.environ["VULTR_INFERENCE_API_KEY"],
)

tools = [{
    "type": "function",
    "function": {
        "name": "search_kb",
        "description": "Search internal knowledge base",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "top_k": {"type": "integer", "default": 5}
            },
            "required": ["query"]
        }
    }
}]

resp = client.chat.completions.create(
    model="kimi-k2-instruct",
    messages=[{"role": "user", "content": "Summarize Q3 sales by region"}],
    tools=tools,
    tool_choice="auto",
)

# resp.choices[0].finish_reason == "tool_calls"
# resp.choices[0].message.tool_calls[0].function.name → "search_kb"
# .arguments → '{"query":"Q3 sales by region","top_k":10}'  (string JSON)
```

Il flusso è a **2 chiamate** (vedi `03-technology-partners.md` → sezione Vultr):

1. Il modello risponde con `finish_reason: "tool_calls"` + payload del function call
2. Il client esegue la funzione e re-invia un messaggio `role: "tool"` con `tool_call_id` + `content` (output JSON) → risposta finale `finish_reason: "stop"`

> 📘 Fonte snippet ufficiale: `vultr-marketing/code-samples/tool-calling-weather.py`.

> 🔗 https://docs.vultr.com/products/serverless/inference · https://docs.vultr.com/how-to-use-tool-calling-with-vultr-serverless-inference

---

## 2. 🗄️ Vector Store + RAG Chat Completion ⭐

Funzionalità **killer** per un Enterprise Agent: retrieval + LLM in **una sola chiamata**.

### Crea collection

```bash
curl -X POST "https://api.vultrinference.com/v1/vector_store" \
  -H "Authorization: Bearer ${INFERENCE_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{ "name": "company-docs" }'
```

### Aggiungi item (embedding auto)

```bash
curl -X POST "https://api.vultrinference.com/v1/vector_store/{collection-id}/items" \
  -H "Authorization: Bearer ${INFERENCE_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Policy: i rimborsi sono garantiti entro 14 giorni dall'\''acquisto.",
    "description": "Refund policy v2024"
  }'
```

**Sono supportati anche file upload** (sezione "Add Collection Files" della doc).
**Embedding pricing:** non documentato come voce separata — costo coperto dalla call (no charge esplicito per embedding).

### RAG Chat Completion (retrieval + LLM in una call)

```bash
curl -X POST "https://api.vultrinference.com/v1/chat/completions/RAG" \
  -H "Authorization: Bearer ${INFERENCE_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "collection": "{collection-id}",
    "model": "llama-3.3-70b-instruct-fp8",
    "messages":[{"role":"user","content":"Qual è la policy sui rimborsi?"}],
    "max_tokens": 512
  }'
```

### Modelli compatibili RAG

| ✅ Compatibili | ❌ Non compatibili |
|---|---|
| `deepseek-r1-distill-qwen-32b` | `mistral-7B-v0.3` |
| `qwen2.5-32b-instruct` | `mistral-nemo-instruct-2407` |
| `qwen2.5-coder-32b-instruct` | |
| `llama-3.1-70b-instruct-fp8` | |
| `llama-3.3-70b-instruct-fp8` | |
| `deepseek-r1-distill-llama-70b` | |
| `deepseek-r1` | |
| ⭐ `kimi-k2-instruct` (solo questo + tool calling) | |

### Quando usare cosa

| Caso | Modello | Endpoint |
|---|---|---|
| Q&A su docs aziendali (no tool) | `llama-3.3-70b-instruct-fp8` | `/RAG` |
| Reasoning forte su docs | `deepseek-r1` | `/RAG` |
| Code Q&A su docs | `qwen2.5-coder-32b-instruct` | `/RAG` |
| **Agent con tool + docs** ⭐ | `kimi-k2-instruct` | `/RAG` con `tools[]` |
| Tool calling senza retrieval | `kimi-k2-instruct` | `/chat/completions` |

> *"RAG enables chat models to incorporate external, domain-specific knowledge"*

> 🔗 https://docs.vultr.com/products/serverless/inference/vector-store

---

## 3. 🚀 Deploy con Coolify Marketplace App ⭐

**Coolify** = PaaS open-source self-hosted (Docker-based). La Marketplace App Vultr fornisce una VM pre-configurata con reverse proxy Traefik + SSL Let's Encrypt automatici.

### Provisioning

- **Console:** Compute → Marketplace Apps → **Coolify**
- **Programmatico:** API/Terraform con `image_id: coolify`
- **CLI:** `vultr-cli instance create --image "coolify"`
- **Access:** `http://<server-ip>:8000` → registra admin

### Tipologie deploy supportate

| Source | Build pack |
|---|---|
| Public Git repo | Nixpacks auto-detect (Node, Python, Go, Rust…) |
| Private Git repo | Nixpacks |
| Database | PostgreSQL · MySQL · Redis |
| Preset | WordPress, … |
| **Dockerfile** | Custom |
| **Docker Compose** | Multi-service |
| Static site | NGINX |

### Configurazione tipica

- **Branch**, **Build Pack**, **Base Directory**, **Port**
- **Env vars** in 4 modalità: Build / Runtime / Literal / Multiline
- **Healthcheck integrato:** Method/Scheme/Host/Port/Path/Response Text + Interval/Timeout/Retries/Start Period
- **Domini:**
  - Temporaneo: `<random-id>.<server-ip>.sslip.io` (solo HTTP, no wildcard Let's Encrypt)
  - Custom: A record `@` + `www` → IP istanza, "Allow www & non-www" + "Force HTTPS" → Traefik richiede certificato automaticamente

### Costo

Solo il prezzo della VM Vultr scelta. **Coolify è gratis e open-source.**

> 🔗 https://docs.vultr.com/how-to-deploy-an-application-with-vultr-coolify-marketplace-app
> 🔗 https://docs.vultr.com/how-to-deploy-claude-code-projects-on-vultr-using-coolify

---

## 4. 🗃️ Supabase Marketplace App + Next.js

Alternativa "batteries included" se vuoi DB + auth + storage + real-time + edge functions **già pronti**, su un'unica VM Vultr.

### Provisioning

- **Marketplace App:** Supabase
- **Programmatico:** `image_id: supabase`
- Attivare **Limited User Login** con sudo
- **Rigenerare ANON_KEY e SERVICE_ROLE_KEY** dal JWT secret nelle App Instructions
- Aggiornare `.env` cartella Supabase Docker + ricreare i container (`docker compose up -d --build`)

### Reverse proxy NGINX

```
/                → 127.0.0.1:3000 (Next.js)
/supabase/       → 127.0.0.1:8000 (Supabase API)
```

DNS A record `@` e `www` → IP istanza.

### Database setup

```bash
docker exec -it supabase-db bash
psql -U postgres
```

- Abilitare **RLS:** `ALTER TABLE <name> ENABLE ROW LEVEL SECURITY`
- Definire policy granulari (SELECT/INSERT/UPDATE/DELETE)
- Estensioni Postgres pre-installate: **50+** (`uuid-ossp`, `pgcrypto`, …)
- ✅ **`pgvector` disponibile** nella distribuzione standard Supabase → RAG self-hosted alternativo

### Frontend Next.js

```bash
npm install
npm run build
npm start
# oppure
docker compose up -d
```

Env: `NEXT_PUBLIC_SUPABASE_URL=https://yourdomain.com/supabase/`

### HTTPS

```bash
certbot --nginx -d yourdomain.com -d www.yourdomain.com
# Certificati 90 giorni, rinnovo automatico
```

### ⚠️ Sicurezza

- **`SERVICE_ROLE_KEY` bypassa RLS** — mai esporre client-side
- Default su porte 3000 / 8000

> 🔗 https://docs.vultr.com/how-to-deploy-a-nextjs-application-with-vultr-supabase-marketplace-app

---

## 5. 💻 Cloud Compute — catalogo VM

| Famiglia | Use case | Pricing tipico |
|---|---|---|
| **VX1** | Enterprise affordable, boot da HP Block Storage, fino a 50 Gbps, vCPU dedicati, provisioning <15s, billing oraria no cap | — |
| **Cloud Compute Regular Performance** | Intel + SSD, low traffic | da **$2.50/mese** (1vCPU/0.5GB) |
| **Cloud Compute High Performance** | AMD EPYC / Intel Xeon + NVMe ⭐ | da **$6/mese** |
| **Cloud Compute High Frequency** | Xeon 3GHz+ + NVMe | da $7/mese |
| **Optimized Cloud Compute** | vCPU AMD EPYC dedicati: General / CPU / Memory / Storage Optimized | da $30/mese (1vCPU/4GB) |
| Cloud GPU L40S | Inferenza GPU | $0.848/GPU/hr prepaid 36m |
| Cloud GPU A100 80GB | Training | $2.397/hr on-demand |
| Cloud GPU H100 / B200 / GH200 | Frontier | contratto 48m |
| Bare Metal 8x H100/B200/MI300X | Inference massiva | $2.99/GPU/hr B200, $1.49/hr A100 |

**Per Web Agent hackathon:** High Performance da **2vCPU/4GB ($24/mese)** o **4vCPU/8GB ($48/mese)** è il sweet spot. GPU **non serve** (inferenza offload su Serverless Inference, vincolo hackathon).

### ⚠️ Limiti operativi

- **Port 25 (SMTP) bloccata di default**
- Snapshot **non preservano IP**
- **Downsize plan non supportato**
- Backup retention **7 giorni** dopo delete

> 🔗 https://docs.vultr.com/products/compute

---

## 6. 🗄️ Managed Databases — stato persistente dell'agent

DB clusterizzati gestiti (config, update, backup, security) con replica nodi opzionali.

### Engine supportati

| Engine | Use case agent |
|---|---|
| **PostgreSQL** ⭐ | Conversation history · audit log · feature flags · users · sessions |
| **MySQL** | Stessi prezzi di Postgres |
| **Valkey** (Redis-compatible) | Cache · message broker · streaming |
| **Apache Kafka** | Stream processing real-time, event bus |

### Pricing Postgres (esempi)

| Tier | Risorse | 0 replica | 1 replica | 2 replica |
|---|---|---|---|---|
| Cloud Compute HP | 1GB / 1vCPU / 32GB | **$18/mese** | — | — |
| Cloud Compute HP | 4GB / 2vCPU / 128GB | $72/mese | $120/mese | $168/mese |
| Optimized GP | 4GB / 1vCPU / 30GB | $90/mese | $150/mese | $210/mese |

### Valkey (in-memory)

- Memory Optimized 16GB/2vCPU **$160/mese** (0 repliche)

> ⚠️ La pagina `docs.vultr.com/products/managed-databases` non esiste come URL pubblico — il pricing pubblico è la fonte canonica.

> 🔗 https://www.vultr.com/pricing/

---

## 7. 🚢 VKE — Vultr Kubernetes Engine

Managed Kubernetes con **control plane GRATUITO** (vs ~$70/mese sui big hyperscaler). Si paga solo:

- Worker node (Cloud Compute)
- Block Storage (per Persistent Volumes via CSI)
- Load Balancer ($10/mese)

### Caratteristiche

| Feature | Dettaglio |
|---|---|
| **CNI default** | Calico |
| **HA control plane** | Opzionale |
| **Firewall integrato** | Sì |
| **Node pool** | Misti (compute types diversi nello stesso cluster) |
| **CSI** | Vultr Container Storage Interface per PV su Block Storage |
| **ETCD** | Criptato a riposo |
| **CNCF-certified** | Sì + Cluster API compatibile (Argo CD, Flux, GitOps) |
| **Ingress** | NON pre-installato — installare NGINX o HAProxy a piacere (supporta PROXY Protocol verso Vultr LB) |

### ⚠️ Non supporta

- Bare-metal worker nodes
- VPC 2.0 (solo VPC legacy)

### Quando usarlo per l'hackathon

Solo se l'agent è **realmente** multi-microservizio (api-gateway + agent-runtime + MCP bridges + embedding-sync + worker queue). Altrimenti Cloud Compute + Coolify è più snello.

> 🔗 https://docs.vultr.com/products/kubernetes

---

## 8. 🔐 IAM — sicurezza dell'agent

**Critico per il punteggio "Application of Technology"** (e per non far esplodere il budget hackathon con chiavi root condivise).

### Componenti

| Componente | Funzione |
|---|---|
| **Organizations** | Top-level boundary: isolamento risorse, billing, accessi |
| **Users** | Regular · **Service** (API-only, M2M) · Root owner |
| **Groups** | Contenitori per ereditare ruoli/policy |
| **Roles** | Bundle di policy — *Assignable* (attaccate) o *Assumable* (trust-based, sessione temporanea) |
| **Policies** | Allow/deny su action+resource — Vultr-managed o custom. **Resource scoping**: permission limitate a specifiche risorse |
| **OIDC** | Provider + issuer per federated auth (es. GitHub Actions OIDC → assume role temporaneo) |
| **ACL legacy** | Mappate automaticamente a policy IAM, coesistenza durante transizione |

### Pattern raccomandato per il progetto

1. **Service User** dedicato al runtime dell'agent
2. Policy **resource-scoped** sulla sola subscription Inference + DB + bucket Object Storage
3. **OIDC trust** dal GitHub Actions repo del progetto → assumable role temporaneo per deploy (no long-lived secret in CI)
4. Session token range: 15 minuti – 12 ore (default **1 ora**)

> *"15 minutes to 12 hours maximum, with a default duration of 1 hour"*

> 🔗 https://docs.vultr.com/platform/iam

---

## 9. 🌐 Networking & Storage di contorno

| Servizio | Prezzo | Quando usarlo |
|---|---|---|
| **Load Balancer** | $10/mese ($0.015/hr) | Front di N pod o N VM |
| **Global Load Balancer** | $10 / regione / mese | Multi-regione |
| **NAT Gateway** | $0.03/hr (~$21.6/mese) | VPC outbound senza esporre instance |
| **Block Storage NVMe** | $1 / 10 GB / mese | PV per VKE, storage istanze |
| **Object Storage S3-compatible** | $18/mese 1TB + 1TB egress | Allegati chat, upload documenti per RAG, immagini generate |
| **CDN** | $10/mese + bandwidth | Static asset + cache |
| **Direct Connect 1 Gbps** | $100/mese | VPN/on-prem privato |
| **Direct Connect 10 Gbps** | $500/mese | Enterprise high-throughput |

> 🔗 https://www.vultr.com/pricing/

---

## 🎯 Checklist requisiti hackathon Vultr

Dal brief ufficiale:

- [ ] **GitHub repository** con setup + documentazione
- [ ] **Vultr VM backend deployment** (Cloud Compute o VKE)
- [ ] **Public demo URL** (HTTPS via Coolify/Traefik o NGINX+Certbot)
- [ ] **Recorded demo video** (≤5 min)
- [ ] **Clear explanation of architecture and use case** (nel README e nelle slide)
- [ ] Multi-step **agentic workflow** dimostrabile
- [ ] Use case **realistico future-of-work**
- [ ] **Production-style web application** (auth, persistenza, monitoring)

## 💡 Tips per il punteggio

| Criterio | Cosa fare |
|---|---|
| **Application of Technology** | Usa **Vultr come system of record** per planning/coordination/execution. Sfrutta **`/chat/completions/RAG`** + Vector Store invece di RAG fatto a mano. Imposta IAM con service user resource-scoped. |
| **Presentation** | README con il diagramma architetturale (sezione 0). Slide con i 2-3 endpoint chiave usati. Demo video che mostra: input utente → tool call → retrieval → risposta. |
| **Business Value** | Scegli un caso d'uso enterprise misurabile (es. customer support su 10k FAQ, sales playbook automation, HR onboarding). Quantifica tempo risparmiato / ticket deflection rate. |
| **Originality** | Combinazione **multi-tool agentic + RAG su collection privata + audit log Postgres** che dimostri comportamenti decisionali emergenti, non solo Q&A. |

## 💰 Stima costi demo hackathon

⚠️ **CHIARIMENTO ufficiale dal Q&A:** Vultr **NON fornisce extra credits** dedicati a questo hackathon (a differenza di Featherless e Speechmatics). I credit citati nei premi ($1.000 ai vincitori) sono **post-evento**.

→ Per la fase di build si usa il **free trial standard di Vultr: $250 credit / 30 giorni** per nuovi account.

| Voce | Costo / mese | Per la finestra hackathon (8 gg) |
|---|---|---|
| Cloud Compute HP 2vCPU/4GB | $24 | ~$6 |
| Managed Postgres HP 1GB/1vCPU | $18 | ~$5 |
| Load Balancer | $10 | ~$3 |
| Object Storage 100GB | $1.80 | ~$0.5 |
| Serverless Inference tokens (1M chiamate medie demo) | — | ~$1-3 |
| **Totale** | **~$54/mese** | **~$15-18** |

**Free trial $250** → coperti ~30 giorni di lavoro completo, ampiamente sufficiente per la demo hackathon. **Apri l'account Vultr ora** se non l'hai già: il trial è una sola volta per email.
