"""
market_data.py — yfinance wrapper לנתוני שוק
תומך במניות ארה"ב (AAPL) ובורסת תל אביב (TEVA.TA)
"""
import yfinance as yf
import pandas as pd
from datetime import datetime, time as dt_time, timedelta
from zoneinfo import ZoneInfo


TASE_SUFFIXES = [".TA", ".ta"]

PERIOD_MAP = {
    "1D": ("1d", "5m"),
    "5D": ("5d", "15m"),
    "1M": ("1mo", "1h"),
    "3M": ("3mo", "1d"),
    "6M": ("6mo", "1d"),
    "1Y": ("1y", "1d"),
    "MAX": ("max", "1wk"),
}


def normalize_ticker(ticker: str) -> str:
    """מוסיף .TA לסמלים ישראליים אם חסר."""
    ticker = ticker.strip().upper()
    return ticker


def get_price_history(ticker: str, period_label: str = "3M") -> pd.DataFrame:
    """
    מחזיר היסטוריית מחירים כ-DataFrame.
    עמודות: Open, High, Low, Close, Volume
    """
    period, interval = PERIOD_MAP.get(period_label, ("3mo", "1d"))
    try:
        df = yf.download(ticker, period=period, interval=interval, progress=False, auto_adjust=True)
        if df.empty:
            raise ValueError(f"לא נמצאו נתונים עבור {ticker}")
        df.index = pd.to_datetime(df.index)
        # Flatten multi-level columns if present
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df
    except Exception as e:
        raise ValueError(f"שגיאה בטעינת נתונים עבור {ticker}: {e}")


def get_current_quote(ticker: str) -> dict:
    """
    מחזיר מחיר נוכחי ונתוני יום.
    """
    try:
        t = yf.Ticker(ticker)
        info = t.fast_info
        hist = t.history(period="2d", interval="1d", auto_adjust=True)

        if hist.empty:
            raise ValueError(f"אין נתונים עבור {ticker}")

        price = float(info.last_price) if hasattr(info, "last_price") and info.last_price else float(hist["Close"].iloc[-1])
        prev_close = float(hist["Close"].iloc[-2]) if len(hist) >= 2 else price
        change = price - prev_close
        change_pct = (change / prev_close * 100) if prev_close else 0.0

        return {
            "ticker": ticker,
            "price": round(price, 2),
            "change": round(change, 2),
            "change_pct": round(change_pct, 2),
            "volume": int(hist["Volume"].iloc[-1]) if "Volume" in hist.columns else 0,
            "high": round(float(hist["High"].iloc[-1]), 2),
            "low": round(float(hist["Low"].iloc[-1]), 2),
            "currency": getattr(info, "currency", "USD"),
            "year_high": round(float(info.year_high), 2) if hasattr(info, "year_high") and info.year_high else None,
            "year_low":  round(float(info.year_low),  2) if hasattr(info, "year_low")  and info.year_low  else None,
        }
    except Exception as e:
        raise ValueError(f"שגיאה בטעינת מחיר עבור {ticker}: {e}")


def get_company_name(ticker: str) -> str:
    """מחזיר שם החברה."""
    try:
        t = yf.Ticker(ticker)
        return t.info.get("longName") or t.info.get("shortName") or ticker
    except Exception:
        return ticker


def get_fundamentals(ticker: str) -> dict:
    """
    מחזיר נתונים פונדמנטליים, אנליסטים ושורט של החברה.
    """
    try:
        t = yf.Ticker(ticker)
        info = t.info

        def _safe(key, transform=None):
            v = info.get(key)
            if v is None:
                return None
            return transform(v) if transform else v

        market_cap = _safe("marketCap")
        sector     = info.get("sector") or "—"
        industry   = info.get("industry") or "—"

        pe_ratio    = _safe("trailingPE",  lambda v: round(float(v), 2))
        forward_pe  = _safe("forwardPE",   lambda v: round(float(v), 2))
        peg_ratio   = _safe("pegRatio",    lambda v: round(float(v), 2))
        debt_equity = _safe("debtToEquity",lambda v: round(float(v), 2))
        div_yield   = _safe("dividendYield",lambda v: round(float(v) * 100, 2))
        eps         = _safe("trailingEps", lambda v: round(float(v), 2))
        profit_margin = _safe("profitMargins", lambda v: round(float(v) * 100, 2))
        revenue     = _safe("totalRevenue")
        beta        = _safe("beta",        lambda v: round(float(v), 2))

        target_price  = _safe("targetMeanPrice",         lambda v: round(float(v), 2))
        target_low    = _safe("targetLowPrice",          lambda v: round(float(v), 2))
        target_high   = _safe("targetHighPrice",         lambda v: round(float(v), 2))
        analyst_count = _safe("numberOfAnalystOpinions", int)
        recommendation = info.get("recommendationKey") or "—"

        short_float = _safe("shortPercentOfFloat", lambda v: round(float(v) * 100, 2))
        short_ratio = _safe("shortRatio",          lambda v: round(float(v), 2))

        return_52w = _safe("52WeekChange", lambda v: round(float(v) * 100, 2))

        sma50  = _safe("fiftyDayAverage",     lambda v: round(float(v), 2))
        sma200 = _safe("twoHundredDayAverage",lambda v: round(float(v), 2))
        current_price = _safe("currentPrice") or _safe("regularMarketPrice")

        return {
            "market_cap": market_cap,
            "sector": sector,
            "industry": industry,
            "pe_ratio": pe_ratio,
            "forward_pe": forward_pe,
            "peg_ratio": peg_ratio,
            "debt_equity": debt_equity,
            "div_yield": div_yield,
            "eps": eps,
            "profit_margin": profit_margin,
            "revenue": revenue,
            "beta": beta,
            "target_price": target_price,
            "target_low": target_low,
            "target_high": target_high,
            "analyst_count": analyst_count,
            "recommendation": recommendation,
            "short_float": short_float,
            "short_ratio": short_ratio,
            "return_52w": return_52w,
            "sma50": sma50,
            "sma200": sma200,
            "current_price": current_price,
        }
    except Exception as e:
        return {"error": str(e)}


def is_valid_ticker(ticker: str) -> bool:
    """בודק אם הסמל קיים."""
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="5d", progress=False)
        return not hist.empty
    except Exception:
        return False


def _next_open_str(is_tase: bool, state: str) -> str | None:
    """Returns 'opens in Xh Ym' when market is closed/pre."""
    if state == "REGULAR":
        return None
    try:
        if is_tase:
            tz = ZoneInfo("Asia/Jerusalem")
            now = datetime.now(tz)
            # TASE: Sun(6)-Thu(0-3) 9:59
            candidate = now.replace(hour=9, minute=59, second=0, microsecond=0)
            for _ in range(8):
                if candidate > now and candidate.weekday() in [0, 1, 2, 3, 6]:
                    break
                candidate += timedelta(days=1)
                candidate = candidate.replace(hour=9, minute=59, second=0, microsecond=0)
            open_label = "9:59 IST"
        else:
            tz = ZoneInfo("America/New_York")
            now = datetime.now(tz)
            candidate = now.replace(hour=9, minute=30, second=0, microsecond=0)
            if state == "PRE":
                # Already before open today — candidate is today's open
                if candidate <= now:
                    candidate += timedelta(days=1)
            for _ in range(8):
                if candidate > now and candidate.weekday() < 5:
                    break
                candidate += timedelta(days=1)
                candidate = candidate.replace(hour=9, minute=30, second=0, microsecond=0)
            open_label = "9:30 ET"

        delta = candidate - now
        total_minutes = int(delta.total_seconds() / 60)
        hours, minutes = divmod(total_minutes, 60)
        if hours > 0:
            return f"opens in {hours}h {minutes}m  ({open_label})"
        return f"opens in {minutes}m  ({open_label})"
    except Exception:
        return None


def get_market_status(ticker: str) -> dict:
    """
    Returns market state + pre/post-market price without slow .info call.
    state: 'REGULAR' | 'PRE' | 'POST' | 'CLOSED'
    """
    is_tase = ticker.upper().endswith(".TA")
    pre_price = post_price = pre_chg_pct = post_chg_pct = None

    try:
        if is_tase:
            tz = ZoneInfo("Asia/Jerusalem")
            now = datetime.now(tz)
            t = now.time()
            is_trading_day = now.weekday() in [0, 1, 2, 3, 6]
            if is_trading_day and dt_time(9, 59) <= t <= dt_time(17, 25):
                state = "REGULAR"
            else:
                state = "CLOSED"
        else:
            tz = ZoneInfo("America/New_York")
            now = datetime.now(tz)
            t = now.time()
            is_weekday = now.weekday() < 5
            if not is_weekday:
                state = "CLOSED"
            elif dt_time(4, 0) <= t < dt_time(9, 30):
                state = "PRE"
            elif dt_time(9, 30) <= t < dt_time(16, 0):
                state = "REGULAR"
            elif dt_time(16, 0) <= t < dt_time(20, 0):
                state = "POST"
            else:
                state = "CLOSED"

            # Fetch pre/post prices only when not regular session
            if state != "REGULAR":
                try:
                    info = yf.Ticker(ticker).info
                    reg = info.get("regularMarketPrice") or info.get("currentPrice")
                    pre_raw  = info.get("preMarketPrice")
                    post_raw = info.get("postMarketPrice")
                    if pre_raw and reg:
                        pre_price   = round(float(pre_raw), 2)
                        pre_chg_pct = round((float(pre_raw) - float(reg)) / float(reg) * 100, 2)
                    if post_raw and reg:
                        post_price   = round(float(post_raw), 2)
                        post_chg_pct = round((float(post_raw) - float(reg)) / float(reg) * 100, 2)
                except Exception:
                    pass

    except Exception:
        state = "UNKNOWN"

    return {
        "state":        state,
        "is_open":      state == "REGULAR",
        "pre_price":    pre_price,
        "pre_chg_pct":  pre_chg_pct,
        "post_price":   post_price,
        "post_chg_pct": post_chg_pct,
        "next_open":    _next_open_str(is_tase, state),
    }
