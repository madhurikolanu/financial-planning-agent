from fastapi import FastAPI, HTTPException
from agent.core import FinancialAgent
from agent.memory import AgentMemory
from agent.models import SalaryInput, SavingsPlan, UserProfile


app   = FastAPI(
    title="Financial Planning Agent",
    description="Phase 1 — single agent with persistent memory",
    version="2.0.0",
)

agent  = FinancialAgent()
memory = AgentMemory()


# ── Health check ────────────────────────────────────────────
@app.get("/")
def root():
    return {
        "status":   "online",
        "agent":    agent.get_status(),
        "profiles": memory.list_profiles(),
    }


# ── Save a user profile ─────────────────────────────────────
@app.post("/profile")
def save_profile(profile: UserProfile):
    """
    Save salary + expense data once.
    After this, just call /analyze/{name} — no body needed.
    """
    memory.save_profile(profile)
    return {"message": f"Profile saved for '{profile.name}'"}


# ── Load a profile ──────────────────────────────────────────
@app.get("/profile/{name}")
def get_profile(name: str):
    profile = memory.get_profile(name)
    if not profile:
        raise HTTPException(404, f"No profile found for '{name}'")
    return profile


# ── Analyze using stored profile — no body needed ──────────
@app.post("/analyze/{name}", response_model=SavingsPlan)
def analyze_by_name(name: str):
    """
    Agent loads the stored profile and runs autonomously.
    No request body required.
    """
    profile = memory.get_profile(name)
    if not profile:
        raise HTTPException(404, f"No profile found for '{name}'. "
                                 f"Call POST /profile first.")
    if agent.state.value != "IDLE":
        raise HTTPException(409, f"Agent busy — state: {agent.state.value}")

    input_data = SalaryInput(
        name           = profile.name,
        monthly_salary = profile.monthly_salary,
        expenses       = profile.expenses,
    )
    plan = agent.run(input_data)
    memory.save_run(name, plan)
    return plan


# ── Original endpoint still works ──────────────────────────
@app.post("/analyze", response_model=SavingsPlan)
def analyze(input_data: SalaryInput):
    if agent.state.value != "IDLE":
        raise HTTPException(409, f"Agent busy — state: {agent.state.value}")
    plan = agent.run(input_data)
    memory.save_run(input_data.name, plan)
    return plan


# ── Run history + trend ─────────────────────────────────────
@app.get("/history/{name}")
def get_history(name: str):
    """
    Returns all past runs and a trend comparison
    between the last two runs.
    """
    history = memory.get_history(name)
    if not history:
        raise HTTPException(404, f"No history for '{name}'")

    trend = memory.get_trend(name)

    return {
        "name":       name,
        "total_runs": len(history),
        "trend":      trend,
        "runs": [
            {
                "timestamp":       r.timestamp,
                "plan_score":      r.plan_score,
                "current_savings": r.current_savings,
                "total_expenses":  r.total_expenses,
            }
            for r in history
        ],
    }


# ── Logs, plan, status (unchanged) ─────────────────────────
@app.get("/logs")
def get_logs():
    return {
        "total":   len(agent.logs),
        "entries": [
            {"state": e.state.value, "level": e.level, "message": e.message}
            for e in agent.logs
        ],
    }

@app.get("/plan", response_model=SavingsPlan)
def get_plan():
    if agent.plan is None:
        raise HTTPException(404, "No plan yet — call /analyze first")
    return agent.plan

@app.get("/status")
def get_status():
    return agent.get_status()