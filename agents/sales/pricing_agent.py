"""
pricing_agent.py — סוכן תמחור דינמי
אחריות:
  - ניטור מחירי מתחרים
  - הצעת A/B tests על תמחור
  - חישוב LTV/CAC אופטימלי
  - המלצות שינוי tier
"""

import json
import os
from datetime import datetime

PRICING_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "sales", "pricing.json")
METRICS_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "sales", "metrics.json")


def load_pricing() -> dict:
    with open(PRICING_PATH, encoding="utf-8") as f:
        return json.load(f)


def load_metrics() -> dict:
    with open(METRICS_PATH, encoding="utf-8") as f:
        return json.load(f)


def save_pricing(data: dict) -> None:
    data["last_updated"] = datetime.now().isoformat()
    with open(PRICING_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def analyze_pricing_position() -> dict:
    """מנתח את מיקום התמחור שלנו מול מתחרים."""
    pricing = load_pricing()
    competitors = pricing["competitors"]
    our_pro = pricing["tiers"]["pro"]["price_usd"]
    our_elite = pricing["tiers"]["elite"]["price_usd"]

    analysis = {
        "our_pro": our_pro,
        "our_elite": our_elite,
        "vs_competitors": {},
        "recommendation": None,
    }

    for comp, tiers in competitors.items():
        closest_tier = None
        closest_price = None
        for tier, price in tiers.items():
            if price and price > 0:
                if closest_price is None or abs(price - our_pro) < abs(closest_price - our_pro):
                    closest_tier = tier
                    closest_price = price
        if closest_tier:
            diff = our_pro - closest_price
            analysis["vs_competitors"][comp] = {
                "their_price": closest_price,
                "their_tier": closest_tier,
                "our_diff": diff,
                "we_are": "cheaper" if diff < 0 else "more_expensive" if diff > 0 else "same",
            }

    # המלצה
    tv_comp = analysis["vs_competitors"].get("TradingView", {})
    if tv_comp.get("we_are") == "more_expensive":
        analysis["recommendation"] = (
            f"שקול להוריד Pro ל-$19 — TradingView Pro עולה ${tv_comp['their_price']}. "
            "אנחנו צריכים להיות זולים יותר בשלב ה-early adopter."
        )
    else:
        analysis["recommendation"] = (
            "התמחור תחרותי. שקול להעלות ל-$34 אחרי 50 משתמשים משלמים לבדוק elasticity."
        )

    return analysis


def suggest_ab_test() -> dict:
    """מציע A/B test על תמחור."""
    pricing = load_pricing()
    current_pro = pricing["tiers"]["pro"]["price_usd"]

    tests = [
        {
            "name": "Price Anchoring Test",
            "variant_a": {"price": current_pro, "label": "Pro"},
            "variant_b": {"price": current_pro - 10, "label": "Pro — Launch Price"},
            "hypothesis": "הוספת 'Launch Price' תגדיל conversion ב-20%+",
            "metric": "trial_to_paying_rate",
            "duration_days": 14,
        },
        {
            "name": "Annual Discount Test",
            "variant_a": {"price": current_pro, "billing": "monthly"},
            "variant_b": {"price": current_pro * 10, "billing": "annual", "savings_label": "חסוך 2 חודשים"},
            "hypothesis": "הצעת שנתית תגדיל LTV ב-40%",
            "metric": "ltv_usd",
            "duration_days": 30,
        },
    ]

    # שמור A/B test ל-pricing.json
    pricing["ab_tests"] = tests
    save_pricing(pricing)

    return {"suggested_tests": tests, "timestamp": datetime.now().isoformat()}


def calculate_optimal_price(target_cac_usd: float = 50.0, target_ltv_cac_ratio: float = 3.0) -> dict:
    """
    מחשב מחיר אופטימלי בהינתן יעדי CAC ו-LTV:CAC.
    LTV = ARPU / Churn_rate
    """
    target_ltv = target_cac_usd * target_ltv_cac_ratio
    assumed_churn_monthly = 0.05  # 5% churn ראשוני

    required_arpu = target_ltv * assumed_churn_monthly

    return {
        "target_ltv_usd": target_ltv,
        "assumed_monthly_churn": assumed_churn_monthly,
        "required_monthly_arpu_usd": round(required_arpu, 2),
        "recommendation": (
            f"כדי לעמוד ב-LTV:CAC={target_ltv_cac_ratio} עם CAC=${target_cac_usd}, "
            f"ה-ARPU צריך להיות לפחות ${required_arpu:.0f}/חודש. "
            f"מחיר Pro מינימלי: ${required_arpu:.0f} (נוכחי: $29 — {'✅ בסדר' if 29 >= required_arpu else '❌ נמוך מדי'})"
        ),
    }


def run_pricing_analysis() -> dict:
    position = analyze_pricing_position()
    ab_suggestion = suggest_ab_test()
    optimal = calculate_optimal_price()

    return {
        "timestamp": datetime.now().isoformat(),
        "position_analysis": position,
        "ab_test_suggestion": ab_suggestion["suggested_tests"][0],
        "optimal_pricing": optimal,
    }


def format_pricing_report(report: dict) -> str:
    pos = report["position_analysis"]
    opt = report["optimal_pricing"]
    lines = [
        "=== דוח תמחור ===",
        f"Pro נוכחי: ${pos['our_pro']} | Elite: ${pos['our_elite']}",
        "",
        "מול מתחרים:",
    ]
    for comp, data in pos["vs_competitors"].items():
        lines.append(f"  {comp}: ${data['their_price']} ({data['we_are']})")
    lines += [
        "",
        f"המלצה: {pos['recommendation']}",
        "",
        f"LTV אופטימלי: {opt['recommendation']}",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    report = run_pricing_analysis()
    print(format_pricing_report(report))
