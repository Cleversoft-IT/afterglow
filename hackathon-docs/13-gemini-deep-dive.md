# Gemini — Deep Dive per "Best use of Gemini"

> Approfondimento dedicato al premio **Google** (1° $5K, 2° $3K, 3° $2K) dell'AI Agent Olympics Hackathon.
> Sfida: **Build intelligent agents or applications using Gemini models and Google AI Studio**.
> Focus: agent agentici, multimodali e production-shaped.

> 📚 **Vedi anche** [`14-tutorial-gemini-vultr-document-agent.md`](./14-tutorial-gemini-vultr-document-agent.md) — tutorial ufficiale lablab.ai con stack completo **Google ADK + Gemini 2.5 Flash + FastAPI + Vultr**, pubblicato 5 giorni prima del kick-off. Pattern *tool-state* per output strutturati, GitHub repo open source come baseline.

## 🎯 Stack consigliato

| Capability | API chiave | Modello consigliato |
|---|---|---|
| **Reasoning multi-step + agentic** | Function Calling + Interactions API | `gemini-3.1-pro-preview` |
| **Real-time / responsive** | `generateContent` + tool | `gemini-3-flash-preview` o `gemini-3.1-flash-lite` |
| **Voice agent** | **Live API** (WebSocket) | `gemini-2.5-flash` (Live) |
| **Multimodal grounded** | Gemini 3 + `google_search` + code execution + function calling combinati | `gemini-3.1-pro-preview` |
| **RAG su corpus aziendale** | Embeddings + Vector Store esterno (oppure tool File Search managed) | `gemini-embedding-2` + `gemini-3.1-pro-preview` |

> ⚠️ **Default Gemini 3:** `temperature = 1.0` (abbassarla peggiora il reasoning) · `thinkingLevel = high` (dynamic) · ricordati di rinviare `id` + `thought_signature` in ogni functionResponse.

---

## 1. 🛠️ Function Calling — la primitiva dell'agent

### Cos'è

Il modello decide quando invocare funzioni esterne e con quali parametri, generando un oggetto `functionCall` strutturato che la tua app esegue e re-immette nel turno successivo.

**Le 3 categorie di tool che puoi combinare:**

1. **Tool integrati Google** — `google_search`, `code_execution`, `url_context`, `file_search`, `maps`
2. **Tool custom** — function declarations OpenAPI-subset
3. **Tool MCP** — Model Context Protocol (gestione automatica dell'execution loop negli SDK Python/JS)

### Schema dichiarazione

Sotto-insieme **OpenAPI**: `name`, `description`, `parameters` con `type` / `properties` / `required` / `enum`.

### Esempio Python (auto function calling SDK)

```python
from google import genai
client = genai.Client()

def set_light_values(brightness: int, color_temp: str) -> dict:
    """Set the lights with brightness 0-100 and color temp warm|cool."""
    return {"brightness": brightness, "color_temp": color_temp}

response = client.models.generate_content(
    model="gemini-3-flash-preview",
    contents="Dim the lights to romantic level",
    config={"tools": [set_light_values]},
)
```

### Flusso request/response

1. **Client:** invia prompt + `tools[]`
2. **Model:** risponde con `functionCall` → `{name, args, id}`
3. **Client:** esegue funzione e re-invia `functionResponse` includendo lo **stesso `id`** + `thought_signature` originale
4. **Model:** risposta finale (oppure altra `functionCall` se chain compositional)

### Feature avanzate

| Feature | Cosa permette |
|---|---|
| **Parallel calling** | Più funzioni in un solo turno; risultati restituibili in ordine arbitrario grazie all'`id` |
| **Compositional / sequential** | Il modello concatena chiamate (es. `get_location` → `get_weather`) |
| **Multi-tool** (Gemini 3) | Combina tool integrati + custom function calling tramite "tool context circulation" (anteprima). **Pre-Gemini 3:** solo via **Live API** |
| **Multimodal function responses** (Gemini 3) | Risposta funzione con parti `inlineData` (`image/png\|jpeg\|webp`, `application/pdf`, `text/plain`), referenziabili con `{"$ref": "<displayName>"}` |
| **Structured output + function calling** (Gemini 3) | Output JSON-schema garantiti anche quando il modello sceglie di rispondere senza tool call |
| **MCP integrato** | SDK Python/JS gestiscono execution loop. ⚠️ Solo tool (no resources/prompts), sperimentale |

### Modalità tool config

| Modalità | Comportamento |
|---|---|
| `AUTO` (default) | Il modello decide se chiamare |
| `ANY` | Sempre tool call. Opzionale `allowed_function_names` |
| `NONE` | Disabilita tool |
| `VALIDATED` | Default quando combini tool integrati o structured output. Vincola schema, riduce call invalide vs `AUTO` |

### Thought signatures (CRITICAL per agent)

I modelli reasoning (Gemini 3 e 2.5) restituiscono `thought_signature` da **rinviare obbligatoriamente** in ogni `functionResponse` per non perdere contesto di pensiero.

- ✅ **SDK Python/JS:** gestione automatica
- ⚠️ **REST diretto:** gestione manuale, non concatenare/mergiare parti con/senza signature

### Limiti

- Solo subset OpenAPI
- In modalità `ANY` schemi grandi/nidificati possono essere rifiutati
- `dict[str: int]` Python non ben supportato
- **Auto function calling** è solo **SDK Python**
- Descrizioni/parametri contano nel limite token input
- Best practice: **max 10–20 tool attivi** (selezione dinamica oltre)

### Modelli compatibili

Tutti i Gemini 3 (Pro/Flash/Flash-Lite incl. preview), 2.5 (Pro/Flash/Flash-Lite), 2.0 Flash — tutti supportano parallel e compositional.

### Variante speciale

`gemini-3.1-pro-preview-customtools` — endpoint dedicato per mix di **bash + tool custom**.

> 🔗 https://ai.google.dev/gemini-api/docs/function-calling

---

## 2. 🌐 Grounding con Google Search

### Cos'è

Tool integrato `google_search` che collega il modello a contenuti web real-time. Il modello pianifica autonomamente le query, esegue la ricerca, sintetizza e ritorna anche `groundingMetadata`.

### Cosa ricevi in risposta

```json
{
  "groundingMetadata": {
    "webSearchQueries": ["UEFA Euro 2024 winner"],
    "searchEntryPoint": "<HTML widget richiesto dai ToS>",
    "groundingChunks": [{"web": {"uri": "...", "title": "uefa.com"}}],
    "groundingSupports": [
      {"segment": {"startIndex": 0, "endIndex": 85, "text": "..."},
       "groundingChunkIndices": [0]}
    ]
  }
}
```

> ⚠️ `searchEntryPoint` HTML è **obbligatorio renderizzarlo** secondo i ToS.

### Modelli compatibili

Gemini 3.1 Pro / Flash-Lite / Flash Image (anteprima), Gemini 3 Pro Image / Flash (anteprima), Gemini 2.5 Pro / Flash / Flash-Lite, 2.0 Flash. *Modelli precedenti usavano `google_search_retrieval` (deprecato).*

### Combinazioni

- Combinabile con **URL context** e **code execution**
- Gemini 3 lo combina con **function calling custom**

### 💰 Pricing extra

| Modello | Billing |
|---|---|
| **Gemini 3** | **Per query** di ricerca (il modello può fare più query in una call → più utilizzi fatturabili). Query vuote non contano |
| **Gemini 2.5 e precedenti** | **Per prompt** |

> Free tier: **500 RPD** per Flash / Flash-Lite (non Pro).
> Paid Gemini 3: 5.000 prompt/mese gratis, poi **$14 / 1.000 query**.

> 🔗 https://ai.google.dev/gemini-api/docs/google-search

---

## 3. 📐 Structured Output

### Cos'è

Vincola la risposta a uno **schema JSON**. Ideale per estrazione dati, classificazione e generazione di input strutturati per tool/API in workflow agentici.

### Tipi supportati nello schema

| Tipo | Note |
|---|---|
| `string` | + `enum`, `format` (`date-time`/`date`/`time`) |
| `number`, `integer` | + `enum`, `minimum`, `maximum` |
| `boolean` | — |
| `object` | + `properties`, `required`, `additionalProperties` |
| `array` | + `items`, `prefixItems` (tupla), `minItems`, `maxItems` |
| `null` | Via `["string","null"]` |

### Esempio Python (Pydantic)

```python
from pydantic import BaseModel

class Ingredient(BaseModel):
    name: str
    quantity: str

class Recipe(BaseModel):
    recipe_name: str
    ingredients: list[Ingredient]

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="Extract recipe from: ...",
    config={
        "response_mime_type": "application/json",
        "response_schema": Recipe,
    },
)
```

> SDK Python supporta Pydantic, SDK JS supporta Zod.

### Streaming

Supportato — chunk = stringhe JSON parziali concatenabili.

### Modelli compatibili

Gemini 3.1 Pro / Flash-Lite (anche preview), Gemini 3 Flash preview, 2.5 Pro / Flash / Flash-Lite, 2.0 Flash / Flash-Lite (questi ultimi richiedono `propertyOrdering` esplicito).

### 🆕 Gemini 3 (anteprima)

Combinabile con **tool integrati** (Search, URL context, code execution, file search) **e function calling**. Il modello sceglie tra tool call o output strutturato.

### Limiti

- Solo **subset** dello schema JSON (proprietà non supportate ignorate)
- Schemi grandi/profondi possono essere rifiutati
- Validazione semantica resta a carico del client

> 🔗 https://ai.google.dev/gemini-api/docs/structured-output

---

## 4. 💻 Code Execution

### Cos'è

Tool builtin che permette al modello di **generare ed eseguire codice Python** in sandbox, iterando sui risultati fino all'output finale. Utile per matematica, parsing, analisi dati, generazione grafici, ispezione immagini.

### Cosa ricevi in risposta

Parti `text`, `executableCode`, `codeExecutionResult` interleaved.

### 🆕 Gemini 3 Flash — Code execution **con immagini**

- **Zoom su dettagli piccoli** (lettura indicatori distanti) — automatico
- **Matematica visiva** (es. somma righe di una ricevuta) — richiesta esplicita
- **Annotazione immagini** — richiesta esplicita

Va abilitato code execution + reasoning.

### Limiti operativi

| Limite | Valore |
|---|---|
| Durata massima ambiente | **30 secondi** |
| Rigenerazione su errore | Fino a **5 volte** |
| File input | Max = finestra token modello (~1M in AI Studio, ~2 MB per file di testo) |
| Linguaggi | **Solo Python** |
| Plot | **Solo matplotlib** |
| Librerie custom | ❌ Non installabili |

### Librerie pre-installate (selezione)

`numpy`, `pandas`, `scikit-learn`, `scipy`, `matplotlib`, `seaborn`, `tensorflow`, `opencv-python`, `pillow`, `PyPDF2`, `python-docx`, `python-pptx`, `openpyxl`, `xlrd`, `reportlab`, `pylatex`, `lxml`, `jinja2`, `joblib`, `sympy`, `mpmath`, `chess`, `geopandas`, `imageio`, `striprtf`, `tabulate`, `toolz`, …

### 💰 Costi extra

**Nessun costo aggiuntivo** per abilitare il tool. Si pagano:

- Token input + codice generato + risultato esecuzione + reasoning + summary
- Token **intermedi → input**; **finali → output**
- L'API include il count dei token intermedi nella risposta

### Combinazioni

- Combinabile con **grounding Search**
- Con **Gemini 3**: anche con **function calling** (richiede `id` + `thought_signature`)

> 🔗 https://ai.google.dev/gemini-api/docs/code-execution

---

## 5. 🆕 Interactions API (beta) — raccomandata per agent

### Cos'è

Nuova primitiva **in beta**, raccomandata per nuovi progetti agentici. Sostituisce `generateContent` con risorse `Interaction` (record di sessione con cronologia completa, passi tipizzati: thoughts, tool call/result, model_output). Ottimizzata per workflow multi-step, multi-turn e multimodali con **stato server-side**.

### Vantaggi vs `generateContent`

| Feature | Beneficio |
|---|---|
| **Stato server** | `previous_interaction_id` evita di reinviare la cronologia (cache implicita migliorata) |
| **Passi tipizzati osservabili** | Facilita debug e rendering UI per eventi intermedi (thoughts, search widget) |
| **Background execution** | `background=true` per task lunghi (Deep Research / Deep Think) |
| **Accesso esclusivo** | Nuovi modelli e agent (Deep Research) saranno rilasciati **solo qui** |

### Storage

| Tier | Retention |
|---|---|
| **Paid** | 55 giorni |
| **Free** | 1 giorno |

- Default `store=true`
- `store=false` disponibile ma **incompatibile** con `background=true` e impedisce `previous_interaction_id`
- Solo `tools`, `system_instruction` e `generation_config` (incl. `thinking_level`) sono **scope-interazione** e vanno **re-specificati ogni turno**

### Modelli supportati

- `gemini-3.1-flash-lite` (+ preview)
- `gemini-3.1-pro-preview`
- `gemini-3-flash-preview`
- `gemini-2.5-pro` / `gemini-2.5-flash` / `gemini-2.5-flash-lite`
- `lyria-3-clip-preview`, `lyria-3-pro-preview`

### Agent supportati

- `deep-research-pro-preview-12-2025`
- `deep-research-preview-04-2026`
- `deep-research-max-preview-04-2026`

### SDK richiesti

- Python `google-genai ≥ 1.55.0`
- JS `@google/genai ≥ 1.33.0`

### Limitazioni beta

- Possibili breaking changes (schema steps aggiornato maggio 2026)
- Mancano: `video_metadata`, Batch API, automatic function calling Python
- Caching esplicito **non disponibile** (implicito via `previous_interaction_id` sì)
- Remote MCP non ancora su Gemini 3

### ⚠️ Quando NON usarla

Per **produzione stabile** usa ancora `generateContent`. Interactions API è ideale per **demo hackathon agentiche** dove vuoi mostrare passi intermedi tipizzati (= bonus "Originality" + "Presentation").

> 🔗 https://ai.google.dev/gemini-api/docs/interactions

---

## 6. 🎙️ Live API — voice / video agent real-time

### Cos'è

API real-time low-latency per agent vocali/video conversazionali. Stream continui audio/video/testo bidirezionali via **WebSocket**.

### Specifiche tecniche

| Aspetto | Valore |
|---|---|
| **Input audio** | PCM 16-bit **16 kHz** little-endian |
| **Output audio** | PCM 16-bit **24 kHz** little-endian |
| **Input immagini** | JPEG, ≤ **1 FPS** |
| **Input testo** | Sì |
| **Protocollo** | WebSocket stateful (WSS) |
| **Lingue** | **70** |

### Feature native

- ✅ Interruzione utente (barge-in)
- ✅ **Function calling + Google Search** (compositional nativo — l'unico modo pre-Gemini 3)
- ✅ Trascrizioni audio (input + output)
- ✅ Audio proattivo (controllo contesto di risposta)
- ✅ Dialogo empatico

### Pattern di integrazione

| Pattern | Use case |
|---|---|
| **Server-to-server** | Backend connette al WebSocket, client invia stream al backend |
| **Client-to-server** | Frontend connette direttamente (migliori prestazioni audio/video). **Per produzione usa token effimeri**, non API key standard |

### Integrazioni partner (utili per l'hackathon)

- **LiveKit Agents** ⭐
- **Pipecat by Daily** ⭐
- **Fishjam** (Software Mansion)
- **Vision Agents** (Stream)
- **Voximplant** · **Agora**
- **Firebase AI Logic**
- **Agent Development Kit (ADK)** supporta streaming

> 🔗 https://ai.google.dev/gemini-api/docs/live-api

---

## 7. 🖼️ Vision (Image Understanding)

### Cosa puoi fare

Captioning · classification · VQA · object detection (bounding box) · prompting multi-image.

### I/O

| Aspetto | Valore |
|---|---|
| Input | `inlineData` (Base64) o **Files API** |
| Max inline | **20 MB richiesta totale** |
| Bounding box | Coordinate `[0,1000]` normalizzate → riscalare alle dimensioni originali |
| Etichette | Custom supportate |

### Formati supportati

`image/png`, `image/jpeg`, `image/webp`, `image/heic`, `image/heif`

### Limiti

- **Max 3600 immagini per richiesta**
- Tokenizzazione: **258 token** se entrambe dimensioni ≤ 384 px. Immagini più grandi: tile 768×768, 258 token/tile. Approx: `unit = floor(min(w,h)/1.5)`; `tiles = (w/unit) * (h/unit)`

### 🆕 Gemini 3 — `media_resolution`

Controllo granulare (`low` / `medium` / `high` / `ultra_high`) per parte multimediale: bilancia accuratezza testo fine vs token/latenza.

> 🔗 https://ai.google.dev/gemini-api/docs/image-understanding

---

## 8. 🔊 Audio Understanding

### Cosa puoi fare

Trascrizione, traduzione, summary, Q&A su audio, detection emozioni voce/musica, analisi segmenti con timestamp.

> Per trascrizione **real-time** usa **Live API** o **Cloud Speech-to-Text**.

### I/O

- Files API (>20 MB) o inline (≤20 MB)
- Timestamp nel prompt in formato `MM:SS`
- `countTokens` per stimare costi

### Formati supportati

WAV · MP3 · AIFF · AAC · OGG Vorbis · FLAC

### Specifiche

| Aspetto | Valore |
|---|---|
| Tokenizzazione | **32 token / secondo** (= 1.920 token / minuto) |
| Durata max | **9,5 ore** per prompt totale (più file ammessi) |
| Downsampling | Auto a 16 kbps |
| Multi-canale | Mix automatico → mono |
| Riconoscimento | Anche componenti non vocali (uccelli, sirene) |

> 🔗 https://ai.google.dev/gemini-api/docs/audio

---

## 9. 🎬 Video Understanding

### Metodi di input

| Metodo | Dim. max | Caso d'uso |
|---|---|---|
| **Files API** | 20 GB (paid) / 2 GB (free) | >100 MB, >10 min, riutilizzo |
| **Cloud Storage** | 2 GB per file, no limit storage | File persistenti |
| **Inline** | <100 MB | <1 min, one-shot |
| **YouTube URL** | N/D | Solo video pubblici |

### YouTube (anteprima, gratis)

- **Free tier:** max **8 ore/giorno** di video YouTube
- **Paid:** nessun limite durata
- **Pre-2.5:** 1 video/request
- **Gemini 2.5+:** fino a **10 video/request**
- Solo video **pubblici** (no privati / unlisted)

### Tokenizzazione (default 1 FPS)

| Componente | Token |
|---|---|
| Frame (default) | **258 token/frame** |
| Frame (`mediaResolution=low`) | **66 token/frame** |
| Audio | 32 token/sec |
| **Totale** | **~300 token/sec** default / **~100 token/sec** low |

### Long video

Modelli a 1M context: **1 ora video default**, **3 ore con low-res**. Usa **context caching** per video > 10 min o riuso multiplo.

### Customizzazione

`videoMetadata` con:

- `offset` start/end (cropping)
- `fps` custom (sotto 1 per video statici tipo lezioni, sopra per azione rapida)

### Formati

mp4 · mpeg · quicktime · avi · x-flv · mpg · webm · wmv · 3gpp

### Best practice

- Un solo video per prompt per risultati ottimali
- Prompt testo **dopo** la parte video

> 🔗 https://ai.google.dev/gemini-api/docs/video-understanding

---

## 10. 📄 Document Processing (PDF)

### Cosa puoi fare

PDF processing con **vision nativa**: testo, immagini, diagrammi, tabelle, grafici. Estrazione strutturata, Q&A, trascrizione preservando layout.

### Limiti operativi

| Limite | Valore |
|---|---|
| Max dim | **50 MB** o **1.000 pagine** per PDF |
| Token / pagina | **258 token** (post-rendering a immagine) |
| Rescaling | Pagine grandi → max 3072×3072 · pagine piccole → upscaling 768×768 |
| Multi-PDF | Fino a 1.000 pagine totali, entro context window |

### 🆕 Gemini 3 — `media_resolution`

- **Testo nativo estratto dal PDF NON viene fatturato** (solo token immagine pagine)
- I token del rendering pagina contati come modalità `IMAGE` (non più `DOCUMENT`)

### Altri tipi documento

TXT, MD, HTML, XML accettati ma trattati come **testo semplice** (no comprensione layout).

> 🔗 https://ai.google.dev/gemini-api/docs/document-processing

---

## 11. 🧠 Long Context (1M+ token)

### Use case sbloccati

- Riassunto large corpus (no sliding window)
- **Q&A senza RAG** (se la knowledge sta entro 1M)
- **Many-shot in-context learning** (100-1.000 esempi, paragonabile al fine-tuning)
- Workflow agentici (stato completo agent + obiettivo)
- Video lunghi (1h default / 3h low-res), audio long-form, codebase

### Equivalenze pratiche

1M token ≈ **50K righe codice** / 8 romanzi medi / 200+ episodi podcast.

### Ottimizzazione costi

- **Context caching** → **4× più economico** vs token standard input (esempio chat-con-i-tuoi-dati)
- Combina con **Interactions API + `previous_interaction_id`** per caching implicito

### Limiti

- Recall **single-needle ~99%**; con multiple needles le performance calano (tradeoff costo/recall)
- Latenza minima fissa, ma TTFT cresce con la lunghezza prompt
- **Posiziona la query alla fine** del prompt dopo il contesto

> 🔗 https://ai.google.dev/gemini-api/docs/long-context

---

## 12. 🔢 Embeddings — `gemini-embedding-2` (multimodale)

### Modelli disponibili

| Modello | Modalità | Note |
|---|---|---|
| **`gemini-embedding-2`** ⭐ | **Multimodale** (testo, image, video, audio, PDF in spazio unificato) | Nuovo, raccomandato |
| `gemini-embedding-001` | Solo testo | Ancora disponibile |

⚠️ Spazi **non compatibili** tra i due → rebuild necessario su upgrade.

### Endpoint

`embedContent` · **Batch API** disponibile al **50% del prezzo standard**

### Specifica del task

#### Per `gemini-embedding-2` (prefisso nel prompt)

```
# Retrieval asimmetrico
task: search result | query: {content}        # lato query
title: {title} | text: {content}              # lato documento

# Varianti
task: question answering | query: {content}
task: fact checking | query: {content}
task: code retrieval | query: {content}

# Retrieval simmetrico
task: classification | query: {content}
task: clustering | query: {content}
task: sentence similarity | query: {content}
```

#### Per `gemini-embedding-001` (parametro `task_type`)

`SEMANTIC_SIMILARITY` · `CLASSIFICATION` · `CLUSTERING` · `RETRIEVAL_DOCUMENT` · `RETRIEVAL_QUERY` · `CODE_RETRIEVAL_QUERY` · `QUESTION_ANSWERING` · `FACT_VERIFICATION`

### Dimensioni (MRL Matryoshka)

| Dimensione | Score MTEB |
|---|---|
| **3072** (default) | — |
| 2048 | 68.16 |
| 1536 | 68.17 |
| 768 | 67.99 |
| 256 | 66.19 |

- Embedding-2 **normalizza automaticamente** le dimensioni troncate
- Embedding-001 richiede **normalizzazione manuale**

### Multimodal limits (embedding-2)

Max **8.192 token input totale**.

| Modalità | Limiti |
|---|---|
| Testo | ≤ 8.192 token |
| Immagini | Max **6 per request**, PNG/JPEG |
| Audio | Max **180s**, MP3/WAV |
| Video | Max **120s**, MP4/MOV, codec H264/H265/AV1/VP9, max 32 frame |
| PDF | Max **6 pagine** |

### Aggregazione

Più parti nello stesso `contents` → **embedding aggregato unico**. Per embedding individuali, wrap in `Content` separati o Batch API.

### Storage suggerito

- **Vector Search 2.0** (Gemini Enterprise Agent Platform)
- BigQuery · AlloyDB · Cloud SQL
- Tutorial con ChromaDB, Qdrant, Weaviate, Pinecone

### Alternativa managed

Tool **File Search** per RAG completamente gestito (citato nelle Files API).

> 🔗 https://ai.google.dev/gemini-api/docs/embeddings

---

## 13. 📁 Files API

### A cosa serve

Upload e gestione file multimediali **riutilizzabili tra request**, alternativa a inline data quando >20 MB (PDF >50 MB).

### Limiti

| Aspetto | Valore |
|---|---|
| Storage | **20 GB per progetto** |
| Max per file | **2 GB** |
| Retention | **48 ore** → eliminazione automatica |
| Disponibilità | **Gratuita** in tutte le regioni Gemini API |
| Download | Solo via metadata `name`/`uri` (no download diretto del contenuto) |

### Operations

`files.upload` · `files.get` (metadata) · `files.list` · `files.delete` (manuale)

### Best practice prompting multimodale

- Istruzioni specifiche
- Few-shot examples
- Breakdown step-by-step
- Formato output esplicito (Markdown/JSON/HTML)
- **Immagine prima del testo** per single-image prompts
- `temperature=1.0` di default su Gemini 3

> 🔗 https://ai.google.dev/gemini-api/docs/files

---

## 14. 💾 Context Caching

### Due meccanismi

#### 1️⃣ Implicit caching

Attivo di default su **Gemini 2.5 e successivi**. **Nessuna garanzia di risparmio.**

| Modello | Min token per hit |
|---|---|
| Gemini 3 Flash (preview) | 1.024 |
| Gemini 3 Pro (preview) | 4.096 |
| Gemini 2.5 Flash | 1.024 |
| Gemini 2.5 Pro | 4.096 |

**Best practice:**
- Contenuti grandi e ricorrenti **all'inizio del prompt**
- Richieste ravvicinate con prefisso simile
- Cache-hit token visibili in `usage_metadata`

#### 2️⃣ Explicit caching

- **Paghi per token cached + storage TTL** (default 1h, customizable)
- Operazioni: create, list (solo metadata), update TTL/expire, delete
- Cached content è prefisso del prompt; non distinguibile dai normali token input dal modello
- **Tariffa ridotta** su token cached riutilizzati
- Compatibile con **OpenAI library** via `cached_content` in `extra_body`

### Quando usare explicit

- Chatbot con system instructions estese
- Analisi ripetuta video lunghi
- Query ricorrenti su grandi doc set
- Codebase Q&A

> 🔗 https://ai.google.dev/gemini-api/docs/caching

---

## 15. 🧩 Thinking / Reasoning

### Cos'è

Processo interno di "pensiero" che migliora reasoning multi-step (coding, math, analisi dati). Disponibile su **Gemini 3 e 2.5**.

### Riepiloghi

`includeThoughts=true` → ricevi `thought=true` nelle parts (anche in streaming, riepiloghi incrementali).

### 🆕 Controllo Gemini 3 — `thinkingLevel`

| Level | 3.1 Pro | 3.1 Flash-Lite | 3 Flash |
|---|---|---|---|
| `minimal` | – | ✓ (default) | ✓ |
| `low` | ✓ | ✓ | ✓ |
| `medium` | ✓ | ✓ | ✓ |
| `high` | ✓ (default, dynamic) | ✓ (dynamic) | ✓ (default, dynamic) |

- `minimal` ≈ "no thinking" ma **non garantito**
- **Gemini 3.1 Pro NON disabilita** il thinking
- Default = `high` dynamic

### Controllo Gemini 2.5 — `thinkingBudget`

| Modello | Default | Range | Off | Dynamic |
|---|---|---|---|---|
| 2.5 Pro | dynamic | 128 – 32.768 | ❌ impossibile | `-1` (default) |
| 2.5 Flash | dynamic | 0 – 24.576 | `0` | `-1` (default) |
| 2.5 Flash-Lite | no thinking | 512 – 24.576 | `0` | `-1` |
| Robotics-ER 1.6 (preview) | dynamic | 0 – 24.576 | `0` | `-1` |

### Thought signatures

Richieste per:

- **Multi-turn con function calling** (Gemini 2.5)
- **Tutte le parti** (Gemini 3)

Gestione automatica negli **SDK** · manuale via **REST** (non concatenare/mergiare parti con/senza signature).

### Prezzi

- Thinking tokens **fatturati come output** (`thoughtsTokenCount`)
- I summary sono gratis, ma il prezzo si basa sui **thinking tokens completi** anche se ricevi solo il summary
- Le signature reinviate **aumentano i token input**

### Compatibilità

Funziona con tutti i tool/strumenti Gemini.

> 🔗 https://ai.google.dev/gemini-api/docs/thinking

---

## 16. 🛡️ Safety Settings

### 4 categorie regolabili

| Categoria | API enum |
|---|---|
| Molestie | `HARM_CATEGORY_HARASSMENT` |
| Incitamento all'odio | `HARM_CATEGORY_HATE_SPEECH` |
| Sessualmente esplicito | (implicito) |
| Pericoloso | (implicito) |

> Protezioni core (es. child safety) **NON modificabili**.

### Soglie

| AI Studio | API |
|---|---|
| Off | `OFF` |
| Nessun blocco | `BLOCK_NONE` |
| Blocco ridotto | `BLOCK_ONLY_HIGH` |
| Blocco limitato | `BLOCK_MEDIUM_AND_ABOVE` |
| Blocco esteso | `BLOCK_LOW_AND_ABOVE` |
| – | `HARM_BLOCK_THRESHOLD_UNSPECIFIED` |

> **Default Gemini 2.5 e 3:** `Off` se non specificato.

### Feedback

- `GenerateContentResponse.promptFeedback.blockReason` → prompt bloccati
- `Candidate.finishReason = SAFETY` + `Candidate.safetyRatings` → response bloccate

> ⚠️ Settings meno restrittive **possono comportare review** secondo i ToS.

> 🔗 https://ai.google.dev/gemini-api/docs/safety-settings

---

## 17. 📦 SDK ufficiali

### SDK GA (raccomandati)

| Linguaggio | Pacchetto |
|---|---|
| Python ⭐ | `google-genai` |
| JavaScript / TypeScript | `@google/genai` |
| Go | `google.golang.org/genai` |
| Java | (nuovo SDK ufficiale, non c'era libreria precedente) |

### 🆕 Google ADK — Agent Development Kit

In aggiunta all'SDK base, Google rilascia **ADK (Agent Development Kit)** — framework specifico per costruire agent agentici complessi:

| Pacchetto | `google-adk` (Python) |
|---|---|
| Versione corrente (al 13/05/2026) | **`1.18.0`** |
| Concetti chiave | `Agent`, `InMemoryRunner`, `ToolContext`, `session_service` |
| Tool pattern | Auto-injection di `ToolContext` come primo parametro · scrittura su `tool_context.state` |
| Multimodal input | `google.genai.types.Part.from_bytes(data, mime_type)` |
| Docs | https://google.github.io/adk-docs/ |

> Pattern d'uso ufficiale: vedi [`14-tutorial-gemini-vultr-document-agent.md`](./14-tutorial-gemini-vultr-document-agent.md) — tutorial completo con codice riutilizzabile.

### Librerie legacy DEPRECATE (retire 30/11/2025)

| Linguaggio | Pacchetto deprecato | Migrazione |
|---|---|---|
| Python | `google-generativeai` | `google-genai` |
| JS | `@google/generativeai` | `@google/genai` |
| Go | `google.golang.org/generative-ai` | `google.golang.org/genai` |
| Dart/Flutter | `google_generative_ai` | Genkit Dart o **Firebase AI Logic** |
| Swift | `generative-ai-swift` | **Firebase AI Logic** |
| Android | `generative-ai-android` | **Firebase AI Logic** |

> ⚠️ Le **legacy non hanno** Live API, Veo e nuove feature.

### Versioni richieste per Interactions API

- Python `google-genai ≥ 1.55.0`
- JS `@google/genai ≥ 1.33.0`

> 🔗 https://ai.google.dev/gemini-api/docs/libraries

---

## 18. 🚀 Google Antigravity

⚠️ **Non documentato** in questo deep-dive: il dominio `antigravity.google` richiede permission non concessa nella sessione corrente, e `antigravity.dev` serve una pagina nginx vuota. Da approfondire direttamente prima del kick-off (probabile risorsa annunciata durante l'evento Google del 13 maggio).

---

## 🎯 Strategia consigliata per il premio Google

### Stack minimale per agent agentico vincente

```
┌──────────────────────────────────────────────────────────────┐
│  Frontend (Next.js / React / Streamlit) — su Vultr           │
│  • UI conversazionale                                        │
│  • Render dei groundingChunks (citazioni cliccabili)         │
│  • Render dei thought summaries (transparency)               │
└──────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────┐
│  Backend Python (FastAPI) — su Vultr Cloud Compute           │
│  • SDK google-genai ≥ 1.55.0                                 │
│  • Interactions API beta                                     │
│    └─ previous_interaction_id per multi-turn                 │
│  • Tools combinati:                                          │
│     - google_search (grounding real-time)                    │
│     - code_execution (analisi dati / grafici)                │
│     - file_search (RAG managed su uploaded docs)             │
│     - custom function calling (API enterprise)               │
│     - MCP tools (es. Slack, Notion, GitHub)                  │
│  • Modello primario: gemini-3.1-pro-preview                  │
│  • Fallback: gemini-3-flash-preview                          │
│  • thinkingLevel: high (dynamic, default)                    │
│  • temperature: 1.0                                          │
└──────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────┐
│  Storage (Vultr Postgres + Object Storage)                   │
│  • Conversation cache (per pre-Interactions fallback)        │
│  • Documenti uploaded (referenziati da file_search)          │
│  • Embeddings con gemini-embedding-2 (multimodale)           │
└──────────────────────────────────────────────────────────────┘
```

### Tips per il punteggio

| Criterio | Cosa fare |
|---|---|
| **Application of Technology** | Usa **Interactions API beta** + **Gemini 3** + **multi-tool combo nativa**. Mostra passi intermedi tipizzati (thoughts, tool calls, structured output). Sfrutta **multimodalità avanzata Gemini 3** (es. code_execution su immagini, function response multimodali) |
| **Presentation** | Render `searchEntryPoint` HTML (ToS), citazioni cliccabili via `groundingSupports`, summary di thinking visibili lato UI |
| **Business Value** | Use case con ROI misurabile: research agent → ore risparmiate, customer support → ticket deflection rate, code review → bug catched |
| **Originality** | Combinazione **multi-tool agentic (search + code + file + custom + MCP)** + **multimodale (immagini, PDF, audio, video)** + **stateful via Interactions API** è una vetrina completa rara nei progetti hackathon |

### Quick wins specifici per Gemini 3

- ✅ **Multimodal function responses**: rispondere con immagini o PDF in functionResponse → unico nei modelli del mercato
- ✅ **Code execution con immagini** (zoom, math visuale, annotazioni)
- ✅ **Structured output + function calling** combinati
- ✅ **Grounding per query** (più granulare di altri modelli)
- ✅ **Thought signatures preservation** = qualità reasoning costante in multi-turn

### Costi stimati per la demo

Modello primario `gemini-3-flash-preview`:

- Input: $0.50 / 1M token
- Output: $3 / 1M token
- 1.000 turni di demo (~500 token input, ~200 token output) → ~**$1**

Modello complesso `gemini-3.1-pro-preview` (≤200K):

- Input: $2 / 1M token
- Output: $12 / 1M token
- 100 turni di demo pesanti → ~**$2-3**

**Free tier:** `gemini-3-flash-preview` e `gemini-3.1-flash-lite` hanno free tier API — costo demo ~**$0** per la parte standard.

**$300 Google Cloud credit** (nuovi account, 90 giorni) → copertura abbondante per stack completo + Vector Search 2.0.

---

## 📚 Link sorgente principali

- Function Calling — https://ai.google.dev/gemini-api/docs/function-calling
- Grounding Google Search — https://ai.google.dev/gemini-api/docs/google-search
- Structured Output — https://ai.google.dev/gemini-api/docs/structured-output
- Code Execution — https://ai.google.dev/gemini-api/docs/code-execution
- Interactions API (beta) — https://ai.google.dev/gemini-api/docs/interactions
- Live API — https://ai.google.dev/gemini-api/docs/live-api
- Image Understanding — https://ai.google.dev/gemini-api/docs/image-understanding
- Audio Understanding — https://ai.google.dev/gemini-api/docs/audio
- Video Understanding — https://ai.google.dev/gemini-api/docs/video-understanding
- Document Processing — https://ai.google.dev/gemini-api/docs/document-processing
- Long Context — https://ai.google.dev/gemini-api/docs/long-context
- Embeddings — https://ai.google.dev/gemini-api/docs/embeddings
- Files API — https://ai.google.dev/gemini-api/docs/files
- Caching — https://ai.google.dev/gemini-api/docs/caching
- Thinking — https://ai.google.dev/gemini-api/docs/thinking
- Safety Settings — https://ai.google.dev/gemini-api/docs/safety-settings
- SDK Libraries — https://ai.google.dev/gemini-api/docs/libraries
