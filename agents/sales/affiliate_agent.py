"""
affiliate_agent.py — סוכן תוכניות שותפים
אחריות:
  - ניהול קישורי affiliate לברוקרים
  - בחירת הברוקר הרלוונטי ביותר לפי מניה/שוק
  - עקיבת קליקים והכנסות
  - דוח הכנסות חודשי
"""

import json
import os
from datetime import datetime

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "sales")
AFFILIATE_DB = os.path.join(DATA_PATH, "affiliates.json")


# ─── Broker Programs ─────────────────────────────────────────────────────────

BROKERS = {
    "ibkr": {
        "name": "Interactive Brokers",
        "logo": "🏦",
        "markets": ["US", "TASE", "global"],
        "affiliate_url": "https://www.interactivebrokers.com/referral/arik123",  # להחליף ב-URL אמיתי
        "commission_model": "revenue_share",
        "commission_usd": 200,        # ממוצע לחשבון ממומן
        "cpa_funded_account": True,
        "min_deposit": 0,
        "description": "הברוקר הטוב ביותר לסוחרים רציניים — TASE + US + 150 שווקים",
        "badge": "מומלץ",
        "badge_color": "green",
        "features": ["עמלות נמוכות", "TASE + US", "API מתקדם", "מסחר בינלאומי"],
    },
    "etoro": {
        "name": "eToro",
        "logo": "🌐",
        "markets": ["US", "global"],
        "affiliate_url": "https://www.etoro.com/referral/arik123",  # להחליף
        "commission_model": "CPA",
        "commission_usd": 200,
        "cpa_funded_account": True,
        "min_deposit": 50,
        "description": "פלטפורמה חברתית — ראה מה הסוחרים הטובים ביותר עושים",
        "badge": "Social Trading",
        "badge_color": "blue",
        "features": ["Copy Trading", "ממשק ידידותי", "מסחר חברתי", "חינם להתחיל"],
    },
    "plus500": {
        "name": "Plus500",
        "logo": "➕",
        "markets": ["US", "global", "CFD"],
        "affiliate_url": "https://www.plus500.com/referral/arik123",  # להחליף
        "commission_model": "CPA",
        "commission_usd": 150,
        "cpa_funded_account": True,
        "min_deposit": 100,
        "description": "פלטפורמת CFD ישראלית — מסחר על מניות, קריפטו, מטח",
        "badge": "ישראלי",
        "badge_color": "blue",
        "features": ["CFD", "פלטפורמה בעברית", "לא צריך בעלות", "leverage"],
    },
    "trading212": {
        "name": "Trading212",
        "logo": "📱",
        "markets": ["US", "EU"],
        "affiliate_url": "https://www.trading212.com/referral/arik123",  # להחליף
        "commission_model": "revenue_share",
        "commission_usd": 50,
        "cpa_funded_account": False,
        "min_deposit": 1,
        "description": "אפליקציה מעולה למתחילים — מניות חינם ללא עמלה",
        "badge": "חינם",
        "badge_color": "green",
        "features": ["ללא עמלה", "ממשק פשוט", "Fractional shares", "ISA"],
    },
    "moomoo": {
        "name": "Moomoo",
        "logo": "🐄",
        "markets": ["US"],
        "affiliate_url": "https://j.moomoo.com/referral/arik123",  # להחליף
        "commission_model": "CPA",
        "commission_usd": 100,
        "cpa_funded_account": True,
        "min_deposit": 0,
        "description": "כלי אנליזה חזק + מסחר — מושלם ל-Day Traders",
        "badge": "Analytics",
        "badge_color": "orange",
        "features": ["Level 2 data", "כלי טכני", "חינם לגמרי", "ניתוח מתקדם"],
    },
}


# ─── Smart Broker Selection ───────────────────────────────────────────────────

def get_brokers_for_ticker(ticker: str) -> list:
    """
    מחזיר רשימת ברוקרים מומלצים לפי המניה/שוק.
    מניה ישראלית (.TA) → IBKR ראשון.
    מניה US → eToro / Moomoo ראשון.
    """
    is_tase = ticker.upper().endswith(".TA")

    if is_tase:
        priority = ["ibkr", "plus500", "etoro"]
    else:
        priority = ["ibkr", "etoro", "moomoo", "trading212", "plus500"]

    result = []
    for key in priority:
        broker = BROKERS[key].copy()
        broker["id"] = key
        # בדוק שהברוקר תומך בשוק
        market = "TASE" if is_tase else "US"
        if market in broker["markets"] or "global" in broker["markets"]:
            result.append(broker)

    return result[:3]  # החזר עד 3 ברוקרים


def get_affiliate_link(broker_id: str, ticker: str = "", source: str = "app") -> str:
    """מחזיר tracked affiliate URL."""
    broker = BROKERS.get(broker_id)
    if not broker:
        return ""
    base_url = broker["affiliate_url"]
    # הוסף UTM parameters לmeasurement
    return f"{base_url}?utm_source=tradeiq&utm_medium={source}&utm_content={ticker or 'general'}"


# ─── Click Tracking ───────────────────────────────────────────────────────────

def _load_db() -> dict:
    if not os.path.exists(AFFILIATE_DB):
        return {"clicks": [], "conversions": [], "revenue": [], "total_clicks": 0,
                "total_conversions": 0, "total_revenue_usd": 0}
    with open(AFFILIATE_DB, encoding="utf-8") as f:
        return json.load(f)


def _save_db(data: dict) -> None:
    os.makedirs(DATA_PATH, exist_ok=True)
    with open(AFFILIATE_DB, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def track_click(broker_id: str, ticker: str = "", source: str = "app") -> str:
    """רושם קליק ומחזיר את ה-affiliate URL."""
    db = _load_db()
    db["clicks"].append({
        "broker": broker_id,
        "ticker": ticker,
        "source": source,
        "timestamp": datetime.now().isoformat(),
    })
    db["total_clicks"] += 1
    _save_db(db)
    return get_affiliate_link(broker_id, ticker, source)


def track_conversion(broker_id: str, commission_usd: float = None) -> None:
    """רושם המרה (חשבון ממומן) כשהברוקר מדווח."""
    db = _load_db()
    commission = commission_usd or BROKERS.get(broker_id, {}).get("commission_usd", 0)
    db["conversions"].append({
        "broker": broker_id,
        "commission_usd": commission,
        "timestamp": datetime.now().isoformat(),
    })
    db["total_conversions"] += 1
    db["total_revenue_usd"] += commission
    _save_db(db)


# ─── Revenue Report ───────────────────────────────────────────────────────────

def get_affiliate_report() -> dict:
    """מחזיר דוח הכנסות affiliates."""
    db = _load_db()

    # פירוט לפי ברוקר
    by_broker = {}
    for click in db.get("clicks", []):
        bid = click["broker"]
        by_broker.setdefault(bid, {"clicks": 0, "conversions": 0, "revenue": 0})
        by_broker[bid]["clicks"] += 1

    for conv in db.get("conversions", []):
        bid = conv["broker"]
        by_broker.setdefault(bid, {"clicks": 0, "conversions": 0, "revenue": 0})
        by_broker[bid]["conversions"] += 1
        by_broker[bid]["revenue"] += conv["commission_usd"]

    # חישוב CTR ו-CVR
    for bid, data in by_broker.items():
        clicks = data["clicks"] or 1
        data["cvr"] = round(data["conversions"] / clicks, 3)
        data["epc"] = round(data["revenue"] / clicks, 2)  # earnings per click

    return {
        "timestamp": datetime.now().isoformat(),
        "total_clicks": db["total_clicks"],
        "total_conversions": db["total_conversions"],
        "total_revenue_usd": db["total_revenue_usd"],
        "by_broker": by_broker,
        "potential_monthly_usd": _estimate_monthly_revenue(),
    }


def _estimate_monthly_revenue() -> dict:
    """מעריך הכנסות חודשיות לפי תחזיות מציאותיות."""
    scenarios = {
        "conservative": {"monthly_users": 500,  "ctr": 0.05, "cvr": 0.02, "avg_cpa": 150},
        "realistic":    {"monthly_users": 2000, "ctr": 0.08, "cvr": 0.03, "avg_cpa": 180},
        "optimistic":   {"monthly_users": 5000, "ctr": 0.10, "cvr": 0.04, "avg_cpa": 200},
    }
    result = {}
    for name, s in scenarios.items():
        clicks = s["monthly_users"] * s["ctr"]
        conversions = clicks * s["cvr"]
        revenue = conversions * s["avg_cpa"]
        result[name] = {
            "monthly_users": s["monthly_users"],
            "affiliate_clicks": int(clicks),
            "conversions": int(conversions),
            "affiliate_revenue_usd": int(revenue),
        }
    return result


def format_affiliate_report(report: dict) -> str:
    lines = [
        "=== דוח Affiliates ===",
        f"תאריך: {report['timestamp'][:10]}",
        f"קליקים: {report['total_clicks']} | המרות: {report['total_conversions']} | הכנסה: ${report['total_revenue_usd']:,.0f}",
        "",
        "--- תחזית הכנסות חודשיות ---",
    ]
    for name, data in report["potential_monthly_usd"].items():
        lines.append(
            f"  {name:12}: {data['monthly_users']:,} users → "
            f"{data['affiliate_clicks']} clicks → "
            f"${data['affiliate_revenue_usd']:,}/mo"
        )
    if report["by_broker"]:
        lines.append("\n--- לפי ברוקר ---")
        for bid, data in report["by_broker"].items():
            name = BROKERS.get(bid, {}).get("name", bid)
            lines.append(f"  {name}: {data['clicks']} clicks | CVR {data['cvr']:.1%} | ${data['revenue']:,.0f}")
    return "\n".join(lines)


if __name__ == "__main__":
    print("=== ברוקרים מומלצים ל-AAPL ===")
    for b in get_brokers_for_ticker("AAPL"):
        print(f"  {b['logo']} {b['name']} [{b['badge']}] — ${b['commission_usd']} CPA")

    print("\n=== ברוקרים מומלצים ל-TEVA.TA ===")
    for b in get_brokers_for_ticker("TEVA.TA"):
        print(f"  {b['logo']} {b['name']} [{b['badge']}] — ${b['commission_usd']} CPA")

    print("\n" + format_affiliate_report(get_affiliate_report()))
