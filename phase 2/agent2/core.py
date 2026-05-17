import json
import os
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI

import agent.database as db
from agent2.actions import (
    create_budget_alert,
    schedule_review,
    track_savings_gap,
    record_summary,
)

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


class ExecutionAgent:
    """
    Agent 2 — receives a savings plan from Agent 1
    and executes concrete actions autonomously.

    State machine:
    IDLE → RECEIVING → DECIDING → EXECUTING → REPORTING → IDLE
    """

    def __init__(self):
        self._reset()

    def _reset(self):
        self.state      = "IDLE"
        self.plan_id    = None
        self.plan_data  = None
        self.actions    = []
        self.logs       = []
        self.started_at = None

    def _log(self, message: str, level: str = "info"):
        entry = {"state": self.state, "level": level, "message": message}
        self.logs.append(entry)
        print(f"[AGENT2   ] [{level.upper():<5}] [{self.state:<10}] {message}")

    def _transition(self, new_state: str):
        self._log(f"transition → {new_state}")
        self.state = new_state

    # ── Main loop ───────────────────────────────────────────
    def run(self, plan_id: int):
        """
        Called with a plan_id from SQLite.
        Agent 2 drives itself through all states autonomously.
        """
        self._reset()
        self.started_at = datetime.now()
        self._log(f"agent 2 waking up for plan_id={plan_id}")

        # IDLE → RECEIVING
        self._transition("RECEIVING")
        plan_data = self._receive(plan_id)
        if not plan_data:
            return

        # RECEIVING → DECIDING
        self._transition("DECIDING")
        actions = self._decide(plan_data)

        # DECIDING → EXECUTING
        self._transition("EXECUTING")
        self._execute(plan_id, plan_data, actions)

        # EXECUTING → REPORTING
        self._transition("REPORTING")
        self._report(plan_id, plan_data)

        # REPORTING → IDLE
        duration_ms = (datetime.now() - self.started_at).total_seconds() * 1000
        self._log(f"done in {duration_ms:.1f}ms — returning to IDLE")
        self._transition("IDLE")

    # ── State handlers ──────────────────────────────────────

    def _receive(self, plan_id: int) -> dict | None:
        """
        RECEIVING: load the plan from SQLite.
        This is the handoff point from Agent 1.
        """
        raw = db.get_plan(plan_id)
        if not raw:
            self._log(f"plan_id={plan_id} not found in database", level="error")
            self._transition("IDLE")
            return None

        plan_data = json.loads(raw["plan_data"])
        self.plan_data = plan_data
        self.plan_id   = plan_id

        self._log(f"received plan for '{plan_data['name']}' — score {raw['plan_score']}/100")
        self._log(f"savings: ₹{raw['current_savings']:,.0f} | expenses: ₹{raw['total_expenses']:,.0f}")
        return plan_data

    def _decide(self, plan_data: dict) -> list[str]:
        """
        DECIDING: ask GPT which actions to take based on the plan.
        GPT returns a prioritised list of action names.
        """
        breakdown   = plan_data["expense_breakdown"]
        overspent   = [i for i in breakdown if i["status"] == "overspent"]
        score       = plan_data["plan_score"]
        savings_gap = plan_data["savings_gap"]

        self._log(f"overspent categories: {len(overspent)} | score: {score} | gap: ₹{savings_gap:,.0f}")

        prompt = f"""
You are a financial execution agent. Given this plan summary, decide which actions to take.

Plan score: {score}/100
Current savings: ₹{plan_data['current_savings']:,.0f}
Savings gap: ₹{savings_gap:,.0f}
Overspent categories: {[i['category'] for i in overspent]}

Available actions:
- budget_alert: create an alert for each overspent category
- savings_tracker: create automation task if savings gap > 0
- schedule_review: always schedule a 30-day review

Return ONLY a JSON array of action names to execute, in priority order.
Example: ["budget_alert", "savings_tracker", "schedule_review"]
""".strip()

        try:
            response = client.chat.completions.create(
                model    = "gpt-4o",
                messages = [{"role": "user", "content": prompt}],
                temperature = 0.2,
                max_tokens  = 100,
            )
            raw     = response.choices[0].message.content.strip()
            # strip markdown fences if GPT wraps the response
            clean   = raw.replace("```json", "").replace("```", "").strip()
            actions = json.loads(clean)
            self._log(f"GPT decided actions: {actions}")
            return actions

        except Exception as e:
            self._log(f"GPT decision failed — using defaults: {e}", level="warn")
            return ["budget_alert", "schedule_review"]

    def _execute(self, plan_id: int, plan_data: dict, actions: list[str]):
        """
        EXECUTING: run each decided action one by one.
        Each action writes to the SQLite actions table.
        """
        breakdown = plan_data["expense_breakdown"]
        score     = plan_data["plan_score"]

        for action in actions:
            self._log(f"executing → {action}")

            if action == "budget_alert":
                for item in breakdown:
                    if item["status"] == "overspent":
                        create_budget_alert(
                            plan_id  = plan_id,
                            category = item["category"],
                            overspend = abs(item["difference"])
                        )

            elif action == "savings_tracker":
                gap = plan_data["savings_gap"]
                if gap > 0:
                    track_savings_gap(plan_id, gap)
                else:
                    self._log("savings gap negative — target met, skipping tracker")

            elif action == "schedule_review":
                schedule_review(plan_id, score)

        self._log(f"all actions executed — {len(actions)} action types processed")

    def _report(self, plan_id: int, plan_data: dict):
        from agent2.notifier import notify_overspend, notify_monthly_summary

        actions_taken = db.get_actions(plan_id)
        self._log(f"{len(actions_taken)} action records created in database")

        # get user email from profile
        profile = db.get_profile(plan_data["name"])
        email   = profile.get("email", "") if profile else ""

        # overspend alert
        overspent = [
            i for i in plan_data["expense_breakdown"]
            if i["status"] == "overspent"
        ]
        if overspent:
            self._log(f"sending overspend alert — {len(overspent)} categories")
            notify_overspend(
                name      = plan_data["name"],
                email     = email,
                overspent = overspent,
            )

        # monthly summary
        summary_action = next(
            (a for a in actions_taken if a["name"] == "plan_summary"), None
        )
        summary_text = summary_action["detail"] if summary_action else "Plan completed."

        self._log("sending monthly summary")
        notify_monthly_summary(
            name      = plan_data["name"],
            email     = email,
            score     = plan_data["plan_score"],
            savings   = plan_data["current_savings"],
            summary   = summary_text,
            plan_data = plan_data,
            trend     = db.get_trend(plan_data["name"]),
            actions   = actions_taken,
        )

        # GPT summary
        try:
            action_lines = "\n".join(
                f"- {a['name']}: {a['detail']}" for a in actions_taken
            )
            response = client.chat.completions.create(
                model    = "gpt-4o",
                messages = [{
                    "role":    "user",
                    "content": (
                        f"Summarise these financial actions in 2 sentences "
                        f"for {plan_data['name']}:\n{action_lines}"
                    )
                }],
                temperature = 0.3,
                max_tokens  = 120,
            )
            summary = response.choices[0].message.content.strip()
            record_summary(plan_id, summary)
            self._log("summary recorded")

        except Exception as e:
            self._log(f"summary GPT call failed: {e}", level="warn")

        db.mark_plan_executed(plan_id)
        self._log(f"plan_id={plan_id} marked as executed")

    def get_status(self) -> dict:
        return {
            "state":    self.state,
            "plan_id":  self.plan_id,
            "logs":     len(self.logs),
        }