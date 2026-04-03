"""
technical_calc.py — חישובי אינדיקטורים טכניים
כל החישובים מתבצעים כאן בלבד (לא inline בשאר הקוד)
"""
import pandas as pd
import numpy as np


def calc_sma(series: pd.Series, window: int) -> pd.Series:
    """Simple Moving Average."""
    return series.rolling(window=window, min_periods=1).mean().round(4)


def calc_ema(series: pd.Series, window: int) -> pd.Series:
    """Exponential Moving Average."""
    return series.ewm(span=window, adjust=False).mean().round(4)


def calc_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """
    RSI (Relative Strength Index).
    מחזיר ערכים 0-100.
    """
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.round(2)


def calc_macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> dict:
    """
    MACD = EMA(fast) - EMA(slow)
    Signal = EMA(MACD, signal)
    Histogram = MACD - Signal
    """
    ema_fast = calc_ema(series, fast)
    ema_slow = calc_ema(series, slow)
    macd_line = (ema_fast - ema_slow).round(4)
    signal_line = macd_line.ewm(span=signal, adjust=False).mean().round(4)
    histogram = (macd_line - signal_line).round(4)
    return {
        "macd": macd_line,
        "signal": signal_line,
        "histogram": histogram,
    }


def calc_bollinger_bands(series: pd.Series, window: int = 20, num_std: float = 2.0) -> dict:
    """Bollinger Bands — upper, middle, lower."""
    middle = calc_sma(series, window)
    std = series.rolling(window=window, min_periods=1).std()
    upper = (middle + num_std * std).round(4)
    lower = (middle - num_std * std).round(4)
    return {"upper": upper, "middle": middle, "lower": lower}


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """מוסיף את כל האינדיקטורים ל-DataFrame של מחירים."""
    close = df["Close"].squeeze()
    df = df.copy()
    df["SMA_50"] = calc_sma(close, 50)
    df["SMA_200"] = calc_sma(close, 200)
    df["RSI"] = calc_rsi(close)
    macd = calc_macd(close)
    df["MACD"] = macd["macd"]
    df["MACD_Signal"] = macd["signal"]
    df["MACD_Hist"] = macd["histogram"]
    return df
