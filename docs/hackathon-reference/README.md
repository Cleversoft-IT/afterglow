# AI Agent Olympics Hackathon — Knowledge Base

> Documentazione strutturata della **AI Agent Olympics Hackathon** — l'hackathon ufficiale di **Milan AI Week 2026** (13–20 maggio 2026, Fiera Milano Rho).
>
> Fonte primaria: https://lablab.ai/ai-hackathons/milan-ai-week-hackathon
> Documenti arricchiti leggendo le pagine reference linkate dal sito ufficiale + kick-off stream + Q&A live Discord.

## 📊 Numeri della knowledge base

| Metrica | Valore |
|---|---|
| File MD totali | **15** (14 contenuto + 1 README) |
| Righe complessive | **3.795** |
| Parole | **~22.900** |
| Dimensione totale | **~200 KB** |
| File deep-dive operativi | 2 (Vultr · Gemini) |
| Tutorial ufficiale integrato | 1 (Gemini + Vultr Document Agent, by lablab.ai) |
| File più corposo | `13-gemini-deep-dive.md` (~940 righe, 36 KB) |
| Sezioni della pagina lablab coperte | 11 su 12 (Speakers escluso su richiesta) |
| Pagine reference esterne lette | **30+** (incluse docs Vultr/Gemini/Kraken/Featherless/Speechmatics/AI Week/lablab.ai/ADK tutorial) |
| Fonti aggiuntive integrate | Kick-off stream (13/05 17:00 CEST) + Q&A live Discord (13/05 18:00 CEST) + Tutorial ufficiale Gemini+Vultr (8/5/2026) |

## Indice dei file

| # | File | Contenuto |
|---|---|---|
| 01 | [01-about.md](./01-about.md) | Cosa è AI Agent Olympics + contesto Milan AI Week |
| 02 | [02-challenge.md](./02-challenge.md) | Obiettivo della sfida + 5 tracks |
| 03 | [03-technology-partners.md](./03-technology-partners.md) | Vultr, Gemini, Kraken, Featherless, Speechmatics (con quickstart, modelli, pricing, snippet) + Workshops |
| 04 | [04-prizes.md](./04-prizes.md) | Prize pool $28.000+ + termini |
| 05 | [05-community-and-social-channels.md](./05-community-and-social-channels.md) | Tutti i canali ufficiali |
| 06 | [06-what-to-submit.md](./06-what-to-submit.md) | Submission form, requisiti, checklist |
| 07 | [07-judging-criteria.md](./07-judging-criteria.md) | I 4 criteri ufficiali + Kraken metrics |
| 08 | [08-hackathon-details.md](./08-hackathon-details.md) | Logistica, regole, team, mentor, payout |
| 09 | [09-event-schedule.md](./09-event-schedule.md) | Timeline e programma kick-off |
| 10 | [10-submissions.md](./10-submissions.md) | Progetti già sottomessi |
| 11 | [11-teams.md](./11-teams.md) | Team iscritti + come unirsi |
| 12 | [12-vultr-deep-dive.md](./12-vultr-deep-dive.md) | ⭐ **Approfondimento Vultr** — Serverless Inference, Vector Store + RAG, Coolify, Supabase, IAM, pricing, stack consigliato |
| 13 | [13-gemini-deep-dive.md](./13-gemini-deep-dive.md) | ⭐ **Approfondimento Gemini** — Function calling, grounding, structured output, code execution, Interactions API, Live API, multimodal, embeddings, caching, thinking, ADK |
| 14 | [14-tutorial-gemini-vultr-document-agent.md](./14-tutorial-gemini-vultr-document-agent.md) | 🚀 **Tutorial ufficiale lablab.ai** — combo Vultr+Gemini: Google ADK + Gemini 2.5 Flash + FastAPI + Docker → enterprise document intelligence agent. GitHub repo riusabile come baseline. **PUBBLICATO 8/5/2026** |

> 🚫 La sezione **Speakers** della pagina ufficiale è stata **esclusa** dalla documentazione (su richiesta dell'utente: "tranne speakers, inutile").
>
> ⭐ I file **12** e **13** sono deep-dive operativi pensati per il team che concorre ai premi **Best use of Vultr** e **Best use of Gemini**.
> 🚀 Il file **14** è un tutorial **ufficiale lablab.ai** che combina entrambe le tracks scelte — direttamente forkable come baseline.

## Lettura consigliata

- **Per decidere se partecipare:** `01-about.md` → `02-challenge.md` → `04-prizes.md`
- **Per scegliere la track:** `02-challenge.md` → `03-technology-partners.md`
- **🚀 Per partire SUBITO con un baseline funzionante (Vultr+Gemini):** `14-tutorial-gemini-vultr-document-agent.md` → forkare il GitHub repo e adattarlo al proprio dominio enterprise
- **🎯 Per costruire la soluzione (premi Vultr + Google):** `12-vultr-deep-dive.md` → `13-gemini-deep-dive.md` → `14-tutorial-gemini-vultr-document-agent.md`
- **Per preparare la submission:** `06-what-to-submit.md` → `07-judging-criteria.md`
- **Per registrarsi e organizzarsi:** `08-hackathon-details.md` → `09-event-schedule.md` → `05-community-and-social-channels.md`
- **Per ispirarsi:** `10-submissions.md` → `11-teams.md`

## 🎙️ Highlights dal kick-off (13 maggio 2026, 17:00 CEST)

Info chiave emerse durante lo stream ufficiale di apertura — integrate nei file relativi:

- 🎟️ **Coupon Speechmatics rivelato:** `AI WEEK 200` (primi 200 partecipanti, $200 credit · vedi `03-technology-partners.md`)
- ⚡ **Featherless = Premium plan unlimited tokens per 1 mese** (primi 1.000 · vedi `03-technology-partners.md`)
- 🎫 **Pass on-site Milano = anche conference pass Milan AI Week** (vedi `01-about.md`)
- 🏷️ **Mentor tags ufficiali Discord:** `@vultrmentors`, `@krakenmentors`, `@featherlessmentors`, `@speechmaticsmentors` (vedi `05-community-and-social-channels.md`)
- 📹 **Submission video MP4:** upload diretto sulla piattaforma — **no YouTube/Drive** (vedi `06-what-to-submit.md`)
- 💾 **Submission editabile** dopo Submit, fino alla deadline + supporta draft (vedi `06-what-to-submit.md`)
- 🌐 **Ecosystem:** 275K+ builder su lablab.ai · 70K+ attivi su Discord

## 🚀 Highlights dal tutorial ufficiale (pubblicato 8 maggio 2026)

Lablab.ai ha pubblicato 5 giorni prima del kick-off un tutorial che combina **esattamente** Vultr + Gemini (le 2 tracks scelte). Documentato in `14-tutorial-gemini-vultr-document-agent.md`:

- 📦 **Stack:** Python 3.11 · **Google ADK 1.18** · **Gemini 2.5 Flash** · FastAPI · Docker · Vultr Cloud Compute
- 🎯 **Use case:** Multimodal document intelligence agent (invoice / contract / general docs → JSON strutturato)
- 🐙 **GitHub repo riusabile come baseline:** https://github.com/Stephen-Kimoi/gemini-multimodal-document-agent
- 💡 **Pattern chiave:** tool-state per output strutturati (no JSON prompt engineering) · `types.Part.from_bytes` multimodal nativo · `list[str]` obbligatorio nei tool param Gemini
- 🚢 **Deploy:** Vultr vc2-1c-1gb ($5/mese, Amsterdam, Ubuntu 24.04) — coperto dal free trial $250/30gg
- ✅ **Direttamente eligible** per **Vultr Award + Google Award** simultaneamente

## 💬 Highlights dal Q&A live Discord (13 maggio 2026, 18:00 CEST)

Chiarimenti su domande dei partecipanti:

- 🔐 **IP del progetto resta al team** — lablab è solo platform per showcase (vedi `08-hackathon-details.md`)
- 🏆 **Multi-partner award eligibility:** un progetto può vincere in PIÙ categorie, MA devi **taggare esplicitamente** ogni tech nel submission form (vedi `06-what-to-submit.md` e `07-judging-criteria.md`)
- 🧑‍⚖️ **Judges:** mix lablab + partner — Isaac (Featherless) e Edgars (Speechmatics) giudicano i progetti che usano le rispettive tech (vedi `07-judging-criteria.md`)
- 📅 **Judging window:** 19 – 25 maggio 2026 (vedi `09-event-schedule.md` e `07-judging-criteria.md`)
- 🏟️ **Winners on stage:** 20 maggio 2026 a Milan AI Week, davanti a 25.000 persone (vedi `04-prizes.md`)
- ⚠️ **Vultr non ha extra credits hackathon** — usa il free trial standard $250/30gg (vedi `03-technology-partners.md` e `12-vultr-deep-dive.md`)
- 📺 **No spam cross-channel** su Discord — usa il channel del partner specifico (vedi `05-community-and-social-channels.md`)
- 🎫 **On-site:** posti limitati, ma lablab cerca di accomodare tutti — se non arriva email conferma, **ticket interno** lablab (NON external) (vedi `08-hackathon-details.md`)

## Note sulla raccolta dei contenuti

Tutta la documentazione è stata raccolta in data **13 maggio 2026**, leggendo:

1. La pagina ufficiale lablab.ai
2. Le pagine reference linkate per ogni sezione, tra cui:
   - https://www.aiweek.it/en/
   - Docs Vultr (docs.vultr.com)
   - Docs Gemini (ai.google.dev) + Google AI Studio
   - GitHub krakenfx/kraken-cli + docs.xstocks.fi
   - Featherless (featherless.ai)
   - Speechmatics (speechmatics.com, docs, GitHub)
   - Guide lablab.ai (delivering-your-hackathon-solution, hackathon-guidelines, getting-started-guide, terms-of-use)
   - **Tutorial ufficiale lablab.ai** (gemini-multimodal-document-agent-vultr-for-ai-hackathons) + GitHub repo demo (Stephen-Kimoi/gemini-multimodal-document-agent)

Una pagina non è stata letta direttamente perché bloccata per safety restrictions:

- https://www.kraken.com/xstocks (sostituita con info da `docs.xstocks.fi` e dal README di `kraken-cli`)
