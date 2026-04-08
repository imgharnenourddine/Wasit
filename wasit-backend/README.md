# Wasit backend

FastAPI service for the Wasit platform (institutional, students, analytics, agents).

## Prerequisites

- Python 3.11+
- PostgreSQL (async URL with `postgresql+asyncpg://...`)

## Setup

1. Create a virtual environment and install dependencies:

```bash
cd wasit-backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

2. Copy environment variables:

```bash
copy .env.example .env
```

Edit `.env` and set `DATABASE_URL`, `SECRET_KEY`, `MISTRAL_API_KEY`, and Cloudinary keys as needed.

## Database migrations (Alembic)

Alembic is configured for **async** SQLAlchemy using `app.models.Base` metadata.

Create a new revision (after model changes):

```bash
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

Apply existing migrations:

```bash
alembic upgrade head
```

> On first run, `init_db()` in `main.py` also calls `create_all` for development; prefer migrations for production.

## Run the API

```bash
uvicorn main:app --reload
```

- Health: `GET http://127.0.0.1:8000/health`
- OpenAPI docs: `http://127.0.0.1:8000/docs`

API routes are mounted under `/api/v1`:

- `/api/v1/auth` — authentication (stub until implemented)
- `/api/v1` institutional, students — schools, filières, classes, trombinoscope, groups
- `/api/v1/tickets`, `/files`, `/notifications`, `/telegram`, `/agents` — stubs until implemented
- `/api/v1/analytics` — dashboards and trends

## Analytics endpoints (summary)

- `GET /api/v1/analytics/school/{school_id}` — admin
- `GET /api/v1/analytics/filiere/{filiere_id}` — admin or filière responsible
- `GET /api/v1/analytics/class/{class_id}` — admin, class delegate, or teacher
- `GET /api/v1/analytics/school/{school_id}/trends?days=30` — admin
- `GET /api/v1/analytics/school/{school_id}/top-issues?limit=10` — admin

All protected routes require a valid Bearer JWT (see auth routes when enabled).
