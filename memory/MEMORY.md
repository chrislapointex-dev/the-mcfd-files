# The MCFD Files — Claude Memory
Last updated: 2026-03-02

## Project
Legal research tool for BC child protection (MCFD) decisions.
Audiences: parents, journalists, lawyers.
Stack: FastAPI + PostgreSQL/pgvector + React/Vite + Tailwind + D3.

## Repo Layout
```
the-mcfd-files/
  backend/        FastAPI app (app/main.py entry)
  frontend/src/   React app
    App.jsx              — main layout, all search/ask/semantic state
    components/
      AskPanel.jsx       — multi-turn Q&A thread
      SemanticPanel.jsx  — vector results grouped by decision
      DecisionDetail.jsx — single decision view
      DecisionCard.jsx   — card in list/search results
      FilterBar.jsx      — filters (source, court, date)
      MemoryPanel.jsx    — R2 memory browser
    pages/
      PatternMapper.jsx  — D3 force graph (judge×outcome co-occurrence)
      About.jsx
  memory/         this dir — Claude cross-session notes
```

## API Endpoints (backend)
- GET  /api/decisions          — paginated browse (FTS via ?q=)
- GET  /api/decisions/{id}     — single decision detail
- GET  /api/decisions/filters  — source/court/year options
- POST /api/ask/stream         — SSE streaming Claude Q&A (R2 memory)
- GET  /api/search/semantic    — HNSW vector search (?q=&k=)
- GET  /api/patterns/co-occurrence   — entity pair analysis
- GET  /api/patterns/entities/{val}  — entity appearances + co-entities
- GET  /api/patterns/timeline        — entity decisions by date

## Running
docker compose up  (db:5432, backend:8000, frontend:5173)
Frontend HMR is live — edits to src/ reload instantly.

## Search Modes (App.jsx)
- FTS (search): full-text search via Postgres, query = submittedQuery
- VECTOR (semantic): HNSW semantic search, state = semanticResults
- ASK: streaming Claude Q&A, state = askMessages[]

## Ask Mode State (multi-turn, as of Session 11)
askMessages = [{ question: string, result: { answer, sources, chunks_used,
  memory_updated, budget, diagnostics } }]
triggerAsk(q) appends a new message and streams into it.
AskPanel receives messages[] + loading + onSelectDecision + onNewConversation.

## Sessions Completed
- Sessions 1–9: data pipeline, scrapers, FTS, semantic search, Claude Q&A,
  R2 memory integration, entity extraction, pattern analysis API, D3 mapper
- Session 10: PatternMapper page (D3 force graph, entity sidebar, timeline)
- Session 11: 4 quick-win UX features (see SESSION-11-AUDIT.md)

## Next Sessions (from 10-idea plan)
- Session 12: Similar Cases panel (#2) + Timeline view (#6)
  - Need: GET /api/decisions/{id}/similar?k=5
  - Need: GET /api/decisions/stats/by-year
- Session 13: Bookmarks / My Case (#5)
- Session 14: Entity Profile Pages (#1)
- Session 15: Analytics Dashboard (#7)
- Session 16: CanLII Citator (#10, needs CANLII_API_KEY)

## Key Patterns
- All Tailwind dark theme: bg-ink-900/800/700, text-slate-*, amber=court, teal=RCY, violet=vector, sky=ask
- Font: IBM Plex Sans (body), IBM Plex Mono (mono), font-display (header)
- No new D3 deps — existing D3 already in PatternMapper only
- CSS-only charts preferred for new analytics (inline style bar widths)
- DecisionCard onClick → setSelectedId → DecisionDetail renders
- Back button in DecisionDetail calls onBack → setSelectedId(null)
