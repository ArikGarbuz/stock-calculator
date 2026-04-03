"""
growth_analyst.py — סוכן ניתוח צמיחה
אחריות:
  - חישוב MRR, ARR, LTV, CAC, Churn
  - מעקב אחר יעדים חודשיים
  - זיהוי בעיות בפני funnel
  - הפקת דוח יומי
"""

import json
import os
from datetime import datetime, date

METRICS_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "sales", "metrics.json")
PIPELINE_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "sales", "pipeline.json")
PRICING_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "sales", "pricing.json")


def load_metrics() -> dict:
    with open(METRICS_PATH, encoding="utf-8") as f:
        return json.load(f)


def save_metrics(data: dict) -> None:
    with open(METRICS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def calculate_mrr(paying_users: list, pricing: dict) -> float:
    """מחשב MRR לפי breakdown של משתמשים משלמים לפי tier."""
    tiers = pricing.get("tiers", {})
    mrr = 0.0
    for user in paying_users:
        tier = user.get("tier", "pro")
        price = tiers.get(tier, {}).get("price_usd", 0)
        mrr += price
    return mrr


def calculate_ltv(arpu: float, churn_rate: float) -> float:
    """LTV = ARPU / Monthly Churn Rate."""
    if churn_rate <= 0:
        return arpu * 24  # assume 24 months if no churn data yet
    return round(arpu / churn_rate, 2)


def calculate_cac(marketing_spend: float, new_customers: int) -> float:
    """CAC = Marketing Spend / New Customers."""
    if new_customers <= 0:
        return 0.0
    return round(marketing_spend / new_customers, 2)


def run_growth_analysis(
    paying_users: int = 0,
    trial_users: int = 0,
    free_users: int = 0,
    new_signups_30d: int = 0,
    churned_30d: int = 0,
    marketing_spend_30d: float = 0.0,
) -> dict:
    """
    מריץ ניתוח צמיחה מלא ועדכן metrics.json.
    כאשר אין נתונים אמיתיים עדיין — מחשב על בסיס pipeline.
    """
    # טען נתונים מה-pipeline אם לא סופקו
    try:
        with open(PIPELINE_PATH, encoding="utf-8") as f:
            pipeline = json.load(f)
        if paying_users == 0:
            paying_users = pipeline["stats"].get("total_paying", 0)
        if trial_users == 0:
            trial_users = pipeline["stats"].get("total_trial", 0)
    except Exception:
        pass

    try:
        with open(PRICING_PATH, encoding="utf-8") as f:
            pricing = json.load(f)
        avg_price = pricing["tiers"]["pro"]["price_usd"]
    except Exception:
        avg_price = 29.0

    total_users = paying_users + trial_users + free_users
    mrr = paying_users * avg_price
    arr = mrr * 12
    churn_rate = churned_30d / max(paying_users, 1)
    ltv = calculate_ltv(avg_price, churn_rate)
    cac = calculate_cac(marketing_spend_30d, max(new_signups_30d - trial_users, 1))
    ltv_cac = round(ltv / max(cac, 1), 2)

    # conversion rates
    free_to_trial = round(trial_users / max(free_users, 1), 3)
    trial_to_paying = round(paying_users / max(trial_users, 1), 3)

    metrics = {
        "date": date.today().isoformat(),
        "mrr_usd": mrr,
        "arr_usd": arr,
        "total_users": total_users,
        "paying_users": paying_users,
        "trial_users": trial_users,
        "free_users": free_users,
        "new_signups_30d": new_signups_30d,
        "churned_30d": churned_30d,
        "churn_rate": round(churn_rate, 3),
        "ltv_usd": ltv,
        "cac_usd": cac,
        "ltv_cac_ratio": ltv_cac,
        "free_to_trial_rate": free_to_trial,
        "trial_to_paying_rate": trial_to_paying,
        "nps": None,
    }

    # שמור ל-metrics.json
    data = load_metrics()
    data["current"] = metrics

    # הוסף snapshot חודשי
    current_month = date.today().strftime("%Y-%m")
    existing_months = [m.get("month") for m in data.get("monthly", [])]
    if current_month not in existing_months:
        data.setdefault("monthly", []).append({"month": current_month, **metrics})

    save_metrics(data)
    return metrics


def check_targets(metrics: dict) -> list:
    """בודק האם אנחנו על המסלול ליעדים."""
    try:
        with open(METRICS_PATH, encoding="utf-8") as f:
            data = json.load(f)
        targets = data.get("targets", {})
    except Exception:
        return []

    alerts = []
    month_num = len([m for m in data.get("monthly", [])]) or 1

    if month_num <= 1:
        target = targets.get("month_1", {})
    elif month_num <= 3:
        target = targets.get("month_3", {})
    elif month_num <= 6:
        target = targets.get("month_6", {})
    else:
        target = targets.get("month_12", {})

    if target:
        mrr_target = target.get("mrr", 0)
        users_target = target.get("paying_users", 0)
        if metrics["mrr_usd"] < mrr_target * 0.5:
            alerts.append(f"⚠️ MRR ${metrics['mrr_usd']:.0f} — רחוק מהיעד ${mrr_target} (חודש {month_num})")
        if metrics["paying_users"] < users_target * 0.5:
            alerts.append(f"⚠️ משתמשים משלמים {metrics['paying_users']} — יעד: {users_target}")
        if metrics.get("trial_to_paying_rate", 0) < 0.15:
            alerts.append(f"⚠️ trial->paying rate נמוך: {metrics['trial_to_paying_rate']:.1%} (יעד: 15%+)")
        if metrics.get("churn_rate", 0) > 0.08:
            alerts.append(f"⚠️ churn גבוה: {metrics['churn_rate']:.1%} (יעד: <8%)")

    return alerts


def format_growth_report(metrics: dict) -> str:
    alerts = check_targets(metrics)
    lines = [
        "=== דוח צמיחה ===",
        f"תאריך: {metrics.get('date', 'N/A')}",
        "",
        f"MRR:     ${metrics['mrr_usd']:,.0f}",
        f"ARR:     ${metrics['arr_usd']:,.0f}",
        "",
        f"משתמשים:   {metrics['total_users']} (Free: {metrics['free_users']} | Trial: {metrics['trial_users']} | Paying: {metrics['paying_users']})",
        f"Churn:     {metrics['churn_rate']:.1%}/mo",
        f"LTV:       ${metrics['ltv_usd']:,.0f}",
        f"CAC:       ${metrics['cac_usd']:,.0f}",
        f"LTV:CAC:   {metrics['ltv_cac_ratio']:.1f}x",
        "",
        f"Free->Trial:   {metrics['free_to_trial_rate']:.1%}",
        f"Trial->Paying: {metrics['trial_to_paying_rate']:.1%}",
    ]
    if alerts:
        lines.append("\n--- התראות ---")
        lines.extend(alerts)
    else:
        lines.append("\n✅ כל המדדים על המסלול")
    return "\n".join(lines)


if __name__ == "__main__":
    metrics = run_growth_analysis()
    print(format_growth_report(metrics))
