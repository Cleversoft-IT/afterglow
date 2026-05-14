# Challenge — AI Agent Olympics Hackathon

> Fonte: https://lablab.ai/ai-hackathons/milan-ai-week-hackathon

## Obiettivo della sfida

> **Design and deploy autonomous AI agents that move beyond copilots — into real decision-making systems that create measurable enterprise value.**

In altre parole: progettare e mettere in produzione **agenti AI autonomi** che vadano oltre il paradigma del "copilot" e diventino sistemi decisionali reali, capaci di generare valore enterprise misurabile.

## Le 5 tracks

Ogni team sceglie una track che rispecchia la propria visione. Le track sono complementari ma indipendenti.

### 🧠 1. Intelligent Reasoning

Sfruttare **ragionamento avanzato** per analizzare gli input e prendere decisioni indipendenti.

L'agente deve:

- Gestire ostacoli (roadblocks) in autonomia
- Cambiare il proprio piano senza intervento umano
- Dimostrare capacità di analisi e adattamento

> Adatta a chi vuole esplorare *deep reasoning*, planning, self-correction, chain-of-thought avanzato.

### 🔄 2. Agentic Workflows

Progettare **flussi di lavoro in cui l'agente pianifica autonomamente i propri passi**, chiama tool esterni e gestisce task multi-step nel tempo.

L'agente deve:

- Pianificare i propri step
- Chiamare tool esterni: API, database, browser
- Coordinare task multi-step (long-running) con stato

> Adatta per tool-use, function calling, browser automation, RAG pipeline, scheduler.

### 🌍 3. Enterprise Utility

Risolvere **un attrito reale** che vivono i manager e gli imprenditori presenti ad AI Week.

L'agente deve:

- Affrontare un caso d'uso enterprise concreto
- Avere ricaduta misurabile (tempo risparmiato, errori ridotti, fatturato, …)

> Adatta a soluzioni B2B verticali: ops, sales, marketing, finance, HR, supporto, ecc.

### 🧩 4. Multimodal Intelligence

Sfruttare la capacità di processare **immagini, documenti, audio o video** per abilitare interazioni più ricche.

Esempi:

- Analisi di report aziendali (documenti complessi)
- Lettura di dati dall'ambiente fisico (immagini, video, sensori)
- Trascrizione e analisi conversazioni vocali
- OCR e parsing di scansioni

> Adatta a chi sfrutta Gemini multimodale, Speechmatics, vision pipelines.

### 🤝 5. Collaborative Systems

Costruire un **sistema multi-agente** in cui agenti specializzati coordinano e condividono informazioni per raggiungere un obiettivo di alto livello che un singolo LLM non potrebbe gestire.

Caratteristiche tipiche:

- Più ruoli specializzati (planner, executor, critic, retriever, …)
- Comunicazione strutturata tra agenti (memory condivisa, message bus)
- Orchestrazione e supervisione

> Adatta a framework tipo AutoGen, CrewAI, LangGraph, Pydantic-AI con agent routing.

## Cosa significa "autonomo" in questo hackathon

Lo spirito della competizione, ribadito anche da AI WEEK, è: **non teoria, ma performance**. Gli agenti devono:

1. Risolvere problemi concreti
2. Prendere decisioni autonome (senza human-in-the-loop costante)
3. Dimostrare capacità operative in tempo reale durante il Demo Showcase

## Track + Sponsor — come si combinano

Le 5 track sono **trasversali** ai partner tecnologici. Significa che, ad esempio, una soluzione di *Enterprise Utility* può candidarsi al premio Vultr E **anche** al premio Google se usa Gemini, e così via.

Ogni partner ha però una sfida specifica (vedi `03-technology-partners.md`):

- **Vultr** → Web-based Enterprise Agent deployato su Vultr
- **Google / Gemini** → Agent intelligenti su Gemini + Google AI Studio
- **Kraken** → Trading agent su xStocks via Kraken CLI
- **Featherless** → Domain-specialized agent open-source su modelli Featherless
- **Speechmatics** → Voice-first / real-time speech AI agents
