from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


# ── Agent state ────────────────────────────────────────────
class AgentState(str, Enum):
    IDLE      = "IDLE"
    READING   = "READING"
    ANALYZING = "ANALYZING"
    PLANNING  = "PLANNING"
    REPORTING = "REPORTING"
    ERROR     = "ERROR"


# ── What the user sends in ──────────────────────────────────
class Expenses(BaseModel):
    housing:       float = Field(..., ge=0, description="Rent or mortgage")
    food:          float = Field(..., ge=0, description="Groceries + dining")
    transport:     float = Field(..., ge=0, description="Fuel, transit, cab")
    utilities:     float = Field(..., ge=0, description="Electric, water, internet")
    entertainment: float = Field(..., ge=0, description="Streaming, outings, hobbies")
    miscellaneous: float = Field(..., ge=0, description="Everything else")


class SalaryInput(BaseModel):
    name:            str
    monthly_salary:  float = Field(..., gt=0, description="Take-home pay after tax")
    expenses:        Expenses


# ── What the agent produces ─────────────────────────────────
class ExpenseAnalysis(BaseModel):
    category:        str
    actual:          float
    recommended:     float
    difference:      float       # negative = overspending
    status:          str         # "ok", "warning", "overspent"


class SavingsPlan(BaseModel):
    name:                   str
    monthly_salary:         float
    total_expenses:         float
    current_savings:        float
    recommended_savings:    float
    savings_gap:            float       # how far from the 20% target
    expense_breakdown:      list[ExpenseAnalysis]
    recommendations:        list[str]
    plan_score:             int         # 0–100, how healthy is this plan


# ── Agent's internal log entry ──────────────────────────────
class LogEntry(BaseModel):
    state:    AgentState
    message:  str
    level:    str = "info"   # "info", "warn", "error"

# ── User profile (stored in memory) ────────────────────────
class UserProfile(BaseModel):
    name:           str
    monthly_salary: float
    expenses:       Expenses
    created_at:     str = ""
    updated_at:     str = ""

# ── A single historical run ─────────────────────────────────
class RunRecord(BaseModel):
    timestamp:        str
    plan_score:       int
    current_savings:  float
    total_expenses:   float
    plan:             SavingsPlan