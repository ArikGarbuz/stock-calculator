# Stock Decision Support Agent

## תיאור הפרויקט
כלי תמיכה בהחלטות מסחר אישי. תומך במניות ארה"ב (NYSE/NASDAQ) ובורסת תל אביב (TASE).
ממשק: Streamlit Dashboard עם כותרות בעברית, dark mode, רענון אוטומטי.

---

## Sub-Agents

### 1. News Scout (סוכן חדשות)
**כלים:** Brave Search MCP + Marketaux API
**קלט:** סמל מניה (למשל: `AAPL` או `TEVA.TA`)
**תפקיד:** מצא 5 כותרות חדשות עדכניות למניה ותן לכל אחת ציון רגש
**פלט:**
```json
{
  "headlines": [
    {"title": "...", "source": "...", "url": "...", "score": 0.7},
    ...
  ],
  "aggregate_score": 0.45
}
```
**ציון:** -1.0 (שלילי מאוד) עד +1.0 (חיובי מאוד)
**חוק:** הציון חייב להיות מחושב דרך `calculators/sentiment_scorer.py::score_headline()`
**לא** לחשב inline בתגובת Claude.

---

### 2. Social Pulse (סוכן סנטימנט חברתי)
**כלים:** StockTwits API (ללא מפתח) + ApeWisdom API (ללא מפתח) + Reddit PRAW
**קלט:** סמל מניה
**תפקיד:** מדוד סנטימנט משקיעים קמעונאיים ברשתות חברתיות
**פלט:**
```json
{
  "stocktwits": {"bullish_pct": 68, "bearish_pct": 32, "messages": 150},
  "reddit": {"mentions": 45, "sentiment": 0.4},
  "apewisdom": {"rank": 12, "mentions_24h": 89},
  "aggregate_score": 0.52
}
```
**חוק:** כל האגרגציה חייבת לעבור `calculators/sentiment_scorer.py::aggregate_scores()`

---

### 3. Trade Calculator (מחשבון עסקה)
**כלים:** `calculators/trade_calc.py` + `data/market_data.py`
**קלט:** ticker, entry, target, stop_loss, risk_amount, portfolio_value, commission, spread_pct
**תפקיד:** חשב כדאיות עסקה — R:R, גודל פוזיציה, breakeven, GO/NO-GO
**פלט:**
```json
{
  "verdict": "GO ✅",
  "rr": {"rr_ratio": 2.14, "formatted": "1 : 2.14"},
  "position": {"shares": 14, "total_cost": 3570},
  "breakeven": {"breakeven_price": 255.82},
  "markdown_table": "| פרמטר | ערך |\n..."
}
```
**כלל GO/NO-GO:** `rr_ratio >= 2.0` → GO ✅, אחרת → NO-GO ❌
**חוק:** כל החישובים חייבים לעבור `calculators/trade_calc.py` בלבד
**CLI:** `python agents/trade_calculator.py AAPL --entry 255 --target 270 --stop 248`

---

## Auto-Trigger Workflow (הפעלה אוטומטית)

לאחר שה-News Scout וה-Social Pulse מסיימים את הסריקה:

1. קרא ל-`combine_signals(news_score, social_score)` מ-`calculators/sentiment_scorer.py`
2. אם `score > 0.2` (סיגנל חיובי) → הצע להפעיל את ה-Trade Calculator
3. חלץ מחיר יעד מכותרות ה-News Scout באמצעות `parse_price_from_text()` מ-`agents/trade_calculator.py`
4. השתמש ב-`get_current_quote(ticker)["price"]` כברירת מחדל לכניסה
5. הצע סטופ אוטומטי: `auto_suggest_stop(entry, atr)` = entry − 1.5 × ATR(14)
6. הפעל: `run_trade_calculator(ticker, entry, target, stop_loss)` מ-`agents/trade_calculator.py`
7. הצג את `result["markdown_table"]` בטאב "🧮 מחשבון עסקה"

**דוגמה לשימוש אוטומטי:**
```python
from agents.trade_calculator import parse_price_from_text, run_trade_calculator, auto_suggest_stop
from calculators.sentiment_scorer import combine_signals
from data.market_data import get_current_quote

signal = combine_signals(news_score, social_score)
if signal["score"] > 0.2:
    entry = get_current_quote(ticker)["price"]
    target = parse_price_from_text(news_headlines[0]["title"])
    stop = auto_suggest_stop(entry, atr)
    if target:
        result = run_trade_calculator(ticker, entry, target, stop)
        print(result["markdown_table"])
```

---

## כללים טכניים

1. **חישובים** — כל חישוב מספרי (ממוצעים, אינדיקטורים, ציונים, עסקאות) → רק דרך Python scripts מקומיים
2. **נתוני שוק** — תמיד דרך `data/market_data.py`, לא ישירות מ-yfinance
3. **מניות ישראליות** — לתוסיף סיומת `.TA` לסמל ב-yfinance (למשל: `TEVA.TA`, `NICE.TA`)
4. **שגיאות** — לטפל תמיד: ticker לא קיים, שוק סגור, timeout של API
5. **שפה** — כותרות, כפתורים, הודעות שגיאה: בעברית

---

## מבנה הפרויקט
```
stock calculator/
├── CLAUDE.md
├── trade_app.py                    ← Streamlit dashboard (ראשי) — wide layout, sidebar watchlist, journal
├── app.py                          ← Streamlit dashboard (ישן)
├── agents/
│   ├── news_scout.py               ← News Scout
│   ├── social_pulse.py             ← Social Pulse
│   ├── trade_calculator.py         ← Trade Calculator Skill
│   ├── sales_manager.py            ← אורקסטרטור מכירות אוטונומי ⭐
│   └── sales/
│       ├── market_researcher.py    ← מחקר שוק, ICP, מתחרים
│       ├── lead_hunter.py          ← ציד לידים Reddit + StockTwits
│       ├── content_marketer.py     ← תוכן שיווקי + לוח שבועי
│       ├── pricing_agent.py        ← תמחור דינמי + A/B tests
│       ├── sales_pipeline.py       ← CRM: Prospect→Lead→Trial→Paying
│       └── growth_analyst.py       ← MRR, LTV, CAC, Churn
├── calculators/
│   ├── sentiment_scorer.py         ← ציונים -1 עד 1
│   ├── technical_calc.py           ← SMA, RSI, MACD
│   └── trade_calc.py               ← R:R, position size, breakeven
├── data/
│   ├── market_data.py              ← yfinance wrapper + get_market_status()
│   ├── user_data.py                ← JSON persistence: watchlist + trade journal
│   ├── watchlist.json              ← רשימת מניות שמורה
│   ├── trade_journal.json          ← יומן עסקאות שמור
│   └── sales/
│       ├── leads.json              ← מאגר לידים
│       ├── pipeline.json           ← CRM pipeline
│       ├── pricing.json            ← תמחור + A/B tests
│       └── metrics.json            ← מדדי צמיחה
├── requirements.txt
└── .env.example
```

## הרצת הדאשבורד הראשי
```bash
streamlit run trade_app.py
```

## גרסה נוכחית: v2.6 (2026-04-03)

## תכונות עיקריות (trade_app.py)
- **Wide layout** — sidebar watchlist + main calculator
- **Watchlist** — שמירה ב-JSON, טעינה חד-קליקית, מחיר חי
- **Trade Journal** — שמירת עסקאות, KPI cards, סינון, מחיקה
- **Market Status** — badge OPEN/PRE-MARKET/AFTER-HOURS/CLOSED + מחיר after-hours
- **Extended Hours Price** — מחיר pre/after-market כמחיר ראשי + "Last Close" כמשני
  - PRE state: אם אין pre-market price → מציג after-hours של אתמול (fallback)
  - POST/CLOSED state: מציג postMarketPrice
- **AI Scan** — News Scout + Social Pulse + sentiment gauge
- **Chart** — candlestick + SMA-20 + volume, tabs 5D/1M/3M
- **GO/NO-GO** — R:R >= 2.0 → GO ✅, עם progress bar ו-glow animation
- **Volume Strip** — volume היום, 3M avg, 6M avg, % vs average
- **Price Trends** — שינוי % ב-30D/60D/90D

## Innovation Index: 78/100
**הבא:** RSI badge (+2), auto-refresh בשוק פתוח (+2), CSV export (+1) → 83/100

## Deployment
- **Streamlit Cloud:** https://stock-calculator.streamlit.app/
- **Entry point:** `trade_app.py` (או `app.py` שמפנה אליו)
- **GitHub:** https://github.com/ArikGarbuz/stock-calculator

## Sales Manager — הפעלה

```bash
# מחזור יומי מלא (מריץ את כל הסוכנים)
python agents/sales_manager.py

# מחזור עם שליחה ב-Telegram
python agents/sales_manager.py --telegram

# סוכן ספציפי
python agents/sales_manager.py --leads      # ציד לידים
python agents/sales_manager.py --pipeline   # דוח CRM
python agents/sales_manager.py --growth     # MRR/ARR/LTV
python agents/sales_manager.py --content    # לוח תוכן
python agents/sales_manager.py --pricing    # ניתוח תמחור
python agents/sales_manager.py --market     # מחקר שוק
```

## משתני סביבה נדרשים (.env)
```
TELEGRAM_BOT_TOKEN=    # לדוחות יומיים
TELEGRAM_CHAT_ID=      # ID של הצ'אט
```

---

## API Keys נדרשים (בקובץ .env)
```
MARKETAUX_API_KEY=    # marketaux.com — חינם, 100 req/day
FINNHUB_API_KEY=      # finnhub.io — חינם, 60 req/min
REDDIT_CLIENT_ID=     # reddit.com/prefs/apps — חינם
REDDIT_CLIENT_SECRET= # reddit.com/prefs/apps — חינם
BRAVE_API_KEY=        # brave.com/search/api — חינם, 2000/month
```

---

## MCP Servers מומלצים (להוסיף ל-Claude Code settings)
```json
{
  "mcpServers": {
    "brave-search": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-brave-search"],
      "env": { "BRAVE_API_KEY": "YOUR_KEY" }
    },
    "fetch": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-fetch"]
    }
  }
}
```
