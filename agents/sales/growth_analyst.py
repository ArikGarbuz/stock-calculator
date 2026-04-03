"""
growth_analyst.py — סוכן ניתוח צמיחה (מודל Freemium)
אחריות:
  - מעקב MAU, retention, affiliate revenue, ad revenue
  - מעקב אחר יעדים חודשיים
  - הפקת דוח יומי
"""

import json
import os
from datetime import datetime, date

METRICS_PATH   = os.path.join(os.path.dirname(__file__), "..", "..", "data", "sales", "metrics.json")
AFFILIATE_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "sales", "affiliates.json")


def load_metrics() -> dict:
    with open(METRICS_PATH, encoding="utf-8") as f:
        return json.load(f)


def save_metrics(data: dict) -> None:
    with open(METRICS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def run_growth_analysis(
    monthly_active_users: int = 0,
    new_users_30d: int = 0,
    ad_impressions_30d: int = 0,
    ad_revenue_usd: float = 0.0,
) -> dict:
    """
    מריץ ניתוח צמיחה freemium.
    affiliate revenue נלקח מ-affiliates.json.
    """
    # קרא affiliate data
    try:
        with open(AFFILIATE_PATH, encoding="utf-8") as f:
            aff = json.load(f)
        affiliate_clicks   = aff.get("total_clicks", 0)
        affiliate_conv     = aff.get("total_conversions", 0)
        affiliate_revenue  = aff.get("total_revenue_usd", 0.0)
    except Exception:
        affiliate_clicks = affiliate_conv = 0
        affiliate_revenue = 0.0

    total_revenue = affiliate_revenue + ad_revenue_usd
    rpm = round((total_revenue / max(ad_impressions_30d, 1)) * 1000, 2)

    metrics = {
        "date": date.today().isoformat(),
        "monthly_active_users": monthly_active_users,
        "new_users_30d": new_users_30d,
        "returning_users_30d": max(0, monthly_active_users - new_users_30d),
        "affiliate_clicks_30d": affiliate_clicks,
        "affiliate_conversions_30d": affiliate_conv,
        "affiliate_revenue_usd": affiliate_revenue,
        "ad_impressions_30d": ad_impressions_30d,
        "ad_revenue_usd": ad_revenue_usd,
        "total_revenue_usd": total_revenue,
        "rpm_usd": rpm,
        "top_broker": None,
        "top_ticker": None,
    }

    data = load_metrics()
    data["current"] = metrics

    current_month = date.today().strftime("%Y-%m")
    existing = [m.get("month") for m in data.get("monthly", [])]
    if current_month not in existing:
        data.setdefault("monthly", []).append({"month": current_month, **metrics})

    save_metrics(data)
    return metrics


def check_targets(metrics: dict) -> list:
    try:
        data = load_metrics()
        targets = data.get("targets", {})
    except Exception:
        return []

    month_num = max(len(data.get("monthly", [])), 1)
    if month_num <= 1:
        target = targets.get("month_1", {})
    elif month_num <= 3:
        target = targets.get("month_3", {})
    elif month_num <= 6:
        target = targets.get("month_6", {})
    else:
        target = targets.get("month_12", {})

    alerts = []
    if target:
        mau_target = target.get("mau", 0)
        aff_target = target.get("affiliate_revenue", 0)
        ad_target  = target.get("ad_revenue", 0)

        if metrics["monthly_active_users"] < mau_target * 0.5:
            alerts.append(f"MAU {metrics['monthly_active_users']} — יעד {mau_target} (חודש {month_num})")
        if metrics["affiliate_revenue_usd"] < aff_target * 0.5:
            alerts.append(f"Affiliate ${metrics['affiliate_revenue_usd']:.0f} — יעד ${aff_target}")
        if metrics["affiliate_clicks_30d"] == 0:
            alerts.append("אפס קליקים על ברוקרים — הוסף affiliate buttons לאפליקציה")
    return alerts


def format_growth_report(metrics: dict) -> str:
    alerts = check_targets(metrics)
    lines = [
        "=== דוח צמיחה (Freemium) ===",
        f"תאריך: {metrics.get('date', 'N/A')}",
        "",
        f"MAU:         {metrics['monthly_active_users']:,}",
        f"משתמשים חדשים: {metrics['new_users_30d']:,}",
        "",
        f"Affiliate clicks:   {metrics['affiliate_clicks_30d']}",
        f"Affiliate conv:     {metrics['affiliate_conversions_30d']}",
        f"Affiliate revenue:  ${metrics['affiliate_revenue_usd']:,.0f}",
        "",
        f"Ad impressions: {metrics['ad_impressions_30d']:,}",
        f"Ad revenue:     ${metrics['ad_revenue_usd']:,.2f}",
        f"RPM:            ${metrics['rpm_usd']:.2f}",
        "",
        f"Total revenue:  ${metrics['total_revenue_usd']:,.0f}",
    ]
    if alerts:
        lines.append("\n--- התראות ---")
        for a in alerts:
            lines.append(f"  {a}")
    else:
        lines.append("\n✅ כל המדדים על המסלול")
    return "\n".join(lines)


if __name__ == "__main__":
    m = run_growth_analysis()
    print(format_growth_report(m))
