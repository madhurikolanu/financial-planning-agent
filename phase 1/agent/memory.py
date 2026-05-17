import json
import os
from datetime import datetime
from agent.models import UserProfile, SavingsPlan, RunRecord


MEMORY_FILE = "data/memory.json"


class AgentMemory:
    """
    Persistent memory for the agent system.

    Stores:
      - User profiles    → no need to re-send salary data
      - Run history      → agent can compare across time
    """

    def __init__(self):
        os.makedirs("data", exist_ok=True)
        if not os.path.exists(MEMORY_FILE):
            self._write({"profiles": {}, "history": {}})
            print("[MEMORY   ] [INFO] memory initialised — new memory.json created")
        else:
            data = self._read()
            profiles = len(data.get("profiles", {}))
            print(f"[MEMORY   ] [INFO] memory loaded — {profiles} profile(s) found")

    # ── Internal read/write ─────────────────────────────────
    def _read(self) -> dict:
        with open(MEMORY_FILE, "r") as f:
            return json.load(f)

    def _write(self, data: dict):
        with open(MEMORY_FILE, "w") as f:
            json.dump(data, f, indent=2, default=str)

    # ── Profile operations ──────────────────────────────────
    def save_profile(self, profile: UserProfile):
        """Save or update a user profile."""
        data = self._read()
        now  = datetime.now().isoformat()

        if profile.name not in data["profiles"]:
            profile.created_at = now
            print(f"[MEMORY   ] [INFO] new profile created for '{profile.name}'")
        else:
            existing           = data["profiles"][profile.name]
            profile.created_at = existing.get("created_at", now)
            print(f"[MEMORY   ] [INFO] profile updated for '{profile.name}'")

        profile.updated_at              = now
        data["profiles"][profile.name]  = profile.model_dump()
        self._write(data)

    def get_profile(self, name: str) -> UserProfile | None:
        """Load a stored profile by name."""
        data = self._read()
        raw  = data["profiles"].get(name)
        if raw is None:
            return None
        return UserProfile(**raw)

    def list_profiles(self) -> list[str]:
        """Return all stored profile names."""
        data = self._read()
        return list(data["profiles"].keys())

    # ── History operations ──────────────────────────────────
    def save_run(self, name: str, plan: SavingsPlan):
        """Append a completed plan to the user's run history."""
        data   = self._read()
        record = RunRecord(
            timestamp       = datetime.now().isoformat(),
            plan_score      = plan.plan_score,
            current_savings = plan.current_savings,
            total_expenses  = plan.total_expenses,
            plan            = plan,
        )
        if name not in data["history"]:
            data["history"][name] = []

        data["history"][name].append(record.model_dump())
        self._write(data)
        print(f"[MEMORY   ] [INFO] run saved for '{name}' — "
              f"score {plan.plan_score}, "
              f"{len(data['history'][name])} total run(s)")

    def get_history(self, name: str) -> list[RunRecord]:
        """Return all past runs for a user."""
        data = self._read()
        raw  = data["history"].get(name, [])
        return [RunRecord(**r) for r in raw]

    def get_last_run(self, name: str) -> RunRecord | None:
        """Return only the most recent run."""
        history = self.get_history(name)
        return history[-1] if history else None

    def get_trend(self, name: str) -> dict | None:
        """
        Compare the last two runs.
        Returns score and savings direction so the agent
        can include trend context in recommendations.
        """
        history = self.get_history(name)
        if len(history) < 2:
            return None

        prev    = history[-2]
        current = history[-1]

        score_delta   = current.plan_score      - prev.plan_score
        savings_delta = current.current_savings - prev.current_savings
        expense_delta = current.total_expenses  - prev.total_expenses

        return {
            "score_delta":    score_delta,
            "savings_delta":  savings_delta,
            "expense_delta":  expense_delta,
            "direction":      "improving" if score_delta > 0 else
                              "declining" if score_delta < 0 else "stable",
        }