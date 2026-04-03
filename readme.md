# TradeIQ — Stock Decision Support Terminal

> Bloomberg-dark Streamlit dashboard for US (NYSE/NASDAQ) and Israeli (TASE) stocks.
> Live at: **https://stock-calculator.streamlit.app/**

---

## Features (v2.6)

| Feature | Description |
|---|---|
| **Live Price Strip** | Real-time price, change %, Day High/Low, ATR(14), 52-week range bar |
| **Extended Hours** | After-Hours & Pre-Market price shown as main price with label + "Last Close" row |
| **Market Status Badge** | OPEN / PRE-MARKET / AFTER-HOURS / CLOSED with color-coded pill |
| **Volume Strip** | Today volume, 3M avg, 6M avg, % vs average |
| **Price Trends** | 30D / 60D / 90D change percentages |
| **Candlestick Chart** | Plotly chart with SMA-20 overlay + volume subplot, tabs: 5D / 1M / 3M |
| **AI Scan** | News Scout (Marketaux/Finnhub) + Social Pulse (StockTwits/Reddit) + combined sentiment gauge |
| **Trade Calculator** | Entry / Target / Stop → R:R ratio, position size, breakeven price, GO ✅ / NO-GO ❌ |
| **Auto-Stop** | Suggested stop-loss = Entry − 1.5 × ATR(14) |
| **Watchlist** | Persistent sidebar watchlist (JSON), one-click load, live prices, add/remove |
| **Trade Journal** | Save trades, KPI cards (total / GO% / avg R:R / best), filter, delete per entry |
| **Bloomberg Dark UI** | Heebo font, gold/green/red palette, animated GO glow, pulse animation on price |

---

## Quick Start

```bash
# Install
pip install -r requirements.txt

# Run dashboard
streamlit run trade_app.py

# CLI trade calculator
python agents/trade_calculator.py AAPL --entry 255 --target 270 --stop 248
```

---

## Project Structure

```
stock calculator/
├── trade_app.py                    ← Main Streamlit dashboard (1,500+ lines)
├── app.py                          ← Legacy entry point → redirects to trade_app.py
├── agents/
│   ├── news_scout.py               ← Fetches 5 headlines + VADER sentiment scores
│   ├── social_pulse.py             ← StockTwits + ApeWisdom + Reddit sentiment
│   └── trade_calculator.py         ← CLI wrapper + parse_price_from_text + auto_suggest_stop
├── calculators/
│   ├── sentiment_scorer.py         ← score_headline(), aggregate_scores(), combine_signals()
│   ├── technical_calc.py           ← SMA, RSI(14), MACD, ATR(14), add_indicators()
│   └── trade_calc.py               ← evaluate_trade(), calc_atr(), R:R, position size, breakeven
├── data/
│   ├── market_data.py              ← yfinance wrapper: get_current_quote(), get_price_history(),
│   │                                  get_market_status() — timezone-aware US+TASE state machine
│   ├── user_data.py                ← JSON persistence: watchlist + trade journal CRUD
│   ├── watchlist.json              ← Saved watchlist (git-ignored)
│   └── trade_journal.json          ← Saved trades (git-ignored)
├── .streamlit/config.toml          ← Streamlit Cloud config (dark theme, headless)
├── Dockerfile                      ← Docker build (exposes 8501 + 5000)
├── railway.toml                    ← Railway deployment config
├── requirements.txt
└── .env.example                    ← API key template
```

---

## API Keys (`.env`)

```env
MARKETAUX_API_KEY=    # marketaux.com — free, 100 req/day
FINNHUB_API_KEY=      # finnhub.io — free, 60 req/min
REDDIT_CLIENT_ID=     # reddit.com/prefs/apps — free
REDDIT_CLIENT_SECRET= # reddit.com/prefs/apps — free
BRAVE_API_KEY=        # brave.com/search/api — free, 2000/month
TELEGRAM_BOT_TOKEN=   # optional — for daily reports
TELEGRAM_CHAT_ID=     # optional — for daily reports
```

---

## Market Status Logic (`data/market_data.py`)

| State | US Hours (ET) | TASE Hours (IST) |
|---|---|---|
| PRE | 4:00 – 9:30 | — |
| REGULAR | 9:30 – 16:00 | 9:59 – 17:25 (Sun–Thu) |
| POST | 16:00 – 20:00 | — |
| CLOSED | otherwise | otherwise |

**Extended hours price logic:**
- PRE state → show `preMarketPrice`; if none, fall back to `postMarketPrice` (yesterday's after-hours)
- POST / CLOSED state → show `postMarketPrice`
- Prices fetched via `yf.Ticker(ticker).info` when state ≠ REGULAR

---

## Innovation Index (v2.6) — 78/100

| Category | Score | Max |
|---|---|---|
| Live Data | 18 | 20 |
| Charts | 13 | 15 |
| AI Signals | 16 | 20 |
| Trade Tools | 17 | 20 |
| Persistence | 10 | 15 |
| Real-time UX | 4 | 10 |

**Next milestone (83/100 = +6.4%):** RSI badge in data strip, auto-refresh during market hours, CSV export.

---

## Deployment

**Streamlit Cloud** (production): https://stock-calculator.streamlit.app/
- Connect repo → set Main file: `trade_app.py` (or `app.py` which redirects)
- Secrets: add API keys in Streamlit Cloud dashboard under Settings → Secrets

**Docker:**
```bash
docker build -t tradeiq .
docker run -p 8501:8501 tradeiq
```

**Railway:** `railway up` (config in `railway.toml`)

---

## Known Behaviours

- `data/watchlist.json` and `data/trade_journal.json` are git-ignored — start empty on fresh deploy (by design)
- TASE stocks require `.TA` suffix: `TEVA.TA`, `NICE.TA`
- Pre/post market prices from yfinance `.info` — availability depends on broker data feed
