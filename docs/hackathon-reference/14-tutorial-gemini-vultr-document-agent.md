# Tutorial ufficiale — Gemini Multimodal Document Agent su Vultr

> 🎯 **Tutorial direttamente rilevante per il team:** combina **Vultr + Gemini** (le 2 tracks scelte).
>
> Fonte ufficiale lablab.ai (pubblicato l'**8 maggio 2026**, 5 giorni prima del kick-off):
> https://lablab.ai/ai-tutorials/gemini-multimodal-document-agent-vultr-for-ai-hackathons
>
> Autore: **Steve Kimoi** (kimoisteve) · GitHub repo: https://github.com/Stephen-Kimoi/gemini-multimodal-document-agent
> Edit on GitHub (lablab community-content): https://github.com/lablab-ai/community-content/tree/main/tutorials/en/gemini-multimodal-document-agent-vultr-for-ai-hackathons.mdx

## 🎁 Perché è importante per noi

- ✅ Pubblicato da **lablab.ai** stesso (l'organizzatore) — segnale forte di "pattern raccomandato"
- ✅ Combina esattamente **Vultr + Gemini** = doppia eligibility (Best use of Vultr + Best use of Gemini)
- ✅ Use case **enterprise concreto** (estrazione strutturata da invoice / contract / general docs) → checka tutti i criteri di *Business Value* e *Enterprise Utility*
- ✅ Stack **production-shaped** (FastAPI + Docker + Vultr Cloud Compute) → fa felici i giudici Vultr
- ✅ Sfrutta **Gemini multimodal** + **function calling** + **tool-state pattern** → fa felici i giudici Google
- ✅ GitHub repo open source riusabile come base

## 📦 Cosa costruisce

> *"A containerized FastAPI service backed by a Google ADK agent that accepts file uploads (PDF, image, plain text), identifies the document type automatically, calls the appropriate extraction tool, and returns clean structured JSON."*

Pattern: **un agent multimodale per estrazione documentale enterprise**.

### Capability

| Tipo doc | Estrae |
|---|---|
| **Invoice** | vendor, invoice number, dates, line items, totals, tax, payment terms |
| **Contract** | parties, effective/expiration dates, obligations, termination conditions, governing law |
| **Images / scanned docs** | testo visibile, key entities, dates, figures |
| **Plain text / Markdown** | title, summary, key entities, dates, key figures, main topics |

## 🛠️ Stack tecnico

| Componente | Versione / dettaglio |
|---|---|
| Python | **3.11** (3.10+ OK) |
| **Google ADK** (Agent Development Kit) | **1.18.0** ⭐ |
| Gemini model | **`gemini-2.5-flash`** |
| Web framework | FastAPI ≥ 0.111.0 |
| ASGI server | `uvicorn[standard]` ≥ 0.29.0 |
| File upload | `python-multipart` ≥ 0.0.9 |
| Validation | `pydantic` ≥ 2.7.0 |
| Env | `python-dotenv` ≥ 1.0.0 |
| Container | Docker + Docker Compose |
| Hosting | Vultr Cloud Compute |

### Vultr instance config raccomandato (dal tutorial)

| Setting | Valore |
|---|---|
| Tipo | **Shared CPU** |
| Location | **Amsterdam** (good latency from most regions) |
| Image | **Ubuntu 24.04 LTS** |
| Plan | **vc2-1c-1gb** ($5/mese, 1 vCPU / 1GB RAM) |
| Hostname | `document-agent` |
| SSH keys | Skip per ora — Vultr emaila la root password |
| Extras | Skip (no backup, no DDoS protection per la demo) |

> 💡 Per la submission hackathon, **vc2-1c-1gb è sufficiente** ($5/mese). Coperto dal free trial Vultr $250/30gg.

## 🏗️ Architettura

```
┌────────────────────────────────────────────────────┐
│  Client (curl, web UI, dashboard)                  │
└────────────────────────────────────────────────────┘
                       │ multipart/form-data POST /analyze
                       ▼
┌────────────────────────────────────────────────────┐
│  FastAPI on Vultr (Ubuntu 24.04, Docker)           │
│  • POST /analyze (file upload, MIME validation)    │
│  • GET /health                                     │
│  • Lifespan: crea InMemoryRunner all'avvio         │
└────────────────────────────────────────────────────┘
                       │
                       ▼
┌────────────────────────────────────────────────────┐
│  Google ADK Agent (gemini-2.5-flash)               │
│  • model = gemini-2.5-flash                        │
│  • instruction = "Enterprise document agent..."    │
│  • tools = [invoice, contract, general]            │
└────────────────────────────────────────────────────┘
                       │
                       ▼
┌────────────────────────────────────────────────────┐
│  InMemoryRunner.run_async()                        │
│  • types.Part.from_bytes(file_bytes, mime_type)    │
│  • Gemini decide quale tool chiamare               │
│  • tool scrive tool_context.state[...]             │
└────────────────────────────────────────────────────┘
                       │
                       ▼
                  Structured JSON Response
```

## 📁 Struttura progetto

```
gemini-multimodal-document-agent/
├── app/
│   ├── __init__.py
│   ├── agent.py        # ADK Agent + runner
│   ├── tools.py        # 3 tool: invoice / contract / general
│   ├── schemas.py      # Pydantic AnalysisResponse
│   └── main.py         # FastAPI app
├── sample_docs/        # File di test
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env                # GOOGLE_API_KEY=...
```

## 💡 Pattern e insegnamenti chiave

### 1. Tool-state pattern per output strutturati (senza prompt engineering tricks)

Il tutorial **non chiede al modello di rispondere con JSON**. Invece:

- Definisce **3 tool** con **parametri tipizzati** (uno per ogni doc type)
- Il modello sceglie un tool e passa i valori come **argomenti**
- Il tool scrive in `tool_context.state["extraction_result"]`
- Dopo la run, leggi lo state → restituisci come JSON

> *"The key design decision is that the tools do not receive the document. Gemini has already read it from the multimodal message context. The tools only receive the extracted fields as typed arguments, which forces the model to commit to specific values rather than returning freeform text."*

### 2. Multimodal input via `types.Part.from_bytes`

```python
content = types.Content(
    role="user",
    parts=[
        types.Part.from_bytes(data=file_bytes, mime_type=mime_type),
        types.Part.from_text(text=prompt),
    ],
)
```

Gemini **legge PDF, immagini e testo nativamente**, senza preprocessing. Niente OCR esterno, niente tesseract.

### 3. ⚠️ Gotcha API Gemini — `list[str]` obbligatorio

> *"The Gemini API generates a JSON schema from your tool's type annotations. An untyped `list` produces a schema without an `items` field, which the API rejects with a 400 INVALID_ARGUMENT error. Using `list[str]` (or any concrete generic) generates the required `items: {type: string}` field automatically."*

✅ `line_items: Optional[list[str]] = None`
❌ `line_items: Optional[list] = None` → **400 INVALID_ARGUMENT**

### 4. `InMemoryRunner` + session per request

- Create runner **una volta al boot** (in `lifespan`)
- Crea una **nuova session per ogni request** (UUID)
- Itera su `run_async()` ma legge solo lo state finale

### 5. ToolContext auto-injected

`ToolContext` è iniettato automaticamente da ADK come primo argomento di ogni tool. **Non instanziarlo manualmente.**

### 6. File size cap a 20MB + escape route

Il tutorial cappa a 20MB con `MAX_FILE_SIZE_MB`. Per file più grandi:

> *"Swap `Part.from_bytes` for the Gemini Files API (`client.files.upload`) and pass a file URI instead. Gemini supports PDFs up to 1,000 pages."*

Vedi `13-gemini-deep-dive.md` → sezione *Files API* e *Document Processing*.

## 🧪 Codice chiave (estratti commentati)

### `app/agent.py` — definizione agent

```python
from google.adk import Agent
from google.adk.runners import InMemoryRunner

INSTRUCTION = """
You are an enterprise document intelligence agent. Your job is to analyze
uploaded documents and extract all relevant structured data from them.

When you receive a document, follow these steps:
1. Identify the document type: invoice, contract, or general.
2. Read the document carefully and extract every relevant field.
3. Call exactly ONE of the following tools with the extracted data.

Rules:
- Extract ALL fields you can find. If a field is missing, pass null.
- Be precise with amounts, dates, and names. Do not infer or guess.
- Always call one of the save tools. Never respond without calling a tool.
"""

def create_runner() -> InMemoryRunner:
    agent = Agent(
        model="gemini-2.5-flash",
        name="document_agent",
        description="Extracts structured data from enterprise documents.",
        instruction=INSTRUCTION,
        tools=[save_invoice_extraction, save_contract_extraction,
               save_general_extraction],
    )
    return InMemoryRunner(agent=agent, app_name=APP_NAME)
```

### `app/tools.py` — tool con state side-effect

```python
def save_invoice_extraction(
    tool_context: ToolContext,
    vendor_name: Optional[str] = None,
    invoice_number: Optional[str] = None,
    line_items: Optional[list[str]] = None,  # 👈 list[str], non list
    # ... altri campi
) -> str:
    """Save structured data extracted from an invoice document."""
    tool_context.state["extraction_result"] = {
        "document_type": "invoice",
        "extracted_data": { ... },
    }
    return "Invoice extraction saved."
```

### `app/main.py` — FastAPI con lifespan + MIME guard

```python
SUPPORTED_MIME_TYPES = {
    "application/pdf",
    "image/jpeg", "image/jpg", "image/png", "image/webp",
    "text/plain", "text/markdown",
}
MAX_FILE_SIZE_MB = 20

@asynccontextmanager
async def lifespan(app: FastAPI):
    if not os.getenv("GOOGLE_API_KEY"):
        raise RuntimeError("GOOGLE_API_KEY environment variable is not set.")
    app.state.runner = create_runner()
    yield

@app.post("/analyze", response_model=AnalysisResponse)
async def analyze(file: UploadFile = File(...)):
    if file.content_type not in SUPPORTED_MIME_TYPES:
        raise HTTPException(415, f"Unsupported file type: {file.content_type}")
    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(413, "File too large. Max 20MB.")
    # ... chiama analyze_document e restituisce JSON
```

### `Dockerfile`

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ ./app/
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### `docker-compose.yml`

```yaml
services:
  app:
    build: .
    ports:
      - "8000:8000"
    env_file:
      - .env
    restart: unless-stopped
```

## 🚀 Quickstart deploy su Vultr (dal tutorial)

```bash
# 1. Provision (via console.vultr.com)
#    - Shared CPU, Amsterdam, Ubuntu 24.04 LTS, vc2-1c-1gb, hostname: document-agent

# 2. SSH al server
ssh root@YOUR_VULTR_IP

# 3. Install Docker
curl -fsSL https://get.docker.com | sh && \
  systemctl enable docker && systemctl start docker

# 4. Copy progetto dal locale al server
scp -r ./gemini-multimodal-document-agent root@YOUR_VULTR_IP:/opt/document-agent

# 5. Sul server: env + deploy
cd /opt/document-agent
echo "GOOGLE_API_KEY=your_api_key_here" > .env
docker compose up -d --build

# 6. Test
curl http://YOUR_VULTR_IP:8000/health
```

Tempo di build prima volta: **2-3 minuti** (pip install Python packages).

## 🎯 Come riusare questo come base per il nostro progetto

### Modifiche minime per espandere

1. **Aggiungi nuovi document type** (es. `save_purchase_order_extraction`):
   - Definisci nuovo tool in `app/tools.py` con parametri tipizzati
   - Aggiungilo alla lista `tools=[...]` in `app/agent.py`
   - Aggiorna `INSTRUCTION` per dire all'agent quando chiamarlo

2. **Persist results**: sostituisci `InMemorySessionService` con session service database-backed → store su **Postgres / Supabase** (vedi `12-vultr-deep-dive.md` per Managed Postgres su Vultr)

3. **File > 20MB**: usa **Gemini Files API** (vedi `13-gemini-deep-dive.md` → *Files API*)

4. **Frontend**: Next.js / React che chiama `/analyze` — deploy su stesso Vultr istanza con **Coolify** (vedi `12-vultr-deep-dive.md`) per HTTPS + dominio custom automatico

5. **Reverse proxy + HTTPS**: aggiungi NGINX davanti a FastAPI con Certbot Let's Encrypt (vedi `12-vultr-deep-dive.md` → *Supabase Marketplace*)

6. **Firewall**: Vultr Firewall Group → restringere porta 8000 a IP fidati (o solo NGINX in front)

### Aree dove andare oltre il tutorial (= bonus Originality)

| Estensione | Impatto |
|---|---|
| **RAG su collection di docs** (es. confronto tra invoice e PO) | Aggiunge *grounding* — usa `gemini-embedding-2` (vedi `13-gemini-deep-dive.md`) |
| **Vector Store Vultr** per cercare doc simili | Sblocca eligibility forte per Vultr (vedi `12-vultr-deep-dive.md` → *Vector Store + RAG*) |
| **Multi-agent collaboration** (es. extractor + validator + summarizer) | Apre la track *Collaborative Systems* |
| **Voice input** via Speechmatics | Aggiunge eligibility Speechmatics (coupon `AI WEEK 200`) |
| **Long-context** (file > 20MB via Files API) | Usa la feature 1M-token di Gemini |
| **Structured output + Function calling combinati** (Gemini 3) | Demo della feature più avanzata di Gemini 3 |
| **Audit log Postgres** dei tool call | Production-shape vero, non solo demo |

## 📺 Esempio di response (dal tutorial)

```json
{
  "document_type": "invoice",
  "filename": "sample_invoice.txt",
  "extracted_data": {
    "vendor_name": "Acme Solutions Ltd.",
    "invoice_number": "INV-2026-0042",
    "invoice_date": "2026-05-05",
    "due_date": "2026-06-04",
    "total_amount": "$6,032.00",
    "currency": "USD",
    "subtotal": "$5,200.00",
    "tax_amount": "$832.00",
    "line_items": [
      "API Integration Services | 1 | $2,500.00 | $2,500.00",
      "Cloud Infrastructure Setup | 1 | $1,200.00 | $1,200.00",
      "Technical Consulting (10 hrs) | 10 | $150.00 | $1,500.00"
    ],
    "payment_terms": "Net 30",
    "billing_address": "TechCorp Inc.\n456 Innovation Drive, Nairobi, Kenya",
    "notes": "Payment Instructions: Bank transfer to Equity Bank..."
  },
  "summary": "Invoice #INV-2026-0042 from Acme Solutions Ltd. for USD $6,032.00."
}
```

## ⚠️ Note critiche

1. **Google ADK ≠ Pydantic-AI**: il tutorial usa **Google Agent Development Kit** (`google-adk==1.18.0`), che è il framework di Google specifico per Gemini. Pattern e API sono diverse da Pydantic-AI / LangChain. Vedere docs: https://google.github.io/adk-docs/
2. **`gemini-2.5-flash` vs Gemini 3:** il tutorial usa la generazione precedente (più stabile e con free tier API). Il team può upgrade a `gemini-3-flash-preview` per fare un punto in più sul criterio *Application of Technology* (vedi `13-gemini-deep-dive.md` per i pro tip Gemini 3 — `thinking_level`, `media_resolution`, multimodal function responses).
3. **Costi:** Vultr vc2-1c-1gb è $5/mese. Coperto dal free trial $250/30gg. Gemini 2.5 Flash è ~$0.30/$2.50 per 1M token — qualche dollaro coprono l'intera fase di test.
4. **Limit 20MB** è arbitrario (cappato nel codice). Files API arriva fino a 2GB / 1.000 pagine PDF.

## 🔗 Reference (tutte le sorgenti del tutorial)

| Risorsa | Link |
|---|---|
| Tutorial post | https://lablab.ai/ai-tutorials/gemini-multimodal-document-agent-vultr-for-ai-hackathons |
| GitHub repo demo (Stephen Kimoi) | https://github.com/Stephen-Kimoi/gemini-multimodal-document-agent |
| Source markdown del tutorial | https://github.com/lablab-ai/community-content/tree/main/tutorials/en/gemini-multimodal-document-agent-vultr-for-ai-hackathons.mdx |
| Google AI Studio (API key) | https://aistudio.google.com/app/apikey |
| Vultr Console | https://console.vultr.com/ |
| Vultr signup | https://vultr.com/ |

## ✅ Take-away per il team

- **Forka il repo come baseline** → ti dà già FastAPI + Docker + ADK setup
- **Espandi con un dominio enterprise specifico** (legal contract review, HR onboarding docs, medical records, sales ops, ecc.) → eligibility *Enterprise Utility*
- **Aggiungi 1-2 sponsor extra** (Speechmatics per voice upload o Featherless per specialized model) → multi-prize-pool eligibility (ricorda di **taggare nel submission form**)
- **Deploy production-shape** (HTTPS + dominio + auth) usando Coolify (vedi `12-vultr-deep-dive.md`)
- **Misura il valore enterprise** (TAM/SAM nel pitch deck, ROI in tempo risparmiato) → eligibility *Business Value*
