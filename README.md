# The MCFD Files

A searchable database of BC court decisions, RCY reports, legislation, and news articles relating to the Ministry of Children and Family Development (MCFD). Built for public interest research.

---

## Stack

| Layer    | Tech                                        |
|----------|---------------------------------------------|
| Backend  | Python 3.12 · FastAPI · SQLAlchemy (async)  |
| Database | PostgreSQL 16 · pgvector (384-dim embeddings) |
| AI       | Claude (Anthropic) · all-MiniLM-L6-v2      |
| Frontend | React 18 · Vite · Tailwind CSS              |
| Runtime  | Docker Compose                              |

---

## Quick Start

```bash
cp .env.example .env        # add ANTHROPIC_API_KEY at minimum
make up
```

| Service  | URL                   |
|----------|-----------------------|
| Frontend | http://localhost:5173 |
| Backend  | http://localhost:8000 |
| DB       | localhost:5432        |

---

## Search Modes

The frontend provides four modes, toggled by the FTS / VECTOR / ASK buttons:

| Mode       | How it works                                                          |
|------------|-----------------------------------------------------------------------|
| **Browse** | Paginated list of all decisions with source/court/year filters        |
| **FTS**    | PostgreSQL full-text search with `<mark>` highlighted snippets        |
| **VECTOR** | pgvector cosine similarity over 384-dim sentence embeddings           |
| **ASK**    | Claude answers your question, grounded in top FTS + semantic chunks   |

---

## Data Sources

| Source       | Count  | Description                                      |
|--------------|--------|--------------------------------------------------|
| `bccourts`   | 954    | BC Supreme Court and Court of Appeal decisions   |
| `rcy`        | 126    | Representative for Children and Youth BC reports |
| `legislation`| 214    | CFCSA and related BC statutes (by section)       |
| `news`       | 139    | News articles (DuckDuckGo + gov.bc.ca)           |

### R2 Memory

The ASK endpoint integrates with an R2-D2 memory system: each question and answer is saved to the `memory` table (PostgreSQL), and prior research context is automatically injected into future queries. The R2 MEMORY panel in the header shows recent searches and flagged cases.

---

## Environment Variables

Copy `.env.example` to `.env` and set:

| Variable           | Required | Default                                   | Description                                      |
|--------------------|----------|-------------------------------------------|--------------------------------------------------|
| `ANTHROPIC_API_KEY`| Yes      | —                                         | API key for Claude (ASK mode)                    |
| `DATABASE_URL`     | No       | `postgresql+asyncpg://mcfd:mcfd@db:5432/mcfd` | Override DB connection string             |
| `CORS_ORIGINS`     | No       | `http://localhost:5173`                   | Comma-separated allowed origins for CORS         |
| `MCFD_API_KEY`     | No       | (unset = open)                            | If set, `/api/ask` requires `X-API-Key` header   |
| `CLAUDE_MODEL`     | No       | `claude-sonnet-4-6`                       | Override the Claude model ID                     |

---

## API Endpoints

| Method | Path                         | Description                              |
|--------|------------------------------|------------------------------------------|
| GET    | `/api/health`                | Health check                             |
| GET    | `/api/decisions`             | Browse + filter decisions (paginated)    |
| GET    | `/api/decisions/filters`     | Available filter options (sources, courts, year range) |
| GET    | `/api/decisions/search`      | Full-text search with highlighted snippets |
| GET    | `/api/decisions/{id}`        | Single decision detail                   |
| GET    | `/api/search/semantic`       | Vector similarity search over chunks     |
| POST   | `/api/ask`                   | Claude Q&A grounded in top chunks        |
| POST   | `/api/ask/stream`            | Same as above, SSE token-by-token stream |
| GET    | `/api/memory`                | List R2 memory entries                   |
| POST   | `/api/memory`                | Save a memory entry                      |
| DELETE | `/api/memory/{id}`           | Delete a memory entry                    |

Rate limit on `/api/ask`: 10 requests per minute per IP.

---

## Data Pipeline

### Scrapers

```bash
cd backend

# BC Courts decisions
python -m app.scrapers.bccourts

# RCY reports (downloads PDFs)
python -m app.scrapers.rcy

# Legislation (CFCSA sections)
python -m app.scrapers.legislation

# News articles (DuckDuckGo search)
python -m app.scrapers.news
python -m app.scrapers.news --limit 10   # test run
python -m app.scrapers.news --reset      # clear manifest and re-fetch
```

### Loaders

```bash
cd backend

# Load scraped data into PostgreSQL
python -m app.loaders.load_decisions
python -m app.loaders.load_rcy
python -m app.loaders.load_legislation
python -m app.loaders.load_news

# All loaders support --dry-run and --data-dir flags
python -m app.loaders.load_decisions --dry-run
```

### Embeddings

```bash
cd backend

# Chunk decisions (splits full_text into overlapping segments)
python -m app.pipeline.chunker

# Embed chunks (384-dim all-MiniLM-L6-v2 via sentence-transformers)
python -m app.pipeline.embedder
```

---

## Database Migrations

Alembic is initialized at `backend/alembic/`. The DB URL is read from `DATABASE_URL` automatically.

```bash
cd backend

# Check current revision
alembic current

# Generate a migration after model changes
alembic revision --autogenerate -m "add new column"

# Apply pending migrations
alembic upgrade head

# Roll back one step
alembic downgrade -1
```

---

## Makefile Commands

```bash
make up             # build and start all services
make down           # stop all services
make logs           # tail logs from all services
make shell-backend  # bash shell inside backend container
make shell-db       # psql shell inside db container
make reset          # wipe volumes and rebuild from scratch
```

---

## Project Structure

```
the-mcfd-files/
├── backend/
│   ├── alembic/              # database migrations
│   ├── app/
│   │   ├── main.py           # FastAPI app, CORS, lifespan startup
│   │   ├── database.py       # async SQLAlchemy engine + Base
│   │   ├── models.py         # Decision, Chunk, Memory ORM models
│   │   ├── routers/          # decisions, search, ask, memory
│   │   ├── services/         # claude_service, embed_service
│   │   ├── loaders/          # load_decisions, load_rcy, load_news, load_legislation
│   │   └── scrapers/         # bccourts, rcy, news, legislation, canlii
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── main.jsx          # entry point with ErrorBoundary + router
│   │   ├── App.jsx           # main shell: header, search, browse, ask, semantic
│   │   ├── components/       # SearchBar, FilterBar, DecisionCard, AskPanel, etc.
│   │   ├── pages/            # About
│   │   └── hooks/            # useDecisions
│   ├── vite.config.js        # proxies /api/* → backend:8000
│   └── Dockerfile
├── docker-compose.yml
├── Makefile
└── README.md
```
