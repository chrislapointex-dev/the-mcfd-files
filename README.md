# The MCFD Files

Document analysis and search platform for MCFD case files.

## Stack

| Layer    | Tech                              |
|----------|-----------------------------------|
| Backend  | Python 3.12 · FastAPI · SQLAlchemy |
| Database | PostgreSQL 16 · pgvector          |
| Frontend | React 18 · Vite · Tailwind CSS    |
| Runtime  | Docker Compose                    |

## Quick Start

```bash
make up
```

That's it. Three services spin up:

| Service  | URL                    |
|----------|------------------------|
| Frontend | http://localhost:5173  |
| Backend  | http://localhost:8000  |
| DB       | localhost:5432         |

## Other Commands

```bash
make down          # stop all services
make logs          # tail logs from all services
make shell-backend # bash shell inside backend container
make shell-db      # psql shell inside db container
make reset         # wipe volumes and rebuild from scratch
```

## Project Structure

```
the-mcfd-files/
├── backend/
│   ├── app/
│   │   ├── main.py        # FastAPI app + CORS + lifespan
│   │   ├── database.py    # async SQLAlchemy engine + Base
│   │   └── routers/       # add route modules here
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── main.jsx
│   │   ├── App.jsx
│   │   └── index.css      # Tailwind entry
│   ├── index.html
│   ├── vite.config.js     # proxy /api → backend
│   ├── tailwind.config.js
│   └── Dockerfile
├── docker-compose.yml
├── Makefile
└── README.md
```

## API Proxy

Vite proxies `/api/*` to the backend, so frontend fetches use `/api/health` and never need to hardcode a port.

## Adding Features

- **New API route**: create `backend/app/routers/your_module.py`, include it in `app/main.py`
- **New DB model**: add to `backend/app/models.py` (create this file), import in `database.py` before `init_db()`
- **pgvector**: `CREATE EXTENSION IF NOT EXISTS vector;` — add to a migration or `init_db()`
