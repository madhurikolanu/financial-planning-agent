# Financial Planning Agent

A four-phase autonomous financial planning system built with Python + FastAPI.
Rule-based in Phase 1 — GPT-powered, scheduled, and notifying in Phase 4.

---

## Project Status

| Phase | Status | What it does |
|-------|--------|--------------|
| Phase 1 — Single Agent | ✅ Complete | Reads salary data, applies rules, produces savings plan |
| Phase 2 — Two Agents + GPT | ✅ Complete | GPT reasoning, SQLite memory, execution agent |
| Phase 3 — Scheduler Agent | ✅ Complete | Autonomous timer, multi-user orchestration, job tracking |
| Phase 4 — Notifications | ✅ Complete | Email alerts for overspend + monthly summary via Gmail |

---

## How it works in plain words

On the 1st of every month at 8am, Agent 3 wakes up automatically.
Nobody triggers it. It loads every stored user profile from SQLite,
then for each user runs Agent 1 and Agent 2 in sequence.

Agent 1 reads the salary profile, checks every expense category
against the 50/30/20 rule, calls GPT with current and past context
to write natural recommendations, scores the plan 0–100, and saves
it to SQLite.

Agent 2 picks up the plan, asks GPT which actions to take, creates
budget alerts for overspent categories, schedules a 30-day review,
writes a plain English summary, and sends two emails — an overspend
alert and a full monthly report with trend, breakdown, recommendations,
and actions taken.

Agent 3 tracks success and failure per user, logs the entire run,
and goes back to sleep. If one user's run fails, the others still
complete.

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
├── phase2/                        ← production system (four phases)
│   ├── agent/                     ← Agent 1 — planner
│   │   ├── core.py                ← state machine + decision loop
│   │   ├── database.py            ← SQLite layer
│   │   ├── llm.py                 ← GPT recommendations
│   │   ├── models.py              ← data shapes
│   │   └── rules.py               ← maths engine
│   ├── agent2/                    ← Agent 2 — executor
│   │   ├── core.py                ← state machine
│   │   ├── actions.py             ← budget alerts, reviews, summaries
│   │   └── notifier.py            ← Gmail email notifications
│   ├── agent3/                    ← Agent 3 — scheduler
│   │   └── core.py                ← orchestrator state machine
│   ├── data/agent.db              ← SQLite database
│   ├── .env                       ← credentials (never commit)
│   └── main.py                    ← FastAPI + APScheduler
│
└── README.md
```

---

## Setup

```bash
cd phase2
python3.12 -m venv venv
source venv/bin/activate
python3.12 -m pip install -r requirements.txt
uvicorn main:app --reload
```

Create `phase2/.env`:
```
OPENAI_API_KEY=sk-...
GMAIL_ADDRESS=your_gmail@gmail.com
GMAIL_APP_PASSWORD=your16charpassword
```

API docs: `http://127.0.0.1:8000/docs`

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
| REPORTING | Save plan to SQLite |

### Agent 2 — ExecutionAgent (executor)
```
IDLE → RECEIVING → DECIDING → EXECUTING → REPORTING → IDLE
```

| State | Job |
|-------|-----|
| RECEIVING | Load plan from SQLite |
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
| LOADING | Fetch all profiles from SQLite |
| DISPATCHING | Loop users — run Agent 1 + 2 per user |
| REPORTING | Log results, return run summary |

---

## Notifications (Phase 4)

Two emails sent per user per run via Gmail SMTP.

### Email 1 — Overspend Alert
Fires only when one or more categories exceed their limit.

```
Subject: ⚠️ Budget Alert — Madhuri | 2 categories overspent

• Housing
  Spent ₹25,000 vs limit ₹24,000
  Over by ₹1,000 (4% above limit)

• Entertainment
  Spent ₹8,000 vs limit ₹6,400
  Over by ₹1,600 (25% above limit)
```

### Email 2 — Monthly Summary
Always sent, regardless of overspend status.

```
Subject: 📊 Monthly Report — Madhuri | Score 80/100 — Excellent

SCORE: 80/100 — Excellent
Savings this month: ₹20,000

TREND (vs last month)
Score:    80 → 80  → (stable)
Savings:  ₹0 unchanged
Expenses: ₹0 unchanged

EXPENSE BREAKDOWN
Housing       ₹25,000 / ₹24,000  ⚠ over by ₹1,000
Food          ₹12,000 / ₹12,000  ⚠ at limit
Transport      ₹6,000 /  ₹8,000  ✓ ok
...

GPT RECOMMENDATIONS
1. Reduce housing by ₹1,000 to meet the ₹24,000 limit.
2. Cut entertainment by ₹1,600...
...

ACTIONS TAKEN BY YOUR AGENT
• Budget alert: housing overspent ₹1,000
• Budget alert: entertainment overspent ₹1,600
• 30-day review scheduled for 2026-06-16
```

---

## How agents communicate

```
Agent 3 (timer fires automatically)
    ↓ loads all profiles from SQLite
    ↓ for each user:
Agent 1 → writes plan to SQLite (status: pending)
Agent 2 → reads plan, executes actions, sends emails
         → marks plan executed in SQLite
Agent 3 → logs job result to scheduler_jobs table
```

No agent calls another directly. SQLite is the communication channel.

---

## SQLite Tables

| Table | What it stores |
|-------|---------------|
| `profiles` | Name, salary, expenses, email per user |
| `plans` | Every plan — score, savings, status |
| `actions` | Every action Agent 2 created |
| `scheduler_jobs` | Per-user job result for every scheduler run |

---

## API Endpoints

### Profiles
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/profile` | Save user profile (include email field) |
| GET | `/profile/{name}` | Load profile |

### Analysis
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/analyze/{name}` | Run Agent 1 + 2 for one user |
| POST | `/analyze` | Run with full JSON body |
| GET | `/history/{name}` | Past runs + trend |
| GET | `/actions/{plan_id}` | Actions Agent 2 created |

### Scheduler
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/scheduler/run` | Trigger all agents manually |
| GET | `/scheduler/status` | Current state + next scheduled run |
| GET | `/scheduler/runs` | All runs with success/fail counts |
| GET | `/scheduler/runs/{run_id}` | Per-user job detail for one run |

### System
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | All agents status + next scheduled run |
| GET | `/logs` | Agent 1 decision log |
| GET | `/status` | Agent 1 state |
| GET | `/agent2/status` | Agent 2 state |
| GET | `/scheduler/status` | Agent 3 state |

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

Trigger manually:
```bash
POST /scheduler/run
```

### Job tracking
Every user in a scheduler run gets a job record:
- `status: success` — plan created, actions executed, emails sent
- `status: failed` — error logged, other users unaffected
- `plan_id` — links to the plan Agent 1 produced
- `started_at / finished_at` — timing per user

---

## Bugs Found and Fixed

| Phase | Bug | Fix |
|-------|-----|-----|
| 1 | `plan_score: -52` on bankrupt input | `max(0, min(score, 100))` |
| 1 | `"saving ₹-13,000/month"` wording | Separate branch for negative savings |
| 2 | GPT returning markdown fences in JSON | Strip ` ```json ` before parsing |
| 2 | `agent3/core.py` methods missing | File not saved completely — re-added |
| 3 | `scheduler_jobs` table not created | Database existed before table was added — `ALTER TABLE` |
| 4 | Email field not in SQLite profiles | `ALTER TABLE profiles ADD COLUMN email` |
| 4 | Gmail port 465 SSL rejected | Switched to port 587 with STARTTLS |

---

## Key Concepts Learned

**Agent vs program** — an agent has a loop and a goal. It drives
itself through states without being told what to do at each step.

**State machine** — one state at a time, one job per state,
transitions decided by the agent.

**Orchestrator pattern** — Agent 3 coordinates without doing
domain work. It only decides who runs and when.

**Error isolation** — each user wrapped in try/except inside
the dispatch loop. One failure never stops the batch.

**Communication via shared storage** — agents never call each
other directly. SQLite is the message channel.

**GPT placement** — rules.py does maths (deterministic),
GPT handles language (flexible). Never mix the two.

**Notifications are fire-and-forget** — email failure is logged
but never crashes the agent. Plan is always saved first.

**Autonomy levels:**
- Phase 1 — human triggers every run
- Phase 2 — human triggers, agents execute
- Phase 3 — agents trigger themselves on a schedule
- Phase 4 — agents notify users with no human involvement

---

## Phase 5 — Ideas

- Frontend dashboard: plans, scores, trends over time
- PostgreSQL: swap SQLite when scaling to real users
- More users: add 10 profiles and watch Agent 3 process all
- Slack notifications alongside email
- Agent 4: watches trends across all users, surfaces insights
- Weekly digest: lighter summary email every Sunday
