# Wasit Backend

FastAPI + SQLAlchemy (async) + PostgreSQL API for **Wasit** — routing student problems through tickets, an **LLM agent pipeline** (classify → aggregate → route → summarize → broadcast), institutional hierarchy (school → filière → class), notifications (REST + WebSocket), Telegram, file uploads (Cloudinary), and analytics dashboards.

For product context see the repo root [`README.md`](../README.md). For architecture gaps and roadmap see [`README_SYSTEM.md`](README_SYSTEM.md) and [`BACKEND_INTEGRATION_PLAN.md`](BACKEND_INTEGRATION_PLAN.md).

---

## Table of contents

1. [Stack](#stack)
2. [Repository layout](#repository-layout)
3. [Prerequisites](#prerequisites)
4. [Environment variables](#environment-variables)
5. [Setup](#setup)
6. [Database & Alembic](#database--alembic)
7. [Run the server](#run-the-server)
8. [Authentication & roles](#authentication--roles)
9. [API overview](#api-overview)
10. [Agent pipeline](#agent-pipeline)
11. [Background jobs](#background-jobs)
12. [Testing](#testing)
13. [Troubleshooting](#troubleshooting)
14. [Further reading](#further-reading)

---

## Stack

| Layer | Technology |
|-------|------------|
| Runtime | Python 3.11+ |
| Framework | FastAPI |
| ORM | SQLAlchemy 2.x (async) |
| Database | PostgreSQL (`asyncpg`) |
| Auth | JWT (access + refresh), bcrypt passwords |
| LLM | Mistral API (classifier + aggregator), OpenRouter-compatible HTTP (summary) |
| Scheduling | APScheduler (ticket escalation) |
| Realtime | WebSockets (notification fan-out) |
| Files | Cloudinary |
| Tests | pytest, pytest-asyncio, respx (HTTP mocks) |

---

## Repository layout

```
wasit-backend/
├── main.py                 # FastAPI app, CORS, scheduler, router includes
├── requirements.txt
├── pytest.ini
├── alembic.ini             # DB migrations
├── alembic/                # Alembic env & versions
├── .env.example            # Template for local secrets (copy to .env)
├── app/
│   ├── api/v1/routes/      # auth, institutional, students, tickets, files,
│   │                       # notifications, telegram, agents, analytics
│   ├── agents/             # classifier, aggregator, router, summary, broadcast, pipeline
│   ├── core/               # config, database, dependencies, security
│   ├── models/             # SQLAlchemy models
│   ├── schemas/            # Pydantic request/response models
│   ├── services/           # Business logic (tickets, agents, telegram, notifications, …)
│   └── utils/
└── tests/                  # pytest (router, classifier mock, agent_persist)
```

---

## Prerequisites

- **Python 3.11+**
- **PostgreSQL** reachable via an async URL: `postgresql+asyncpg://user:pass@host:port/dbname`
- API keys as needed: **Mistral** (agents), **OpenRouter** (summaries; optional if you rely on fallbacks), **Cloudinary** (file routes)

---

## Environment variables

Copy **`.env.example`** to **`.env`** and fill values. Pydantic loads from `.env` via `app/core/config.py`.

| Variable | Required | Purpose |
|----------|----------|---------|
| `DATABASE_URL` | Yes | `postgresql+asyncpg://…` |
| `SECRET_KEY` | Yes | JWT signing (use a long random string) |
| `MISTRAL_API_KEY` | Yes* | Classifier + aggregator (`*required` for full agent path) |
| `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET` | Yes | File upload routes |
| `OPENROUTER_API_KEY` | No | Summaries via `openrouter_client`; empty → summary uses text fallback |
| `OPENROUTER_MODEL`, `OPENROUTER_BASE_URL`, `OPENROUTER_REFERER`, `OPENROUTER_TITLE` | No | Defaults in settings |
| `TELEGRAM_BOT_TOKEN` | No | Telegram integrations |
| `SMTP_*` | No | Reserved; email not wired to notifications yet |

Never commit **`.env`** or real secrets.

---

## Setup

### 1. Virtual environment

**Linux / macOS**

```bash
cd wasit-backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Windows (cmd)**

```bat
cd wasit-backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Environment file

```bash
cp .env.example .env
# Edit .env: DATABASE_URL, SECRET_KEY, MISTRAL_API_KEY, Cloudinary, etc.
```

### 3. Database

Create an empty PostgreSQL database, point `DATABASE_URL` at it, then apply migrations (see [Database & Alembic](#database--alembic)).

---

## Database & Alembic

Migrations live under `alembic/`. Metadata is built from `app.models` / `app.core.database.Base`.

**Create a new revision** (after model changes):

```bash
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

**Apply existing migrations**

```bash
alembic upgrade head
```

**Development note:** On startup, **`init_db_background()`** runs **`create_all`** in a **background task** (so **`GET /health`** is not blocked by a slow DB). Logs success/failure at INFO/ERROR. For **production**, prefer **Alembic** migrations and consider disabling automatic `create_all` if you rely solely on revisions.

---

## Run the server

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

| URL | Description |
|-----|-------------|
| `GET /health` | Liveness / version JSON |
| `GET /docs` | Swagger UI (OpenAPI) |
| `GET /redoc` | ReDoc |

All versioned REST routes are under **`/api/v1`** (see `settings.api_prefix`).

---

## Authentication & roles

- **Register / login** issue JWT **Bearer** tokens (see `/api/v1/auth` in OpenAPI).
- Protected routes use **`Authorization: Bearer <access_token>`**.
- Roles (enum): `student`, `delegate`, `teacher`, `admin`, `listening`.
- Tickets and analytics enforce **role + scope** (e.g. students see own tickets; delegates/teachers see class-level resources where implemented).

---

## API overview

Groups below are mounted under **`/api/v1`**. Exact paths and bodies are in **`/docs`**.

| Prefix | Purpose |
|--------|---------|
| `/auth` | Register, login, refresh, logout, current user |
| Institutional | Schools, filières, classes (CRUD / listing by role) |
| `/students` | Student profiles, groups, trombinoscope-related flows |
| `/tickets` | Create ticket + problem, list by student/class, status updates, admin lists |
| `/files` | Uploads (Cloudinary-backed service) |
| `/notifications` | List/mark read; WebSocket endpoint for live updates |
| `/telegram` | Register class Telegram group, send, message history, webhook-style intake |
| `/agents` | **`POST /agents/dry-run`** — admin-only; runs classifier → router → summary **without** DB aggregation (for prompt/key checks) |
| `/analytics` | School overview, filière stats, class patterns, trends, top issues |

---

## Agent pipeline

When a **ticket** is created from student text (`app/services/tickets.py`), the service runs **`run_pipeline`** in a **new async DB session**:

1. **Classifier** — Mistral chat completions → `category`, `priority`, `language` (JSON).
2. **Aggregator** — Mistral + DB: `AggregationGroup` / `Problem` rows; **updates** the existing `Problem` for that ticket when present (single row per ticket in the normal path).
3. **Router** — Rule-based `destination`: `teacher`, `admin`, `listening`, `emergency`, `delegate`.
4. **Persist** — Maps outputs onto **`Ticket`** and **`Problem`** (`agent_persist`) **before** downstream steps.
5. **Summary** — OpenRouter JSON chat (or fallback text if API unavailable).
6. **Broadcast** — **`notify_destination`** with DB (persisted `Notification` + WebSocket). For **`teacher`**, may call **Telegram** `send_to_group` when a group is registered.

Emergency category **skips** the LLM summary step and uses a **text fallback** in broadcast.

```text
Ticket created → run_pipeline(SessionLocal)
  → classify → aggregate(DB) → route → persist(Ticket/Problem)
  → [if not emergency] summary → broadcast(DB + optional Telegram)
  → [if emergency] broadcast only
```

---

## Background jobs

- **APScheduler** runs **hourly**: tickets in **`in_progress`** for **≥ 48 hours** without update → **`escalated`**, with a **`TicketHistory`** row attributed to an **active admin** user (if one exists).

---

## Testing

```bash
source .venv/bin/activate   # or Windows: .venv\Scripts\activate
pytest tests/ -v
```

- **`test_router.py`** — routing rules (no network).
- **`test_classifier.py`** — Mistral HTTP **mocked** with **respx**.
- **`test_agent_persist.py`** — SQLite in-memory: ORM + **`persist_agent_outputs`**.
- **`test_pipeline_e2e.py`** — full **`run_agent_pipeline`**: Mistral ×2 + OpenRouter ×1 via **respx**, SQLite fixture, **`notify_destination`** / **`send_to_group`** patched (real persistence of `Problem` in-session).

`tests/conftest.py` sets minimal env vars so **`Settings`** loads without a real `.env` (includes a dummy **`OPENROUTER_API_KEY`** for summary in e2e).

---

## Troubleshooting

| Symptom | Check |
|---------|--------|
| `Settings` / import errors on startup | All **required** env vars in `.env`; see [Environment variables](#environment-variables) |
| Summary always fallback | `OPENROUTER_API_KEY` empty or invalid; check logs |
| No notifications after ticket | Staff users exist for routed **role**; DB connection; WebSocket client subscribed |
| Telegram not sending | Class registered via Telegram routes; bot token + chat id; destination is **`teacher`** |
| Migration errors | `DATABASE_URL` matches DB; run `alembic upgrade head` |

---

## Further reading

| Document | Content |
|----------|---------|
| [`README_SYSTEM.md`](README_SYSTEM.md) | System capabilities, remaining gaps |
| [`BACKEND_INTEGRATION_PLAN.md`](BACKEND_INTEGRATION_PLAN.md) | Phased roadmap & checklist |
| [`README_USE_CASES.md`](README_USE_CASES.md) | Product use cases (UC-01 …) |
| [`README_DEV2.md`](README_DEV2.md) | Dev integration notes |
| [`../README.md`](../README.md) | Product vision (Wasit platform) |
| [`docs/FEATURE_AI_DELEGATE.md`](docs/FEATURE_AI_DELEGATE.md) | AI Delegate, Chef de filière, hierarchy (feature spec vs current code) |

---

*Wasit — واسط · backend service for institutional student support.*
