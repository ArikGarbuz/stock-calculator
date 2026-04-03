"""
sales_manager.py — אורקסטרטור מכירות אוטונומי
=========================================
מנהל מכירות אוטונומי שמפעיל את כל הסוכנים ומקבל החלטות.

תזמון יומי מומלץ (הפעל עם cron/scheduler):
  - 08:00 — run_daily_cycle()
  - 20:00 — run_daily_cycle(send_telegram=True)

הפעלה ידנית:
  python agents/sales_manager.py [--full | --leads | --pipeline | --growth | --content | --pricing]
"""

import os
import sys
import json
import argparse
from datetime import datetime

# Windows UTF-8 fix
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# הוסף את שורש הפרויקט ל-path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.sales.market_researcher import run_market_research, format_report as fmt_market
from agents.sales.lead_hunter import hunt_leads, format_hunt_report
from agents.sales.content_marketer import generate_weekly_calendar, get_content_for_platform, format_calendar
from agents.sales.pricing_agent import run_pricing_analysis, format_pricing_report
from agents.sales.sales_pipeline import get_pipeline_summary, generate_followup_messages, format_pipeline_report
from agents.sales.growth_analyst import run_growth_analysis, format_growth_report

# ─── Telegram (אופציונלי) ──────────────────────────────────────────────────────

def _send_telegram(message: str) -> bool:
    """שולח הודעה ב-Telegram דרך Python בלבד."""
    import os
    import requests
    from dotenv import load_dotenv
    load_dotenv()
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return False
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        resp = requests.post(url, data={"chat_id": chat_id, "text": message}, timeout=10)
        return resp.status_code == 200
    except Exception:
        return False


# ─── Decision Engine ──────────────────────────────────────────────────────────

def _make_decisions(growth: dict, pipeline: dict, leads_result: dict, pricing: dict) -> list:
    """
    לוגיקת קבלת החלטות אוטונומית.
    מחזיר רשימת פעולות מומלצות.
    """
    decisions = []

    # החלטה 1: האם להגביר ציד לידים?
    overdue = pipeline.get("overdue_followups", 0)
    total_prospects = pipeline.get("stages", {}).get("prospect", 0)
    if total_prospects < 20:
        decisions.append({
            "priority": "HIGH",
            "action": "הגבר ציד לידים",
            "reason": f"רק {total_prospects} prospects בפייפליין. יעד מינימום: 20.",
            "agent": "lead_hunter",
        })

    # החלטה 2: האם יש follow-ups דחופים?
    if overdue > 5:
        decisions.append({
            "priority": "HIGH",
            "action": f"בצע {overdue} follow-ups שעברו מועד",
            "reason": "לידים קרים מאבדים עניין מהר",
            "agent": "sales_pipeline",
        })

    # החלטה 3: האם trial->paying נמוך?
    trial_rate = growth.get("trial_to_paying_rate", 0)
    if trial_rate < 0.15:
        decisions.append({
            "priority": "MEDIUM",
            "action": "שפר onboarding flow",
            "reason": f"trial->paying = {trial_rate:.1%} (יעד: 15%). שקול email sequence + discount offer",
            "agent": "content_marketer",
        })

    # החלטה 4: שינוי תמחור?
    pricing_rec = pricing.get("position_analysis", {}).get("recommendation", "")
    if "הוריד" in pricing_rec or "raise" in pricing_rec.lower():
        decisions.append({
            "priority": "LOW",
            "action": pricing_rec,
            "reason": "ניתוח תחרותי מצביע על הזדמנות לשינוי מחיר",
            "agent": "pricing_agent",
        })

    # החלטה 5: תוכן שיווקי?
    if leads_result.get("new_leads_added", 0) < 5:
        decisions.append({
            "priority": "MEDIUM",
            "action": "פרסם תוכן ב-Reddit + Twitter היום",
            "reason": "מעט לידים חדשים — תוכן אורגני יכניס תנועה",
            "agent": "content_marketer",
        })

    return decisions


# ─── Daily Cycle ──────────────────────────────────────────────────────────────

def run_daily_cycle(send_telegram: bool = False, verbose: bool = True) -> dict:
    """
    מחזור יומי מלא — מפעיל את כל הסוכנים ומקבל החלטות.
    """
    results = {"timestamp": datetime.now().isoformat(), "agents": {}}

    if verbose:
        print(f"\n{'='*50}")
        print(f"Sales Manager — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print(f"{'='*50}\n")

    # 1. ציד לידים
    if verbose:
        print("[1/5] מריץ Lead Hunter...")
    leads_result = hunt_leads(max_per_source=5)
    results["agents"]["leads"] = leads_result
    if verbose:
        print(format_hunt_report(leads_result))

    # 2. Pipeline
    if verbose:
        print("\n[2/5] בודק Pipeline...")
    pipeline = get_pipeline_summary()
    results["agents"]["pipeline"] = pipeline
    if verbose:
        print(format_pipeline_report(pipeline))

    # 3. צמיחה
    if verbose:
        print("\n[3/5] מנתח צמיחה...")
    growth = run_growth_analysis()
    results["agents"]["growth"] = growth
    if verbose:
        print(format_growth_report(growth))

    # 4. תמחור
    if verbose:
        print("\n[4/5] בודק תמחור...")
    pricing = run_pricing_analysis()
    results["agents"]["pricing"] = pricing
    if verbose:
        print(format_pricing_report(pricing))

    # 5. קבלת החלטות
    if verbose:
        print("\n[5/5] מקבל החלטות...")
    decisions = _make_decisions(growth, pipeline, leads_result, pricing)
    results["decisions"] = decisions

    if verbose:
        print("\n--- החלטות אוטונומיות ---")
        for d in decisions:
            print(f"[{d['priority']}] {d['action']}")
            print(f"  סיבה: {d['reason']}")

    # 6. תוכן יומי מומלץ
    content = get_content_for_platform("Reddit")
    results["agents"]["content_suggestion"] = {
        "platform": "Reddit",
        "template_id": content.get("id"),
        "preview": (content.get("title") or content.get("text", ""))[:80],
    }

    # 7. Telegram
    if send_telegram:
        report = _build_telegram_report(growth, pipeline, leads_result, decisions)
        sent = _send_telegram(report)
        results["telegram_sent"] = sent
        if verbose:
            print(f"\nTelegram: {'נשלח ✅' if sent else 'לא נשלח (בדוק TELEGRAM_BOT_TOKEN)'}")

    return results


def _build_telegram_report(growth: dict, pipeline: dict, leads: dict, decisions: list) -> str:
    lines = [
        f"📊 Sales Manager — {datetime.now().strftime('%d/%m %H:%M')}",
        "",
        f"💰 MRR: ${growth['mrr_usd']:,.0f}",
        f"👥 משלמים: {growth['paying_users']} | Trial: {growth['trial_users']}",
        f"🔄 Churn: {growth['churn_rate']:.1%}",
        "",
        f"🎯 Pipeline:",
        f"  Prospects: {pipeline['stages'].get('prospect', 0)}",
        f"  Leads: {pipeline['stages'].get('lead', 0)}",
        f"  Trials: {pipeline['stages'].get('trial', 0)}",
        f"  Follow-ups דחופים: {pipeline['overdue_followups']}",
        "",
        f"🔍 לידים חדשים היום: {leads['new_leads_added']}",
        f"⚡ High-intent: {leads['high_intent_leads']}",
    ]
    if decisions:
        lines.append("")
        lines.append("🤖 החלטות:")
        for d in decisions[:3]:
            priority_emoji = "🔴" if d["priority"] == "HIGH" else "🟡" if d["priority"] == "MEDIUM" else "🟢"
            lines.append(f"  {priority_emoji} {d['action']}")
    return "\n".join(lines)


# ─── Weekly Market Research ───────────────────────────────────────────────────

def run_weekly_market_research(send_telegram: bool = False) -> dict:
    """מריץ מחקר שוק שבועי."""
    report = run_market_research()
    formatted = fmt_market(report)
    print(formatted)

    if send_telegram:
        short = (
            f"📈 מחקר שוק שבועי\n\n"
            f"TAM: {report['market_opportunity']['TAM']:,}\n"
            f"יעד שנה 1: {report['market_opportunity']['SOM_year1']:,} משתמשים\n"
            f"MRR פוטנציאלי: ${report['market_opportunity']['potential_MRR_y1_usd']:,}\n\n"
            + "\n".join(f"• {a}" for a in report['recommended_actions'][:2])
        )
        _send_telegram(short)

    return report


# ─── Weekly Content Calendar ──────────────────────────────────────────────────

def print_weekly_calendar() -> None:
    calendar = generate_weekly_calendar()
    print(format_calendar(calendar))


# ─── CLI ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sales Manager — אורקסטרטור מכירות אוטונומי")
    parser.add_argument("--full", action="store_true", help="מחזור יומי מלא")
    parser.add_argument("--leads", action="store_true", help="ציד לידים בלבד")
    parser.add_argument("--pipeline", action="store_true", help="דוח pipeline")
    parser.add_argument("--growth", action="store_true", help="דוח צמיחה")
    parser.add_argument("--content", action="store_true", help="לוח תוכן שבועי")
    parser.add_argument("--pricing", action="store_true", help="ניתוח תמחור")
    parser.add_argument("--market", action="store_true", help="מחקר שוק")
    parser.add_argument("--telegram", action="store_true", help="שלח דוח ב-Telegram")
    args = parser.parse_args()

    if args.leads:
        r = hunt_leads()
        print(format_hunt_report(r))
    elif args.pipeline:
        s = get_pipeline_summary()
        print(format_pipeline_report(s))
        print("\n--- Follow-ups ---")
        for m in generate_followup_messages():
            print(f"\n{m['lead_id']}: {m['message']}")
    elif args.growth:
        g = run_growth_analysis()
        print(format_growth_report(g))
    elif args.content:
        print_weekly_calendar()
    elif args.pricing:
        p = run_pricing_analysis()
        print(format_pricing_report(p))
    elif args.market:
        run_weekly_market_research(send_telegram=args.telegram)
    else:
        # ברירת מחדל: מחזור יומי מלא
        run_daily_cycle(send_telegram=args.telegram, verbose=True)
