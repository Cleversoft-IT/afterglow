---
name: feedback-audit-collapse-pattern
description: Pattern overview-first per UI list-heavy (call → agent → step → payload).
metadata:
  type: feedback
---

**Regola:** ogni pagina dell'app Expo che può crescere oltre ~100 entries
deve essere **overview-first**, non una FlatList flat. La discriminante
è: "posso ispezionare una singola call/agent/step senza scrollare 350
righe miste?". Se la risposta è no, refactor a Accordion.

**Why:** discussione del round-9 (2026-05-18). L'audit drawer originale
era una `FlatList` di ~350 entries miste (call seed × 5 step × 12
customer). Utile come stream "cosa è successo nelle ultime ore", ma
cieco per ispezionare *una* call — esattamente quello che la RAG attiva
in demo rende il momento "wow" del pitch (audit row `rag_semantic` con
`prior_facts_preview` non vuoto). Una FlatList flat lo seppellisce.
L'overview-first rende ogni call un sub-tree ispezionabile, e collassato
di default così la prima impressione resta una lista pulita di N call.

**How to apply (pattern canonico):**

```
ScrollView
├─ SummaryBanner aggregato (counts/totals — invariato rispetto al flat)
└─ for each top-level entity (call_id, ticket_id, run_id, etc.):
   List.Accordion
     title  = friendly label (display_name ?? phone ?? id)
     desc   = chip status + counts compatti
     left   = avatar/icon colored by worst child status
     right  = IconButton open-in-new → navigate al detail
     children:
       for each grouping (agent, stage, etc.):
         List.Accordion (lazy)
           title = group label + count
           children:
             for each leaf:
               List.Item (chips + tokens + duration + altri metadata)
               + Pressable "Show payload" → Surface monospace JSON
└─ "System events (N)" sezione finale per gli orfani (top-level null)
```

**Vincoli e gotcha:**

- **Default collassato** — la prima impressione resta una pagina
  navigabile, non un wall of text.
- **NO terzo Accordion per il payload**: usare un toggle `Pressable
  "Show payload" → Surface monospace` invece. Tre livelli di Accordion
  rendono brutta UX (l'utente apre tre tap solo per leggere il JSON).
- **Render-on-expand**: `List.Accordion` di Paper renderizza i children
  solo all'apertura — usare quello, non un componente custom che monta
  tutto. Con ~70 call × ~5 step la pagina cold-load resta cheap.
- **Status worst-case sul top-level avatar**: precedenza
  `error > degraded > skipped > success`. Riusare la palette di
  `statusVisuals(status, theme)`; promuovere a un modulo condiviso se
  servirà in più di una pagina.
- **`limit` lato client**: alzare il default API a un cap ragionevole
  (es. 500 per audit; 1000 per call list) PRIMA del rewrite UI,
  altrimenti il group-by salta entries silenziosamente. Pagination via
  cursor è scope futuro.
- **Performance ceiling**: ScrollView outer regge fino a ~100 call
  cards. Oltre, swap a `FlatList` outer (mantieni la nested struttura
  Accordion children).
- **Orphan rows** (es. audit row con `call_id IS NULL`, lifespan
  events): in sezione separata `"System events"` a fondo pagina —
  NON mescolarle col fluxo principale.
- **Date/ora**: passare sempre per `app/lib/dateFormat.ts` (cf.
  [[feedback-locale-dates-only]]), mai `.toLocaleString()` raw.

**Antipattern (cosa NON fare):**

- FlatList flat di 350 entries miste senza grouping — il default
  pre-round-9 dell'audit drawer.
- Accordion default-aperto su tutti i top-level — perde il valore
  "overview".
- Group-by client-side senza alzare il `limit` API — il 30% delle
  entries non compaiono affatto.
- Filtri/search come unico modo di ispezionare una call — funzionano
  per power user, ma il giudice della demo deve poter tappare la
  call e vederne il sub-tree senza pensare al filtro giusto.

**Coordinate del primo applicazione:**

- `app/app/(drawer)/audit.tsx` (rewrite ScrollView +
  List.Accordion, default collassato, IconButton open-in-new per call).
- `app/lib/api.ts.listAudit({ limit: 500 })` default lato
  client.
- `backend/app/schemas/audit.py` + `backend/app/api/audit.py`
  — LEFT JOIN Customer (NON solo Call: `display_name` è su Customer)
  per popolare `call_phone_e164` / `call_display_name` / `call_status`.

**Quando applicarlo di nuovo:** customer list che superasse ~100,
call list filtrata per status, integrations marketplace con N bucket ×
M action, qualsiasi screen "audit-like" futura.
