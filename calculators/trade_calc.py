"""
trade_calc.py — Trade Calculator: חישובי כדאיות עסקה
כל החישובים מתבצעים כאן בלבד (לא inline בשאר הקוד)
"""
import math
import pandas as pd
import numpy as np


def calc_atr(df: pd.DataFrame, period: int = 14) -> float:
    """
    Average True Range מ-DataFrame של OHLC.
    True Range = max(High-Low, |High-PrevClose|, |Low-PrevClose|)
    """
    high = df["High"].squeeze()
    low = df["Low"].squeeze()
    close = df["Close"].squeeze()
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    atr = tr.ewm(span=period, adjust=False).mean().iloc[-1]
    return round(float(atr), 4)


def calc_position_size(price: float, stop_loss: float,
                       risk_amount: float = None,
                       portfolio_value: float = None,
                       risk_pct: float = 0.01) -> dict:
    """
    מחשב כמה מניות לקנות לפי סיכון קבוע.
    risk_amount = portfolio_value * risk_pct אם לא סופק ישירות.
    """
    if risk_amount is None:
        if portfolio_value is None or portfolio_value <= 0:
            raise ValueError("יש לספק risk_amount או portfolio_value")
        risk_amount = portfolio_value * risk_pct

    risk_per_share = abs(price - stop_loss)
    if risk_per_share <= 0:
        raise ValueError("מחיר הכניסה חייב להיות גדול מהסטופ לוס")

    shares = int(risk_amount / risk_per_share)
    if shares < 1:
        shares = 1

    total_cost = shares * price
    return {
        "shares": shares,
        "risk_amount": round(risk_amount, 2),
        "risk_per_share": round(risk_per_share, 4),
        "total_cost": round(total_cost, 2),
    }


def calc_risk_reward(entry: float, target: float, stop_loss: float) -> dict:
    """
    מחשב יחס סיכוי:סיכון.
    rr_ratio = (target - entry) / (entry - stop_loss)
    """
    reward = target - entry
    risk = entry - stop_loss
    if risk <= 0:
        raise ValueError("הסטופ לוס חייב להיות מתחת למחיר הכניסה")
    if reward <= 0:
        raise ValueError("היעד חייב להיות מעל מחיר הכניסה")
    rr = reward / risk
    return {
        "reward": round(reward, 4),
        "risk": round(risk, 4),
        "rr_ratio": round(rr, 2),
        "formatted": f"1 : {rr:.2f}",
    }


def calc_breakeven(entry: float, shares: int,
                   commission_per_trade: float = 5.0,
                   spread_pct: float = 0.001) -> dict:
    """
    מחשב מחיר break-even אחרי עמלות וספרד.
    total_cost = (entry × shares) + (2 × commission) + (spread_pct × entry × shares)
    breakeven = total_cost / shares
    """
    gross_cost = entry * shares
    commission_total = 2 * commission_per_trade          # כניסה + יציאה
    spread_cost = spread_pct * gross_cost
    total_cost = gross_cost + commission_total + spread_cost
    breakeven_price = total_cost / shares
    return {
        "breakeven_price": round(breakeven_price, 4),
        "total_commission": round(commission_total + spread_cost, 2),
        "effective_entry": round(breakeven_price, 4),
        "gross_cost": round(gross_cost, 2),
        "total_cost": round(total_cost, 2),
    }


def evaluate_trade(entry: float, target: float, stop_loss: float,
                   risk_amount: float = 100.0,
                   portfolio_value: float = None,
                   commission: float = 5.0,
                   spread_pct: float = 0.001,
                   atr: float = None,
                   ticker: str = "") -> dict:
    """
    מרכז את כל החישובים ומחזיר dict מלא עם markdown_table ו-verdict.
    """
    rr = calc_risk_reward(entry, target, stop_loss)
    pos = calc_position_size(entry, stop_loss, risk_amount=risk_amount,
                             portfolio_value=portfolio_value)
    be = calc_breakeven(entry, pos["shares"], commission, spread_pct)

    verdict = "GO" if rr["rr_ratio"] >= 2.0 else "NO-GO"
    verdict_reason = (
        f"R:R = {rr['formatted']} >= 1:2" if rr["rr_ratio"] >= 2.0
        else f"R:R = {rr['formatted']} < 1:2 (נדרש לפחות 1:2)"
    )

    result = {
        "ticker": ticker,
        "entry": entry,
        "target": target,
        "stop_loss": stop_loss,
        "atr": atr,
        "rr": rr,
        "position": pos,
        "breakeven": be,
        "verdict": verdict,
        "verdict_reason": verdict_reason,
    }
    result["markdown_table"] = _build_markdown_table(result)
    return result


def evaluate_trade_v3(
    ticker: str,
    direction: str,
    account_size: float,
    pct_investing: float,
    entry: float,
    stop: float,
    target: float,
    commission: float = 7.0,
) -> dict:
    """
    מחשבון מסחר v3: Account Size, % Investing, LONG/SHORT, Income Forecast + Exit Tiers.

    Args:
        direction:    "LONG" | "SHORT"
        pct_investing: 0.0–1.0 (e.g. 1.0 = 100%)
    """
    planned_investment = account_size * pct_investing
    shares = math.floor(planned_investment / entry) if entry > 0 else 0
    if shares < 1:
        shares = 1
    actual_investment = shares * entry

    if direction == "LONG":
        risk_per_share   = entry - stop
        reward_per_share = target - entry
    else:  # SHORT
        risk_per_share   = stop - entry
        reward_per_share = entry - target

    if risk_per_share <= 0:
        raise ValueError("Stop Loss אינו תקין ביחס למחיר הכניסה")
    if reward_per_share <= 0:
        raise ValueError("Target אינו תקין ביחס למחיר הכניסה")

    rr_ratio         = round(reward_per_share / risk_per_share, 2)
    total_commission = commission * 2
    gross_profit     = shares * reward_per_share
    net_profit       = gross_profit - total_commission
    risk_total       = shares * risk_per_share
    profit_pct       = (net_profit / actual_investment * 100) if actual_investment > 0 else 0
    verdict          = "GO" if rr_ratio >= 2.0 else "NO-GO"

    # Exit tiers: 25% / 50% / 75% / 100% of position
    exit_tiers = []
    for tier_pct in [25, 50, 75, 100]:
        frac        = tier_pct / 100
        tier_shares = math.floor(shares * frac)
        if direction == "LONG":
            tier_price  = round(entry + reward_per_share * frac, 2)
            tier_profit = round(tier_shares * (tier_price - entry), 2)
        else:
            tier_price  = round(entry - reward_per_share * frac, 2)
            tier_profit = round(tier_shares * (entry - tier_price), 2)
        tier_pct_return = round(tier_profit / actual_investment * 100, 2) if actual_investment > 0 else 0
        exit_tiers.append({
            "pct":        tier_pct,
            "shares":     tier_shares,
            "price":      tier_price,
            "profit":     tier_profit,
            "pct_return": tier_pct_return,
        })

    return {
        "verdict":            verdict,
        "direction":          direction,
        "rr":                 rr_ratio,
        "rr_formatted":       f"1 : {rr_ratio:.2f}",
        "verdict_reason":     f"R:R = 1:{rr_ratio:.2f} {'≥' if rr_ratio >= 2.0 else '<'} 1:2",
        "account_size":       round(account_size, 2),
        "pct_investing":      round(pct_investing * 100, 1),
        "planned_investment": round(planned_investment, 2),
        "actual_investment":  round(actual_investment, 2),
        "shares":             shares,
        "entry":              entry,
        "stop":               stop,
        "target":             target,
        "risk_per_share":     round(risk_per_share, 4),
        "reward_per_share":   round(reward_per_share, 4),
        "risk_total":         round(risk_total, 2),
        "gross_profit":       round(gross_profit, 2),
        "net_profit":         round(net_profit, 2),
        "profit_pct":         round(profit_pct, 2),
        "commission_total":   round(total_commission, 2),
        "exit_tiers":         exit_tiers,
        "ticker":             ticker,
    }


def _build_markdown_table(data: dict) -> str:
    """מבנה טבלת Markdown מסכמת לעסקה."""
    entry = data["entry"]
    target = data["target"]
    stop = data["stop_loss"]
    rr = data["rr"]
    pos = data["position"]
    be = data["breakeven"]
    atr = data.get("atr")
    verdict = data["verdict"]
    verdict_reason = data.get("verdict_reason", "")
    ticker = data.get("ticker", "")
    currency = "₪" if (ticker or "").endswith(".TA") else "$"

    rows = [
        ("מניה", ticker or "—"),
        ("מחיר כניסה", f"{currency}{entry:,.2f}"),
        ("יעד (Target)", f"{currency}{target:,.2f}"),
        ("סטופ לוס", f"{currency}{stop:,.2f}"),
        ("סיכוי : סיכון (R:R)", rr["formatted"]),
        ("רווח פוטנציאלי", f"{currency}{rr['reward']:,.2f} למניה"),
        ("סיכון למניה", f"{currency}{rr['risk']:,.2f}"),
        ("גודל פוזיציה", f"{pos['shares']} מניות"),
        ("סיכון כולל", f"{currency}{pos['risk_amount']:,.2f}"),
        ("עלות כוללת (ברוטו)", f"{currency}{be['gross_cost']:,.2f}"),
        ("עמלות + ספרד", f"{currency}{be['total_commission']:,.2f}"),
        ("Breakeven", f"{currency}{be['breakeven_price']:,.2f}"),
    ]
    if atr is not None:
        rows.append(("ATR (14)", f"{currency}{atr:,.2f}"))

    lines = [
        "| פרמטר | ערך |",
        "|---|---|",
    ]
    for k, v in rows:
        lines.append(f"| {k} | **{v}** |")

    lines.append("|---|---|")
    verdict_display = "GO ✅" if verdict == "GO" else "NO-GO ❌"
    lines.append(f"| **המלצה** | **{verdict_display}** |")
    lines.append(f"| סיבה | {verdict_reason} |")

    return "\n".join(lines)
