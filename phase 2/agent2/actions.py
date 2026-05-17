import agent.database as db
from datetime import datetime, timedelta


def create_budget_alert(plan_id: int, category: str, overspend: float):
    """Flag an overspent category with a specific action."""
    db.save_action(
        plan_id  = plan_id,
        name     = "budget_alert",
        category = category,
        detail   = (
            f"Overspent by ₹{overspend:,.0f}. "
            f"Review and reduce {category} spending this month."
        )
    )
    print(f"[AGENT2   ] [ACTION] budget_alert — {category} overspent ₹{overspend:,.0f}")


def schedule_review(plan_id: int, score: int):
    """Schedule a 30-day review with urgency based on score."""
    review_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    urgency     = "urgent" if score < 50 else "routine"
    db.save_action(
        plan_id  = plan_id,
        name     = "schedule_review",
        category = "general",
        detail   = f"{urgency.title()} 30-day review scheduled for {review_date}. Score: {score}/100."
    )
    print(f"[AGENT2   ] [ACTION] schedule_review — {urgency}, due {review_date}")


def track_savings_gap(plan_id: int, gap: float):
    """Create a savings automation action if gap exists."""
    db.save_action(
        plan_id  = plan_id,
        name     = "savings_tracker",
        category = "savings",
        detail   = (
            f"Automate ₹{gap:,.0f} transfer on salary day "
            f"to close savings gap."
        )
    )
    print(f"[AGENT2   ] [ACTION] savings_tracker — gap ₹{gap:,.0f}")


def record_summary(plan_id: int, summary: str):
    """Store GPT-generated plain English summary."""
    db.save_action(
        plan_id  = plan_id,
        name     = "plan_summary",
        category = "general",
        detail   = summary
    )
    print(f"[AGENT2   ] [ACTION] plan_summary — recorded")