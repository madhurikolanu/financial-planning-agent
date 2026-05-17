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
def build_plan(data: SalaryInput, analysis: dict) -> SavingsPlan:
    """
    Turn the raw analysis into a structured plan with
    a score and human-readable recommendations.
    """
    recommendations = _generate_recommendations(data, analysis)
    score           = _score_plan(analysis)

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


# ── Recommendations ─────────────────────────────────────────
def _generate_recommendations(data: SalaryInput, analysis: dict) -> list[str]:
    """
    Decision logic: look at each category and savings gap,
    then produce specific, actionable advice.
    """
    tips = []
    salary = data.monthly_salary

    for item in analysis["breakdown"]:
        cat    = item["category"]
        status = item["status"]
        over   = abs(item["difference"])

        if status == "overspent":
            pct = round((over / salary) * 100, 1)
            if cat == "housing":
                tips.append(
                    f"Housing is over budget by ₹{over:,.0f} ({pct}% of salary). "
                    f"Consider a roommate or relocating closer to work."
                )
            elif cat == "food":
                tips.append(
                    f"Food spend is ₹{over:,.0f} over limit. "
                    f"Meal prepping 3 days a week can cut this by 30–40%."
                )
            elif cat == "transport":
                tips.append(
                    f"Transport is over by ₹{over:,.0f}. "
                    f"Review monthly pass vs daily fare — could save significantly."
                )
            elif cat == "entertainment":
                tips.append(
                    f"Entertainment exceeds limit by ₹{over:,.0f}. "
                    f"Audit subscriptions — cancel unused ones first."
                )
            elif cat == "utilities":
                tips.append(
                    f"Utilities over by ₹{over:,.0f}. "
                    f"Check for appliances running on standby."
                )
            elif cat == "miscellaneous":
                tips.append(
                    f"Miscellaneous spend is ₹{over:,.0f} over. "
                    f"Track this category for 2 weeks to find the leak."
                )
   # Savings gap advice
    gap = analysis["savings_gap"]
    if analysis["current_savings"] < 0:
        tips.append(
            "Expenses exceed income by "
            f"₹{abs(analysis['current_savings']):,.0f}/month. "
            "Immediate action needed — cut wants before needs."
        )
    elif gap > 0:
        tips.append(
            f"Currently saving ₹{analysis['current_savings']:,.0f}/month, "
            f"but the 20% target is ₹{analysis['recommended_savings']:,.0f}. "
            f"Gap: ₹{gap:,.0f}. Automate a transfer on salary day."
        )
    else:
        tips.append(
            f"Savings target met. Consider splitting ₹{analysis['current_savings']:,.0f} "
            f"between an emergency fund (3 months expenses) and investments."
        )

    return tips


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