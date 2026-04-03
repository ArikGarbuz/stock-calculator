"""
lead_hunter.py — סוכן ציד לידים
אחריות:
  - סריקת Reddit לאיתור משתמשים שמדברים על trading + כאבים
  - סריקת StockTwits לזיהוי traders פעילים
  - ניקוד וסיווג לידים לפי כוונת רכישה
  - הוספת לידים ל-pipeline
"""

import os
import json
import time
from datetime import datetime

import requests

LEADS_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "sales", "leads.json")
PIPELINE_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "sales", "pipeline.json")

# ─── Keywords שמעידים על כוונת רכישה ────────────────────────────────────────

HIGH_INTENT_KEYWORDS = [
    "looking for", "recommend", "best tool", "what do you use",
    "מחפש כלי", "המלצה", "מה אתם משתמשים", "risk reward", "position size",
    "trade calculator", "stop loss calculator", "מחשבון מסחר",
    "tase", "בורסה ישראלית", "מניות ישראל",
]

PAIN_KEYWORDS = [
    "tradingview expensive", "tradingview too expensive", "tradingview price",
    "can't afford", "free alternative", "alternative to tradingview",
    "יקר מדי", "אלטרנטיבה", "בלי תשלום", "חינם",
    "r:r calculation", "risk management tool", "position sizing",
]

TARGET_SUBREDDITS = [
    "stocks", "investing", "algotrading", "Daytrading",
    "IsraeliFinance", "wallstreetbets",
]


# ─── Reddit Scraper ───────────────────────────────────────────────────────────

def _search_reddit_posts(subreddit: str, query: str, limit: int = 10) -> list:
    """מחפש פוסטים ב-Reddit דרך API ציבורי (ללא מפתח)."""
    url = f"https://www.reddit.com/r/{subreddit}/search.json"
    headers = {"User-Agent": "StockCalc-LeadHunter/1.0"}
    params = {"q": query, "sort": "new", "limit": limit, "restrict_sr": "true"}
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        resp.raise_for_status()
        posts = []
        for item in resp.json().get("data", {}).get("children", []):
            d = item.get("data", {})
            posts.append({
                "id": d.get("id"),
                "title": d.get("title", ""),
                "selftext": d.get("selftext", "")[:300],
                "author": d.get("author"),
                "subreddit": subreddit,
                "url": f"https://reddit.com{d.get('permalink', '')}",
                "score": d.get("score", 0),
                "created_utc": d.get("created_utc"),
                "num_comments": d.get("num_comments", 0),
            })
        return posts
    except Exception:
        return []


def _score_lead(post: dict) -> float:
    """
    מחשב ציון כוונת רכישה 0–1 לפי:
    - מילות מפתח high-intent
    - כאב שמוזכר
    - engagement (score + comments)
    """
    text = (post.get("title", "") + " " + post.get("selftext", "")).lower()
    score = 0.0

    # מילות מפתח high-intent
    for kw in HIGH_INTENT_KEYWORDS:
        if kw.lower() in text:
            score += 0.25

    # כאב
    for kw in PAIN_KEYWORDS:
        if kw.lower() in text:
            score += 0.20

    # engagement bonus
    if post.get("score", 0) > 10:
        score += 0.10
    if post.get("num_comments", 0) > 5:
        score += 0.10

    return min(round(score, 2), 1.0)


# ─── StockTwits Scraper ───────────────────────────────────────────────────────

def _search_stocktwits(symbol: str = "SPY", limit: int = 20) -> list:
    """מחפש ב-StockTwits משתמשים שדנים ב-symbol."""
    url = f"https://api.stocktwits.com/api/2/streams/symbol/{symbol}.json"
    params = {"limit": limit}
    try:
        resp = requests.get(url, params=params, timeout=8)
        resp.raise_for_status()
        messages = resp.json().get("messages", [])
        leads = []
        for msg in messages:
            user = msg.get("user", {})
            leads.append({
                "username": user.get("username"),
                "followers": user.get("followers", 0),
                "following": user.get("following", 0),
                "posts": user.get("ideas", 0),
                "text": msg.get("body", "")[:200],
                "source": "stocktwits",
                "symbol": symbol,
                "created_at": msg.get("created_at"),
            })
        return leads
    except Exception:
        return []


# ─── Lead Management ──────────────────────────────────────────────────────────

def _load_leads() -> dict:
    with open(LEADS_PATH, encoding="utf-8") as f:
        return json.load(f)


def _save_leads(data: dict) -> None:
    data["last_updated"] = datetime.now().isoformat()
    with open(LEADS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _load_pipeline() -> dict:
    with open(PIPELINE_PATH, encoding="utf-8") as f:
        return json.load(f)


def _save_pipeline(data: dict) -> None:
    data["last_updated"] = datetime.now().isoformat()
    with open(PIPELINE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _add_to_pipeline(lead: dict) -> None:
    """מוסיף ליד ל-prospect stage בפייפליין."""
    pipeline = _load_pipeline()
    existing_ids = [p.get("id") for p in pipeline["stages"]["prospect"]]
    if lead.get("id") not in existing_ids:
        pipeline["stages"]["prospect"].append({
            "id": lead.get("id") or lead.get("username"),
            "source": lead.get("source", "reddit"),
            "contact": lead.get("url") or f"https://stocktwits.com/{lead.get('username')}",
            "intent_score": lead.get("intent_score", 0),
            "title": lead.get("title") or lead.get("text", "")[:80],
            "added_at": datetime.now().isoformat(),
            "status": "new",
            "notes": "",
        })
        pipeline["stats"]["total_prospects"] = len(pipeline["stages"]["prospect"])
        _save_pipeline(pipeline)


# ─── Main Hunt ────────────────────────────────────────────────────────────────

def hunt_leads(max_per_source: int = 5) -> dict:
    """
    מריץ ציד לידים מלא.
    מחזיר סיכום: כמה נמצאו, כמה high-intent, כמה נוספו ל-pipeline.
    """
    leads_data = _load_leads()
    found_reddit = []
    found_stocktwits = []

    # Reddit — סריקת subreddits עם query חיפוש
    queries = ["risk reward calculator", "trade calculator free", "תמחור מסחר", "position size tool"]
    for sub in TARGET_SUBREDDITS[:3]:  # מוגבל ל-3 כדי לא לקבל rate-limit
        for q in queries[:2]:
            posts = _search_reddit_posts(sub, q, limit=5)
            for post in posts:
                post["intent_score"] = _score_lead(post)
                post["source"] = "reddit"
                found_reddit.append(post)
            time.sleep(1)  # polite delay

    # StockTwits — סריקת סמלים פופולריים
    for symbol in ["SPY", "AAPL", "TEVA"]:
        msgs = _search_stocktwits(symbol, limit=10)
        for msg in msgs:
            msg["intent_score"] = 0.3  # ציון בסיסי — לא ניתן לנתח כוונה טוב מ-StockTwits
            found_stocktwits.append(msg)

    # שמור leads
    all_new = found_reddit + found_stocktwits
    existing_ids = {l.get("id") or l.get("username") for l in leads_data["leads"]}
    added = 0
    high_intent = []

    for lead in all_new:
        lead_id = lead.get("id") or lead.get("username")
        if lead_id and lead_id not in existing_ids:
            leads_data["leads"].append(lead)
            leads_data["total_found"] += 1
            existing_ids.add(lead_id)
            added += 1

            if lead.get("intent_score", 0) >= 0.5:
                high_intent.append(lead)
                _add_to_pipeline(lead)

    leads_data["sources"]["reddit"] += len(found_reddit)
    leads_data["sources"]["stocktwits"] += len(found_stocktwits)
    _save_leads(leads_data)

    return {
        "timestamp": datetime.now().isoformat(),
        "total_scanned": len(all_new),
        "new_leads_added": added,
        "high_intent_leads": len(high_intent),
        "added_to_pipeline": len(high_intent),
        "top_leads": sorted(high_intent, key=lambda x: x.get("intent_score", 0), reverse=True)[:3],
    }


def format_hunt_report(result: dict) -> str:
    lines = [
        "=== דוח ציד לידים ===",
        f"תאריך: {result['timestamp'][:10]}",
        f"נסרקו: {result['total_scanned']} פוסטים/הודעות",
        f"לידים חדשים: {result['new_leads_added']}",
        f"High-intent (>0.5): {result['high_intent_leads']}",
        f"נוספו ל-pipeline: {result['added_to_pipeline']}",
    ]
    if result["top_leads"]:
        lines.append("\nלידים מובילים:")
        for lead in result["top_leads"]:
            title = lead.get("title") or lead.get("text", "")[:60]
            lines.append(f"  [{lead['intent_score']:.2f}] {title}")
    return "\n".join(lines)


if __name__ == "__main__":
    result = hunt_leads()
    print(format_hunt_report(result))
