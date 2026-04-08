# Wasit Backend - Dev 2 Execution Guide

This README is your personal implementation guide as **Developer 2**.
It is based on the task split defined in `mon_conversation_claude.md`.

## Your Mission

You own:

1. Ticket Service
2. Agent Router
3. Agent Summary
4. Agent Broadcast
5. LangGraph Pipeline Assembly
6. Telegram Service
7. Notification Service

Goal: deliver the full "problem -> routing -> notification" execution flow.

---

## Dependency and Sync

You can start coding now, but one dependency must be ready from Dev 1:

- Auth dependency (`get_current_user`)
- Roles and RBAC (`student`, `delegate`, `teacher`, `admin`, `listening`)

### Sync rule

- Blocker: role-protected routes depend on Auth from Dev 1.
- Workaround: implement your services/routes first, then wire final role checks after Dev 1 merge.

---

## Build Order (strict)

1. Ticket Service first
2. Router + Summary + Broadcast agents
3. Pipeline assembly (`pipeline.py`)
4. Telegram service/routes
5. Notification service/routes + WebSocket
6. Final integration and tests

Do not start Telegram/Notifications before Ticket + agent core is stable.

---

## Detailed Task List

## 1) Ticket Service

### Files

- `app/schemas/ticket.py`
- `app/services/ticket_service.py`
- `app/api/v1/routes/tickets.py`

### Required features

- `POST /tickets` (student): create ticket from free text (`raw_text`)
- `GET /tickets/{ticket_id}`: owner or staff can read details
- `GET /students/me/tickets`: list current student tickets
- `GET /classes/{class_id}/tickets`: delegate/teacher/admin access
- `PATCH /tickets/{ticket_id}/status`: staff update with note + history
- `GET /admin/tickets`: admin global view (optional status filter)

### Business logic

- Create `Problem` + `Ticket` together
- Trigger `agent_service.run_pipeline(...)` after ticket creation
- Store `TicketHistory` for every status transition
- Implement auto escalation after 48h for stale `in_progress` tickets

### Done criteria

- Ticket lifecycle works end-to-end
- History is persisted
- Role/ownership checks are enforced

---

## 2) Agent Router

### File

- `app/agents/router.py`

### Logic rules (no LLM)

- `emergency -> emergency`
- `personal -> listening`
- `academic` + `similar_count >= 3 -> teacher`
- `academic` + `similar_count < 3 -> delegate`
- `administrative -> admin`

### Done criteria

- Deterministic routing, unit-testable, no external dependency.

---

## 3) Agent Summary

### File

- `app/agents/summary.py`

### Goal

- Generate concise professional message for the selected destination.
- Use state fields: category, priority, raw_text, similar_count, destination.
- Keep output short and actionable.

### Done criteria

- For valid input state, returns non-empty structured summary.
- Handles provider/API errors safely.

---

## 4) Agent Broadcast

### File

- `app/agents/broadcast.py`

### Responsibilities

- Update ticket metadata (category, priority, destination/assignment field)
- Trigger destination notification via notification service
- Send Telegram group message when required
- Mark broadcast completion in state (`telegram_sent`)

### Done criteria

- No silent failures: errors are logged/propagated safely.

---

## 5) LangGraph Pipeline Assembly

### Files

- `app/agents/pipeline.py`
- `app/services/agent_service.py`

### Graph

- Nodes: classifier -> aggregator -> router -> summary -> broadcast
- Conditional: emergency can skip summary and go directly to broadcast

### `agent_service.run_pipeline(...)`

- Build initial state
- Invoke compiled graph
- Return final state
- Catch and log errors with ticket context

### Done criteria

- Pipeline can be called from ticket creation flow without breaking request.

---

## 6) Telegram Service

### Files

- `app/services/telegram_service.py`
- `app/api/v1/routes/telegram.py`

### Endpoints

- `POST /telegram/webhook/{bot_token}`
- `POST /classes/{class_id}/telegram/register`
- `POST /classes/{class_id}/telegram/send`
- `GET /classes/{class_id}/telegram/messages`

### Responsibilities

- Register class group
- Send outbound messages and persist `TelegramMessage`
- Process inbound webhook messages
- Convert student message into ticket when needed

### Done criteria

- Webhook path functions
- Outbound/inbound message records are saved
- Ticket creation from Telegram works

---

## 7) Notification Service

### Files

- `app/services/notification_service.py`
- `app/api/v1/routes/notifications.py`

### Features

- WebSocket connection manager
  - connect/disconnect by user
  - send to user
  - broadcast by role
- Persist notification rows
- Mark notification as read
- Retrieve user notifications

### Endpoints

- `GET /notifications/me`
- `PATCH /notifications/{id}/read`
- `WS /ws/{user_id}` (token-authenticated)

### Done criteria

- Real-time + persistence both work.

---

## Integration Checklist

- [ ] Ticket creation calls pipeline service
- [ ] Pipeline reaches broadcast node
- [ ] Broadcast triggers notification service
- [ ] Telegram route can create ticket from webhook
- [ ] Status updates write history correctly
- [ ] Role checks applied to all protected routes
- [ ] Error responses use proper HTTP status codes

---

## Suggested 5-Day Plan

### Day 1

- Implement `schemas/ticket.py`, `ticket_service.py`, `tickets.py` routes.

### Day 2

- Implement `router.py`, `summary.py`, `broadcast.py`.

### Day 3

- Implement `pipeline.py` and `agent_service.py`, wire to ticket flow.

### Day 4

- Implement Telegram service + routes + webhook handling.

### Day 5

- Implement notifications (REST + WS), final integration, bug fixes, tests.

---

## Minimum Test Scope (must have)

- Ticket creation and retrieval
- Ticket status update + history persistence
- Router logic table test (all categories/conditions)
- One pipeline smoke test
- One Telegram webhook -> ticket test (mocked)
- One notification WebSocket delivery test (or service-level unit test)

---

## Git Workflow for Your Branch

- Branch: `feature/dev2-ticket-agents-integrations`
- Commit small and often by module
- Rebase/merge from `main` regularly
- Resolve conflicts early in:
  - `main.py`
  - shared models/schemas
  - route registration

---

## Handover Definition

Your handover is complete when:

1. A student can submit a problem
2. A ticket is created and processed by pipeline
3. Destination is selected and notified
4. Staff can update status with full history
5. Telegram and WebSocket channels both function

If these 5 are true, your Dev 2 scope is successful.
