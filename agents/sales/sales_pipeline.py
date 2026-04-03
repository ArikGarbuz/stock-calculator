"""
sales_pipeline.py — CRM פנימי + Pipeline
אחריות:
  - ניהול funnel: Prospect -> Lead -> Trial -> Paying -> Churned
  - מעקב follow-up אוטומטי
  - חישוב conversion rates
  - זיהוי leads שצריכים מגע
"""

import json
import os
from datetime import datetime, timedelta
from typing import Optional

PIPELINE_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "sales", "pipeline.json")


# ─── Stages & Transitions ─────────────────────────────────────────────────────

STAGES = ["prospect", "lead", "trial", "paying", "churned"]
STAGE_SLA_DAYS = {
    "prospect": 3,   # follow up תוך 3 ימים
    "lead": 7,       # המר ל-trial תוך שבוע
    "trial": 14,     # המר ל-paying תוך 14 יום
    "paying": 90,    # חידוש / upsell כל 90 יום
}


def _load() -> dict:
    with open(PIPELINE_PATH, encoding="utf-8") as f:
        return json.load(f)


def _save(data: dict) -> None:
    data["last_updated"] = datetime.now().isoformat()
    # עדכן stats
    for stage in STAGES:
        data["stats"][f"total_{stage}"] = len(data["stages"].get(stage, []))
    # חשב conversion rates
    leads = data["stats"].get("total_lead", 1) or 1
    trials = data["stats"].get("total_trial", 0)
    paying = data["stats"].get("total_paying", 0)
    data["stats"]["conversion_rate_lead_to_trial"] = round(trials / leads, 3)
    data["stats"]["conversion_rate_trial_to_paying"] = round(paying / max(trials, 1), 3)
    with open(PIPELINE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def add_lead(lead_id: str, source: str, contact: str, intent_score: float = 0.0, notes: str = "") -> dict:
    """מוסיף ליד חדש ל-prospect."""
    pipeline = _load()
    existing = {
        item["id"]
        for stage in STAGES
        for item in pipeline["stages"].get(stage, [])
    }
    if lead_id in existing:
        return {"status": "exists", "id": lead_id}

    entry = {
        "id": lead_id,
        "source": source,
        "contact": contact,
        "intent_score": intent_score,
        "notes": notes,
        "stage": "prospect",
        "added_at": datetime.now().isoformat(),
        "last_contact": None,
        "next_followup": (datetime.now() + timedelta(days=STAGE_SLA_DAYS["prospect"])).isoformat(),
        "history": [{"event": "added", "timestamp": datetime.now().isoformat()}],
    }
    pipeline["stages"]["prospect"].append(entry)
    _save(pipeline)
    return {"status": "added", "id": lead_id, "stage": "prospect"}


def advance_stage(lead_id: str, to_stage: str, notes: str = "") -> dict:
    """מקדם ליד לשלב הבא."""
    if to_stage not in STAGES:
        return {"error": f"שלב לא חוקי: {to_stage}"}

    pipeline = _load()
    for stage in STAGES:
        for i, item in enumerate(pipeline["stages"].get(stage, [])):
            if item["id"] == lead_id:
                entry = pipeline["stages"][stage].pop(i)
                entry["stage"] = to_stage
                entry["last_contact"] = datetime.now().isoformat()
                entry["next_followup"] = (
                    datetime.now() + timedelta(days=STAGE_SLA_DAYS.get(to_stage, 7))
                ).isoformat()
                entry.setdefault("history", []).append({
                    "event": f"moved_to_{to_stage}",
                    "from": stage,
                    "notes": notes,
                    "timestamp": datetime.now().isoformat(),
                })
                pipeline["stages"].setdefault(to_stage, []).append(entry)
                _save(pipeline)
                return {"status": "advanced", "id": lead_id, "from": stage, "to": to_stage}
    return {"error": f"ליד לא נמצא: {lead_id}"}


def get_overdue_followups() -> list:
    """מחזיר רשימת לידים שה-follow-up שלהם עבר מועד."""
    pipeline = _load()
    now = datetime.now()
    overdue = []
    for stage in ["prospect", "lead", "trial"]:
        for item in pipeline["stages"].get(stage, []):
            next_fp = item.get("next_followup")
            if next_fp:
                try:
                    if datetime.fromisoformat(next_fp) < now:
                        overdue.append({**item, "days_overdue": (now - datetime.fromisoformat(next_fp)).days})
                except ValueError:
                    pass
    return sorted(overdue, key=lambda x: x.get("days_overdue", 0), reverse=True)


def get_pipeline_summary() -> dict:
    """מחזיר סיכום pipeline."""
    pipeline = _load()
    stats = pipeline["stats"]
    overdue = get_overdue_followups()

    return {
        "timestamp": datetime.now().isoformat(),
        "stages": {
            stage: len(pipeline["stages"].get(stage, []))
            for stage in STAGES
        },
        "conversion_rates": {
            "lead_to_trial": f"{stats.get('conversion_rate_lead_to_trial', 0):.1%}",
            "trial_to_paying": f"{stats.get('conversion_rate_trial_to_paying', 0):.1%}",
        },
        "overdue_followups": len(overdue),
        "top_overdue": overdue[:3],
    }


def generate_followup_messages() -> list:
    """מייצר הודעות follow-up לכל ליד שעבר מועד."""
    overdue = get_overdue_followups()
    messages = []

    templates = {
        "prospect": "היי! ראיתי שהגעת דרך {source}. יש לך 5 דקות לנסות את מחשבון ה-R:R בחינם? קישור: [LINK]",
        "lead": "שלום! רציתי לבדוק — ניסית את הכלי? אם יש שאלות אשמח לעזור. Trial חינם ל-14 יום.",
        "trial": "הטריאל שלך מסתיים בקרוב. מה הרגשת? אשמח לשמוע feedback ולהציע deal מיוחד להמרה.",
    }

    for lead in overdue:
        stage = lead.get("stage", "prospect")
        template = templates.get(stage, "")
        if template:
            messages.append({
                "lead_id": lead["id"],
                "contact": lead.get("contact"),
                "stage": stage,
                "days_overdue": lead.get("days_overdue", 0),
                "message": template.format(source=lead.get("source", "האתר")),
            })
    return messages


def format_pipeline_report(summary: dict) -> str:
    lines = [
        "=== דוח Pipeline ===",
        f"תאריך: {summary['timestamp'][:10]}",
        "",
        "שלבים:",
    ]
    for stage, count in summary["stages"].items():
        lines.append(f"  {stage:12}: {count}")
    lines += [
        "",
        f"Conversion lead->trial:   {summary['conversion_rates']['lead_to_trial']}",
        f"Conversion trial->paying: {summary['conversion_rates']['trial_to_paying']}",
        "",
        f"Follow-ups שעברו מועד: {summary['overdue_followups']}",
    ]
    if summary["top_overdue"]:
        lines.append("דחופים:")
        for item in summary["top_overdue"]:
            lines.append(f"  [{item['days_overdue']}d] {item['id']} ({item['stage']})")
    return "\n".join(lines)


if __name__ == "__main__":
    summary = get_pipeline_summary()
    print(format_pipeline_report(summary))
    print("\n--- הודעות Follow-up ---")
    for msg in generate_followup_messages():
        print(f"\n[{msg['stage']}] {msg['lead_id']} ({msg['days_overdue']}d overdue):")
        print(f"  {msg['message']}")
