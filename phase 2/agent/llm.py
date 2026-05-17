import os
import json
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def generate_recommendations(
    name: str,
    monthly_salary: float,
    analysis: dict,
    context: dict = None       # past runs + trend from SQLite
) -> list[str]:
    """
    Ask GPT to generate context-aware recommendations.
    Falls back to rules-based recommendations if GPT fails.
    
    context = {
        "trend":    { score_delta, expense_delta, direction },
        "last_run": { plan_score, current_savings, total_expenses }
    }
    """

    # ── Build the prompt ────────────────────────────────────
    system_prompt = """You are a personal financial planning assistant.
You receive a person's salary, expense breakdown, and optional history.
Your job is to produce clear, specific, actionable recommendations.

Rules:
- Be specific — mention actual amounts in ₹
- Be direct — no fluff, no generic advice
- Max 5 recommendations
- Each recommendation is 1–2 sentences
- If trend data is available, reference it
- Prioritise the biggest problems first

Respond ONLY with a JSON array of strings. No preamble, no markdown.
Example: ["Rec 1", "Rec 2", "Rec 3"]"""

    # ── Expense breakdown summary ────────────────────────────
    breakdown_lines = []
    for item in analysis["breakdown"]:
        line = (
            f"  {item['category']}: actual ₹{item['actual']:,.0f} / "
            f"recommended ₹{item['recommended']:,.0f} — {item['status']}"
        )
        breakdown_lines.append(line)
    breakdown_text = "\n".join(breakdown_lines)

    # ── Context section (only if we have past data) ──────────
    context_text = ""
    if context:
        trend    = context.get("trend")
        last_run = context.get("last_run")

        if last_run:
            context_text += (
                f"\nPrevious run: score {last_run['plan_score']}/100, "
                f"savings ₹{last_run['current_savings']:,.0f}, "
                f"expenses ₹{last_run['total_expenses']:,.0f}"
            )
        if trend:
            context_text += (
                f"\nTrend: {trend['direction']} | "
                f"score changed by {trend['score_delta']:+d} | "
                f"expenses changed by ₹{trend['expense_delta']:+,.0f} | "
                f"savings changed by ₹{trend['savings_delta']:+,.0f}"
            )

    user_prompt = f"""
Person: {name}
Monthly salary: ₹{monthly_salary:,.0f}

Expense breakdown:
{breakdown_text}

Summary:
  Total expenses:      ₹{analysis['total_expenses']:,.0f}
  Current savings:     ₹{analysis['current_savings']:,.0f}
  Recommended savings: ₹{analysis['recommended_savings']:,.0f}
  Savings gap:         ₹{analysis['savings_gap']:,.0f}
{context_text}

Generate recommendations.
""".strip()

    # ── Call GPT ─────────────────────────────────────────────
    try:
        print("[LLM      ] [INFO] calling GPT for recommendations")
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt},
            ],
            temperature=0.4,     # low = consistent, focused
            max_tokens=600,
        )

        raw  = response.choices[0].message.content.strip()
        tips = json.loads(raw)

        print(f"[LLM      ] [INFO] GPT returned {len(tips)} recommendations")
        return tips

    except json.JSONDecodeError as e:
        print(f"[LLM      ] [WARN] GPT response was not valid JSON — {e}")
        print(f"[LLM      ] [WARN] falling back to rules engine")
        return _fallback(analysis)

    except Exception as e:
        print(f"[LLM      ] [ERROR] GPT call failed — {e}")
        print(f"[LLM      ] [WARN] falling back to rules engine")
        return _fallback(analysis)


def _fallback(analysis: dict) -> list[str]:
    """
    Rules-based fallback when GPT is unavailable.
    Returns simple recommendations so the agent never crashes.
    """
    tips = []
    for item in analysis["breakdown"]:
        if item["status"] == "overspent":
            tips.append(
                f"{item['category'].title()} is over budget by "
                f"₹{abs(item['difference']):,.0f}. Review this category."
            )
    if analysis["current_savings"] < 0:
        tips.append("Expenses exceed income. Immediate action needed.")
    elif analysis["savings_gap"] > 0:
        tips.append(
            f"Savings gap of ₹{analysis['savings_gap']:,.0f}. "
            f"Automate a transfer on salary day."
        )
    else:
        tips.append("Savings target met. Consider investing the surplus.")
    return tips