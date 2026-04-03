"""
trade_calculator.py — Trade Calculator Skill
ממשק ראשי: מקבל קלטים (כולל טקסט חופשי מה-News Agent), מושך ATR, מחשב עסקה.
"""
import sys
import os
import re
import argparse
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from data.market_data import get_price_history, get_current_quote
from calculators.trade_calc import calc_atr, evaluate_trade


def parse_price_from_text(text: str) -> float | None:
    """
    מחלץ מחיר ראשון מטקסט חופשי של ה-News/Social Agent.
    דוגמאות נתמכות:
      "Target is the recent resistance at $210"
      "resistance level at 210.50"
      "Stop at $248"
      "price target: 270"
    """
    if not text:
        return None
    patterns = [
        r"\$\s*(\d{1,6}(?:\.\d{1,4})?)",   # $210 / $ 210.50
        r"(?:at|@|:)\s*(\d{2,6}(?:\.\d{1,4})?)",  # at 210 / @ 210 / : 270
        r"\b(\d{2,6}\.\d{1,4})\b",           # 210.50 (with decimal)
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            try:
                return float(m.group(1))
            except ValueError:
                continue
    return None


def run_trade_calculator(ticker: str,
                         entry: float,
                         target: float,
                         stop_loss: float,
                         risk_amount: float = 100.0,
                         portfolio_value: float = None,
                         risk_pct: float = 0.01,
                         commission: float = 5.0,
                         spread_pct: float = 0.001) -> dict:
    """
    ממשק ראשי של מחשבון העסקה.
    1. מושך ATR(14) מ-yfinance
    2. קורא ל-evaluate_trade()
    3. מחזיר dict מלא כולל markdown_table
    """
    # ATR מ-3 חודשים
    try:
        df = get_price_history(ticker, "3M")
        atr = calc_atr(df, period=14)
    except Exception:
        atr = None

    # אם risk_amount לא סופק אך portfolio_value כן — חשב לפי %
    if risk_amount is None and portfolio_value:
        risk_amount = portfolio_value * risk_pct

    result = evaluate_trade(
        entry=entry,
        target=target,
        stop_loss=stop_loss,
        risk_amount=risk_amount,
        portfolio_value=portfolio_value,
        commission=commission,
        spread_pct=spread_pct,
        atr=atr,
        ticker=ticker,
    )
    return result


def auto_suggest_stop(entry: float, atr: float, multiplier: float = 1.5) -> float:
    """הצעה אוטומטית לסטופ לוס: entry - 1.5 × ATR."""
    return round(entry - multiplier * atr, 4)


# ─── CLI ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Trade Calculator Skill")
    parser.add_argument("ticker", help="סמל מניה, למשל: AAPL או TEVA.TA")
    parser.add_argument("--entry", type=float, help="מחיר כניסה (ברירת מחדל: מחיר נוכחי)")
    parser.add_argument("--target", type=float, required=True, help="מחיר יעד")
    parser.add_argument("--stop", type=float, help="סטופ לוס (ברירת מחדל: entry - 1.5×ATR)")
    parser.add_argument("--risk", type=float, default=100.0, help="סיכון בדולרים (ברירת מחדל: 100)")
    parser.add_argument("--portfolio", type=float, default=None, help="גודל תיק לחישוב אחוז סיכון")
    parser.add_argument("--commission", type=float, default=5.0, help="עמלה לצד (ברירת מחדל: 5)")
    parser.add_argument("--spread", type=float, default=0.001, help="ספרד דצימלי (ברירת מחדל: 0.001)")
    parser.add_argument("--target-text", type=str, default="", help="טקסט חופשי לחילוץ יעד")
    parser.add_argument("--stop-text", type=str, default="", help="טקסט חופשי לחילוץ סטופ")
    parser.add_argument("--json", action="store_true", help="פלט JSON גולמי")
    args = parser.parse_args()

    # חילוץ מחיר מטקסט חופשי
    target = args.target
    if not target and args.target_text:
        target = parse_price_from_text(args.target_text)
        if not target:
            print(f"שגיאה: לא הצלחתי לחלץ מחיר מהטקסט: '{args.target_text}'")
            sys.exit(1)

    # מחיר כניסה — ברירת מחדל: מחיר שוק
    entry = args.entry
    if not entry:
        try:
            q = get_current_quote(args.ticker)
            entry = q["price"]
            print(f"מחיר כניסה (שוק): {entry}")
        except Exception as e:
            print(f"שגיאה בטעינת מחיר: {e}")
            sys.exit(1)

    # ATR לסטופ אוטומטי
    try:
        df = get_price_history(args.ticker, "3M")
        atr = calc_atr(df)
    except Exception:
        atr = None

    stop = args.stop
    if not stop and args.stop_text:
        stop = parse_price_from_text(args.stop_text)
    if not stop and atr:
        stop = auto_suggest_stop(entry, atr)
        print(f"סטופ לוס אוטומטי (1.5×ATR): {stop}")

    if not stop:
        print("שגיאה: יש לספק --stop או --stop-text")
        sys.exit(1)

    result = run_trade_calculator(
        ticker=args.ticker,
        entry=entry,
        target=target,
        stop_loss=stop,
        risk_amount=args.risk,
        portfolio_value=args.portfolio,
        commission=args.commission,
        spread_pct=args.spread,
    )

    if args.json:
        out = {k: v for k, v in result.items() if k != "markdown_table"}
        sys.stdout.buffer.write((json.dumps(out, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    else:
        sys.stdout.buffer.write(("\n" + result["markdown_table"] + "\n").encode("utf-8"))
