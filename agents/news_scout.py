"""
news_scout.py — News Scout Agent
מוצא 5 כותרות חדשות עדכניות למניה ומדרג אותן -1 עד +1
מקורות: Marketaux API (ראשי) + Finnhub (גיבוי)
"""
import os
import sys
import requests
from dotenv import load_dotenv
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from calculators.sentiment_scorer import score_headline, aggregate_scores

load_dotenv()

MARKETAUX_KEY = os.getenv("MARKETAUX_API_KEY", "")
FINNHUB_KEY = os.getenv("FINNHUB_API_KEY", "")


def _fetch_marketaux(ticker: str, limit: int = 5) -> list:
    """מושך חדשות מ-Marketaux עם ציון סנטימנט."""
    if not MARKETAUX_KEY:
        return []
    # הסרת סיומת .TA למניות ישראליות (Marketaux לא תומך בה)
    clean_ticker = ticker.replace(".TA", "").replace(".ta", "")
    url = "https://api.marketaux.com/v1/news/all"
    params = {
        "symbols": clean_ticker,
        "filter_entities": "true",
        "language": "en",
        "api_token": MARKETAUX_KEY,
        "limit": limit,
    }
    try:
        resp = requests.get(url, params=params, timeout=8)
        resp.raise_for_status()
        data = resp.json()
        results = []
        for item in data.get("data", [])[:limit]:
            title = item.get("title", "")
            # Marketaux מחזיר sentiment מובנה
            entities = item.get("entities", [])
            built_in_score = None
            for e in entities:
                if e.get("symbol", "").upper() == clean_ticker.upper():
                    built_in_score = e.get("sentiment_score")
                    break
            score = float(built_in_score) if built_in_score is not None else score_headline(title)
            score = round(max(-1.0, min(1.0, score)), 3)
            results.append({
                "title": title,
                "source": item.get("source", "Marketaux"),
                "url": item.get("url", ""),
                "published_at": item.get("published_at", ""),
                "score": score,
            })
        return results
    except Exception:
        return []


def _fetch_finnhub(ticker: str, limit: int = 5) -> list:
    """מושך חדשות מ-Finnhub כגיבוי."""
    if not FINNHUB_KEY:
        return []
    clean_ticker = ticker.replace(".TA", "").replace(".ta", "")
    url = "https://finnhub.io/api/v1/company-news"
    from datetime import date, timedelta
    today = date.today().isoformat()
    week_ago = (date.today() - timedelta(days=7)).isoformat()
    params = {
        "symbol": clean_ticker,
        "from": week_ago,
        "to": today,
        "token": FINNHUB_KEY,
    }
    try:
        resp = requests.get(url, params=params, timeout=8)
        resp.raise_for_status()
        items = resp.json()[:limit]
        results = []
        for item in items:
            title = item.get("headline", "")
            score = score_headline(title)
            results.append({
                "title": title,
                "source": item.get("source", "Finnhub"),
                "url": item.get("url", ""),
                "published_at": str(item.get("datetime", "")),
                "score": score,
            })
        return results
    except Exception:
        return []


def get_news(ticker: str) -> dict:
    """
    מחזיר 5 כותרות עדכניות עם ציוני סנטימנט.
    ממשק ראשי של ה-News Scout Agent.
    """
    headlines = _fetch_marketaux(ticker, limit=5)
    if len(headlines) < 3:
        fallback = _fetch_finnhub(ticker, limit=5)
        headlines = (headlines + fallback)[:5]

    if not headlines:
        return {
            "ticker": ticker,
            "headlines": [],
            "aggregate_score": 0.0,
            "error": "לא נמצאו חדשות. בדוק את מפתחות ה-API ב-.env",
        }

    scores = [h["score"] for h in headlines]
    agg = aggregate_scores(scores)

    return {
        "ticker": ticker,
        "headlines": headlines,
        "aggregate_score": agg,
        "count": len(headlines),
    }


if __name__ == "__main__":
    import json
    ticker = sys.argv[1] if len(sys.argv) > 1 else "AAPL"
    result = get_news(ticker)
    print(json.dumps(result, ensure_ascii=False, indent=2))
