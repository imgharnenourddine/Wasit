# Wasit Backend — System State, Capabilities & Roadmap

This document describes **what the backend is today**, **what it can do end-to-end**, and **what still needs to be implemented or fixed**. It complements product-level docs in the repo root (`README.md`, `README_USE_CASES.md`).

---

## 1. Purpose (one paragraph)

**Wasit** is an institutional intermediary API: students submit problems as **tickets**, an **agent pipeline** is meant to classify, aggregate, route, summarize, and **broadcast** to the right staff (and optionally Telegram), while **analytics** exposes school / filière / class views. The backend is **FastAPI + SQLAlchemy (async) + PostgreSQL**, with **JWT auth**, **role-based access**, and background **scheduling** for ticket escalation.

---

## 2. High-level architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  FastAPI (main.py) — CORS, global error middleware, APScheduler  │
└─────────────────────────────────────────────────────────────────┘
         │ includes routers under settings.api_prefix (/api/v1)
         ▼
┌──────────────┬──────────────┬─────────────┬──────────────┬─────────┐
│ auth         │ institutional│ students    │ tickets      │ files   │
│ notifications│ telegram     │ agents      │ analytics    │         │
└──────────────┴──────────────┴─────────────┴──────────────┴─────────┘
         │                    │
         ▼                    ▼
┌─────────────────┐   ┌──────────────────────────────────────────────┐
│ Services        │   │ Agent layer (app/agents/)                     │
│ tickets, auth,  │   │ pipeline → classifier → aggregator → router │
│ telegram,       │   │ → summary → broadcast                        │
│ notifications,  │   │ (see §5 for current wiring gaps)             │
│ analytics_*     │   └──────────────────────────────────────────────┘
└─────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│  SQLAlchemy models: users, institutions, students, tickets,    │
│  problems, aggregation_groups, notifications, telegram, …        │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. What is implemented and usable

### 3.1 API surface (routers mounted in `main.py`)

| Area | Route module | Role (short) |
|------|----------------|--------------|
| Authentication | `routes/auth.py` | Register, login, tokens, user profile (JWT). |
| Institutions | `routes/institutional.py` | Schools, filières, classes (admin / scoped roles). |
| Students | `routes/students.py` | Student profiles, groups, trombinoscope-style flows as implemented. |
| Tickets | `routes/tickets.py` | Create ticket + problem, list/filter, status updates, admin lists. |
| Files | `routes/files.py` | File upload handling (Cloudinary-related service). |
| Notifications | `routes/notifications.py` | REST + WebSocket for in-app notifications. |
| Telegram | `routes/telegram.py` | Register bot/group, send, messages, webhook-style intake. |
| Agents | `routes/agents.py` | **Placeholder** — router exists, no operational endpoints yet. |
| Analytics | `routes/analytics.py` | School / filière / class stats, trends, top issues (uses `analytics_service.py`). |

### 3.2 Domain & data

- **Users & roles:** `student`, `delegate`, `teacher`, `admin`, `listening` (see `app/models/user.py`).
- **Hierarchy:** `School` → `Filiere` → `Class`; students linked to classes; tickets scoped by class/student.
- **Tickets:** `Ticket`, `TicketHistory`, statuses, priorities, categories (`app/models/ticket.py`).
- **Problems & patterns:** `Problem`, `AggregationGroup` (`app/models/problem.py`); aggregator agent targets these tables.
- **Notifications:** persisted `Notification` model + in-memory WebSocket fan-out (`app/services/notifications.py`).
- **Telegram:** `TelegramGroup` / `TelegramMessage`; real HTTP calls to Telegram Bot API when configured (`app/services/telegram.py`).

### 3.3 Cross-cutting behavior

- **DB:** `init_db_background()` runs `create_all` in a **background task** with logging; engine uses **15s asyncpg connect timeout** for PostgreSQL. Prefer Alembic for production (e.g. revision `6c31492135c4` for `problems` columns).
- **Escalation job:** APScheduler runs **hourly** and calls `auto_escalate_overdue_tickets` (tickets in progress too long → escalated + history row).
- **Agent orchestration (intended):** `run_pipeline` in `app/services/agents.py` builds `AgentState` and calls `run_agent_pipeline` in `app/agents/pipeline.py` after a ticket is created (`app/services/tickets.py`).

### 3.4 Agent building blocks (code present)

| Module | Responsibility |
|--------|------------------|
| `state.py` | `AgentState` TypedDict (text, category, priority, routing, summary, ids, errors). |
| `classifier.py` | `ClassifierAgent` — Mistral API, JSON classification + `langdetect`. |
| `aggregator.py` | `AggregatorAgent` — Mistral + DB; groups problems, writes `AggregationGroup` / `Problem`. |
| `router.py` | Rule-based destination: teacher / admin / listening / emergency / delegate. |
| `summary.py` | `build_summary` — OpenRouter `chat_json` + French fallback text. |
| `broadcast.py` | Calls `notify_destination`; sets `telegram_sent` flag (see §5). |
| `openrouter_client.py` | Shared JSON chat helper for OpenRouter-compatible APIs. |

---

## 4. Functional scenarios (what the system *should* do)

Aligned with `README_USE_CASES.md`:

1. **Student submits a problem** → ticket + problem row → agent pipeline → notifications (and optionally Telegram).
2. **Staff sees routed work** → notifications (and WebSockets) for mapped roles by destination.
3. **Delegates / teachers / admins** → list class tickets, update status, view history.
4. **Analytics** → school overview, filière stats, class patterns, trends, top issues.
5. **Telegram** → register class group, send summaries, optional webhook to create tickets from messages.
6. **Operations** → overdue escalation without manual cron.

---

## 5. Implementation status (not done or partial)

| Area | Status |
|------|--------|
| **End-to-end test (automated)** | **`tests/test_pipeline_e2e.py`** runs **`run_agent_pipeline`** with **Mistral + aggregator + OpenRouter** HTTP mocked (**respx**) and SQLite; **`notify_destination`** / Telegram **mocked** at broadcast. |
| **SMTP / email** | Config only; not wired into notifications. |
| **Rate limiting / idempotency** | Not implemented. |
| **Full dry-run + aggregation** | **`POST /agents/dry-run`** is light (no aggregation). |
| **Manual verification** | Real DB: ticket → persisted notifications → Telegram still needs a live check. |
| **Frontend / mobile** | Out of scope for this backend repo. |
| **Full `README_USE_CASES.md` coverage** | Backend is a **subset** of the product story. |

**Secrets:** **`MISTRAL_API_KEY`**, **`OPENROUTER_API_KEY`**, DB, **`SECRET_KEY`**, Cloudinary — see **`.env.example`**.

---

## 6. Tests

From `wasit-backend/` with a venv and **`pip install -r requirements.txt`**:

```bash
pytest tests/ -v
```

Covers **router** rules, **classifier** (Mistral mocked via **respx**), **`agent_persist`** on SQLite, and **`test_pipeline_e2e`** — full **`run_agent_pipeline`** with Mistral + OpenRouter mocked and broadcast side effects patched.

## 7. Next backlog (see `BACKEND_INTEGRATION_PLAN.md`)

1. **Email / SMTP** — optional mail channel for notifications.
2. **Rate limiting & idempotency** — ticket creation and Telegram webhooks.
3. **Optional:** admin endpoint that runs aggregation against a throwaway/rollback session.

---

## 8. Environment & dependencies (summary)

- **Runtime:** Python 3.11+ recommended; see `requirements.txt` (FastAPI, SQLAlchemy, asyncpg, JWT, httpx, APScheduler, websockets, etc.).
- **Required secrets (typical):** `DATABASE_URL`, `SECRET_KEY`, `MISTRAL_API_KEY`, Cloudinary keys; plus OpenRouter variables once settings are aligned; optional `TELEGRAM_BOT_TOKEN`, SMTP.

---

## 9. Related documents

| Document | Content |
|----------|---------|
| `../README.md` | Product vision & narrative |
| `README_USE_CASES.md` | User-level use cases |
| `README_DEV2.md` | Developer integration notes |
| `README_DEV2_STATUS.md` | Session checklist (may be partially outdated vs `main`) |
| `BACKEND_INTEGRATION_PLAN.md` | Phased plan: bugs, missing pieces, wiring DB/agents/notifications |

---

*Last updated to reflect the backend layout on branch `main` (merge of `dev1/foundation` and subsequent work). Revisit §5–§6 after major merges.*
