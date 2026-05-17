import uuid
from datetime import datetime
from agent.models import SalaryInput
import agent.database as db


class SchedulerAgent:
    """
    Agent 3 — orchestrator.

    Wakes up on a schedule, loads all user profiles,
    and runs Agent 1 + Agent 2 for each user autonomously.

    State machine:
    IDLE → WAKING → LOADING → DISPATCHING → REPORTING → IDLE
    """

    def __init__(self, planner, executor):
        """
        Receives Agent 1 and Agent 2 as dependencies.
        Agent 3 does not plan or execute — it only coordinates.
        """
        self.planner  = planner    # FinancialAgent instance
        self.executor = executor   # ExecutionAgent instance
        self._reset()

    def _reset(self):
        self.state      = "IDLE"
        self.run_id     = None
        self.profiles   = []
        self.results    = []
        self.logs       = []
        self.started_at = None

    def _log(self, message: str, level: str = "info"):
        entry = {
            "state":   self.state,
            "level":   level,
            "message": message
        }
        self.logs.append(entry)
        print(f"[AGENT3   ] [{level.upper():<5}] [{self.state:<11}] {message}")

    def _transition(self, new_state: str):
        self._log(f"transition → {new_state}")
        self.state = new_state

    def get_status(self) -> dict:
        return {
            "state":    self.state,
            "run_id":   self.run_id,
            "profiles": len(self.profiles),
        }
    
    def run(self) -> dict:
        self._reset()
        self.started_at = datetime.now()
        self.run_id     = f"run_{self.started_at.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        self._log(f"scheduler waking up — run_id: {self.run_id}")

        self._transition("WAKING")
        self._wake()

        self._transition("LOADING")
        profiles = self._load()

        if not profiles:
            self._log("no profiles found — nothing to run", level="warn")
            self._transition("IDLE")
            return self._summary()

        self._transition("DISPATCHING")
        self._dispatch(profiles)

        self._transition("REPORTING")
        self._report()

        duration = (datetime.now() - self.started_at).total_seconds()
        self._log(f"done in {duration:.1f}s — returning to IDLE")
        self._transition("IDLE")
        return self._summary()

    def _wake(self):
        if self.planner.state.value != "IDLE":
            self._log(f"planner not idle — {self.planner.state.value}", level="warn")
        if self.executor.state != "IDLE":
            self._log(f"executor not idle — {self.executor.state}", level="warn")
        self._log("agents checked — proceeding")

    def _load(self) -> list[str]:
        names = db.list_profiles()
        self._log(f"loaded {len(names)} profile(s): {names}")
        self.profiles = names
        return names

    def _dispatch(self, profiles: list[str]):
        total   = len(profiles)
        success = 0
        failed  = 0

        for i, name in enumerate(profiles, 1):
            self._log(f"processing user {i}/{total} — '{name}'")
            job_id = db.create_job(self.run_id, name)

            try:
                profile = db.get_profile(name)
                if not profile:
                    raise ValueError(f"profile not found for '{name}'")

                history  = db.get_history(name)
                last_run = history[-1] if history else None
                trend    = db.get_trend(name)
                context  = {"last_run": last_run, "trend": trend} if last_run or trend else None

                input_data = SalaryInput(
                    name           = profile["name"],
                    monthly_salary = profile["monthly_salary"],
                    expenses       = profile["expenses"],
                )

                plan    = self.planner.run(input_data, context=context)
                plan_id = db.save_plan(plan)
                self._log(f"'{name}' — Agent 1 done, plan_id={plan_id}, score={plan.plan_score}")

                self.executor.run(plan_id)
                self._log(f"'{name}' — Agent 2 done")

                db.complete_job(job_id, plan_id)
                self.results.append({
                    "name":    name,
                    "status":  "success",
                    "plan_id": plan_id,
                    "score":   plan.plan_score,
                })
                success += 1

            except Exception as e:
                error_msg = str(e)
                self._log(f"'{name}' failed — {error_msg}", level="error")
                db.fail_job(job_id, error_msg)
                self.results.append({
                    "name":   name,
                    "status": "failed",
                    "error":  error_msg,
                })
                failed += 1

        self._log(f"dispatch complete — {success} success, {failed} failed")

    def _report(self):
        self._log(f"run_id: {self.run_id}")
        self._log(f"total users: {len(self.profiles)}")
        for r in self.results:
            if r["status"] == "success":
                self._log(f"  ✓ {r['name']} — score {r['score']}/100, plan_id={r['plan_id']}")
            else:
                self._log(f"  ✗ {r['name']} — {r['error']}", level="error")

    def _summary(self) -> dict:
        return {
            "run_id":   self.run_id,
            "total":    len(self.profiles),
            "success":  sum(1 for r in self.results if r["status"] == "success"),
            "failed":   sum(1 for r in self.results if r["status"] == "failed"),
            "results":  self.results,
            "duration": (datetime.now() - self.started_at).total_seconds()
                        if self.started_at else 0,
        }

    # ── Main loop ────────────────────────────────────────────