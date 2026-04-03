"""
support_resistance.py — 10 מדדי תמיכה/התנגדות
מחשב ומחזיר רמות מחיר מרכזיות אוטומטית עבור כל טיקר.
"""
import math
import numpy as np
import pandas as pd
import yfinance as yf


def _safe_float(val, default=None):
    try:
        v = float(val)
        return v if not math.isnan(v) else default
    except Exception:
        return default


def _fetch_daily(ticker: str, period: str = "1y") -> pd.DataFrame:
    df = yf.download(ticker, period=period, interval="1d", progress=False, auto_adjust=True)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df


def get_support_resistance(ticker: str) -> dict:
    """
    מחשב 10 קטגוריות של מדדי תמיכה/התנגדות.
    Returns:
        {
          "levels": [{"name", "price", "type": "support"|"resistance"|"neutral", "group"}],
          "current_price": float,
          "error": None | str
        }
    Sorted by price descending. Deduped within 0.2%.
    """
    try:
        df = _fetch_daily(ticker, period="1y")
        if df.empty or len(df) < 5:
            return {"levels": [], "current_price": None, "error": "לא נמצאו נתונים"}

        close = df["Close"].squeeze()
        high  = df["High"].squeeze()
        low   = df["Low"].squeeze()
        vol   = df["Volume"].squeeze()

        current_price = _safe_float(close.iloc[-1])
        levels = []

        # ── 1. Daily Pivot Points (based on previous trading day) ─────────────
        prev_h = _safe_float(high.iloc[-2])
        prev_l = _safe_float(low.iloc[-2])
        prev_c = _safe_float(close.iloc[-2])
        if prev_h and prev_l and prev_c:
            pp = (prev_h + prev_l + prev_c) / 3
            s1 = 2 * pp - prev_h
            s2 = pp - (prev_h - prev_l)
            s3 = prev_l - 2 * (prev_h - pp)
            r1 = 2 * pp - prev_l
            r2 = pp + (prev_h - prev_l)
            r3 = prev_h + 2 * (pp - prev_l)
            for name, val in [("Pivot PP", pp), ("Pivot S1", s1), ("Pivot S2", s2),
                               ("Pivot S3", s3), ("Pivot R1", r1), ("Pivot R2", r2), ("Pivot R3", r3)]:
                levels.append({"name": name, "price": round(val, 2), "group": "Daily Pivot"})

        # ── 2. Weekly Pivot Points ─────────────────────────────────────────────
        df_weekly = df.resample("W").agg({"High": "max", "Low": "min", "Close": "last"}).dropna()
        if len(df_weekly) >= 2:
            wh = _safe_float(df_weekly["High"].iloc[-2])
            wl = _safe_float(df_weekly["Low"].iloc[-2])
            wc = _safe_float(df_weekly["Close"].iloc[-2])
            if wh and wl and wc:
                wpp = (wh + wl + wc) / 3
                ws1 = 2 * wpp - wh
                wr1 = 2 * wpp - wl
                wr2 = wpp + (wh - wl)
                for name, val in [("Weekly PP", wpp), ("Weekly S1", ws1),
                                   ("Weekly R1", wr1), ("Weekly R2", wr2)]:
                    levels.append({"name": name, "price": round(val, 2), "group": "Weekly Pivot"})

        # ── 3. Fibonacci Retracement (3-month swing) ───────────────────────────
        window_3m = min(63, len(close))
        fib_high = _safe_float(high.iloc[-window_3m:].max())
        fib_low  = _safe_float(low.iloc[-window_3m:].min())
        if fib_high and fib_low and fib_high > fib_low:
            diff = fib_high - fib_low
            for ratio, label in [(0.236, "Fib 23.6%"), (0.382, "Fib 38.2%"), (0.5, "Fib 50%"),
                                  (0.618, "Fib 61.8%"), (0.786, "Fib 78.6%")]:
                price_level = fib_high - diff * ratio
                levels.append({"name": label, "price": round(price_level, 2), "group": "Fibonacci"})

        # ── 4. 52W High / Low ─────────────────────────────────────────────────
        w52_high = _safe_float(high.max())
        w52_low  = _safe_float(low.min())
        if w52_high:
            levels.append({"name": "52W High", "price": round(w52_high, 2), "group": "Historical"})
        if w52_low:
            levels.append({"name": "52W Low",  "price": round(w52_low,  2), "group": "Historical"})

        # ── 5. 20D High / Low ─────────────────────────────────────────────────
        w20_high = _safe_float(high.iloc[-20:].max())
        w20_low  = _safe_float(low.iloc[-20:].min())
        if w20_high:
            levels.append({"name": "20D High", "price": round(w20_high, 2), "group": "Historical"})
        if w20_low:
            levels.append({"name": "20D Low",  "price": round(w20_low,  2), "group": "Historical"})

        # ── 6. Previous Day High / Low ────────────────────────────────────────
        if prev_h:
            levels.append({"name": "Prev Day High", "price": round(prev_h, 2), "group": "Historical"})
        if prev_l:
            levels.append({"name": "Prev Day Low",  "price": round(prev_l, 2), "group": "Historical"})

        # ── 7. SMA 20 / 50 / 200 ──────────────────────────────────────────────
        for period_sma, label in [(20, "SMA 20"), (50, "SMA 50"), (200, "SMA 200")]:
            if len(close) >= period_sma:
                sma_val = _safe_float(close.rolling(period_sma).mean().iloc[-1])
                if sma_val:
                    levels.append({"name": label, "price": round(sma_val, 2), "group": "Moving Avgs"})

        # ── 8. Bollinger Bands (20, 2σ) ───────────────────────────────────────
        if len(close) >= 20:
            bb_mid   = close.rolling(20).mean()
            bb_std   = close.rolling(20).std()
            bb_upper = _safe_float((bb_mid + 2 * bb_std).iloc[-1])
            bb_lower = _safe_float((bb_mid - 2 * bb_std).iloc[-1])
            if bb_upper:
                levels.append({"name": "BB Upper", "price": round(bb_upper, 2), "group": "Bollinger"})
            if bb_lower:
                levels.append({"name": "BB Lower", "price": round(bb_lower, 2), "group": "Bollinger"})

        # ── 9. VWAP — try intraday, fallback to 20D approximation ────────────
        vwap_added = False
        try:
            df_intra = yf.download(ticker, period="1d", interval="5m",
                                   progress=False, auto_adjust=True)
            if isinstance(df_intra.columns, pd.MultiIndex):
                df_intra.columns = df_intra.columns.get_level_values(0)
            if not df_intra.empty and len(df_intra) > 3:
                tp = ((df_intra["High"].squeeze()
                       + df_intra["Low"].squeeze()
                       + df_intra["Close"].squeeze()) / 3)
                denom = df_intra["Volume"].squeeze().sum()
                if denom > 0:
                    vwap_val = _safe_float((tp * df_intra["Volume"].squeeze()).sum() / denom)
                    if vwap_val:
                        levels.append({"name": "VWAP (Daily)", "price": round(vwap_val, 2), "group": "VWAP"})
                        vwap_added = True
        except Exception:
            pass

        if not vwap_added:
            # Fallback: volume-weighted avg of last 20 days typical prices
            tp_daily   = (high + low + close) / 3
            last20_tp  = tp_daily.iloc[-20:]
            last20_vol = vol.iloc[-20:]
            denom = last20_vol.sum()
            if denom > 0:
                vwap_approx = _safe_float((last20_tp * last20_vol).sum() / denom)
                if vwap_approx:
                    levels.append({"name": "VWAP (20D)", "price": round(vwap_approx, 2), "group": "VWAP"})

        # ── 10. Volume POC — price bucket with highest 20D volume ─────────────
        df_20d = df.iloc[-20:].copy()
        if len(df_20d) >= 5:
            h20 = _safe_float(df_20d["High"].squeeze().max())
            l20 = _safe_float(df_20d["Low"].squeeze().min())
            if h20 and l20 and h20 > l20:
                bucket_size = (h20 - l20) / 20
                typ_price = ((df_20d["High"].squeeze()
                              + df_20d["Low"].squeeze()
                              + df_20d["Close"].squeeze()) / 3)
                buckets = ((typ_price - l20) / bucket_size).astype(int).clip(0, 19)
                vol_by_bucket = {}
                for b, v in zip(buckets, df_20d["Volume"].squeeze()):
                    vol_by_bucket[b] = vol_by_bucket.get(b, 0) + v
                if vol_by_bucket:
                    poc_bucket = max(vol_by_bucket, key=vol_by_bucket.get)
                    poc_price  = l20 + (poc_bucket + 0.5) * bucket_size
                    levels.append({"name": "Volume POC", "price": round(poc_price, 2), "group": "Volume"})

        # ── Classify as support / resistance / neutral ─────────────────────────
        if current_price:
            for lvl in levels:
                p = lvl["price"]
                diff_pct = abs(p - current_price) / current_price * 100
                if diff_pct < 0.15:
                    lvl["type"] = "neutral"
                elif p > current_price:
                    lvl["type"] = "resistance"
                else:
                    lvl["type"] = "support"
        else:
            for lvl in levels:
                lvl["type"] = "neutral"

        # Sort descending by price
        levels.sort(key=lambda x: x["price"], reverse=True)

        # Deduplicate levels within 0.2% of each other
        deduped = []
        for lvl in levels:
            if not deduped:
                deduped.append(lvl)
            else:
                gap_pct = abs(lvl["price"] - deduped[-1]["price"]) / max(deduped[-1]["price"], 0.01) * 100
                if gap_pct > 0.2:
                    deduped.append(lvl)

        return {"levels": deduped, "current_price": current_price, "error": None}

    except Exception as e:
        return {"levels": [], "current_price": None, "error": str(e)}
