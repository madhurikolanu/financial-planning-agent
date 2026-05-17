from agent.models import SalaryInput, SavingsPlan, ExpenseAnalysis

# ── The 50/30/20 rule ───────────────────────────────────────
# Each category gets a recommended % of monthly salary.
# Needs (housing, utilities, transport) → total 50%
# Wants (food, entertainment, misc)     → total 30%
# Savings target                        → 20%

CATEGORY_RULES = {
    "housing":       {"limit_pct": 0.30, "bucket": "needs"},
    "transport":     {"limit_pct": 0.10, "bucket": "needs"},
    "utilities":     {"limit_pct": 0.10, "bucket": "needs"},
    "food":          {"limit_pct": 0.15, "bucket": "wants"},
    "entertainment": {"limit_pct": 0.08, "bucket": "wants"},
    "miscellaneous": {"limit_pct": 0.07, "bucket": "wants"},
}

SAVINGS_TARGET_PCT = 0.20


# ── Expense analysis ────────────────────────────────────────
def analyze_expenses(data: SalaryInput) -> dict:
    """
    Compare each actual expense against the recommended limit.
    Returns a breakdown and summary numbers.
    """
    salary = data.monthly_salary
    expenses = data.expenses.model_dump()   # → plain dict
    breakdown = []
    total_expenses = 0.0

    for category, actual in expenses.items():
        rule        = CATEGORY_RULES[category]
        recommended = salary * rule["limit_pct"]
        difference  = recommended - actual      # positive = under, negative = over
        total_expenses += actual

        if actual <= recommended * 0.90:
            status = "ok"
        elif actual <= recommended:
            status = "warning"
        else:
            status = "overspent"

        breakdown.append({
            "category":    category,
            "actual":      round(actual, 2),
            "recommended": round(recommended, 2),
            "difference":  round(difference, 2),
            "status":      status,
            "bucket":      rule["bucket"],
        })

    current_savings    = round(salary - total_expenses, 2)
    recommended_savings = round(salary * SAVINGS_TARGET_PCT, 2)
    savings_gap        = round(recommended_savings - current_savings, 2)

    return {
        "breakdown":            breakdown,
        "total_expenses":       round(total_expenses, 2),
        "current_savings":      current_savings,
        "recommended_savings":  recommended_savings,
        "savings_gap":          savings_gap,
    }


# ── Plan builder ────────────────────────────────────────────
def build_plan(data: SalaryInput, analysis: dict, recommendations: list[str]) -> SavingsPlan:
    """
    Recommendations now come from GPT via llm.py.
    rules.py only handles scoring and structure.
    """
    score = _score_plan(analysis)

    expense_breakdown = [
        ExpenseAnalysis(**item) for item in analysis["breakdown"]
    ]

    return SavingsPlan(
        name                = data.name,
        monthly_salary      = data.monthly_salary,
        total_expenses      = analysis["total_expenses"],
        current_savings     = analysis["current_savings"],
        recommended_savings = analysis["recommended_savings"],
        savings_gap         = analysis["savings_gap"],
        expense_breakdown   = expense_breakdown,
        recommendations     = recommendations,
        plan_score          = score,
    )

# ── Scoring ─────────────────────────────────────────────────
def _score_plan(analysis: dict) -> int:
    """
    Score 0–100 based on:
      40 pts — savings rate vs 20% target
      40 pts — how many categories are within budget
      20 pts — no category severely overspent (>150% of limit)
    """
    score = 0
    salary_factor = analysis["recommended_savings"]

    # Savings score (40 pts)
    if salary_factor > 0:
        savings_ratio = analysis["current_savings"] / salary_factor
        score += min(40, int(savings_ratio * 40))

    # Category score (40 pts)
    breakdown   = analysis["breakdown"]
    ok_count    = sum(1 for i in breakdown if i["status"] == "ok")
    total_cats  = len(breakdown)
    score += int((ok_count / total_cats) * 40)

    # No severe overspend (20 pts)
    severe = any(
        i["actual"] > (i["recommended"] * 1.5)
        for i in breakdown
    )
    if not severe:
        score += 20

    return max(0, min(score, 100))