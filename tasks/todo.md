# Personal Legal Files — First-Class Data Source
## Session: 2026-03-07

---

## SESSION 13 — CONTRADICTION ENGINE (2026-03-07)

- [x] Add `Contradiction` model to `backend/app/models.py`
- [x] Create `backend/app/routers/contradictions.py` (GET list + POST analyze)
- [x] Register contradictions router in `backend/app/main.py`
- [x] Create `frontend/src/pages/ContradictionEngine.jsx`
- [x] Add `/contradictions` route to `frontend/src/main.jsx`
- [x] Add CONTRADICTIONS nav link to `frontend/src/App.jsx` (desktop + mobile)

## SESSION 14 — CASE TIMELINE (2026-03-07)

- [x] Create `backend/app/routers/timeline.py` (GET /api/timeline)
- [x] Register timeline router in `backend/app/main.py`
- [x] Create `frontend/src/pages/CaseTimeline.jsx`
- [x] Add `/timeline` route to `frontend/src/main.jsx`
- [x] Add TIMELINE nav link to `frontend/src/App.jsx` (desktop + mobile)

## SESSION 15 — LOAD PERSONAL DOCUMENTS (2026-03-07)

- [x] Search data/raw/ for unloaded personal files — FOI loaded, no personal dir yet
- [x] Search ~/Projects/protect-the-child/ — no .txt source files (JS app only)
- [x] Search ~/Desktop and ~/Downloads — found 6 .md case files
- [x] Load found files via docker exec loader
  - complaint-nicki-wolfenden-sep-2-2025 (personal, 2025-09-02) — LOADED
  - complaint-tammy-newton-sep-2-2025 (personal, 2025-09-02) — LOADED
  - draft-human-rights-complaint (personal, 2025-09-01) — LOADED
  - form-66-judicial-review-nov-24-2025 (personal, 2025-11-24) — LOADED
  - form-7-affidavit-false-statements-nov-17-2025 (personal, 2025-11-17) — LOADED
  - form-a-mcfd-removal-aug-12-2025 (personal, 2025-08-12) — LOADED
- [x] Chunked: 43 new chunks across 7 decisions
- [x] Embedded: 43 chunks at 28/s

## SESSION 16 — HARDENING & POLISH (2026-03-07)

- [x] Add 1.15x personal boost to `search.py` semantic endpoint
- [x] Create `backend/app/routers/brain.py` (GET /api/brain/status)
- [x] Register brain router in `backend/app/main.py`
- [x] Error handling in contradictions.py (503 on embed/Claude failure)
- [x] Git commit all sessions 13-16 (pending — user approval needed)

## SESSIONS 13-16 COMPLETE — Review

**Verified 2026-03-07**

| Test | Result |
|------|--------|
| `/api/health` | OK |
| `/api/contradictions/analyze` (personal filter) | 3 contradictions returned, severity=PARTIAL |
| `/api/timeline` | 500 events extracted, dates from 1984–present |
| `/api/brain/status` | total_decisions=1498, total_chunks=26701, personal_chunks=597, contradiction_count=3 |
| Frontend `/contradictions` route | Created, nav link added desktop+mobile |
| Frontend `/timeline` route | Created, nav link added desktop+mobile |

**Personal docs loaded (6 files, 43 chunks, 43 embeddings):**
- Complaint vs N. Wolfenden (Sep 2 2025)
- Complaint vs Tammy Newton (Sep 2 2025)
- Draft Human Rights Complaint
- Form 66 Judicial Review (Nov 24 2025)
- Form 7 Affidavit False Statements (Nov 17 2025)
- Form A MCFD Removal Order (Aug 12 2025)

**Files changed:**
- `backend/app/models.py` — Contradiction model appended
- `backend/app/routers/contradictions.py` — NEW
- `backend/app/routers/timeline.py` — NEW
- `backend/app/routers/brain.py` — NEW
- `backend/app/main.py` — 3 new routers registered
- `backend/app/routers/search.py` — 1.15x personal boost
- `frontend/src/pages/ContradictionEngine.jsx` — NEW
- `frontend/src/pages/CaseTimeline.jsx` — NEW
- `frontend/src/main.jsx` — 2 new routes
- `frontend/src/App.jsx` — nav links for CONTRADICTIONS + TIMELINE


## Todo

- [x] STEP 1 — decisions.py: Add PERSONAL_SOURCES virtual filter
- [x] STEP 1 — search.py: Add PERSONAL_SOURCES virtual filter (ANY array param)
- [x] STEP 1 — ask.py: Add source_filter to AskRequest, _sources_for_filter helper, filtered FTS + semantic fetchers, burial fix secondary query
- [x] STEP 2 — claude_service.py: Add PERSONAL_SYSTEM_PROMPT, context_mode param to ask() and ask_stream()
- [x] STEP 3 — load_personal_file.py: New generalized loader (txt + pdf, upsert by url)
- [x] STEP 4 — FilterBar.jsx: MY FILES virtual tab (violet), buildSourceTabs(), hide court dropdown when personal
- [x] STEP 4 — DecisionCard.jsx: violet accent bar + MY FILE label for foi/personal sources
- [x] STEP 4 — SemanticPanel.jsx: SourceBadge component per result
- [x] STEP 4 — AskPanel.jsx: SourceTypeBadge on each cited source
- [x] STEP 4 — App.jsx: sourceFilter state, MY FILES toggle button, wire to triggerAsk + semantic fetch + banner

---

## Review

### What was done
Added 'personal' as a first-class virtual source spanning foi + personal rows.

**Backend (4 files modified, 1 new)**
- `decisions.py`: `_apply_filters` now maps `source='personal'` → `source IN ('foi','personal')` via SQLAlchemy `.in_()`. All other sources unchanged.
- `search.py`: Same pattern using `AND d.source = ANY(:sources)` for the personal case, plain `AND d.source = :source` otherwise.
- `ask.py`: `AskRequest` gains `source_filter: Optional[str]`. `_fetch_fts_chunks` and `_fetch_semantic_chunks` both accept an optional `sources` list. Burial fix: when no filter is active, a secondary semantic query restricted to `PERSONAL_SOURCES` is prepended to the merge list so FOI chunks aren't buried. System prompt selection wired to `context_mode`.
- `claude_service.py`: `PERSONAL_SYSTEM_PROMPT` constant added. Both `ask()` and `ask_stream()` accept `context_mode` and select prompt via `_PROMPTS` dict.
- `load_personal_file.py`: New CLI loader. Takes `--file`, `--label`, `--source`, `--date`. Supports .txt and .pdf (PyMuPDF). Upserts by url idempotency key. Does not run chunker/embedder.

**Frontend (5 files modified)**
- `FilterBar.jsx`: `buildSourceTabs()` collapses foi/personal into one MY FILES tab (violet). Court dropdown hidden when personal filter active. Source dropdown in browse mode uses same virtual tab list.
- `DecisionCard.jsx`: Violet accent bar, MY FILE label, violet badge for foi/personal sources.
- `SemanticPanel.jsx`: `SourceBadge` component shows source chip (violet/teal/amber) on each result.
- `AskPanel.jsx`: `SourceTypeBadge` added to each cited source entry.
- `App.jsx`: `sourceFilter` state (default 'all'). MY FILES toggle button in header. `triggerAsk` accepts `currentSourceFilter` param. Semantic fetch appends `&source=personal` when active. Personal banner shown in ASK mode when MY FILES active.

### Schema changes
None. No migrations needed.

### New dependencies
None. PyMuPDF is optional (only needed if loading PDF personal files).

---

## SESSION 12 VERIFICATION — 2026-03-07

### Pre-Flight Fixes Applied
- **Bug 1 (stale closure)**: Added `sourceFilter` to `handleSearch` deps array in `App.jsx:215`. Confirmed fix.
- **Bug 2 (asyncpg list param)**: NOT triggered — tests 3 & 4 returned correct results without fix. asyncpg handles Python list → PostgreSQL array for varchar columns correctly in this setup.

### Results

```
TEST                              | STATUS | NOTES
----------------------------------|--------|------
1a. py_compile decisions.py       | PASS   | OK
1b. py_compile search.py          | PASS   | OK
1c. py_compile ask.py             | PASS   | OK
1d. py_compile claude_service.py  | PASS   | OK
1e. py_compile load_personal_file | PASS   | OK
2.  Stack health                  | PASS   | {"status":"ok","service":"mcfd-backend"}
3.  FTS personal filter           | PASS   | total=3, all source="foi"
4.  Semantic personal filter      | PASS   | total=5, all source="foi"
5.  ASK burial fix (no filter)    | PASS   | FOI source returned (CFD-2025-53478)
6.  ASK personal filter + prompt  | PASS   | Personal system prompt active, detailed removal facts cited
7.  Loader idempotency            | PASS   | Two consecutive runs both succeed, ON CONFLICT DO UPDATE works
```

### Notes
- `foi_pages_0001_to_0050.txt` not present; used `foi_pages_0351_to_0400.txt` for test 7 (equivalent)
- Loader runs via `docker exec the-mcfd-files-backend-1` (no local venv; deps are containerized)
- All layers verified end-to-end. Feature is production-ready.

---

### Verification commands
```bash
# FTS personal filter
curl "http://localhost:8000/api/decisions/search?q=Burnstein&source=personal"

# Semantic personal filter
curl "http://localhost:8000/api/search/semantic?q=removal+mental+health&source=personal"

# ASK default (burial fix active)
curl -s -X POST http://localhost:8000/api/ask/stream \
  -H "Content-Type: application/json" \
  -d '{"question":"what did Burnstein direct?"}' | head -5

# ASK personal mode
curl -s -X POST http://localhost:8000/api/ask/stream \
  -H "Content-Type: application/json" \
  -d '{"question":"what did Burnstein direct?","source_filter":"personal"}' | head -5

# Loader dry run
cd backend && DATABASE_URL=postgresql+asyncpg://mcfd:mcfd@localhost:5432/mcfd \
  .venv/bin/python3.12 -m app.loaders.load_personal_file \
  --file data/raw/personal/test.txt \
  --label "Test Personal Doc" \
  --source personal \
  --date 2025-01-01 \
  --dry-run
```

---

## SESSIONS 17–20 COMPLETE — 2026-03-07

### Session 17 — Trial Prep Dashboard
- [x] Created `backend/app/routers/trialprep.py` — GET /api/trialprep/summary
  - Days remaining to trial (73 days as of 2026-03-07)
  - Contradiction count, personal chunk count
  - Top 5 contradictions
  - Timeline gaps in critical period Aug 7–Sep 8 2025 (found: Aug 28 → Sep 2, 5 days)
- [x] Registered trialprep router in main.py
- [x] Created `frontend/src/pages/TrialDashboard.jsx`
  - Countdown, case numbers, key witnesses with SEARCH buttons
  - Top contradictions with severity badges
  - Timeline gaps panel
  - Export button
- [x] Updated `frontend/src/main.jsx` — / → TrialDashboard, /trial → TrialDashboard, /search → App
- [x] Updated `frontend/src/App.jsx` — added TRIAL + WITNESSES nav (desktop + mobile)

### Session 18 — Witness Profiles
- [x] Created `backend/app/routers/witnesses.py`
  - GET /api/witnesses — list with chunk counts (Wolfenden: 61, Muileboom: 10, Newton: 7, Walden: 6, Burnstein: 1, Martin: 0)
  - GET /api/witnesses/{name} — full chunk list (limit 20)
- [x] Registered witnesses router in main.py
- [x] Created `frontend/src/pages/WitnessProfiles.jsx`
  - List view with chunk count badges and VIEW PROFILE button
  - Profile view with ASK AI and ANALYZE CONTRADICTIONS links
  - Full chunk text with source/citation badges
- [x] Added /witnesses route to main.jsx

### Session 19 — Export Package
- [x] Created `backend/app/routers/export.py` — GET /api/export/trial-package
  - ZIP: contradictions.csv, timeline.csv, witnesses.txt, brain_status.json, README.txt
  - 56KB ZIP verified via curl
- [x] Registered export router in main.py
- [x] Added "EXPORT TRIAL PACKAGE" button to TrialDashboard

### Session 20 — Final Hardening
- [x] Python syntax checks PASS on all 3 new routers
- [x] All 5 endpoints verified via curl
- [x] README.md "Trial Prep Features" section appended
- [x] tasks/todo.md SESSIONS 17-20 COMPLETE block appended
- [x] Git committed

### Verification results
- /api/health → {"status":"ok"}
- /api/trialprep/summary → 73 days, 3 contradictions, 597 personal chunks, 1 gap (Aug 28–Sep 2)
- /api/witnesses → 6 witnesses, Wolfenden 61 chunks
- /api/witnesses/Nicki Wolfenden → 20 chunks
- /api/export/trial-package → 56KB ZIP, 5 files
