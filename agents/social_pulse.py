"""
social_pulse.py — Social Pulse Agent
מדד סנטימנט משקיעים קמעונאיים: StockTwits + ApeWisdom + Reddit
"""
import os
import sys
import requests
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from calculators.sentiment_scorer import aggregate_scores, score_headline, score_from_stocktwits

load_dotenv()

REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID", "")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET", "")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT", "StockAgent/1.0")


def _fetch_stocktwits(ticker: str) -> dict:
    """
    StockTwits — ניסיון ישיר, עם fallback ל-Finnhub Social Sentiment.
    StockTwits חסם גישה ישירה (Cloudflare), אז Finnhub משמש כגיבוי.
    """
    clean = ticker.replace(".TA", "").replace(".ta", "")

    # ניסיון ב-StockTwits
    try:
        url = f"https://api.stocktwits.com/api/2/streams/symbol/{clean}.json"
        resp = requests.get(url, timeout=6, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        if resp.status_code == 200:
            data = resp.json()
            messages = data.get("messages", [])
            bullish = sum(1 for m in messages if (m.get("entities") or {}).get("sentiment", {}) and m["entities"]["sentiment"].get("basic") == "Bullish")
            bearish = sum(1 for m in messages if (m.get("entities") or {}).get("sentiment", {}) and m["entities"]["sentiment"].get("basic") == "Bearish")
            total = len(messages)
            score = score_from_stocktwits(bullish, bearish)
            return {"available": True, "source": "stocktwits", "bullish": bullish, "bearish": bearish, "total_messages": total, "score": score}
    except Exception:
        pass

    # Fallback: Finnhub Social Sentiment
    finnhub_key = os.getenv("FINNHUB_API_KEY", "")
    if finnhub_key:
        try:
            url = f"https://finnhub.io/api/v1/stock/social-sentiment?symbol={clean}&token={finnhub_key}"
            resp = requests.get(url, timeout=6)
            if resp.status_code == 200:
                data = resp.json()
                reddit_data = data.get("reddit", [])
                twitter_data = data.get("twitter", [])
                all_mentions = reddit_data + twitter_data
                if all_mentions:
                    avg_score = sum(m.get("score", 0) for m in all_mentions) / len(all_mentions)
                    # Finnhub score is 0-1, convert to -1 to 1
                    norm_score = (avg_score - 0.5) * 2
                    return {
                        "available": True, "source": "finnhub",
                        "mentions": len(all_mentions),
                        "score": round(norm_score, 3),
                        "total_messages": len(all_mentions),
                        "bullish": sum(1 for m in all_mentions if m.get("score", 0.5) > 0.5),
                        "bearish": sum(1 for m in all_mentions if m.get("score", 0.5) <= 0.5),
                    }
        except Exception:
            pass

    return {"available": False, "reason": "StockTwits ו-Finnhub לא זמינים"}


def _fetch_apewisdom(ticker: str) -> dict:
    """ApeWisdom — trending stocks on Reddit/4chan, ללא key."""
    clean = ticker.replace(".TA", "").replace(".ta", "")
    url = "https://apewisdom.io/api/v1.0/filter/all-stocks/"
    try:
        resp = requests.get(url, timeout=8)
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results", [])
        for item in results:
            if item.get("ticker", "").upper() == clean.upper():
                mentions = item.get("mentions", 0)
                mentions_24h = item.get("mentions_24h", 0)
                rank = item.get("rank", 999)
                # rank 1-10 = very bullish signal, 11-50 = moderate, >50 = low interest
                if rank <= 10:
                    score = 0.5
                elif rank <= 30:
                    score = 0.2
                else:
                    score = 0.0
                return {
                    "available": True,
                    "rank": rank,
                    "mentions": mentions,
                    "mentions_24h": mentions_24h,
                    "score": score,
                }
        return {"available": True, "rank": None, "mentions": 0, "mentions_24h": 0, "score": 0.0}
    except Exception:
        return {"available": False}


def _fetch_reddit(ticker: str) -> dict:
    """Reddit PRAW — מנתח פוסטים ב-r/wallstreetbets, r/stocks, r/investing."""
    if not REDDIT_CLIENT_ID or not REDDIT_CLIENT_SECRET:
        return {"available": False, "reason": "Reddit credentials חסרים ב-.env"}
    try:
        import praw
        clean = ticker.replace(".TA", "").replace(".ta", "")
        reddit = praw.Reddit(
            client_id=REDDIT_CLIENT_ID,
            client_secret=REDDIT_CLIENT_SECRET,
            user_agent=REDDIT_USER_AGENT,
        )
        subreddits = ["wallstreetbets", "stocks", "investing"]
        posts = []
        for sub in subreddits:
            for post in reddit.subreddit(sub).search(clean, limit=10, time_filter="week"):
                posts.append(post.title + " " + (post.selftext[:200] if post.selftext else ""))

        if not posts:
            return {"available": True, "mentions": 0, "score": 0.0}

        scores = [score_headline(p) for p in posts]
        avg = aggregate_scores(scores)
        return {
            "available": True,
            "mentions": len(posts),
            "score": avg,
            "subreddits": subreddits,
        }
    except Exception as e:
        return {"available": False, "reason": str(e)}


def get_social_pulse(ticker: str) -> dict:
    """
    ממשק ראשי של Social Pulse Agent.
    מחזיר סנטימנט מאוחד מכל המקורות.
    """
    st = _fetch_stocktwits(ticker)
    ape = _fetch_apewisdom(ticker)
    reddit = _fetch_reddit(ticker)

    scores = []
    weights = []

    if st.get("available") and st.get("total_messages", 0) > 0:
        scores.append(st["score"])
        weights.append(2.0)  # StockTwits — ציון אמין יחסית

    if ape.get("available") and ape.get("mentions_24h", 0) > 0:
        scores.append(ape["score"])
        weights.append(1.0)

    if reddit.get("available") and reddit.get("mentions", 0) > 0:
        scores.append(reddit["score"])
        weights.append(1.5)

    aggregate = aggregate_scores(scores, weights) if scores else 0.0

    return {
        "ticker": ticker,
        "stocktwits": st,
        "apewisdom": ape,
        "reddit": reddit,
        "aggregate_score": aggregate,
        "sources_active": sum([
            st.get("available", False),
            ape.get("available", False),
            reddit.get("available", False),
        ]),
    }


if __name__ == "__main__":
    import json
    ticker = sys.argv[1] if len(sys.argv) > 1 else "AAPL"
    result = get_social_pulse(ticker)
    print(json.dumps(result, ensure_ascii=False, indent=2))
