# Judging Criteria — AI Agent Olympics Hackathon

> Fonte: https://lablab.ai/ai-hackathons/milan-ai-week-hackathon
> Allineato con Submission Guidelines: https://lablab.ai/delivering-your-hackathon-solution
> Integrazioni dal Q&A live su Discord (13 maggio 2026, 18:00 CEST).

## 📅 Quando vengono giudicati i progetti

| Data | Cosa succede |
|---|---|
| **19 maggio 2026, 17:00 CEST** | Deadline submission |
| **19 – 25 maggio 2026** | Finestra di **judging** (judges in fusi orari diversi → la fairness è garantita) |
| **20 maggio 2026** | 🏆 **Winner announcement sul palco di Milan AI Week** — i vincitori salgono sul Main Stage davanti a 25.000 persone |

## 👥 Chi giudica i progetti

Confermato al Q&A live:

- **Mix di profili:** giudici con background **tecnico** + giudici con background **business**
- **Mix di organizzazioni:** giudici interni **lablab.ai** + giudici dei **partner**
- Esempi citati al Q&A:
  - **Isaac Gemal** (Featherless) giudica i progetti che usano Featherless
  - **Edgars Adamovics** (Speechmatics) giudica i progetti che usano Speechmatics
- *"All of them are professionals so no worries about that"* — Sophia (lablab) al Q&A
- *"Mostly technical backgrounds, people working in professional environments for big companies"*

## ⭐ Multi-partner eligibility — come funziona davvero (conferma Q&A)

> *"If multiple partners choose projects for their prizes okay it's totally fine. You can win in few categories."* — lablab al Q&A

Il sistema dei premi è **non esclusivo**: un singolo progetto può **vincere in più categorie contemporaneamente** se usa più tecnologie partner.

⚠️ **Attenzione**, però: **NON sei giudicato in tutte le categorie automaticamente**.

> *"It's not that if you use technologies in your projects we will automatically judge in all categories. You need to really be careful when submitting your solution and you actually need to let us know which technologies did you use."*

✅ Devi **taggare esplicitamente** ogni tech partner usata nel **submission form** per essere eligible al rispettivo prize pool. Vedi `06-what-to-submit.md` → sezione *Track tagging*.

I progetti verranno valutati su **4 criteri ufficiali**, con peso (esplicitamente) paritario. Sono gli stessi criteri standard di tutti gli hackathon lablab.ai.

## 1. Application of Technology

> *"How effectively the chosen model(s) are integrated into the solution."*

**Cosa guardano i giudici:**

- Quanto profondamente il modello (Gemini, Featherless model, Speechmatics, ecc.) è integrato — non solo "chiamato"
- Uso di feature avanzate: tool-use, function calling, multimodal, streaming, structured output, RAG, fine-tuning
- Architettura agentica (planning, memory, multi-step, self-correction)
- Scelte tecniche coerenti con il problema risolto

**Bonus multi-tech** (confermato al Q&A da Featherless):

> *"The more APIs you use the more exciting projects become. That's always a little bonus because you are thinking so outside the box."*

Combinare più partner tech (es. Vultr + Gemini + Speechmatics) è **incoraggiato** sia per l'eligibility ai prize pool sia perché viene visto come segnale di pensiero creativo.

**Note specifiche per i premi sponsor:**

- **Vultr Award** richiede deploy effettivo su VM Vultr come system of record
- **Google Award** richiede uso reale di Gemini API o Google AI Studio
- **Kraken Award** richiede uso del Kraken CLI come execution layer
- **Featherless Award** richiede modelli del catalogo Featherless + open source license (MIT/Apache 2.0)

## 2. Presentation

> *"The clarity and effectiveness of the project presentation."*

**Cosa guardano i giudici:**

- Chiarezza del **video pitch** (≤5 min): problema → soluzione → demo
- Quality dello screen-recording / demo live
- Slide PDF concise (2-3 frasi per slide)
- README repo chiaro, con istruzioni di setup riproducibili
- Documentazione architetturale (per Vultr: "Clear explanation of architecture and use case")

## 3. Business Value

> *"The impact and practical value, considering how well it fits into business areas."*

**Cosa guardano i giudici:**

- Caso d'uso reale e identificabile (specie per la track *Enterprise Utility*)
- Mercato indirizzabile: TAM / SAM stimati
- Modello di ricavo plausibile
- Competitive analysis con USP
- Scalabilità futura: roadmap post-hackathon

**Tip ufficiale:** includere queste informazioni nella **Long Description** e nelle slide.

## 4. Originality

> *"The uniqueness & creativity of the solution, highlighting approaches and ability to demonstrate behaviors."*

**Cosa guardano i giudici:**

- Approccio non visto / non banale
- Capacità dell'agente di mostrare comportamenti emergenti, decisionali, adattivi
- Combinazioni inedite di tool, modalità o domini
- Estetica del prodotto (UX/UI) come segno di cura

> Ricordiamo che i Terms of Use richiedono lavoro **originale** e **open source** (MIT salvo diversa indicazione).

## Premi sponsor con regole di scoring proprie

Alcuni premi sono valutati con metriche **quantitative** invece che soggettive:

### Kraken — Trading Performance (PnL)

- Net PnL (realized + unrealized) sul periodo di gara
- Audit di Kraken sui top agent
- Read-only API key fornita da ogni partecipante

### Kraken — Social Engagement

- Score quantitativo su impression, like, share, reach (X, YouTube, blog, IG, LI)
- Finestra di 30 giorni
- Tag obbligatori degli account ufficiali Kraken / lablab.ai / Surge

## Riepilogo pesi e metriche

| Criterio | Tipo | Note |
|---|---|---|
| Application of Technology | Soggettivo (giudici) | Track principale + premi sponsor |
| Presentation | Soggettivo (giudici) | Video + slide + repo |
| Business Value | Soggettivo (giudici) | Specie per *Enterprise Utility* |
| Originality | Soggettivo (giudici) | + Compliance MIT |
| Kraken PnL | Quantitativo | Audit Kraken |
| Kraken Social | Quantitativo | Engagement pubblico |
