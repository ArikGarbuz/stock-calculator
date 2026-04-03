"""
content_marketer.py — סוכן שיווק תוכן
אחריות:
  - יצירת פוסטים שיווקיים ל-Reddit, Twitter/X, LinkedIn
  - התאמת תוכן לפי אירועי שוק נוכחיים (news hooks)
  - ניהול calendar תוכן שבועי
  - A/B testing על הודעות
"""

import os
import json
import random
from datetime import datetime, timedelta

CONTENT_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "sales")


# ─── Templates ────────────────────────────────────────────────────────────────

REDDIT_TEMPLATES = [
    {
        "id": "pain_point_rr",
        "subreddit": "Daytrading",
        "title": "I built a free R:R + position size calculator that also supports TASE (Israeli stocks)",
        "body": (
            "Hey r/Daytrading,\n\n"
            "I've been frustrated with having to use 3 different tools before each trade "
            "(TradingView for charts, a spreadsheet for R:R, and another for position sizing). "
            "So I built a single dashboard that does it all:\n\n"
            "- **Trade Calculator**: enter entry/target/stop → instant GO/NO-GO with R:R\n"
            "- **News Scout**: 5 latest headlines with sentiment score (-1 to +1)\n"
            "- **Social Pulse**: StockTwits + Reddit bullish/bearish %\n"
            "- Supports both NYSE/NASDAQ and **TASE** (Israeli market) 🇮🇱\n\n"
            "It's free during beta. Would love feedback from actual traders.\n\n"
            "Link in profile. What do you think — what would you add?"
        ),
        "type": "soft_sell",
    },
    {
        "id": "value_post_tase",
        "subreddit": "IsraeliFinance",
        "title": "כלי חינמי למחשבון עסקה עם תמיכה ב-TASE + מס ישראלי",
        "body": (
            "שלום לכולם,\n\n"
            "בניתי כלי שמטרתו לפשט את הכניסה לעסקה:\n\n"
            "**מחשבון עסקה (Trade Calculator)**\n"
            "- הכנס מחיר כניסה, יעד, סטופ → מקבל R:R + גודל פוזיציה + breakeven\n"
            "- כולל חישוב עמלות + מס 25% + מס יסף\n"
            "- GO/NO-GO אוטומטי (R:R >= 2 = GO ✅)\n\n"
            "**סנטימנט חדשות ורשתות**\n"
            "- 5 כותרות עדכניות עם ציון רגש\n"
            "- StockTwits + Reddit bullish/bearish %\n\n"
            "תומך ב-TASE (סיומת .TA) וב-NYSE/NASDAQ.\n\n"
            "חינם בבטא. מה היה עוזר לכם?"
        ),
        "type": "soft_sell",
    },
    {
        "id": "educational_rr",
        "subreddit": "stocks",
        "title": "Why most retail traders lose: they skip R:R calculation (+ a free tool to fix that)",
        "body": (
            "Studies show 70%+ of retail traders don't calculate Risk:Reward before entering a trade.\n\n"
            "**The math is simple:**\n"
            "- Entry: $100, Target: $106, Stop: $98\n"
            "- R:R = (106-100)/(100-98) = 3:1 ✅\n\n"
            "But most traders skip this because it's \"annoying\" to calculate manually. "
            "I made a tool that does it automatically + suggests position size based on your risk %.\n\n"
            "It also pulls in news sentiment so you know if the market agrees with your thesis.\n\n"
            "Happy to share if there's interest. What's your pre-trade checklist?"
        ),
        "type": "educational",
    },
]

TWITTER_TEMPLATES = [
    {
        "id": "tw_quick_hook",
        "text": (
            "Most traders use 3+ tools before each trade.\n\n"
            "I combined them into one:\n"
            "✅ R:R calculator\n"
            "✅ Position sizer\n"
            "✅ News sentiment\n"
            "✅ Social pulse\n\n"
            "Works for NYSE, NASDAQ + Israeli stocks (TASE)\n\n"
            "Free during beta 👇"
        ),
        "type": "product",
    },
    {
        "id": "tw_tip_rr",
        "text": (
            "Trading tip: if your R:R is below 2:1, skip the trade.\n\n"
            "A quick formula:\n"
            "(Target - Entry) / (Entry - Stop) ≥ 2.0\n\n"
            "This single rule alone will cut your losing trades in half.\n\n"
            "I built a calculator that checks this automatically ↓"
        ),
        "type": "educational",
    },
    {
        "id": "tw_tase_hook",
        "text": (
            "יש כלי מסחר שתומך ב-TASE?\n\n"
            "בניתי אחד:\n"
            "📊 מחשבון R:R עם חישוב מס ישראלי\n"
            "📰 חדשות + סנטימנט\n"
            "📈 תמיכה ב-TEVA.TA, NICE.TA ועוד\n\n"
            "חינם בבטא. לינק בפרופיל."
        ),
        "type": "product_he",
    },
]

LINKEDIN_TEMPLATES = [
    {
        "id": "li_story",
        "text": (
            "I spent 6 months watching retail traders make the same mistake:\n\n"
            "They'd spend 2 hours researching a stock, then enter the trade without calculating R:R.\n\n"
            "So I built a tool to solve this.\n\n"
            "It combines:\n"
            "→ Real-time news sentiment analysis\n"
            "→ Social media pulse (StockTwits + Reddit)\n"
            "→ Trade calculator with automatic GO/NO-GO\n"
            "→ Support for both US and Israeli (TASE) markets\n\n"
            "The result: traders who use it consistently trade with ≥ 2:1 R:R.\n\n"
            "Still in beta — would love feedback from anyone in trading or fintech.\n\n"
            "#trading #fintech #stocks #riskmanagement"
        ),
        "type": "thought_leadership",
    },
]


# ─── Content Calendar ─────────────────────────────────────────────────────────

def generate_weekly_calendar() -> list:
    """מייצר לוח תוכן שבועי."""
    today = datetime.now()
    calendar = []

    schedule = [
        {"day_offset": 0, "platform": "Reddit", "template": REDDIT_TEMPLATES[0]},
        {"day_offset": 1, "platform": "Twitter", "template": TWITTER_TEMPLATES[1]},
        {"day_offset": 2, "platform": "Twitter", "template": TWITTER_TEMPLATES[0]},
        {"day_offset": 3, "platform": "Reddit", "template": REDDIT_TEMPLATES[1]},
        {"day_offset": 4, "platform": "LinkedIn", "template": LINKEDIN_TEMPLATES[0]},
        {"day_offset": 5, "platform": "Reddit", "template": REDDIT_TEMPLATES[2]},
        {"day_offset": 6, "platform": "Twitter", "template": TWITTER_TEMPLATES[2]},
    ]

    for item in schedule:
        post_date = today + timedelta(days=item["day_offset"])
        calendar.append({
            "date": post_date.strftime("%Y-%m-%d"),
            "platform": item["platform"],
            "template_id": item["template"]["id"],
            "type": item["template"]["type"],
            "preview": (item["template"].get("title") or item["template"].get("text", ""))[:80] + "...",
            "status": "scheduled",
        })

    return calendar


def get_content_for_platform(platform: str, content_type: str = None) -> dict:
    """מחזיר תוכן מוכן לפלטפורמה."""
    if platform.lower() == "reddit":
        pool = REDDIT_TEMPLATES
    elif platform.lower() in ("twitter", "x"):
        pool = TWITTER_TEMPLATES
    elif platform.lower() == "linkedin":
        pool = LINKEDIN_TEMPLATES
    else:
        return {"error": f"פלטפורמה לא מוכרת: {platform}"}

    if content_type:
        pool = [t for t in pool if t.get("type") == content_type] or pool

    template = random.choice(pool)
    return {
        "platform": platform,
        "timestamp": datetime.now().isoformat(),
        **template,
    }


def generate_news_hook(headline: str, ticker: str) -> str:
    """
    מייצר פוסט שמשתמש בכותרת חדשות כ-hook.
    משמש כשה-News Scout מוצא חדשות חמות.
    """
    return (
        f"📰 {headline}\n\n"
        f"Before you trade ${ticker} on this news — did you calculate your R:R?\n\n"
        f"Use the trade calculator → enter entry, target, stop → get GO/NO-GO in seconds.\n\n"
        f"Link in bio. #trading #{ticker} #stockmarket"
    )


def format_calendar(calendar: list) -> str:
    lines = ["=== לוח תוכן שבועי ==="]
    for item in calendar:
        lines.append(f"{item['date']} | {item['platform']:10} | {item['type']:20} | {item['preview']}")
    return "\n".join(lines)


if __name__ == "__main__":
    print(format_calendar(generate_weekly_calendar()))
    print("\n--- דוגמה לפוסט Reddit ---")
    content = get_content_for_platform("Reddit", "soft_sell")
    print(f"Title: {content.get('title', '')}")
    print(f"Body preview: {content.get('body', '')[:200]}...")
