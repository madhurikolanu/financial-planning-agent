import time
from datetime import datetime
from agent.models import (
    AgentState, SalaryInput, SavingsPlan,
    ExpenseAnalysis, LogEntry
)


class FinancialAgent:
    """
    A single autonomous agent that reads salary data,
    analyzes it, and produces a savings plan.

    It moves through states on its own — no external code
    tells it when to transition. That's what makes it an agent.
    """

    def __init__(self):
        self._reset()

    def _reset(self):
        """Put the agent back to a clean IDLE state."""
        self.state       = AgentState.IDLE
        self.input_data  = None
        self.analysis    = None
        self.plan        = None
        self.context     = None
        self.logs: list[LogEntry] = []
        self.started_at  = None
        self.finished_at = None

    # ── Logging ────────────────────────────────────────────────
    def _log(self, message: str, level: str = "info"):
        """Record every decision the agent makes."""
        entry = LogEntry(state=self.state, message=message, level=level)
        self.logs.append(entry)
        print(f"[{self.state.value:<10}] [{level.upper()}] {message}")

    # ── State transition ────────────────────────────────────────
    def _transition(self, new_state: AgentState):
        """Move to the next state and log it."""
        self._log(f"transition → {new_state.value}")
        self.state = new_state

    # ── The decision loop ───────────────────────────────────────
    def run(self, input_data: SalaryInput, context: dict = None) -> SavingsPlan:
        """
        The main autonomous loop.
        Called once with input — the agent drives itself
        through every state until a plan is produced.
        """
        self._reset()
        self.context    = context
        self.started_at = datetime.now()
        self._log(f"agent waking up for '{input_data.name}'")

        # ── IDLE → READING ──────────────────────────────────────
        self._transition(AgentState.READING)
        salary_data = self._read(input_data)

        # ── READING → ANALYZING ─────────────────────────────────
        self._transition(AgentState.ANALYZING)
        analysis = self._analyze(salary_data)

        # ── ANALYZING → PLANNING ────────────────────────────────
        self._transition(AgentState.PLANNING)
        plan = self._plan(salary_data, analysis)

        # ── PLANNING → REPORTING ────────────────────────────────
        self._transition(AgentState.REPORTING)
        self._report(plan)

        # ── REPORTING → IDLE ────────────────────────────────────
        self.finished_at = datetime.now()
        duration_ms = (self.finished_at - self.started_at).total_seconds() * 1000
        self._log(f"done in {duration_ms:.1f}ms — returning to IDLE")
        self._transition(AgentState.IDLE)

        return plan

    # ── State handlers ──────────────────────────────────────────

    def _read(self, input_data: SalaryInput) -> SalaryInput:
        """
        READING: validate and ingest the salary data.
        In Phase 2 this could read from a file, DB, or API.
        """
        self._log(f"reading salary data for {input_data.name}")
        self._log(f"monthly salary: ₹{input_data.monthly_salary:,.0f}")

        total_expenses = sum(input_data.expenses.model_dump().values())
        self._log(f"total expenses declared: ₹{total_expenses:,.0f}")

        if total_expenses > input_data.monthly_salary:
            self._log(
                f"expenses (₹{total_expenses:,.0f}) exceed salary "
                f"(₹{input_data.monthly_salary:,.0f}) — flagging",
                level="warn"
            )

        self.input_data = input_data
        return input_data

    def _analyze(self, data: SalaryInput) -> dict:
        """
        ANALYZING: apply the 50/30/20 rule and check each
        expense category against recommended limits.

        50% → needs (housing, utilities, transport)
        30% → wants (food, entertainment, misc)
        20% → savings target
        """
        from agent.rules import analyze_expenses
        self._log("applying 50/30/20 rule to expense categories")
        analysis = analyze_expenses(data)
        self.analysis = analysis

        for item in analysis["breakdown"]:
            if item["status"] == "overspent":
                self._log(
                    f"{item['category']} overspent by "
                    f"₹{abs(item['difference']):,.0f}",
                    level="warn"
                )
            else:
                self._log(f"{item['category']} — {item['status']}")

        return analysis

    def _plan(self, data: SalaryInput, analysis: dict) -> SavingsPlan:
        from agent.rules import build_plan
        from agent.llm import generate_recommendations

        self._log("requesting GPT recommendations")

        # GPT generates recommendations using current data + past context
        recommendations = generate_recommendations(
            name           = data.name,
            monthly_salary = data.monthly_salary,
            analysis       = analysis,
            context        = self.context,   # ← past runs from SQLite
        )

        self._log(f"building savings plan with {len(recommendations)} recommendations")
        plan = build_plan(data, analysis, recommendations)
        self._log(f"plan score: {plan.plan_score}/100")
        self.plan = plan
        return plan

    def _report(self, plan: SavingsPlan):
        """
        REPORTING: summarise the plan. Later this will
        hand off to Agent 2 for execution.
        """
        self._log(f"plan ready — {len(plan.recommendations)} recommendations generated")
        self._log("ready to hand off to execution agent (Phase 2)")

    # ── Status (for the API to query) ───────────────────────────
    def get_status(self) -> dict:
        return {
            "state":       self.state.value,
            "log_entries": len(self.logs),
            "has_plan":    self.plan is not None,
        }