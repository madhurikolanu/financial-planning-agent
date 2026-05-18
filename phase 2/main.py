from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.routing import APIRouter
from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from agent.core import FinancialAgent
from agent2.core import ExecutionAgent
from agent3.core import SchedulerAgent
from agent.models import SalaryInput, SavingsPlan, UserProfile
import agent.database as db
import os

# ── Agent instances ──────────────────────────────────────────
agent  = FinancialAgent()
agent2 = ExecutionAgent()
agent3 = SchedulerAgent(planner=agent, executor=agent2)

# ── Scheduler ────────────────────────────────────────────────
scheduler = AsyncIOScheduler()

async def scheduled_run():
    print("[SCHEDULER] [INFO ] timer fired — starting monthly run")
    agent3.run()

@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    scheduler.add_job(
        scheduled_run,
        trigger=CronTrigger(day=1, hour=8, minute=0),
        id="monthly_run",
        replace_existing=True,
    )
    scheduler.start()
    print("[SCHEDULER] [INFO ] timer armed — runs on 1st of every month at 08:00")
    yield
    scheduler.shutdown()

app = FastAPI(
    title="Financial Planning Agent",
    description="Phase 2 — SQLite + GPT + Three Agents",
    version="3.0.0",
    lifespan=lifespan,
)

# ── API Router ───────────────────────────────────────────────
api = APIRouter(prefix="/api")

@api.get("/status")
def get_status():
    job      = scheduler.get_job("monthly_run")
    next_run = str(job.next_run_time) if job else "not scheduled"
    return {
        "status":   "online",
        "profiles": db.list_profiles(),
        "agents": {
            "agent1": agent.get_status(),
            "agent2": agent2.get_status(),
            "agent3": agent3.get_status(),
        },
        "next_scheduled_run": next_run,
    }

@api.post("/profile")
def save_profile(profile: UserProfile):
    db.save_profile(profile)
    return {"message": f"Profile saved for '{profile.name}'"}

@api.get("/profile/{name}")
def get_profile(name: str):
    profile = db.get_profile(name)
    if not profile:
        raise HTTPException(404, f"No profile found for '{name}'")
    return profile

@api.post("/analyze/{name}", response_model=SavingsPlan)
def analyze_by_name(name: str, background_tasks: BackgroundTasks):
    profile = db.get_profile(name)
    if not profile:
        raise HTTPException(404, f"No profile found for '{name}'.")
    if agent.state.value != "IDLE":
        raise HTTPException(409, f"Agent busy — state: {agent.state.value}")
    history  = db.get_history(name)
    last_run = history[-1] if history else None
    trend    = db.get_trend(name)
    context  = {"last_run": last_run, "trend": trend} if last_run or trend else None
    input_data = SalaryInput(
        name           = profile["name"],
        monthly_salary = profile["monthly_salary"],
        expenses       = profile["expenses"],
    )
    plan    = agent.run(input_data, context=context)
    plan_id = db.save_plan(plan)
    background_tasks.add_task(agent2.run, plan_id)
    return plan

@api.post("/analyze", response_model=SavingsPlan)
def analyze(input_data: SalaryInput):
    if agent.state.value != "IDLE":
        raise HTTPException(409, f"Agent busy — state: {agent.state.value}")
    plan    = agent.run(input_data)
    plan_id = db.save_plan(plan)
    return plan

@api.get("/history")
def get_all_history():
    profiles = db.list_profiles()
    result   = {}
    for name in profiles:
        history = db.get_history(name)
        if history:
            result[name] = {
                "total_runs": len(history),
                "trend":      db.get_trend(name),
                "runs": [
                    {
                        "id":              r["id"],
                        "plan_score":      r["plan_score"],
                        "current_savings": r["current_savings"],
                        "total_expenses":  r["total_expenses"],
                        "status":          r["status"],
                        "created_at":      r["created_at"],
                    }
                    for r in history
                ]
            }
    return result

@api.get("/history/{name}")
def get_history(name: str):
    history = db.get_history(name)
    if not history:
        raise HTTPException(404, f"No history for '{name}'")
    return {
        "name":       name,
        "total_runs": len(history),
        "trend":      db.get_trend(name),
        "runs": [
            {
                "id":              r["id"],
                "plan_score":      r["plan_score"],
                "current_savings": r["current_savings"],
                "total_expenses":  r["total_expenses"],
                "status":          r["status"],
                "created_at":      r["created_at"],
            }
            for r in history
        ],
    }

@api.get("/actions/{plan_id}")
def get_actions(plan_id: int):
    actions = db.get_actions(plan_id)
    if not actions:
        raise HTTPException(404, f"No actions for plan_id={plan_id}")
    return {"plan_id": plan_id, "total": len(actions), "actions": actions}

@api.post("/scheduler/run")
def run_scheduler():
    if agent3.state != "IDLE":
        raise HTTPException(409, f"Scheduler busy — state: {agent3.state}")
    result = agent3.run()
    return result

@api.get("/scheduler/status")
def scheduler_status():
    job      = scheduler.get_job("monthly_run")
    next_run = str(job.next_run_time) if job else "not scheduled"
    return {**agent3.get_status(), "next_scheduled_run": next_run}

@api.get("/scheduler/runs")
def get_scheduler_runs():
    return db.get_scheduler_runs()

@api.get("/scheduler/runs/{run_id}")
def get_run_detail(run_id: str):
    jobs = db.get_run_jobs(run_id)
    if not jobs:
        raise HTTPException(404, f"No jobs found for run_id '{run_id}'")
    return {"run_id": run_id, "jobs": jobs}

@api.get("/logs")
def get_logs():
    return {
        "total":   len(agent.logs),
        "entries": [
            {"state": e.state.value, "level": e.level, "message": e.message}
            for e in agent.logs
        ],
    }

@api.get("/logs/agent2")
def get_agent2_logs():
    return {"total": len(agent2.logs), "entries": agent2.logs}

@api.get("/logs/agent3")
def get_agent3_logs():
    return {"total": len(agent3.logs), "entries": agent3.logs}

@api.get("/plan", response_model=SavingsPlan)
def get_plan():
    if agent.plan is None:
        raise HTTPException(404, "No plan yet — call /analyze first")
    return agent.plan

app.include_router(api)

# ── Serve React frontend ─────────────────────────────────────
BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
frontend_dist = os.path.join(BASE_DIR, "frontend", "dist")
index_html    = os.path.join(frontend_dist, "index.html")

print(f"[FRONTEND ] BASE_DIR: {BASE_DIR}")
print(f"[FRONTEND ] dist path: {frontend_dist}")
print(f"[FRONTEND ] dist exists: {os.path.exists(frontend_dist)}")
print(f"[FRONTEND ] index exists: {os.path.exists(index_html)}")

assets_dir = os.path.join(frontend_dist, "assets")
if os.path.exists(assets_dir):
    app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")
    print(f"[FRONTEND ] assets mounted from {assets_dir}")

@app.get("/")
def serve_root():
    if os.path.exists(index_html):
        return FileResponse(index_html)
    return {"status": "api running", "frontend": "not found", "path": frontend_dist}

@app.get("/{full_path:path}")
def serve_frontend(full_path: str):
    if os.path.exists(index_html):
        return FileResponse(index_html)
    return {"status": "api running", "frontend": "not found", "path": frontend_dist}