"""
sentiment_scorer.py — חישוב ציוני סנטימנט -1 עד +1
כל ה-sub-agents חייבים להשתמש בפונקציות אלו בלבד
"""
import re

# NLTK VADER — ניתוח סנטימנט בסיסי
try:
    import nltk
    from nltk.sentiment.vader import SentimentIntensityAnalyzer
    try:
        nltk.data.find("sentiment/vader_lexicon.zip")
    except LookupError:
        nltk.download("vader_lexicon", quiet=True)
    _vader = SentimentIntensityAnalyzer()
    VADER_AVAILABLE = True
except ImportError:
    VADER_AVAILABLE = False

# מילות מפתח פיננסיות לחיזוק הציון
BULLISH_KEYWORDS = [
    "beat", "beats", "record", "surge", "soar", "rally", "upgrade",
    "buy", "outperform", "bullish", "profit", "growth", "strong",
    "positive", "gain", "rise", "jumped", "exceeded", "above",
    "breakout", "מעל הציפיות", "עלייה", "רווח", "צמיחה",
]
BEARISH_KEYWORDS = [
    "miss", "misses", "fall", "drop", "decline", "downgrade",
    "sell", "underperform", "bearish", "loss", "weak", "negative",
    "concern", "risk", "crash", "below", "cut", "layoff", "warning",
    "investigation", "lawsuit", "חלשה", "ירידה", "הפסד", "אזהרה",
]


def score_headline(text: str) -> float:
    """
    ציון כותרת חדשות: -1.0 (שלילי מאוד) עד +1.0 (חיובי מאוד).
    משלב VADER + מילות מפתח פיננסיות.
    """
    text_lower = text.lower()

    # VADER base score
    if VADER_AVAILABLE:
        scores = _vader.polarity_scores(text)
        base_score = scores["compound"]  # -1 to 1
    else:
        base_score = 0.0

    # keyword boost
    bullish_hits = sum(1 for kw in BULLISH_KEYWORDS if kw in text_lower)
    bearish_hits = sum(1 for kw in BEARISH_KEYWORDS if kw in text_lower)
    keyword_boost = (bullish_hits - bearish_hits) * 0.15

    raw = base_score + keyword_boost
    return round(max(-1.0, min(1.0, raw)), 3)


def aggregate_scores(scores: list, weights: list = None) -> float:
    """
    ממוצע משוקלל של רשימת ציונים.
    אם אין weights — ממוצע פשוט.
    """
    if not scores:
        return 0.0
    if weights is None:
        weights = [1.0] * len(scores)
    if len(weights) != len(scores):
        weights = [1.0] * len(scores)
    total_weight = sum(weights)
    if total_weight == 0:
        return 0.0
    weighted_sum = sum(s * w for s, w in zip(scores, weights))
    return round(weighted_sum / total_weight, 3)


def combine_signals(news_score: float, social_score: float,
                    news_weight: float = 0.6, social_weight: float = 0.4) -> dict:
    """
    משלב ציון חדשות + ציון חברתי לסיגנל סופי.
    מחזיר: score, label, color
    """
    score = aggregate_scores(
        [news_score, social_score],
        [news_weight, social_weight]
    )
    if score >= 0.3:
        label, color = "קנייה", "#00C853"
    elif score <= -0.3:
        label, color = "מכירה", "#D50000"
    else:
        label, color = "המתנה", "#FF6F00"
    return {"score": score, "label": label, "color": color}


def score_from_stocktwits(bullish: int, bearish: int) -> float:
    """ממיר % bullish/bearish לציון -1 עד 1."""
    total = bullish + bearish
    if total == 0:
        return 0.0
    net = (bullish - bearish) / total
    return round(net, 3)
