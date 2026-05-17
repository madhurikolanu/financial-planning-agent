import os
import json
import psycopg2
import psycopg2.extras
from datetime import datetime
from dotenv import load_dotenv
from agent.models import UserProfile, SavingsPlan

load_dotenv()

_URL = os.getenv("DATABASE_URL", "postgresql://localhost/financial_agent")

# Railway provides postgres:// — psycopg2 needs postgresql://
DATABASE_URL = _URL.replace("postgres://", "postgresql://", 1) if _URL.startswith("postgres://") else _URL


def get_connection():
    conn = psycopg2.connect(DATABASE_URL)
    return conn


def init_db():
    conn   = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS profiles (
            name            TEXT PRIMARY KEY,
            monthly_salary  REAL NOT NULL,
            expenses        TEXT NOT NULL,
            email           TEXT DEFAULT '',
            created_at      TEXT NOT NULL,
            updated_at      TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS plans (
            id                  SERIAL PRIMARY KEY,
            name                TEXT NOT NULL,
            plan_score          INTEGER NOT NULL,
            current_savings     REAL NOT NULL,
            recommended_savings REAL NOT NULL,
            total_expenses      REAL NOT NULL,
            savings_gap         REAL NOT NULL,
            plan_data           TEXT NOT NULL,
            created_at          TEXT NOT NULL,
            status              TEXT DEFAULT 'pending'
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS actions (
            id          SERIAL PRIMARY KEY,
            plan_id     INTEGER NOT NULL,
            name        TEXT NOT NULL,
            category    TEXT,
            detail      TEXT,
            status      TEXT DEFAULT 'pending',
            created_at  TEXT NOT NULL,
            executed_at TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scheduler_jobs (
            id          SERIAL PRIMARY KEY,
            run_id      TEXT NOT NULL,
            name        TEXT NOT NULL,
            status      TEXT DEFAULT 'pending',
            plan_id     INTEGER,
            error       TEXT,
            started_at  TEXT,
            finished_at TEXT
        )
    """)

    conn.commit()
    conn.close()
    print("[DATABASE ] [INFO] PostgreSQL tables ready")


# ── Profiles ─────────────────────────────────────────────────
def save_profile(profile: UserProfile):
    conn = get_connection()
    now  = datetime.now().isoformat()

    existing   = get_profile(profile.name)
    created_at = existing["created_at"] if existing else now

    conn.cursor().execute("""
        INSERT INTO profiles (name, monthly_salary, expenses, email, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (name) DO UPDATE SET
            monthly_salary = EXCLUDED.monthly_salary,
            expenses       = EXCLUDED.expenses,
            email          = EXCLUDED.email,
            updated_at     = EXCLUDED.updated_at
    """, (
        profile.name,
        profile.monthly_salary,
        json.dumps(profile.expenses.model_dump()),
        profile.email,
        created_at,
        now
    ))
    conn.commit()
    conn.close()
    print(f"[DATABASE ] [INFO] profile saved — '{profile.name}'")


def get_profile(name: str) -> dict | None:
    conn   = get_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute("SELECT * FROM profiles WHERE name = %s", (name,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    return {
        "name":           row["name"],
        "monthly_salary": row["monthly_salary"],
        "expenses":       json.loads(row["expenses"]),
        "email":          row["email"] or "",
        "created_at":     row["created_at"],
        "updated_at":     row["updated_at"],
    }


def list_profiles() -> list[str]:
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM profiles")
    rows = cursor.fetchall()
    conn.close()
    return [r[0] for r in rows]


# ── Plans ─────────────────────────────────────────────────────
def save_plan(plan: SavingsPlan) -> int:
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO plans
            (name, plan_score, current_savings, recommended_savings,
             total_expenses, savings_gap, plan_data, created_at, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'pending')
        RETURNING id
    """, (
        plan.name,
        plan.plan_score,
        plan.current_savings,
        plan.recommended_savings,
        plan.total_expenses,
        plan.savings_gap,
        json.dumps(plan.model_dump()),
        datetime.now().isoformat(),
    ))
    plan_id = cursor.fetchone()[0]
    conn.commit()
    conn.close()
    print(f"[DATABASE ] [INFO] plan saved — id={plan_id}, score={plan.plan_score}")
    return plan_id


def get_plan(plan_id: int) -> dict | None:
    conn   = get_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute("SELECT * FROM plans WHERE id = %s", (plan_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_pending_plans() -> list[dict]:
    conn   = get_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute("SELECT * FROM plans WHERE status = 'pending' ORDER BY created_at")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def mark_plan_executed(plan_id: int):
    conn = get_connection()
    conn.cursor().execute(
        "UPDATE plans SET status = 'executed' WHERE id = %s", (plan_id,)
    )
    conn.commit()
    conn.close()


# ── History + trend ───────────────────────────────────────────
def get_history(name: str) -> list[dict]:
    conn   = get_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute(
        "SELECT * FROM plans WHERE name = %s ORDER BY created_at", (name,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_trend(name: str) -> dict | None:
    history = get_history(name)
    if len(history) < 2:
        return None

    prev    = history[-2]
    current = history[-1]

    score_delta   = current["plan_score"]      - prev["plan_score"]
    savings_delta = current["current_savings"] - prev["current_savings"]
    expense_delta = current["total_expenses"]  - prev["total_expenses"]

    return {
        "previous_score":  prev["plan_score"],
        "current_score":   current["plan_score"],
        "score_delta":     score_delta,
        "savings_delta":   savings_delta,
        "expense_delta":   expense_delta,
        "direction":       "improving" if score_delta > 0
                           else "declining" if score_delta < 0
                           else "stable",
    }


# ── Actions ───────────────────────────────────────────────────
def save_action(plan_id: int, name: str, category: str, detail: str):
    conn = get_connection()
    conn.cursor().execute("""
        INSERT INTO actions (plan_id, name, category, detail, status, created_at)
        VALUES (%s, %s, %s, %s, 'pending', %s)
    """, (plan_id, name, category, detail, datetime.now().isoformat()))
    conn.commit()
    conn.close()


def get_actions(plan_id: int) -> list[dict]:
    conn   = get_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute("SELECT * FROM actions WHERE plan_id = %s", (plan_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def mark_action_done(action_id: int):
    conn = get_connection()
    conn.cursor().execute("""
        UPDATE actions SET status = 'done', executed_at = %s WHERE id = %s
    """, (datetime.now().isoformat(), action_id))
    conn.commit()
    conn.close()


# ── Scheduler jobs ────────────────────────────────────────────
def create_job(run_id: str, name: str) -> int:
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO scheduler_jobs (run_id, name, status, started_at)
        VALUES (%s, %s, 'pending', %s)
        RETURNING id
    """, (run_id, name, datetime.now().isoformat()))
    job_id = cursor.fetchone()[0]
    conn.commit()
    conn.close()
    return job_id


def complete_job(job_id: int, plan_id: int):
    conn = get_connection()
    conn.cursor().execute("""
        UPDATE scheduler_jobs
        SET status = 'success', plan_id = %s, finished_at = %s
        WHERE id = %s
    """, (plan_id, datetime.now().isoformat(), job_id))
    conn.commit()
    conn.close()


def fail_job(job_id: int, error: str):
    conn = get_connection()
    conn.cursor().execute("""
        UPDATE scheduler_jobs
        SET status = 'failed', error = %s, finished_at = %s
        WHERE id = %s
    """, (error, datetime.now().isoformat(), job_id))
    conn.commit()
    conn.close()


def get_scheduler_runs() -> list[dict]:
    conn   = get_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute("""
        SELECT
            run_id,
            COUNT(*)                                              AS total,
            SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END)  AS success,
            SUM(CASE WHEN status = 'failed'  THEN 1 ELSE 0 END)  AS failed,
            MIN(started_at)                                       AS started_at,
            MAX(finished_at)                                      AS finished_at
        FROM scheduler_jobs
        GROUP BY run_id
        ORDER BY started_at DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_run_jobs(run_id: str) -> list[dict]:
    conn   = get_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute(
        "SELECT * FROM scheduler_jobs WHERE run_id = %s ORDER BY started_at",
        (run_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]