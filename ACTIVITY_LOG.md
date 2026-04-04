# TradeIQ — Activity Log

> קובץ לוגים לסשנים. מעודכן בסוף כל סשן פיתוח.
> ניתן לקרוא בתחילת סשן כדי להבין את מצב הפרויקט במהירות.

---

## 2026-04-04 — סשן פיתוח (v3.1 → v3.3)

### מה נעשה

| גרסה | קובץ ראשי | שינוי |
|------|-----------|-------|
| v3.1 | `trade_app.py` | RSI(14) + MACD badge בdata strip; Auto-refresh 60s כשהשוק פתוח (`streamlit-autorefresh`) |
| v3.1.1 | `trade_app.py` | גרף מחיר משודרג: hover tooltip, spike cursor, volume avg line, labels; `requirements.txt` updated |
| v3.2 | `trade_app.py` | CSV export ליומן; S/R lines על גרף (top 3 resistance/support, dashed); Earnings Date בprice strip |
| v3.3 | `trade_app.py`, `data/user_data.py` | PnL Sheet: snapshot אוטומטי בכל טעינת טיקר, גליון מעקב עם מחיר חי, עריכת מניות, CSV export |
| fix | `trade_app.py` | `_pnl_live_price` הועבר ל-module level (cache אפקטיבי) |

### קבצים שהשתנו
- `trade_app.py` — הקובץ הראשי (כל הלוגיקה + UI)
- `data/user_data.py` — נוספו: `load_pnl_sheet`, `save_pnl_entry`, `delete_pnl_entry`, `update_pnl_shares`, `PNL_FILE`
- `requirements.txt` — נוסף: `streamlit-autorefresh>=1.0`
- `.gitignore` — נוסף: `data/pnl_sheet.json`
- `runtime.txt` — **חדש**: מפרט Python 3.11 לפריסה ב-Streamlit Cloud

### קבצי נתונים (git-ignored, לא מחויבים)
- `data/watchlist.json` — רשימת מעקב
- `data/trade_journal.json` — יומן עסקאות
- `data/pnl_sheet.json` — גליון PnL (חדש ב-v3.3)

---

## Innovation Index
| גרסה | ציון |
|------|------|
| v3.0 | 86 |
| v3.1 | 87 |
| v3.2 | 87 |
| v3.3 | 88 |

---

## Known Issues / Notes
- Streamlit Cloud: ללא `runtime.txt` עלול להשתמש ב-Python לא עדכני → נוסף `runtime.txt` ב-2026-04-04
- `st.data_editor` עם `key=` קבוע: אם columns ישתנו בין reruns, צריך לנקות state
- `_load_quote` TTL=30s (מהיר לפריצת cache) — מתאים לאחר שינוי טיקר

---

## Next Session — v3.4 (Candidates)
1. **Risk of Ruin calculator** — `calculators/risk_of_ruin.py`
2. **Telegram price alerts** — credentials: `C:/Users/arikg/.claude/secrets/telegram_credentials.env`
3. **Portfolio tracker** — מעקב על מספר פוזיציות במקביל
