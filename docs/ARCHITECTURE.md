# Orbit — Architecture

This document describes the foundation architecture. It will evolve as features land.

## Principles

1. **Layered backend** — routes → services → models. Routes handle HTTP concerns only; business logic belongs in `app/services`.
2. **Contracts first** — every request/response shape is a Pydantic model in `app/schemas`.
3. **Configuration via environment** — all runtime config flows through `app/core/config.py` (`Settings`). No hardcoded secrets.
4. **Structured logs** — the backend emits single-line JSON logs to stdout (`app/core/logging.py`), ready for container log collectors.
5. **Migrations are source-controlled** — schema changes are only made through Alembic revisions.

## Backend Layers

```
HTTP request
    │
    ▼
app/api/routes/*      FastAPI routers, dependency injection, status codes
    │
    ▼
app/services/*        business logic (empty — future feature code)
    │
    ▼
app/models/*          SQLAlchemy ORM models (Base: app/db/base.py)
    │
    ▼
app/db/session.py     engine + SessionLocal + get_db dependency
    │
    ▼
SQLite (data/orbit.db)
```

Cross-cutting modules:

- `app/core/config.py` — `Settings` (Pydantic Settings), loaded from env / `.env`, cached with `lru_cache`.
- `app/core/logging.py` — JSON formatter + `setup_logging()`.
- `app/main.py` — app factory: CORS middleware, lifespan hooks, router registration under `/api`.

Reserved (empty) packages: `app/auth`, `app/rag`, `app/analytics`.

## Database & Migrations

- SQLite file: `backend/data/orbit.db` (`DATABASE_URL=sqlite:///./data/orbit.db`).
- The session layer creates the `data/` directory automatically if missing.
- Alembic is configured in `backend/alembic.ini` + `backend/alembic/env.py`; the URL comes from `Settings`, and `render_as_batch=True` is enabled because SQLite does not support most `ALTER` statements.

Workflow:

```bash
# 1. edit app/models
# 2. generate a revision
alembic revision -m "add example table"
# 3. apply
alembic upgrade head
```

## Frontend

- Next.js 15 App Router under `frontend/app`.
- `app/layout.tsx` is the global shell (fonts, metadata, `dark` class on `<html>`).
- `app/dashboard/page.tsx` is the empty dashboard; `/` redirects to it.
- shadcn/ui is initialized (`components.json`); components live in `frontend/components/ui`, helpers in `frontend/lib`.
- Theming: CSS variables define light and dark palettes in `app/globals.css`; the `dark` class toggles them. The app ships dark by default.

## Data Stores

| Store | Location | Purpose |
| --- | --- | --- |
| SQLite | `backend/data/orbit.db` | relational data (users, orgs, documents metadata, ...) |
| Redis | service `redis` (`redis://redis:6379`) | cache, rate limiting, background job broker |
| ChromaDB | `backend/chroma_db/` (local folder) | vector persistence for future RAG |

ChromaDB deliberately has **no container** — the backend owns the folder as a bind mount so the index persists across rebuilds.

## API Conventions

- All endpoints are prefixed with `/api` (configurable via `api_prefix`).
- Health: `GET /api/health` → `{status, service, version, environment, timestamp, checks}`.
- OpenAPI docs served at `/docs` (Swagger) and `/redoc`.
- CORS origins come from `Settings.cors_origins` (defaults cover `localhost:3000`).

## Environment

See `.env.example`:

```
GEMINI_API_KEY=        # future AI features
DATABASE_URL=sqlite:///./data/orbit.db
CHROMA_PATH=./chroma_db
REDIS_URL=redis://redis:6379
JWT_SECRET=            # future authentication
```

## Service Topology (Compose)

```
docker compose
├── frontend   build: docker/frontend/Dockerfile   :3000
├── backend    build: docker/backend/Dockerfile    :8000   (runs alembic upgrade head on start)
├── redis      image: redis:7-alpine               :6379   (healthcheck: redis-cli ping)
└── volumes    redis-data, ./backend/data, ./backend/uploads, ./backend/chroma_db
```

## Extension Roadmap

| Module | Status | Plan |
| --- | --- | --- |
| `app/auth` | empty | JWT auth, `JWT_SECRET`, user model, login/refresh routes |
| `app/rag` | empty | ingestion → chunking → embedding → ChromaDB retrieval, `GEMINI_API_KEY` |
| `app/analytics` | empty | event aggregation and reporting endpoints |
| `app/services` | empty | cross-route business logic |
