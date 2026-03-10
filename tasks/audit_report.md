# Session 50 — Full Codebase Audit Report

**Date:** 2026-03-09
**Project:** The MCFD Files
**Auditor:** Claude Sonnet 4.6 (read-only, no changes made)
**Status:** Pre-deployment audit. Session 49 changes uncommitted.

---

## SECTION 1 — PROJECT OVERVIEW

**Project:** The MCFD Files
**Purpose:** BC child protection (MCFD) legal research platform for personal case (C vs MCFD). Semantic search, contradiction detection, cross-exam generation, cost calculator, trial prep.
**Trial Date:** May 19-21, 2026
**Status:** Deployment-ready. 49 sessions complete. Session 49 changes uncommitted.
**Docker:** All 3 services running (db ✓, backend ✓, frontend ✓)
**Auth:** Production mode (MCFD_API_KEY set)
**Build:** Clean (791 modules, 1.13s)

---

## SECTION 2 — DIRECTORY TREE (3 levels, excl. node_modules/.git/__pycache__/dist/build)

```
/Users/1nd1g0/Projects/the-mcfd-files/
├── .env                                 (gitignored — API keys)
├── .env.example
├── .gitignore
├── README.md
├── Makefile                             (up, down, logs, shell-*, reset)
├── docker-compose.yml                   (3 services: db, backend, frontend)
├── cloudflare/
│   ├── DEPLOY.md                        (step-by-step deployment guide, 177 lines)
│   ├── VAULT.md                         (options A/B/C for 171MB PDF)
│   └── tunnel-config.yml                (cloudflared template — <TUNNEL_ID> to fill)
├── data/
│   ├── raw/                             (bccourts, canlii, foi, personal source dirs)
│   └── vault/
│       └── court-final.pdf              (171MB — gitignored, must deploy manually)
├── backend/
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── alembic/
│   │   ├── env.py
│   │   ├── README
│   │   ├── script.py.mako
│   │   └── versions/
│   │       ├── e2fea8a3872b_initial_schema.py
│   │       └── 1594fe9ae105_add_entities_table.py
│   └── app/
│       ├── __init__.py
│       ├── main.py                      (FastAPI app, 18 routers, CORS, lifespan)
│       ├── auth.py                      (require_api_key dependency)
│       ├── database.py                  (async SQLAlchemy, pgvector, engine)
│       ├── models.py                    (14 ORM models)
│       ├── schemas.py                   (Pydantic request/response models)
│       ├── ratelimit.py                 (in-memory sliding window)
│       ├── routers/
│       │   ├── ask.py                   (Claude Q&A with SSE streaming, R2 memory)
│       │   ├── brain.py                 (GET /api/brain/status)
│       │   ├── checklist.py             (hearing prep checklist)
│       │   ├── complaints.py            (complaint tracker)
│       │   ├── contradictions.py        (GET/POST contradiction analysis)
│       │   ├── costs.py                 (taxpayer cost calculator — PUBLIC)
│       │   ├── crossexam.py             (cross-exam generator)
│       │   ├── decisions.py             (browse, FTS, filters, detail)
│       │   ├── export.py                (trial reports, media package, caryma-brief)
│       │   ├── memory.py                (R2 memory CRUD)
│       │   ├── patterns.py              (entity co-occurrence analysis)
│       │   ├── search.py                (semantic vector search)
│       │   ├── share.py                 (view counter, case strength — PUBLIC)
│       │   ├── timeline.py              (case timeline events)
│       │   ├── trialprep.py             (trial prep summary)
│       │   ├── vault.py                 (secure PDF streaming)
│       │   └── witnesses.py             (witness profiles + evidence chunks)
│       ├── pipeline/
│       │   ├── chunker.py               (text → 500-800 token chunks)
│       │   └── embedder.py              (chunks → 384-dim vectors)
│       └── scripts/
│           ├── seed_costs_v2.py
│           └── seed_timeline.py
├── frontend/
│   ├── index.html                       (OG + Twitter Card tags)
│   ├── package.json
│   ├── package-lock.json
│   ├── vite.config.js                   (backend proxy to :8000)
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   ├── Dockerfile
│   ├── public/
│   │   ├── _redirects                   (/api/* → https://api.themcfdfiles.ca/:splat 200)
│   │   └── og-image.png                 (1200x630 social preview)
│   └── src/
│       ├── main.jsx                     (React Router entry, 20+ routes)
│       ├── App.jsx                      (main search shell: FTS/vector/ask modes)
│       ├── index.css                    (Tailwind + custom scrollbar/print/gradient)
│       ├── components/
│       │   ├── AskPanel.jsx             (multi-turn Q&A thread with SSE streaming)
│       │   ├── DecisionCard.jsx
│       │   ├── DecisionDetail.jsx       (full decision + vault PDF link)
│       │   ├── DiagnosticsPanel.jsx     (ask mode internals: budget, chunks, memory)
│       │   ├── ErrorBoundary.jsx
│       │   ├── FilterBar.jsx            (source, court, date filters)
│       │   ├── MemoryPanel.jsx          (R2 memory browser: cortex/hippocampus/etc)
│       │   ├── Pagination.jsx
│       │   ├── SearchBar.jsx            (multi-mode input)
│       │   ├── SemanticPanel.jsx        (vector results grouped by decision)
│       │   └── TrialBanner.jsx          (countdown alert < 30 days)
│       ├── hooks/
│       │   └── useDecisions.js          (paginated fetch, browse/search/detail modes)
│       └── pages/
│           ├── About.jsx
│           ├── AdminDashboard.jsx       (private: status tables, quick actions)
│           ├── CaseTimeline.jsx
│           ├── ComplaintsTracker.jsx
│           ├── ContradictionEngine.jsx
│           ├── CostCalculator.jsx
│           ├── CrossExamPanel.jsx
│           ├── EventTimeline.jsx
│           ├── HearingChecklist.jsx
│           ├── Methodology.jsx
│           ├── PatternMapper.jsx        (D3 force-directed entity graph)
│           ├── PressKit.jsx
│           ├── PrintView.jsx
│           ├── PublicShare.jsx          (23 contradictions, case strength, social)
│           ├── TrialDashboard.jsx       (countdown, exports, key witnesses)
│           └── WitnessProfiles.jsx
├── memory/
│   ├── MEMORY.md
│   └── SESSION-11-AUDIT.md
├── scripts/
│   └── generate_og_image.py
└── tasks/
    └── todo.md                          (1340 lines, sessions 13-49)
```

---

## SECTION 3 — SESSION HISTORY (tasks/todo.md summary)

| Sessions | Focus | Status |
|----------|-------|--------|
| 13 | Contradiction engine (model, router, frontend page) | ✅ |
| 14 | Case timeline router + frontend | ✅ |
| 15 | Load 6 personal .md files → 43 chunks embedded | ✅ |
| 16 | 1.15x personal boost, brain status router, error handling | ✅ |
| 17-20 | Trial prep, witnesses, exports, checklist | ✅ |
| 21-24 | Contradictions seeded, timeline polish, pattern mapper | ✅ |
| 25-27 | Hearing checklist, complaint tracker, integration | ✅ |
| 28-32 | Load personal/FOI docs, OCR PDFs, trial export | ✅ |
| 33-37 | PDF audit, FOI gap, cross-exam generator, fixes | ✅ |
| 38-40 | Batch cross-exam, cost calculator, FOI gap contradictions | ✅ |
| 41-42 | Cost expansion, public share page, contradiction #23 | ✅ |
| 43 | API key auth middleware, Cloudflare deployment prep | ✅ |
| 44 | Caryma brief PDF, share view counter, OG tags | ✅ |
| 45 | Methodology page, case strength score, contradiction filter, OG image | ✅ |
| 46 | In-memory rate limiting, deploy-check endpoint, press kit | ✅ |
| 47 | PDF v5 audit, admin dashboard, pre-deploy checklist | ✅ |
| 48 | API key generated, vault documentation, domain placeholders noted | ✅ |
| 49 | Domain swap YOUR-DOMAIN.ca→themcfdfiles.ca, deploy-check fix | ✅ (uncommitted) |

---

## SECTION 4 — BACKEND: FULL TECHNICAL DETAIL

### Stack
- Python 3.12 + FastAPI 0.115.0 + Uvicorn (reload mode)
- PostgreSQL 16 + pgvector (384-dim HNSW index)
- SQLAlchemy 2.0 async ORM + asyncpg driver
- Alembic migrations (2 versions applied)
- Anthropic Claude API: claude-sonnet-4-6
- sentence-transformers: all-MiniLM-L6-v2 (384-dim, CPU)
- PyMuPDF (PDF export rendering)

### Database Models (14 tables)

| Table | Rows | Purpose |
|-------|------|---------|
| Decision | 1,498 | Court decisions, RCY reports, legislation, news articles |
| Chunk | 26,701 | 500-800 token chunks with 384-dim embeddings |
| Entity | (extracted) | Named entities (judge, statute, social_worker, lawyer, office, outcome) |
| Memory | (active) | R2-D2 persistent memory (region, category, key, value JSONB) |
| Contradiction | 23 | Analyzed contradictions (DIRECT/PARTIAL/NONE severity) |
| ContradictionEvidence | 23+ | Join: contradiction ↔ chunk (cosine similarity score) |
| CostEntry | 15 | Taxpayer cost line items (category, amount, source) |
| TimelineEvent | 12 | Curated case events (date, title, description, severity) |
| CrossExamQuestion | 23 | AI-generated cross-exam Q sets per contradiction |
| ChecklistItem | (seeded) | Trial prep checklist (EVIDENCE, FILINGS, WITNESSES, LOGISTICS) |
| Complaint | (seeded) | OIPC/RCY complaint tracking |
| ShareView | 0 | Public page view counter (new in session 44) |
| WitnessProfile | 6 | Key witnesses + evidence chunk refs |
| (brain_state) | 1 | Single-row stats counter |

### Routers — 18 total

**Protected (require X-API-Key):**
- `ask.py` — POST /api/ask + /api/ask/stream (Claude Q&A, hybrid search, R2 memory, SSE streaming)
- `brain.py` — GET /api/brain/status
- `checklist.py` — GET/PATCH /api/checklist
- `complaints.py` — GET/PATCH /api/complaints
- `contradictions.py` — GET list, POST analyze, GET /{id}/evidence
- `crossexam.py` — POST /generate, GET /{contradiction_id}
- `decisions.py` — GET paginated list, FTS search, filters, single detail
- `export.py` — GET trial-package (ZIP), trial-report.md, trial-report.pdf (protected); media-package, caryma-brief.pdf (public)
- `memory.py` — GET recall/context/searches
- `patterns.py` — GET entities, co-occurrence, timeline
- `search.py` — GET /semantic, /keyword
- `timeline.py` — GET /timeline, /timeline/events
- `trialprep.py` — GET /summary (days to trial, top contradictions, gap analysis)
- `vault.py` — GET /vault/{filename} (path-traversal-safe PDF streaming)
- `witnesses.py` — GET list, /{name}

**Public (no key):**
- `costs.py` — GET /api/costs, /api/costs/scale (BC projection)
- `share.py` — GET /strength, /views; POST /view
- Health endpoints in main.py — GET /health, /api/deploy-check, /

### Key Design Patterns
- **Hybrid Search in ask.py**: FTS + semantic combined, top 20 chunks, 1.15x personal/FOI boost, name boost for witnesses
- **Citation Validation (validator.py)**: Extract [Source: citation] tags → cosine similarity → VERIFIED(≥0.5)/PARTIAL(≥0.3)/UNVERIFIED(<0.3)
- **R2 Memory**: Every Q&A stored to HIPPOCAMPUS region; context pre-loaded for subsequent questions
- **SSE Streaming**: ask/stream endpoint yields tokens in real-time
- **Budget Allocation**: Context window split between memory items and document chunks
- **Rate Limiting (ratelimit.py)**: In-memory sliding window, no Redis needed

### Auth Model (auth.py)
```
MCFD_API_KEY env var:
  - Set    → production mode: 14 routers require X-API-Key header, 401 without
  - Unset  → dev mode: all endpoints open, no behavior change
Current state: PRODUCTION (key set)
```

### deploy-check Output (current)
```json
{
  "ready": true,
  "checks": {
    "database": { "ok": true, "contradictions": 23, "cost_entries": 15,
                  "timeline_events": 12, "witness_profiles": 6,
                  "cross_exam_sets": 23, "share_views": 0 },
    "auth":     { "ok": true, "mode": "production (key set)" },
    "vault":    { "ok": true, "file": "court-final.pdf" },
    "cloudflare": { "ok": false,
                    "files": { "cloudflare/tunnel-config.yml": false,
                               "frontend/public/_redirects": false },
                    "note": "Domain set to themcfdfiles.ca — fill <TUNNEL_ID> in tunnel-config.yml after tunnel creation" }
  },
  "warnings": [],
  "errors": []
}
```
Note: cloudflare.ok=false is expected — Docker container can't see the cloudflare/ dir (not mounted). Files exist on host. Not a real error.

---

## SECTION 5 — FRONTEND: FULL TECHNICAL DETAIL

### Stack
- React 18.3.1 + React Router 6.26.2
- Vite 5.4.8 (dev server :5173, API proxy → :8000)
- Tailwind CSS 3.4.13 + PostCSS + Autoprefixer
- D3 7.9.0 (force-directed entity graph)
- react-markdown 10.1.0 + DOMPurify 3.3.1 (XSS protection)
- IBM Plex fonts (condensed, sans, mono)

### Pages (16+)

| Page | Route | Auth | Purpose |
|------|-------|------|---------|
| App.jsx | / | key | Main search/browse (FTS/vector/ask modes) |
| TrialDashboard.jsx | /trial | key | Countdown, contradictions, exports, witnesses |
| PublicShare.jsx | /share | none | 23 contradictions, case strength, social |
| AdminDashboard.jsx | /admin | key | Status, tables, quick actions |
| ContradictionEngine.jsx | /contradictions | key | Interactive analysis |
| WitnessProfiles.jsx | /witnesses | key | Per-witness evidence chunks |
| CaseTimeline.jsx | /timeline | key | Chunk-extracted date events |
| EventTimeline.jsx | /event-timeline | key | Curated timeline events |
| CrossExamPanel.jsx | /cross-exam | key | AI cross-exam question sets |
| HearingChecklist.jsx | /checklist | key | Interactive checklist |
| ComplaintsTracker.jsx | /complaints | key | Complaint log |
| CostCalculator.jsx | /costs | none | Taxpayer cost estimator |
| PatternMapper.jsx | /patterns | key | D3 force graph of entities |
| Methodology.jsx | /methodology | none | Data sources, methods |
| PressKit.jsx | /press | none | Key facts for media |
| PrintView.jsx | /print | key | Print-optimized summary |
| About.jsx | /about | none | Project info |

### Components (11)
AskPanel, DecisionCard, DecisionDetail, DiagnosticsPanel, ErrorBoundary, FilterBar, MemoryPanel, Pagination, SearchBar, SemanticPanel, TrialBanner

### Search Modes
1. Browse — paginated list with source/court/date filters
2. FTS — PostgreSQL full-text search (highlighted snippets)
3. Vector — pgvector cosine similarity (384-dim, score badges)
4. ASK — Claude Q&A (top FTS + semantic chunks, SSE streaming, citation validation)

---

## SECTION 6 — DATA SNAPSHOT

```
Data Sources:
  bccourts   — BC Supreme Court + Court of Appeal decisions
  rcy        — Representative for Children & Youth reports
  legislation — CFCSA + related BC statutes
  news       — News articles
  foi        — Freedom of Information documents
  personal   — Judicial review, affidavits, complaints (6 files, 43 chunks)

Database:
  Decisions : 1,498
  Chunks    : 26,701
  Contradictions : 23 (DIRECT severity × many)
  Timeline events: 12
  Cost entries   : 15
  Witness profiles: 6 (Wolfenden, Newton, Muileboom, Burnstein, Martin, Walden)
  Cross-exam sets: 23
  Case strength  : 100/100 (STRONG)

Vault:
  court-final.pdf — 171MB, gitignored, deployed manually to data/vault/
```

---

## SECTION 7 — DEPLOYMENT & INFRA

### tunnel-config.yml (current)
```yaml
tunnel: <TUNNEL_ID>
credentials-file: /root/.cloudflared/<TUNNEL_ID>.json
ingress:
  - hostname: api.themcfdfiles.ca
    service: http://localhost:8000
  - service: http_status:404
```

### _redirects (current)
```
/api/* https://api.themcfdfiles.ca/:splat 200
```

### docker-compose.yml services
- **db**: pgvector:pg16, port 5432, healthcheck: pg_isready
- **backend**: FastAPI, port 8000, volumes: ./data → /app/data, reload mode
- **frontend**: Vite dev server, port 5173

### Manual Steps Remaining (run on Mac Mini)
1. `cloudflared tunnel login` (browser auth)
2. `cloudflared tunnel create mcfd-files` → copy UUID
3. Edit tunnel-config.yml → replace `<TUNNEL_ID>` with UUID
4. `cloudflared tunnel route dns mcfd-files api.themcfdfiles.ca`
5. `cloudflared tunnel run mcfd-files` (or install as launchd service)
6. Cloudflare Pages (browser): Connect GitHub → root: frontend, build: `npm run build`, output: dist, NODE_VERSION=20, custom domain: themcfdfiles.ca

---

## SECTION 8 — GIT STATUS

### Last 10 Commits
```
c82710d config: production API key active, vault plan, deploy-ready — session 48
769639f feat: admin dashboard, PDF v5 audit, pre-deploy audit — session 47
afa8068 feat: API key auth middleware + Cloudflare deployment prep — session 43
9ce9dcf feat: session 42 — public share page, media package export, contradiction #23
741da95 feat(costs): session 41 — cost calculator expansion + BC scale projection
7f4ae8c session 40: taxpayer cost calculator + FOI gap contradiction #22 + brain sync
d07f3fd feat: Newton 12 failures, 3 new timeline events, push to origin — session 39
0308c9a feat: batch cross-exam, witness enhancements, print view — session 38
27a0603 feat: FOI audit, bug fixes, cross-exam generator — session 37
4e76d23 feat: event timeline — seeded, API, visual component — session 35
```

### Remote
`origin https://github.com/chrislapointex-dev/the-mcfd-files.git`

### Uncommitted Changes (Session 49 work — not yet pushed)
```
Modified:
  backend/app/main.py               (deploy-check: removed false-positive cf_deploy_md check)
  cloudflare/DEPLOY.md              (YOUR-DOMAIN.ca → themcfdfiles.ca, all refs)
  cloudflare/tunnel-config.yml      (YOUR-DOMAIN.ca → themcfdfiles.ca)
  frontend/public/_redirects        (YOUR-DOMAIN.ca → themcfdfiles.ca)
  frontend/src/components/DecisionDetail.jsx  (vault PDF link if vault_file present)
  frontend/src/pages/TrialDashboard.jsx       (caryma-brief.pdf button added)
  frontend/src/pages/PublicShare.jsx          (contradiction filter, case strength)
  tasks/todo.md                     (session 49 notes appended)
```

**Not committed. Not pushed. Awaiting user approval.**

---

## SECTION 9 — KNOWN ISSUES

1. **cloudflare.ok = false in deploy-check**: Expected false-positive. Docker can't see `cloudflare/` dir (not volume-mounted). Files exist on host. No real issue.
2. **`<TUNNEL_ID>` placeholder in tunnel-config.yml**: Must be filled manually after `cloudflared tunnel create mcfd-files`. Not a bug — intentional template.
3. **Witness notes hardcoded in witnesses.py**: Should eventually move to DB for editability. Low priority.
4. **Entity extraction is regex-only**: Misses complex patterns. Could improve with spaCy NER. Low priority.
5. **No OIPC API integration**: Complaints manually tracked. No automation.
6. **court-final.pdf gitignored (171MB)**: Must be manually SCP'd to deployment host. Documented in cloudflare/VAULT.md.
7. **Frontend running in Vite dev mode**: Should build and serve via nginx for production. Currently using Vite dev server in Docker (fine for local; consider for Cloudflare Pages).
8. **Session 49 changes uncommitted**: 7 files modified. Commit + push needed before Cloudflare Pages deploy.

---

## SECTION 10 — RECOMMENDED NEXT STEPS

1. **Commit Session 49** — `git add -A && git commit -m "config: domain swap + deploy-check fix — session 49"` (user must approve push)
2. **Cloudflare Tunnel** — Run steps 1-5 from Section 7 on Mac Mini to go live
3. **Cloudflare Pages** — Connect GitHub repo, deploy frontend to themcfdfiles.ca
4. **Verify live endpoints** — `curl https://api.themcfdfiles.ca/api/health` and `curl https://themcfdfiles.ca`
5. **Fill `<TUNNEL_ID>`** in tunnel-config.yml → commit after tunnel creation
6. **Consider nginx for frontend** — Replace Vite dev server with production build for Docker deployment (optional — Cloudflare Pages handles this)
7. **MCFD_API_KEY in Cloudflare Pages env** — Set `VITE_API_KEY` as Pages env var if frontend needs to send key
8. **Trial countdown** — TrialBanner activates < 30 days out → active around April 19, 2026

---

*Audit complete. No code changes made. Read-only session.*
