Explication simple des 9 services
1. Auth Service — Gère qui peut entrer et avec quel rôle. Quand quelqu'un se connecte, il reçoit un token JWT. Ce token prouve son identité à chaque requête. Les 5 rôles (étudiant, délégué, enseignant, admin, écoute) déterminent ce qu'il peut voir/faire.
2. Institutional Service — Le CRUD de la structure de l'université : créer une école, ajouter une filière, créer une classe. C'est la fondation sur laquelle tout le reste s'appuie.
3. Student Service — Gère les profils étudiants. Quand l'admin upload le CSV (trombinoscope), ce service le parse et crée les profils automatiquement. Il gère aussi les groupes projet.
4. Agent Pipeline Service — Le cœur. 5 agents qui se passent le problème comme une chaîne de montage : Classifier → Aggregator → Router → Summary → Broadcast. Chaque agent fait une seule chose et passe le résultat au suivant.
5. Ticket Service — Chaque problème soumis devient un ticket. Ce service gère son cycle de vie : créé → en cours → résolu. Si pas de réponse après X jours, escalade automatique au niveau supérieur.
6. Telegram Service — Connecte chaque classe à son groupe Telegram. Le bot reçoit des messages, envoie des annonces, et relaie les notifications. Bidirectionnel.
7. Notification Service — WebSocket pour le dashboard en temps réel (les admins voient les updates instantanément) + email SMTP pour les notifications importantes.
8. Analytics Service — Agrège les données de tous les tickets pour produire des statistiques : quels problèmes reviennent le plus, dans quelle filière, à quelle période. Dashboard admin.
9. File Service — Upload et parsing du CSV trombinoscope, stockage des photos étudiants.

Prompts Cursor Pro — dans l'ordre
Colle-les un par un, dans cet ordre exact.

Prompt 2 — Base de données & modèles SQLAlchemy
In the wasit-backend project, implement all SQLAlchemy models in app/models/.

Create these files with full model definitions:

app/models/user.py:
- User: id (UUID), email, hashed_password, role (enum: student/delegate/teacher/admin/listening), first_name, last_name, phone, is_active, created_at, updated_at
- Role enum class

app/models/institution.py:
- School: id, name, domain, created_at
- Filiere: id, school_id (FK), name, responsible_id (FK -> User), created_at
- Class: id, filiere_id (FK), name, academic_year, delegate_id (FK -> User), telegram_group_id, created_at

app/models/student.py:
- Student: id, user_id (FK -> User), class_id (FK -> Class), student_number, photo_url, is_active
- ProjectGroup: id, class_id, name, created_at
- ProjectGroupMember: id, group_id (FK), student_id (FK)

app/models/ticket.py:
- Ticket: id (UUID), student_id (FK), class_id (FK), title, description, status (enum: open/in_progress/escalated/resolved/closed), priority (enum: low/medium/high/urgent/emergency), category (enum: academic/administrative/personal/emergency), assigned_to (FK -> User nullable), created_at, updated_at, resolved_at
- TicketHistory: id, ticket_id (FK), changed_by (FK -> User), old_status, new_status, note, created_at

app/models/problem.py:
- Problem: id, ticket_id (FK), raw_text, language_detected, classified_category, aggregation_group_id, created_at
- AggregationGroup: id, class_id (FK), pattern_key, count, first_seen, last_seen

app/models/telegram.py:
- TelegramGroup: id, class_id (FK unique), chat_id (string), bot_token, is_active
- TelegramMessage: id, group_id (FK), direction (in/out), message_text, sent_at

app/models/notification.py:
- Notification: id, user_id (FK), title, body, type, is_read, created_at

Use SQLAlchemy 2.0 declarative style with mapped_column and Mapped types. Add __tablename__, __repr__, and all relationships. Import Base from app/core/database.py.

Also implement app/core/database.py with async SQLAlchemy engine, SessionLocal, Base, and get_db dependency.

Also implement app/core/config.py using pydantic-settings BaseSettings reading from .env: DATABASE_URL, SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES, ANTHROPIC_API_KEY, TELEGRAM_BOT_TOKEN.

Prompt 3 — Auth Service complet
Implement the complete Auth Service for wasit-backend.

app/core/security.py:
- hash_password(password) using bcrypt
- verify_password(plain, hashed)
- create_access_token(data, expires_delta) returning JWT
- create_refresh_token(data) with longer expiry
- decode_token(token) returning payload or raising HTTPException 401

app/schemas/auth.py:
- UserCreate: email, password, role, first_name, last_name, phone (optional)
- UserLogin: email, password
- Token: access_token, refresh_token, token_type
- TokenRefresh: refresh_token
- UserResponse: id, email, role, first_name, last_name, is_active (no password)

app/services/auth_service.py:
- register(db, user_create) -> User: check email uniqueness, hash password, create user
- login(db, email, password) -> Token: verify credentials, return both tokens
- refresh_token(db, refresh_token) -> Token: validate refresh token, return new pair
- get_current_user(token, db) -> User: decode JWT, fetch user from DB

app/core/dependencies.py:
- get_current_user: FastAPI dependency extracting user from Bearer token
- require_role(*roles): dependency factory that checks user.role is in allowed roles
  Example: require_role("admin", "delegate")

app/api/v1/routes/auth.py:
- POST /auth/register -> UserResponse
- POST /auth/login -> Token
- POST /auth/refresh -> Token
- GET /auth/me -> UserResponse (protected)
- POST /auth/logout (invalidate token — add token to a blocklist set in memory for now)

Wire the router into main.py with prefix /api/v1.
Use async def everywhere. Handle all errors with appropriate HTTPException codes.

Prompt 4 — Institutional & Student Services
Implement the Institutional Service and Student Service for wasit-backend.

app/schemas/institution.py:
- SchoolCreate, SchoolResponse
- FiliereCreate (name, school_id, responsible_id), FiliereResponse
- ClassCreate (name, filiere_id, academic_year), ClassResponse (includes delegate info)

app/services/institutional_service.py (all async):
- create_school(db, data) -> School
- get_schools(db) -> list[School]
- create_filiere(db, data) -> Filiere (validate school exists)
- create_class(db, data) -> Class (validate filiere exists)
- assign_delegate(db, class_id, user_id) -> Class (validate user role is delegate)
- get_class_with_details(db, class_id) -> dict with school, filiere, class, students count

app/api/v1/routes/institutional.py:
- POST /schools (admin only)
- GET /schools
- POST /filieres (admin only)
- POST /classes (admin only)
- PATCH /classes/{class_id}/delegate (admin only)
- GET /classes/{class_id} (any authenticated)

app/services/file_service.py:
- parse_trombinoscope_csv(file: UploadFile) -> list[dict]
  CSV format: student_number, first_name, last_name, email, phone, photo_url (optional)
  Validate each row, return errors for invalid rows
- save_upload(file, destination_folder) -> str (returns file path)

app/services/student_service.py:
- bulk_create_students(db, class_id, parsed_rows) -> dict{created, skipped, errors}
  For each row: create User (role=student, random temp password), then create Student record
- get_class_students(db, class_id) -> list[Student with user info]
- generate_project_groups(db, class_id, group_size) -> list[ProjectGroup]
  Distribute students evenly into groups of group_size, create ProjectGroup and ProjectGroupMember records, return the groups
- get_student_by_user(db, user_id) -> Student

app/api/v1/routes/students.py:
- POST /classes/{class_id}/upload-trombinoscope (admin/delegate, multipart/form-data)
- GET /classes/{class_id}/students
- POST /classes/{class_id}/project-groups (body: {group_size: int})
- GET /classes/{class_id}/project-groups

Prompt 5 — Ticket Service
Implement the complete Ticket Service for wasit-backend.

app/schemas/ticket.py:
- ProblemSubmit: raw_text (the student's free-text problem, any language)
- TicketResponse: id, title, category, priority, status, assigned_to, created_at, history
- TicketUpdate: status, note (for staff to update tickets)
- TicketHistoryResponse: old_status, new_status, note, changed_by_name, created_at

app/services/ticket_service.py (all async):
- create_ticket_from_problem(db, student_id, class_id, raw_text) -> Ticket
  Create a Problem record and a Ticket with status=open, fire the agent pipeline (call agent_service.run_pipeline — stub for now, implement in next prompt)
  
- get_ticket(db, ticket_id) -> Ticket with history
- get_student_tickets(db, student_id) -> list[Ticket]
- get_class_tickets(db, class_id, status_filter=None) -> list[Ticket]
- get_all_open_tickets(db, school_id) -> list[Ticket] (for admin dashboard)

- update_ticket_status(db, ticket_id, new_status, changed_by_id, note) -> Ticket
  Update status, create TicketHistory entry, trigger notification

- auto_escalate_overdue_tickets(db) -> int (number escalated)
  Find tickets with status=in_progress and updated_at older than 48h
  Change status to escalated, create history entry with note="Auto-escalated: no response in 48h"
  This will be called by a background scheduler

app/api/v1/routes/tickets.py:
- POST /tickets (authenticated student) — body: {raw_text: str}
- GET /tickets/{ticket_id} (ticket owner or staff)
- GET /students/me/tickets (current student's tickets)
- GET /classes/{class_id}/tickets (delegate/teacher/admin)
- PATCH /tickets/{ticket_id}/status (staff only — delegate/teacher/admin/listening)
- GET /admin/tickets (admin only, optional ?status= filter)

In main.py, add an APScheduler background job that calls auto_escalate_overdue_tickets every hour.
Install apscheduler and add to requirements.txt.

Prompt 6 — Agent Pipeline (LangGraph + Claude)
Implement the 5-agent LangGraph pipeline for wasit-backend.

app/agents/state.py:
Define the shared AgentState TypedDict:
- raw_text: str
- language: str
- category: str (academic/administrative/personal/emergency)
- priority: str (low/medium/high/urgent/emergency)
- aggregation_group_id: str | None
- similar_count: int
- destination: str (teacher/admin/listening/emergency/delegate)
- structured_summary: str
- ticket_id: str
- class_id: str
- student_id: str
- telegram_sent: bool
- error: str | None

app/agents/classifier.py — ClassifierAgent:
- Input: raw_text, language detected via langdetect library
- Call Claude API (claude-sonnet-4-6) with this system prompt:
  "You are a classifier for university student problems. Classify the problem into: category (academic/administrative/personal/emergency) and priority (low/medium/high/urgent/emergency). Respond ONLY with JSON: {category, priority, language}"
- Parse response, update state with category, priority, language

app/agents/aggregator.py — AggregatorAgent:
- Query DB for recent Problems in same class_id with same category (last 7 days)
- Use Claude to compare raw_text with existing aggregation groups:
  "Given this new problem: [text]. Given these existing problem groups: [list]. Does this belong to an existing group? Respond ONLY with JSON: {group_id: string_or_null, is_new_group: bool, pattern_key: string}"
- If new group: create AggregationGroup record
- If existing: increment count, update last_seen
- Update state with aggregation_group_id, similar_count

app/agents/router.py — RouterAgent:
- Logic (no LLM needed, pure rules):
  - emergency → destination = "emergency"
  - personal → destination = "listening"
  - academic + similar_count >= 3 → destination = "teacher" (group issue)
  - academic + similar_count < 3 → destination = "delegate"
  - administrative → destination = "admin"
- Update state with destination

app/agents/summary.py — SummaryAgent:
- Call Claude with the full state context:
  "Write a professional, concise message to the [destination] about this student issue. Category: [category]. Problem: [raw_text]. Similar issues in class: [similar_count]. Priority: [priority]. Write in French. Be direct and actionable. Max 150 words."
- Update state with structured_summary

app/agents/broadcast.py — BroadcastAgent:
- Update the Ticket in DB: set category, priority, assigned destination
- Call notification_service.notify_destination(destination, structured_summary, ticket_id) — stub
- Call telegram_service.send_to_group(class_id, message) if destination == teacher — stub
- Set state telegram_sent = True

app/agents/pipeline.py — assemble the LangGraph graph:
- Create StateGraph(AgentState)
- Add nodes: classifier, aggregator, router, summary, broadcast
- Add edges: classifier → aggregator → router → summary → broadcast
- Add conditional edge after router: if category == emergency, go directly to broadcast (skip summary)
- Compile and export as pipeline

app/services/agent_service.py:
- run_pipeline(ticket_id, class_id, student_id, raw_text) -> AgentState
  Build initial state, invoke compiled pipeline, return final state
  Wrap in try/except, log errors to ticket

Install: langgraph, anthropic, langdetect. Add to requirements.txt.

Prompt 7 — Telegram & Notifications
Implement the Telegram Service and Notification Service for wasit-backend.

app/services/telegram_service.py:
- init_bot(bot_token) -> Application (python-telegram-bot)
- register_group(db, class_id, chat_id, bot_token) -> TelegramGroup
- send_message(db, class_id, text) -> TelegramMessage record
  Fetch group by class_id, send via bot, save outbound TelegramMessage
- handle_incoming(db, update) -> None
  When a student sends a message to the group, create a ticket via ticket_service.create_ticket_from_problem
  Save inbound TelegramMessage

app/api/v1/routes/telegram.py:
- POST /telegram/webhook/{bot_token} — receives Telegram webhook updates, calls handle_incoming
- POST /classes/{class_id}/telegram/register (admin) — body: {chat_id, bot_token}
- POST /classes/{class_id}/telegram/send (delegate/admin) — body: {text}
- GET /classes/{class_id}/telegram/messages

app/services/notification_service.py:
- WebSocket manager:
  class ConnectionManager:
    - connect(websocket, user_id)
    - disconnect(websocket, user_id)  
    - send_to_user(user_id, message: dict)
    - broadcast_to_role(role, message: dict)

- notify_destination(destination, summary, ticket_id, db) -> None
  Based on destination string, find the right user(s) and:
  1. Send WebSocket notification if connected
  2. Create Notification record in DB
  3. (stub) send email via SMTP

- get_user_notifications(db, user_id, unread_only=False) -> list[Notification]
- mark_notification_read(db, notification_id, user_id) -> Notification

app/api/v1/routes/notifications.py:
- GET /notifications/me (current user's notifications)
- PATCH /notifications/{id}/read
- WebSocket: WS /ws/{user_id} — authenticates via token query param, registers connection

Add websockets to requirements.txt.
In main.py: mount the webhook route without auth middleware (Telegram doesn't send JWT). Add startup event to log "Wasit backend ready".

Prompt 8 — Analytics & finalisation
Implement the Analytics Service and finalize wasit-backend.

app/services/analytics_service.py (all async):
- get_school_overview(db, school_id) -> dict:
  {total_tickets, open_tickets, resolved_tickets, escalated_tickets, avg_resolution_hours, tickets_by_category: {academic: n, administrative: n, personal: n, emergency: n}}

- get_filiere_stats(db, filiere_id) -> dict:
  {classes: [{class_name, total_tickets, open_tickets, top_category}]}

- get_class_patterns(db, class_id) -> dict:
  {aggregation_groups: [{pattern_key, count, last_seen, category}], total_students, active_tickets}

- get_ticket_trends(db, school_id, days=30) -> list[dict]:
  Group tickets by day for the last N days: [{date, created_count, resolved_count}]

- get_top_issues(db, school_id, limit=10) -> list[dict]:
  Most frequent aggregation groups across all classes: [{pattern_key, count, category, class_name}]

app/api/v1/routes/analytics.py:
- GET /analytics/school/{school_id} (admin only)
- GET /analytics/filiere/{filiere_id} (admin/responsible)
- GET /analytics/class/{class_id} (admin/delegate/teacher)
- GET /analytics/school/{school_id}/trends?days=30 (admin only)
- GET /analytics/school/{school_id}/top-issues (admin only)

Final wiring in main.py:
- Include all routers with /api/v1 prefix
- Add CORS middleware (allow all origins for hackathon)
- Add global exception handler returning {detail: str} for unhandled errors
- Add /health endpoint returning {status: ok, version: 1.0.0}

Create .env.example with all variables:
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/wasit
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
ANTHROPIC_API_KEY=sk-ant-...
TELEGRAM_BOT_TOKEN=...
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=...
SMTP_PASSWORD=...

Create requirements.txt with exact versions:
fastapi==0.115.0, uvicorn==0.30.6, sqlalchemy==2.0.35, asyncpg==0.29.0, alembic==1.13.3, pydantic-settings==2.5.2, python-jose==3.3.0, passlib[bcrypt]==1.7.4, python-multipart==0.0.12, anthropic==0.34.2, langgraph==0.2.28, langdetect==1.0.9, python-telegram-bot==21.6, apscheduler==3.10.4, websockets==13.1, httpx==0.27.2

Create alembic/env.py configured for async SQLAlchemy with our Base metadata.
Create a README with: setup instructions, how to run migrations, how to start the server.

Ordre d'exécution : Colle prompt 2 → attends que Cursor finisse → prompt 3 → etc. Ne saute pas d'étape car chaque prompt dépend des modèles et services créés avant.Files hidden in shared chatsest ce que en peut remplacer telegrame par notre chat et ce que peut realiser et encas de telegram et ce que ca gratuit5:12 PMRemplacer Telegram par votre propre chat
Oui, c'est faisable. Voici la comparaison honnête :

Ce que Telegram fait pour vous (gratuitement)

Infrastructure déjà existante, les étudiants ont déjà l'app
Notifications push natives sur mobile
Bot API gratuite et stable
Zéro coût d'hébergement pour le chat lui-même
Fonctionne offline (messages en attente)


Ce que votre propre chat peut faire

Interface intégrée dans votre dashboard Next.js
Contrôle total sur les données
Pas de dépendance externe
Design custom selon vos besoins
Techniquement : WebSocket (déjà dans votre stack) + table messages en DB


Ce que vous perdez

Les étudiants doivent ouvrir votre app au lieu de Telegram qu'ils ont déjà
Pas de notifications push mobile sans PWA ou app native
Vous hébergez le trafic vous-même (coût serveur)
Temps de développement supplémentaire en plein hackathon


Mon conseil pour le hackathon
Gardez Telegram. Les raisons :

C'est gratuit et illimité
Le prompt 7 l'implémente en ~2h avec Cursor
L'adoption étudiante est immédiate (ils ont déjà Telegram)
Vous économisez 2-3 jours de dev pour construire un chat from scratch

Si après le hackathon le projet évolue en produit réel, là vous construisez votre propre chat. Pour l'instant, Telegram est un avantage, pas une limitation.est ce que c'est possible avec whatsapp5:14 PMWhatsApp — La réalité
Techniquement possible, mais compliqué
WhatsApp n'a pas d'API officielle gratuite comme Telegram.

Les options disponibles
1. WhatsApp Business API (officielle)

Payante — environ 0.05$/message
Nécessite une approbation Meta (1-2 semaines)
Impossible pour un hackathon

2. Twilio WhatsApp

Payant aussi, passe par WhatsApp Business API
Même contrainte d'approbation

3. whatsapp-web.js (non officielle)

Simule un navigateur connecté à votre compte WhatsApp
Gratuit mais fragile — Meta peut bloquer votre numéro à tout moment
Risque réel en production


Comparaison directe
CritèreTelegramWhatsAppAPI gratuite✅ Oui❌ NonDélai d'accèsImmédiat1-2 semainesRisque de blocageZéroÉlevé (API non officielle)Faisable en hackathon✅ Oui❌ Non

Conclusion
Pour le hackathon, WhatsApp est à éviter absolument. Telegram reste la seule option gratuite, stable, et implémentable en quelques heures avec python-telegram-bot.ok je peut garder avec telegrame je veut travailer ce projet a avec mon mie et nous avons besoin de diviser les tache de backend en deux tu peut me diviser les services en deux avec l'rode de reaisation pour cahcun5:15 PMDivision du backend en 2

👤 Développeur 1 — Fondations & Cœur métier
Ordre de réalisation :

Auth Service — JWT, 5 rôles, refresh tokens
Institutional Service — école / filière / classe, assign délégué
Student Service — profils, upload CSV trombinoscope, groupes projet
Ticket Service — création, cycle de vie, escalade automatique, historique

Il construit la base sur laquelle tout repose. Sans ses 4 services, rien ne fonctionne.

👤 Développeur 2 — Intelligence & Communication
Ordre de réalisation :

File Service — upload/parsing CSV (utilisé par Dev 1 pour le trombinoscope, à livrer en premier)
Agent Pipeline Service — les 5 agents LangGraph + Claude API
Telegram Service — bot par classe, webhooks, envoi/réception
Notification Service — WebSocket temps réel, emails
Analytics Service — dashboard admin, patterns, statistiques


Point de synchronisation important
Dev 2 doit livrer le File Service en premier car Dev 1 en a besoin pour l'upload CSV. C'est le seul point de dépendance critique entre les deux.
Le reste peut avancer en parallèle sans blocage.

Qui fait quoi sur la DB
Les deux créent leurs propres modèles SQLAlchemy. Dev 1 crée : users, schools, filieres, classes, students, tickets. Dev 2 crée : problems, aggregation_groups, telegram_groups, notifications.
Un seul fait tourner alembic revision --autogenerate à la fin quand les deux ont mergé leurs modèles.nonn rediviser d'une maniere equivalente car le 2eme devoloeur prendre l'ensemble des tache tu peut diviser aussi l'agent pipline pas de problem5:17 PMDivision équilibrée en 2

👤 Développeur 1 — Auth + Fondations + 2 Agents
Ordre de réalisation :

Auth Service — JWT, 5 rôles, refresh tokens, RBAC
Institutional Service — école / filière / classe, assign délégué
File Service — upload CSV, parsing, stockage photos
Student Service — profils, trombinoscope, groupes projet
Agent : Classifier — détecte catégorie + priorité via Claude
Agent : Aggregator — regroupe problèmes similaires, détecte patterns


👤 Développeur 2 — Tickets + Intégrations + 3 Agents
Ordre de réalisation :

Ticket Service — création, cycle de vie, escalade automatique, historique
Agent : Router — règles de routage (teacher/admin/écoute/urgence)
Agent : Summary — génère message structuré via Claude
Agent : Broadcast — notifie destinations, met à jour ticket
Telegram Service — bot par classe, webhooks bidirectionnels
Notification Service — WebSocket temps réel, emails
Analytics Service — dashboard, patterns, statistiques


Point de synchronisation
Dev 2 attend que Dev 1 finisse Auth Service avant de commencer — tous les services ont besoin du système de rôles et de get_current_user.
Le reste avance en parallèle sans blocage.le developeur avoir meme des tache simple que devolpeur 25:19 PMDivision équilibrée — Mix simple + complexe pour chacun

👤 Développeur 1 — Auth + Fondations + Analytics
#ServiceComplexité1Auth Service — JWT, rôles, RBAC🔴 Complexe2Institutional Service — école/filière/classe🟡 Moyenne3File Service — upload CSV, parsing🟢 Simple4Student Service — profils, groupes projet🟡 Moyenne5Agent Classifier — catégorie + priorité via Claude🟢 Simple6Agent Aggregator — patterns, regroupement🔴 Complexe7Analytics Service — dashboard, statistiques🟡 Moyenne

👤 Développeur 2 — Tickets + Agents + Intégrations
#ServiceComplexité1Ticket Service — cycle de vie, escalade auto🔴 Complexe2Agent Router — règles de routage🟢 Simple3Agent Summary — message structuré via Claude🟢 Simple4Agent Broadcast — notifie, met à jour ticket🟡 Moyenne5Pipeline LangGraph — assemble les 5 agents🔴 Complexe6Telegram Service — bot, webhooks🟡 Moyenne7Notification Service — WebSocket, emails🟡 Moyenne

Résumé par développeur
Dev 1Dev 2🔴 ComplexeAuth, AggregatorTicket, LangGraph🟡 MoyenneInstitutional, Student, AnalyticsBroadcast, Telegram, Notification🟢 SimpleFile, ClassifierRouter, SummaryTotal7 tâches7 tâches

Point de sync : Dev 2 attend Auth de Dev 1, puis tout avance en parallèle.