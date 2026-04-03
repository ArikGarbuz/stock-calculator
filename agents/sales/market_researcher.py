"""
market_researcher.py — סוכן מחקר שוק
אחריות:
  - מיפוי מתחרים ומחיריהם
  - הגדרת ICP (Ideal Customer Profile)
  - זיהוי הזדמנויות שוק
  - המלצות positioning
"""

import json
import os
from datetime import datetime

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "sales", "pricing.json")


# ─── ICP Definition ───────────────────────────────────────────────────────────

ICP_PROFILES = [
    {
        "segment": "Retail Day Trader — ישראלי",
        "description": "סוחר יומי פרטי שפעיל ב-TASE, מחפש כלי מהיר לחישוב R:R לפני כניסה לעסקה",
        "pain_points": [
            "אין כלי עברי שתומך גם ב-TASE וגם בארה\"ב",
            "חישוב מס ישראלי ידני מסובך (25% + מס יסף)",
            "חוסר בסנטימנט-סוציאלי עברי",
        ],
        "channels": ["Reddit r/TASE", "Facebook groups סוחרים", "Telegram קבוצות"],
        "willingness_to_pay_usd": 29,
        "estimated_market_size_il": 12000,
    },
    {
        "segment": "Swing Trader — ארה\"ב",
        "description": "סוחר swing שפעיל ב-NYSE/NASDAQ, מחפש כלי all-in-one שמשלב חדשות + אנליזה",
        "pain_points": [
            "TradingView יקר + אין מחשבון עסקה משולב",
            "צריך לעבור בין כלים שונים",
            "חוסר ב-social sentiment מובנה",
        ],
        "channels": ["Reddit r/stocks", "Reddit r/algotrading", "StockTwits", "Twitter/X #trading"],
        "willingness_to_pay_usd": 29,
        "estimated_market_size_global": 500000,
    },
    {
        "segment": "Algo Trader מתחיל",
        "description": "מפתח שרוצה להאיץ את pipeline ה-research שלו עם API",
        "pain_points": [
            "בניית sentiment scraper מאפס לוקחת זמן",
            "חיבור מקורות נתונים שונים",
        ],
        "channels": ["Reddit r/algotrading", "GitHub", "Hacker News"],
        "willingness_to_pay_usd": 79,
        "estimated_market_size_global": 80000,
    },
]


# ─── Competitor Analysis ──────────────────────────────────────────────────────

def get_competitor_analysis() -> dict:
    """מחזיר ניתוח מתחרים עם positioning."""
    return {
        "competitors": {
            "TradingView": {
                "strengths": ["UI מעולה", "charts מתקדמים", "community גדול"],
                "weaknesses": ["אין מחשבון עסקה", "אין תמיכה ב-TASE", "יקר"],
                "price_range_usd": "14.95–59.95/mo",
                "our_advantage": "תמיכת TASE + מחשבון R:R + מס ישראלי",
            },
            "Finviz": {
                "strengths": ["סריקת מניות מהירה", "מחיר סביר"],
                "weaknesses": ["אין social sentiment", "אין TASE", "אין מחשבון עסקה"],
                "price_range_usd": "0–39.50/mo",
                "our_advantage": "כלי all-in-one + social pulse + TASE",
            },
            "Moomoo": {
                "strengths": ["ברוקר + ניתוח משולב", "חינם"],
                "weaknesses": ["לא זמין בישראל", "אין מחשבון R:R", "ממשק מורכב"],
                "price_range_usd": "0",
                "our_advantage": "שוק ישראלי + פשטות + מחשבון ייעודי",
            },
        },
        "our_positioning": "הכלי הישראלי היחיד שמשלב TASE + ארה\"ב + מחשבון R:R + סנטימנט חברתי",
        "unique_value_props": [
            "תמיכה מלאה ב-TASE (כולל מס יסף)",
            "News + Social Pulse בממשק אחד",
            "Trade Calculator עם GO/NO-GO אוטומטי",
            "עברית",
        ],
    }


def get_market_opportunity() -> dict:
    """מחשב גודל הזדמנות השוק."""
    tam = 592000   # סה"כ retail traders רלוונטיים
    sam = 62000    # ניתן להגיע אליהם בשנה הראשונה
    som_y1 = 500  # יעד ריאלי: 500 משתמשים משלמים שנה 1

    avg_arpu = 35  # USD ממוצע per user per month
    return {
        "TAM": tam,
        "SAM": sam,
        "SOM_year1": som_y1,
        "potential_MRR_y1_usd": som_y1 * avg_arpu,
        "potential_ARR_y1_usd": som_y1 * avg_arpu * 12,
        "icp_profiles": ICP_PROFILES,
    }


def run_market_research() -> dict:
    """מריץ מחקר שוק מלא ומחזיר דוח."""
    competitor_analysis = get_competitor_analysis()
    market_opportunity = get_market_opportunity()

    report = {
        "timestamp": datetime.now().isoformat(),
        "competitor_analysis": competitor_analysis,
        "market_opportunity": market_opportunity,
        "recommended_actions": [
            "התמקד ראשית בסגמנט Retail Day Trader ישראלי — כאב הכי ברור + שוק נגיש",
            "השתמש ב-r/TASE ובקבוצות Facebook ישראליות לרכישת משתמשים ראשונים",
            "תמחר Pro ב-$29 — מתחת ל-TradingView Pro ($14.95) אבל עם ערך גבוה יותר",
            "בנה case study עם 3 traders ישראלים שמשתמשים בכלי — social proof",
        ],
    }

    # שמור לקובץ pricing עם timestamp
    try:
        with open(DATA_PATH) as f:
            pricing = json.load(f)
        pricing["last_updated"] = datetime.now().isoformat()
        with open(DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(pricing, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

    return report


def format_report(report: dict) -> str:
    """מפרמט דוח מחקר שוק לטקסט."""
    lines = [
        "=== דוח מחקר שוק ===",
        f"תאריך: {report['timestamp'][:10]}",
        "",
        "--- הזדמנות שוק ---",
        f"TAM: {report['market_opportunity']['TAM']:,} traders",
        f"SAM: {report['market_opportunity']['SAM']:,} traders",
        f"יעד שנה 1: {report['market_opportunity']['SOM_year1']:,} משתמשים משלמים",
        f"MRR פוטנציאלי שנה 1: ${report['market_opportunity']['potential_MRR_y1_usd']:,}",
        "",
        "--- Positioning ---",
        report['competitor_analysis']['our_positioning'],
        "",
        "--- פעולות מומלצות ---",
    ]
    for i, action in enumerate(report['recommended_actions'], 1):
        lines.append(f"{i}. {action}")
    return "\n".join(lines)


if __name__ == "__main__":
    report = run_market_research()
    print(format_report(report))
