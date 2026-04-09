# Wasit Backend - System Use Cases

This document describes the main end-to-end use cases of the entire Wasit system.
It is product-focused and implementation-aware.

## Actors

- Student
- Delegate (class representative)
- Teacher
- Listening service staff
- Admin
- System (scheduler + agent pipeline + integrations)

---

## UC-01 - Student submits a problem

**Actor:** Student  
**Trigger:** Student sends free-text issue from dashboard or chat channel.

**Flow:**

1. Student submits problem text.
2. System creates `Ticket` + `Problem` record.
3. Agent pipeline starts: `Classifier -> Aggregator -> Router -> Summary -> Broadcast`.
4. Destination user/group gets notification.
5. Student can track status updates.

**Result:** A traceable ticket exists and is routed to the right destination.

---

## UC-02 - Academic issue aggregation

**Actor:** System  
**Trigger:** Multiple students report similar academic issue.

**Flow:**

1. Aggregator detects similar pattern.
2. System increments group count.
3. Router chooses:
   - `teacher` for repeated class-level issue,
   - `delegate` for isolated case.
4. Summary agent builds structured message.

**Result:** Staff receives grouped context instead of many isolated messages.

---

## UC-03 - Personal support routing

**Actor:** Student/System  
**Trigger:** Student reports personal/emotional issue.

**Flow:**

1. Classifier marks category `personal`.
2. Router sends destination to `listening`.
3. Summary generated for listening service.
4. Notification delivered to relevant staff.

**Result:** Sensitive cases go to the correct human channel quickly.

---

## UC-04 - Emergency escalation

**Actor:** Student/System  
**Trigger:** Emergency keywords/context detected.

**Flow:**

1. Classifier marks `emergency`.
2. Router selects emergency destination.
3. Pipeline uses fast path (summary may be skipped depending on config).
4. Broadcast sends urgent notifications.

**Result:** Critical incidents are escalated with priority.

---

## UC-05 - Staff updates ticket lifecycle

**Actor:** Delegate/Teacher/Admin/Listening  
**Trigger:** Staff changes ticket status.

**Flow:**

1. Staff updates status (`open`, `in_progress`, `resolved`, `closed`, `escalated`).
2. System stores `TicketHistory` entry with actor and note.
3. Student and relevant stakeholders are notified.

**Result:** Ticket lifecycle remains auditable and transparent.

---

## UC-06 - Automatic overdue escalation

**Actor:** System Scheduler  
**Trigger:** Ticket in `in_progress` exceeds configured SLA (e.g., 48h).

**Flow:**

1. Scheduler scans overdue tickets periodically.
2. Status changes to `escalated`.
3. History note is added automatically.
4. Escalation notifications are sent.

**Result:** Stuck tickets are not silently forgotten.

---

## UC-07 - Telegram class integration

**Actor:** Delegate/Admin/System/Student  
**Trigger:** Telegram messages or announcements.

**Flow (outbound):**

1. Delegate/admin sends class message via API.
2. Bot sends to class Telegram group.
3. Message is persisted in DB.

**Flow (inbound):**

1. Telegram webhook receives student message.
2. System maps group -> class.
3. System creates ticket from message if it is an issue.

**Result:** Existing student communication channel is integrated into support workflow.

---

## UC-08 - Real-time notifications dashboard

**Actor:** Staff/Admin  
**Trigger:** New ticket events or status changes.

**Flow:**

1. System pushes live events via WebSocket.
2. Notification is also saved in DB for offline users.
3. User opens notifications list and marks items as read.

**Result:** Real-time visibility with persistent notification history.

---

## UC-09 - Institutional setup and class structure

**Actor:** Admin  
**Trigger:** Start of academic year / organization setup.

**Flow:**

1. Admin creates school, filieres, classes.
2. Admin assigns delegate.
3. Admin links Telegram group to class.
4. Student list is imported (trombinoscope flow).

**Result:** Institutional hierarchy is ready for ticket and communication operations.

---

## UC-10 - Analytics and decision support

**Actor:** Admin/Filiere responsible  
**Trigger:** Need to monitor institutional health.

**Flow:**

1. System aggregates ticket data by class/filiere/school.
2. Shows top issue patterns, trends, SLA indicators.
3. Decision makers identify hotspots and unresolved areas.

**Result:** Data-driven intervention at class and institution level.

---

## Cross-Cutting Rules

- Role-based access control required for protected endpoints.
- Every status change must create a history entry.
- Agent failures should not crash API request path; errors are captured and logged.
- Sensitive categories (personal/emergency) must be routed safely.
- External integrations (LLM/Telegram/email) should have safe fallbacks.

---

## Success Criteria (System-Level)

The system is considered operational when:

1. Students can submit issues in plain language.
2. Each issue becomes a trackable ticket.
3. Agent pipeline routes to correct destination.
4. Staff receives structured actionable notifications.
5. Ticket lifecycle updates are auditable.
6. Telegram and dashboard channels both work.
7. Admin can view patterns and trends for decisions.
