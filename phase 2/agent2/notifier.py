import os
import smtplib
import json
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

GMAIL_ADDRESS    = os.getenv("GMAIL_ADDRESS")
GMAIL_PASSWORD   = os.getenv("GMAIL_APP_PASSWORD")
SLACK_WEBHOOK    = os.getenv("SLACK_WEBHOOK_URL")


# ── Email ────────────────────────────────────────────────────
def send_email(to: str, subject: str, body: str) -> bool:
    """
    Send a plain text email via Gmail SMTP.
    Returns True on success, False on failure.
    Never raises — failure is logged, not crashed.
    """
    if not to:
        print("[NOTIFIER ] [WARN ] no recipient email — skipping")
        return False
    if not GMAIL_ADDRESS or not GMAIL_PASSWORD:
        print("[NOTIFIER ] [WARN ] Gmail credentials missing in .env")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = GMAIL_ADDRESS
        msg["To"]      = to
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_ADDRESS, GMAIL_PASSWORD)
            server.sendmail(GMAIL_ADDRESS, to, msg.as_string())

        print(f"[NOTIFIER ] [INFO ] email sent → {to}")
        return True

    except Exception as e:
        print(f"[NOTIFIER ] [ERROR] email failed → {e}")
        return False


# ── Slack ─────────────────────────────────────────────────────
def send_slack(message: str) -> bool:
    """
    Post a message to Slack via webhook.
    Returns True on success, False on failure.
    """
    if not SLACK_WEBHOOK:
        print("[NOTIFIER ] [WARN ] Slack webhook missing in .env — skipping")
        return False

    try:
        response = requests.post(
            SLACK_WEBHOOK,
            json={"text": message},
            timeout=5,
        )
        if response.status_code == 200:
            print("[NOTIFIER ] [INFO ] Slack message sent")
            return True
        else:
            print(f"[NOTIFIER ] [WARN ] Slack returned {response.status_code}")
            return False

    except Exception as e:
        print(f"[NOTIFIER ] [ERROR] Slack failed → {e}")
        return False


# ── Notification builders ─────────────────────────────────────
def notify_overspend(name: str, email: str, overspent: list[dict]):
    if not overspent:
        return

    lines = "\n".join(
        f"  • {item['category'].title()}\n"
        f"    Spent ₹{item['actual']:,.0f} vs limit ₹{item['recommended']:,.0f}\n"
        f"    Over by ₹{abs(item['difference']):,.0f} "
        f"({round(abs(item['difference'])/item['recommended']*100)}% above limit)"
        for item in overspent
    )

    subject = f"⚠️ Budget Alert — {name} | {len(overspent)} categor{'y' if len(overspent)==1 else 'ies'} overspent"
    body    = f"""Hi {name},

    Your financial agent flagged overspending this month:

    {lines}

    Review these categories before next month. Small cuts now
    compound into big savings over time.

    — Financial Agent
    """
    send_email(email, subject, body)


def notify_monthly_summary(
    name:        str,
    email:       str,
    score:       int,
    savings:     float,
    summary:     str,
    plan_data:   dict = None,
    trend:       dict = None,
    actions:     list = None,
):
    if score >= 80:  grade = "Excellent"
    elif score >= 60: grade = "Good"
    elif score >= 40: grade = "Needs attention"
    else:             grade = "Critical"

    from datetime import datetime
    month = datetime.now().strftime("%B %Y")

    # ── Trend section ────────────────────────────────────────
    trend_lines = ""
    if trend:
        def arrow(val):
            return "▲" if val > 0 else "▼" if val < 0 else "→"

        trend_lines = f"""
        TREND (vs last month)
        {'─'*45}
        Score:    {trend['previous_score']} → {trend['current_score']}  {arrow(trend['score_delta'])} ({trend['direction']})
        Savings:  ₹{abs(trend.get('savings_delta', 0)):,.0f} {"increase" if trend.get('savings_delta', 0) > 0 else "decrease" if trend.get('savings_delta', 0) < 0 else "unchanged"}
        Expenses: ₹{abs(trend.get('expense_delta', 0)):,.0f} {"increase" if trend.get('expense_delta', 0) > 0 else "decrease" if trend.get('expense_delta', 0) < 0 else "unchanged"}
        """
    else:
        trend_lines = "\nTREND\n" + "─"*45 + "\nFirst run — no previous data to compare.\n"

    # ── Expense breakdown ────────────────────────────────────
    breakdown_lines = ""
    if plan_data:
        breakdown_lines = "\nEXPENSE BREAKDOWN\n" + "─"*45 + "\n"
        for item in plan_data.get("expense_breakdown", []):
            status_icon = "⚠" if item["status"] in ("overspent", "warning") else "✓"
            over_text   = (
                f"  ⚠ over by ₹{abs(item['difference']):,.0f}"
                if item["difference"] < 0 else "  ✓ ok"
            )
            breakdown_lines += (
                f"{item['category'].title():<14}"
                f"₹{item['actual']:>8,.0f} / ₹{item['recommended']:>8,.0f}"
                f"  {status_icon}{over_text}\n"
            )

    # ── Recommendations ──────────────────────────────────────
    rec_lines = ""
    if plan_data and plan_data.get("recommendations"):
        rec_lines = "\nGPT RECOMMENDATIONS\n" + "─"*45 + "\n"
        for i, rec in enumerate(plan_data["recommendations"], 1):
            # wrap long lines at 50 chars
            words   = rec.split()
            lines   = []
            current = f"{i}. "
            for word in words:
                if len(current) + len(word) > 52:
                    lines.append(current)
                    current = "   " + word + " "
                else:
                    current += word + " "
            lines.append(current)
            rec_lines += "\n".join(lines) + "\n\n"

    # ── Actions taken ────────────────────────────────────────
    actions_lines = ""
    if actions:
        actions_lines = "\nACTIONS TAKEN BY YOUR AGENT\n" + "─"*45 + "\n"
        for a in actions:
            if a["name"] != "plan_summary":
                actions_lines += f"• {a['detail']}\n"

    # ── Assemble full email ──────────────────────────────────
    body = f"""Hi {name},

    Monthly Financial Report — {month}
    {'━'*45}

    SCORE: {score}/100 — {grade}
    Savings this month: ₹{savings:,.0f}
    {trend_lines}{breakdown_lines}{rec_lines}{actions_lines}
    {'━'*45}
    — Financial Agent
    """

    subject = f"📊 Monthly Report — {name} | Score {score}/100 — {grade}"
    send_email(email, subject, body)