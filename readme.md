# Financial Planning Agent

A fully autonomous multi-agent financial planning system built with
Python + FastAPI + React. Rule-based in Phase 1 — GPT-powered,
scheduled, notifying, and deployed in Phase 5.

---

## Project Status

| Phase | Status | What it does |
|-------|--------|--------------|
| Phase 1 — Single Agent | ✅ Complete | State machine, rules engine, savings plan |
| Phase 2 — Two Agents + GPT | ✅ Complete | GPT reasoning, SQLite, execution agent |
| Phase 3 — Scheduler Agent | ✅ Complete | Autonomous timer, multi-user, job tracking |
| Phase 4 — Notifications | ✅ Complete | Gmail alerts — overspend + monthly summary |
| Phase 5 — UI + Deployment | ✅ Complete | React dashboard, PostgreSQL, Railway deploy |

---

## How it works in plain words

On the 1st of every month at 8am, Agent 3 wakes up automatically.
Nobody triggers it. It loads every stored user profile from PostgreSQL,
then for each user runs Agent 1 and Agent 2 in sequence.

**Agent 1** reads the salary profile, checks every expense category
against the 50/30/20 rule, calls GPT with current and past context
to write natural recommendations, scores the plan 0–100, and saves
it to the database.

**Agent 2** picks up the plan, asks GPT which actions to take, creates
budget alerts for overspent categories, schedules a 30-day review,
and sends two emails — an overspend alert and a full monthly report
with trend, breakdown, GPT recommendations, and actions taken.

**Agent 3** tracks success and failure per user, logs the entire run,
and goes back to sleep. If one user's run fails, the others still complete.

You can also trigger any of this manually via the React UI or API.

---

## Folder Structure

```
financial-agent/
├── phase1/                        ← rule-based single agent (reference)
│   ├── agent/
│   │   ├── core.py
│   │   ├── memory.py
│   │   ├── models.py
│   │   └── rules.py
│   └── main.py
│
├── phase2/                        ← production system
│   ├── agent/                     ← Agent 1 — planner
│   │   ├── core.py                ← state machine + decision loop
│   │   ├── database.py            ← PostgreSQL layer
│   │   ├── llm.py                 ← GPT recommendations
│   │   ├── models.py              ← data shapes
│   │   └── rules.py               ← maths engine
│   ├── agent2/                    ← Agent 2 — executor
│   │   ├── core.py                ← state machine
│   │   ├── actions.py             ← budget alerts, reviews, summaries
│   │   └── notifier.py            ← Gmail notifications
│   ├── agent3/                    ← Agent 3 — scheduler
│   │   └── core.py                ← orchestrator state machine
│   ├── frontend/                  ← React dashboard
│   │   ├── src/
│   │   │   ├── App.jsx            ← sidebar + routing
│   │   │   ├── api.js             ← all API calls
│   │   │   └── pages/
│   │   │       ├── Dashboard.jsx
│   │   │       ├── ControlPanel.jsx
│   │   │       ├── Profiles.jsx
│   │   │       ├── RunHistory.jsx
│   │   │       └── AgentLogs.jsx
│   │   └── dist/                  ← React build (served by FastAPI)
│   ├── .env                       ← credentials (never commit)
│   ├── runtime.txt                ← Python 3.12 for Railway
│   └── main.py                    ← FastAPI + APScheduler
│
└── README.md
```

---

## Setup (local)

```bash
cd phase2
python3.12 -m venv venv
source venv/bin/activate
python3.12 -m pip install -r requirements.txt

# build React
cd frontend
npm install
npm run build
cd ..

# start server (serves both API and React UI)
uvicorn main:app --reload
```

Open `http://127.0.0.1:8000`

Create `phase2/.env`:
```
OPENAI_API_KEY=sk-...
GMAIL_ADDRESS=your_gmail@gmail.com
GMAIL_APP_PASSWORD=your16charpassword
DATABASE_URL=postgresql://localhost/financial_agent
```

---

## Three Agents

### Agent 1 — FinancialAgent (planner)
```
IDLE → READING → ANALYZING → PLANNING → REPORTING → IDLE
```

| State | Job |
|-------|-----|
| READING | Validate and ingest salary + expense data |
| ANALYZING | Apply 50/30/20 rule, flag overspends per category |
| PLANNING | Call GPT with current data + past context + trend |
| REPORTING | Save plan to PostgreSQL |

### Agent 2 — ExecutionAgent (executor)
```
IDLE → RECEIVING → DECIDING → EXECUTING → REPORTING → IDLE
```

| State | Job |
|-------|-----|
| RECEIVING | Load plan from PostgreSQL |
| DECIDING | Ask GPT which actions to take |
| EXECUTING | Create budget alerts, schedule 30-day review |
| REPORTING | GPT summary, send emails, mark plan executed |

### Agent 3 — SchedulerAgent (orchestrator)
```
IDLE → WAKING → LOADING → DISPATCHING → REPORTING → IDLE
```

| State | Job |
|-------|-----|
| WAKING | Check all agents are idle |
| LOADING | Fetch all profiles from PostgreSQL |
| DISPATCHING | Loop users — run Agent 1 + 2 per user |
| REPORTING | Log results, return run summary |

---

## React UI (Phase 5)

Five pages, all connected to live FastAPI data.

| Page | What it shows |
|------|--------------|
| Dashboard | Score cards, trend chart, recent plans, trend alert |
| Control panel | Agent states, trigger run manually, run results |
| Profiles | View, add, edit users — Analyze now button with live log |
| Run history | All scheduler runs, per-user job detail |
| Agent logs | Agent 1 decision log with level filter |

Sidebar shows real-time backend status — green when online, red when offline.
Agent dots update every 10 seconds, every 1 second when any agent is active.

---

## Notifications (Phase 4)

Two emails sent per user per scheduler run via Gmail SMTP.

**Email 1 — Overspend Alert** (only when categories exceed limit)
```
Subject: ⚠️ Budget Alert — Madhuri | 2 categories overspent
• Housing: spent ₹25,000 vs limit ₹24,000 (over by ₹1,000)
• Entertainment: spent ₹8,000 vs limit ₹6,400 (over by ₹1,600)
```

**Email 2 — Monthly Summary** (always sent)
```
Subject: 📊 Monthly Report — Madhuri | Score 80/100 — Excellent

Score, savings, trend vs last month, full expense breakdown,
GPT recommendations, actions taken by the agent.
```

---

## PostgreSQL Tables

| Table | What it stores |
|-------|---------------|
| `profiles` | Name, salary, expenses, email per user |
| `plans` | Every plan — score, savings, status |
| `actions` | Every action Agent 2 created |
| `scheduler_jobs` | Per-user job result for every scheduler run |

---

## API Endpoints

All routes prefixed with `/api`.

### Profiles
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/profile` | Save user profile |
| GET | `/api/profile/{name}` | Load profile |

### Analysis
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/analyze/{name}` | Run Agent 1 + 2 for one user |
| POST | `/api/analyze` | Run with full JSON body |
| GET | `/api/history` | All users history |
| GET | `/api/history/{name}` | Single user history + trend |
| GET | `/api/actions/{plan_id}` | Actions Agent 2 created |

### Scheduler
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/scheduler/run` | Trigger all agents manually |
| GET | `/api/scheduler/status` | Current state + next scheduled run |
| GET | `/api/scheduler/runs` | All runs with success/fail counts |
| GET | `/api/scheduler/runs/{run_id}` | Per-user job detail |

### Logs
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/logs` | Agent 1 decision log |
| GET | `/api/logs/agent2` | Agent 2 decision log |
| GET | `/api/logs/agent3` | Agent 3 decision log |
| GET | `/api/status` | All agents status + next run time |

---

## Deployment (Railway)

```
Backend:   FastAPI + APScheduler (serves React build too)
Database:  Railway managed PostgreSQL
Scheduler: APScheduler runs inside FastAPI process — stays alive 24/7
```

### Environment variables on Railway
```
OPENAI_API_KEY       sk-...
GMAIL_ADDRESS        your_gmail@gmail.com
GMAIL_APP_PASSWORD   your16charpassword
DATABASE_URL         (auto-set by Railway PostgreSQL addon)
```

### Start command
```
uvicorn main:app --host 0.0.0.0 --port $PORT
```

### Root directory
```
phase 2
```

---

## Scheduler

Runs automatically on the 1st of every month at 8:00am.

```python
scheduler.add_job(
    scheduled_run,
    trigger=CronTrigger(day=1, hour=8, minute=0),
    id="monthly_run",
)
```

Trigger manually from UI → Control panel → Run all users now
Or via API: `POST /api/scheduler/run`

---

## Bugs Found and Fixed

| Phase | Bug | Fix |
|-------|-----|-----|
| 1 | `plan_score: -52` on bankrupt input | `max(0, min(score, 100))` |
| 1 | `"saving ₹-13,000/month"` wording | Separate branch for negative savings |
| 2 | GPT returning markdown fences in JSON | Strip ` ```json ` before parsing |
| 2 | `agent3/core.py` methods missing | File not saved completely — re-added |
| 3 | `scheduler_jobs` table missing | Database existed — `ALTER TABLE` |
| 4 | Email field not in PostgreSQL profiles | Added column + updated save/get |
| 4 | Gmail port 465 SSL rejected | Switched to port 587 with STARTTLS |
| 5 | React showing offline when backend up | `/` route was JSON — moved to `/api/status` |
| 5 | Button text invisible | Missing `color: '#333'` on buttons |
| Deploy | pydantic fails on Python 3.13 | `runtime.txt` pins Python 3.12 |

---

## Key Concepts Learned

**Agent vs program** — an agent has a loop and a goal. Drives itself
through states without being told what to do at each step.

**State machine** — one state at a time, one job per state,
transitions decided by the agent.

**Three memory types:**
- Working → RAM, current run only
- Episodic → PostgreSQL history, survives restarts
- Semantic → rules that never change

**Orchestrator pattern** — Agent 3 coordinates without doing domain
work. It only decides who runs and when.

**Error isolation** — each user wrapped in try/except. One failure
never stops the batch.

**GPT placement** — rules.py does maths (deterministic), GPT handles
language (flexible). Never mix the two.

**Autonomy levels:**
- Phase 1 — human triggers every run
- Phase 2 — human triggers, agents execute
- Phase 3 — agents trigger themselves on a schedule
- Phase 4 — agents notify users with no human involvement
- Phase 5 — UI + deployed, accessible from anywhere

---

## Phase 6 — Ideas

- Add more users and test multi-user batch runs
- Slack notifications alongside email
- Agent 4 — watches trends across all users, surfaces insights
- Weekly digest — lighter summary email every Sunday
- Mobile-responsive UI
- Authentication — login before accessing the dashboard