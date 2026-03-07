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

---

## SESSIONS 21–24 COMPLETE — 2026-03-07

### Session 21 — Seed Known Contradictions
- [x] Created `backend/app/loaders/seed_contradictions.py`
  - 10 known contradictions seeded (idempotent — safe to re-run)
  - DB now has 13 total contradictions (3 existing + 10 seeded)
  - Severity breakdown: 8 DIRECT, 2 PARTIAL

### Session 22 — ASK Name-Boost + Keyword Search
- [x] `backend/app/routers/ask.py` — added BOOST_NAMES list + _detect_boost_name()
  - Name boost fires in both ask_endpoint and ask_stream_endpoint
  - Prepends up to 5 FTS hits for detected witness name before personal_boost
  - Names: Wolfenden, Newton, Muileboom, Burnstein, Walden, Martin, Nadia, CFD-2025-53478
- [x] `backend/app/routers/search.py` — added GET /api/search/keyword
  - LIKE-based keyword search on chunks.text
  - Optional source filter (personal = foi+personal sources)
  - Returns chunk_id, text, source, citation, decision_id

### Session 23 — Mobile/Print Polish
- [x] Created `frontend/src/components/TrialBanner.jsx`
  - Fetches /api/trialprep/summary on mount
  - Only renders if days_remaining < 30 (currently 73 — hidden)
- [x] `frontend/src/pages/TrialDashboard.jsx`
  - Countdown: text-7xl → text-6xl sm:text-8xl (mobile responsive)
  - Added PRINT TRIAL SUMMARY button (print:hidden)
  - Header nav: print:hidden
  - TrialBanner wired below top accent line
- [x] `frontend/src/pages/WitnessProfiles.jsx`
  - COPY button per chunk card (copies source + citation + text)
  - TrialBanner wired below top accent line
- [x] `frontend/src/pages/ContradictionEngine.jsx`
  - COPY button per result item and per history item
  - TrialBanner wired below top accent line

### Session 24 — Final Hardening
- [x] Python syntax checks PASS (seed_contradictions, ask, search)
- [x] /api/health → ok
- [x] /api/contradictions → 13 results
- [x] /api/search/keyword?q=Burnstein&source=personal → 3 results
- [x] Git committed and pushed

### Verification results
- contradiction count: 13 (3 existing + 10 seeded)
- keyword search: /api/search/keyword?q=Burnstein&source=personal → 3 chunks
- name boost: fires for Wolfenden/Newton/Muileboom/Burnstein/Walden/Martin/Nadia in ASK mode
- TrialBanner: wired in Trial/Witnesses/Contradictions pages, hidden until < 30 days

## SESSIONS 25–27 COMPLETE — 2026-03-07

### Session 25 — Hearing Prep Checklist
- [x] ChecklistItem model appended to models.py (Boolean imported)
- [x] backend/app/routers/checklist.py — GET /api/checklist, PATCH toggle, PATCH notes
- [x] Registered checklist router in main.py
- [x] backend/app/loaders/seed_checklist.py — 22 items seeded (EVIDENCE/FILINGS/WITNESSES/LOGISTICS)
- [x] frontend/src/pages/HearingChecklist.jsx — grouped view, per-category progress bars, inline notes
- [x] /checklist route in main.jsx
- [x] CHECKLIST nav link in TrialDashboard (with incomplete count badge)

### Session 26 — OIPC & Complaint Tracker
- [x] Complaint model appended to models.py
- [x] backend/app/routers/complaints.py — GET /api/complaints, PATCH update
- [x] Registered complaints router in main.py
- [x] backend/app/loaders/seed_complaints.py — 6 complaints seeded
- [x] frontend/src/pages/ComplaintsTracker.jsx — table view, status badges/dropdown, inline notes, copy summary
- [x] /complaints route in main.jsx
- [x] COMPLAINTS nav link in TrialDashboard

### Session 27 — Final Integration Test
- [x] Python syntax checks PASS (models, checklist, complaints, seeds)
- [x] /api/checklist → 22 items, 4 categories
- [x] /api/complaints → 6 complaints (2 ACTIVE, 4 FILED)
- [x] /api/trialprep/summary → days_remaining: 73, contradictions: 13
- [x] /api/health → ok
- [x] Git committed and pushed

### Verification results
- checklist: 22 items (EVIDENCE:6, FILINGS:5, WITNESSES:6, LOGISTICS:5)
- complaints: 6 (OIPC INV-F-26-00220, CRA GB260151737209, BC Ombudsperson, RCMP, RCY, Health Canada)
- trial dashboard: 73 days remaining, CHECKLIST badge shows pending count
- all endpoints healthy

SESSIONS 25–27 COMPLETE — PLATFORM FEATURE-COMPLETE FOR TRIAL
Platform has: Trial Dashboard + Contradiction Engine + Timeline + Witnesses + Checklist + Complaints + Export + ASK/Search

## SESSIONS 25-27 RE-RUN COMPLETE — 2026-03-07

### Changes from re-run (corrections to prior implementation)
- GET /api/checklist changed from flat list → grouped dict {CATEGORY: [items]}
- PATCH /api/checklist/{id} unified endpoint (was separate /toggle + /notes)
- 7 seed item texts corrected to match spec:
  - "playable + clipped" → "playable and clipped"
  - "not already served" → "not voluntarily attending"
  - "Confirm attendance or arrange testimony" → DELETED
  - All 4 LOGISTICS items corrected to spec text
- HearingChecklist.jsx and TrialDashboard.jsx updated for new API shape

### Final endpoint sweep results

| Endpoint | Result |
|----------|--------|
| /api/health | ok |
| /api/trialprep/summary | days_remaining: 73 |
| /api/checklist | 21 items (EVIDENCE:6, FILINGS:5, WITNESSES:5, LOGISTICS:5) |
| /api/complaints | 6 complaints (OIPC, CRA, BC Ombudsperson, RCMP, RCY, Health Canada) |
| /api/contradictions | 13 |
| /api/witnesses | 6 |

PLATFORM FEATURE-COMPLETE FOR TRIAL — 73 days remaining

## SESSION 28 — DOCUMENTS LOADED — 2026-03-07

### Files found and loaded (34 files → 29 decisions loaded, 5 skipped)

**Text files loaded (13):**
| File | Label | Chars |
|------|-------|-------|
| chris-mcfd-report-apr-11-2025.txt | MCFD Report Chris Apr 11 2025 | 4698 |
| email-false-f1-claims-oct-27-2025.txt | Email False F1 Claims Oct 27 2025 | 5807 |
| email-request-clarification-mcfd-sep-18-2025.txt | Email Request Clarification MCFD Sep 18 2025 | 2418 |
| foi-findings-update.txt | FOI Findings Update 2026 | 9414 |
| tammy-newton-letter-sep-24-2025.txt | Tammy Newton Response Letter Sep 24 2025 | 5213 |
| sexual-assault-disclosure-aug-1-2025.txt | Disclosure Transcript Aug 1 2025 | 5778 |
| ptc-nicki-wolfenden.txt | Witness Profile N. Wolfenden | loaded |
| ptc-tammy-newton.txt | Witness Profile T. Newton | loaded |
| ptc-burnstein.txt | Witness Profile R. Burnstein | loaded |
| ptc-jordon-muileboom.txt | Witness Profile J. Muileboom | loaded |
| ptc-plessa-walden.txt | Witness Profile P. Walden | loaded |
| ptc-cheryl-martin.txt | Witness Profile C. Martin | loaded |
| ptc-court-files.txt | Court Files Summary PTC | loaded |

**PDF files loaded (16):**
| File | Label | Chars |
|------|-------|-------|
| exhibit-a-25-contradictions.pdf | Exhibit A 25 Contradictions | 14254 |
| lapointe-response-sep-24-2025.pdf | LaPointe Response Sep 24 2025 | 5250 |
| court-plan-of-care-dec-23-2025.pdf | Court Plan of Care Dec 23 2025 | 12701 |
| form-31-notice-app-64242-nov-24-2025.pdf | Form 31 Notice of Application 64242 Nov 24 2025 | 699 |
| form-32-nov-24-2025.pdf | Form 32 LaPointe v Wolfenden MCFD Nov 24 2025 | 699 |
| form-66-wolfenden-director-nov-24-2025.pdf | Form 66 LaPointe v Wolfenden Director Nov 24 2025 | 699 |
| form-7-wolfenden-form66-nov-24-2025.pdf | Form 7 Affidavit Wolfenden Form 66 Nov 24 2025 | 3055 |
| form-7-newton-19709-nov-17-2025.pdf | Form 7 Affidavit Newton 19709 Nov 17 2025 | 10713 |
| form-7-mcfd-19709-oct-7-2025.pdf | Form 7 Affidavit MCFD 19709 Oct 7 2025 | 95381 |
| form109-wolfenden-nov-24-2025.pdf | Form 109 Affidavit Wolfenden MCFD Nov 24 2025 | 699 |
| gmail-misconduct-newton.pdf | Gmail Misconduct Tammy Newton MCFD | 10342 |
| gmail-oipc-inv-f-26-00220.pdf | Gmail OIPC INV-F-26-00220 CFD-2025-53478 | 9210 |
| h-notice-intent-full-custody.pdf | Notice of Intent Full Custody Nadia | 10211 |
| i-f1-mcfd-aug-12-2025.pdf | F1 MCFD Form Aug 12 2025 | 25264 |
| legend-lapointe-mcfd.pdf | Legend LaPointe v MCFD | 8482 |
| mcfd-newton-letter-sep-24-2025.pdf | MCFD Newton Comprehensive Response Sep 24 2025 | 48585 |
| nadia-analysis-report.pdf | Nadia Comprehensive Analysis Report 2024-2025 | 19528 |
| timeline-lapointe-mcfd.pdf | Timeline LaPointe v MCFD | 5662 |

**Skipped (scanned image PDFs — text extraction yielded < 100 chars):**
- form-a-circumstances-removal-aug-12-2025.pdf (KLC Form A)
- seyler-application-protection-order-aug-5-2025.pdf
- court-final.pdf (Desktop)

**Also skipped (metadata/not case content):**
- FOI_FINDINGS_UPDATE (1).md — duplicate
- G Sexual_Assault_Disclosure_Transcript.txt.txt — identical to loaded version
- Form 7 Affidavit of Christopher S. La Pointe v MCFD (duplicate of Oct 7 version)
- H Notice (1).pdf and H Notice (2).pdf — duplicates
- nadia_comprehensive_analysis_report 2024 to 2025.pdf — duplicate
- README_Caryma_LaPointe_v_MCFD.pdf — metadata only
- MCFD_FILES_MAC_SETUP_GUIDE.md — setup doc
- FOI_LOAD_PROMPT.md — setup instructions

**protect-the-child brain:** 7 files loaded (6 witness profiles + court_files.md)

### Final counts
- personal_chunks: 720 (was 597, +123)
- total_chunks: 26824
- total_decisions: 1529
- new decisions loaded: 29
- chunker: 123 chunks inserted across 29 decisions
- embedder: 123 embeddings at 46 chunks/s

### ASK verification
Query: "Summarize all evidence of pre-planned removal" (source_filter: personal)
Result: Cited "FOI Findings Update 2026" — newly loaded document. Working.
