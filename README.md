# Wasit — واسط
### The Intelligent Institutional Intermediary

> *"An agentic AI platform that acts as the missing layer between university students and their institution — routing every problem, complaint, and request to exactly the right person, automatically."*

---

## Table of Contents

- [The Problem](#the-problem)
- [The Solution](#the-solution)
- [How It Works](#how-it-works)
- [Key Features](#key-features)
- [Who It Serves](#who-it-serves)
- [What Makes Wasit Different](#what-makes-wasit-different)
- [Tech Stack](#tech-stack)
- [Project Origin](#project-origin)
- [Official Submission Description](#official-submission-description)

---

## The Problem

Universities have services. Students can't find them.

Every university in the world has academic advisors, administrative offices, mental health counselors, listening services, and class representatives. The infrastructure exists. But students don't know which door to knock on — so they knock on none. Problems go unreported. Issues escalate silently. Students drop out not because they weren't helped, but because they never asked for help in the right place.

The current system forces students to navigate a bureaucratic maze alone, at the exact moment they are most overwhelmed. A first-year student failing an exam doesn't know whether to talk to their teacher, their delegate, the academic office, or the listening service. So they talk to nobody.

| Metric | Data |
|--------|------|
| Students unaware of support services | **50%** |
| Retention increase when students know 5+ services | **+13 points** |
| Students who used mental health services (despite being top dropout reason) | **Only 12%** |
| Students abandoning school yearly in Morocco alone | **280,000** |

---

## The Solution

**Wasit — واسط — the intelligent intermediary**

Wasit is a multi-agent AI platform that gives every university a complete institutional nervous system.

Students submit any problem in plain language — any language — through a single interface. Wasit's agent pipeline classifies the problem, aggregates similar issues from other students, routes it to the right person with a structured summary, and tracks resolution until the student receives a response.

- **At the class level:** each class has its own AI delegate — a digital version of the human class representative — that handles day-to-day communication, broadcasts teacher announcements to student Telegram groups, and manages administrative tasks like trombinoscope creation and project group generation.
- **At the filière level:** a supervisor agent aggregates patterns across classes.
- **At the institutional level:** administrators see the full picture in real time — what's happening, what's unresolved, and where the institution needs to act.

---

## How It Works

```
Student submits → Classifier → Aggregator → Router → Summary → Broadcast
```

| Step | Agent | Role |
|------|-------|------|
| 01 | **Student submits** | Any problem, any language, one interface. No forms, no categories to guess. |
| 02 | **Classifier agent** | Identifies: academic, administrative, personal, urgent, or emergency. |
| 03 | **Aggregator agent** | Groups similar issues. Counts frequency. Detects patterns across the class. |
| 04 | **Router agent** | Sends to the right destination: teacher, admin, listening service, or emergency. |
| 05 | **Summary agent** | Drafts a structured, professional message for the recipient. Not a raw complaint. |
| 06 | **Broadcast agent** | Student notified. Telegram updated. Ticket tracked until resolved. |

---

## Key Features

### 🤖 AI Class Delegate — per class, fully autonomous
Every class gets its own AI delegate that replicates everything a human delegate does. It collects student feedback, aggregates repeated issues, communicates with teachers, broadcasts announcements to the class Telegram group, and escalates unresolved problems upward.

At the start of the year, the delegate is activated with a CSV upload — the trombinoscope — and immediately knows every student by name, email, and photo. When a teacher needs project groups, the delegate generates and distributes them automatically.

### 🔀 Intelligent Routing Engine — five destinations, zero confusion
- **Academic problems** → teacher with a grouped summary
- **Administrative issues** → the relevant office
- **Personal or emotional problems** → listening service staff with a full context briefing already prepared
- **Repeated unresolved issues** → escalate automatically to the filière responsible
- **Emergency signals** → reach all relevant parties simultaneously

The student never has to decide who to contact.

### 🏛️ Institutional Hierarchy — class, filière, school
Wasit mirrors the real structure of a university:
- Each **class** has an AI delegate
- Each **filière** has a supervisor dashboard that aggregates patterns and manages escalations
- The **school administration** has a real-time view of every open ticket, every resolved issue, and every emerging pattern — across all filières, all promotions, all classes

### 📋 Trombinoscope System — the delegate knows its class
At the start of each academic year, the admin uploads the class list as a CSV. Wasit parses it automatically and builds a complete student identity model: names, emails, phone numbers, photos. Messages can be attributed, patterns can be linked to specific student groups, and the trombinoscope is available as a searchable directory.

### 📱 Real-time Telegram Integration — the channel students already use
Wasit doesn't ask students to download a new app. It connects directly to the class Telegram group that already exists. Teacher announcements, course cancellations, deadline reminders, and project group assignments are broadcast automatically — formatted, professional, and instant.

---

## Who It Serves

| User | Value |
|------|-------|
| **Students** | One place for any problem. No bureaucracy. Submit in Arabic, French, Darija, or English. |
| **Class delegates (human)** | AI handles repetitive admin work. Human delegate focuses on representation. |
| **Teachers** | Receive structured summaries — not 30 individual messages. "8 students are struggling with chapter 3" instead of 8 separate WhatsApp DMs at midnight. |
| **Listening service staff** | Receive only cases that need a human — with full context already prepared. |
| **Filière responsibles** | See patterns across all classes. Receive escalated cases. Coordinate with teachers and administration. |
| **Administration** | Real-time institutional dashboard. Every open ticket. Every resolved issue. Every emerging pattern. |

---

## What Makes Wasit Different

- **Not a chatbot.** Wasit is a pipeline of specialized agents — each with a single job — that together replicate the entire institutional communication system of a university.
- **Not a ticketing system.** Wasit understands context, aggregates patterns, routes intelligently, and escalates autonomously. It acts, not just records.
- **Not local.** Built for ENSET, deployable at any university on earth. The agent pipeline is language-agnostic. The hierarchy mirrors every university structure globally.
- **Built from lived experience.** The core idea came from a real class delegate who spent years doing this job manually. Wasit automates what he knows is broken.
- **Zero new apps for students.** Telegram integration means students use what they already have. Adoption barrier is zero.

---

## Tech Stack

| Layer | Technologies |
|-------|-------------|
| **Agent layer** | LangGraph · Claude API (`claude-sonnet-4-6`) · 5 specialized agents |
| **Backend** | FastAPI · PostgreSQL · WebSockets · python-telegram-bot |
| **Frontend** | Next.js 14 · Tailwind CSS · shadcn/ui · real-time WebSocket feed |
| **Infrastructure** | Railway · Vercel · Telegram Bot API |

---

## Project Origin

This project was built by a real class delegate at ENSET. For years, the routine was the same every week: collect student complaints manually, figure out who to forward them to, write individual messages to teachers, broadcast announcements to the Telegram group, create project groups on request, manage the trombinoscope at the start of the year.

Every one of those tasks is now automated by Wasit.

The name واسط — Wasit — means *the intermediary* in Arabic. It is not decoration. It is the exact function this system performs, named in the language of the students it was built for.

---

## Official Submission Description

> Wasit — واسط is a multi-agent AI platform that acts as the intelligent intermediary between university students and their institution. Every class is assigned an autonomous AI delegate that collects student problems, aggregates them, and routes each one to the right person — teacher, administrator, listening service, or emergency contact — with a structured summary already prepared. Students submit any problem in any language through a single interface and receive updates through their existing Telegram group. The platform mirrors the real institutional hierarchy: AI delegates at class level, supervisor dashboards at filière level, and a real-time analytics panel for school administration. Additional features include automated trombinoscope management, project group generation, and cross-class pattern detection that surfaces institutional problems before they escalate. Built on a LangGraph multi-agent pipeline with a Next.js dashboard and Telegram Bot integration, Wasit transforms the fragmented, manual communication system of a university into a living, intelligent institutional nervous system — deployable at any university on earth.

---

*Wasit — واسط · ENSET Challenge · Agentic AI · Education · Real-world impact*
