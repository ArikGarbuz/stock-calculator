סגנון: Day Trading + Swing Trading
שווקים: TASE + ארה"ב (NYSE/NASDAQ)
נתונים בזמן אמת: כן
סגנון: כלי מקצועי (לא פשוט, עם גרפים, אוטומציה ותצוגה נקייה)
AI: נשאיר להמשך – עכשיו MVP ב-Google Sheets בלבד

להלן ארכיטקטורה מלאה ומפורטת של ה-MVP.
הקובץ יהיה מקצועי, אוטומטי ככל האפשר, ומותאם בדיוק לצרכים של Day/Swing trader שפעיל בשני השווקים.
מבנה הקובץ (7 Sheets בלבד – נקי ומאורגן)





















































Sheetשםמטרה עיקריתעדכון אוטומטי1Dashboardתצוגת-על מקצועית (P&L, חשיפה, התראות)כן (על פתיחה + כל 5 דק')2Portfolioתיק השקעות מלא + P&L בזמן אמתכן3Trade Calculatorמחשבון עסקה לפני כניסה (כולל מס ישראלי)—4Risk ManagerPosition Sizer + ניהול סיכונים—5Stock Analyzerניתוח מהיר של מניה (TASE או US)כן6Journalיומן מסחר + ניתוח Win Rate—7Settingsפרמטרים + API Keys (מוגן)—
1. Dashboard (ה"מסך הראשי" – מקצועי כמו TradingView)

תצוגה עליונה: Equity כולל, Cash, P&L יומי/שבועי/חודשי (בשקלים ובאחוזים)
כרטיסים:
חשיפה נוכחית (% מהתיק)
מספר עסקאות פתוחות
Risk-to-Reward ממוצע
Drawdown מקסימלי

טבלה קטנה: 5-10 מניות "בפוקוס" (Watchlist) עם מחיר, שינוי %, ATR, Volume
גרפים (Embedded Charts):
Equity Curve
התפלגות תיק (Pie)
P&L לפי יום (Bar)

התראות (Conditional Formatting + Notes): "סיכון גבוה", "Stop Loss קרוב"

2. Portfolio (הליבה)
טבלה ראשית:
















סמלשוקכמותמחיר קנייהמחיר נוכחי (Live)P&L ₪P&L %% מהתיקBetaSectorתאריך כניסה

מחיר נוכחי: פונקציה אוטומטית (ראה להלן)
P&L: נוסחה אוטומטית כולל עמלות ומס (25% + מס יסף)
סכום כולל: QUERY + SUMIFS
סינון: Data Filter + Slicer לפי שוק (TASE / US)

3. Trade Calculator (לפני כל עסקה)
קלטים (עם Data Validation):

סמל + שוק
מחיר כניסה (או Live)
Stop Loss (₪ או %)
Take Profit (1R, 2R, 3R)
כמות / סכום
עמלות (ברוקר + מס)

פלטים:

גודל פוזיציה מומלץ (מה-Risk Manager)
Risk-Reward Ratio
רווח/הפסד צפוי אחרי מס
Break-even price
כפתור "הוסף לעסקה פתוחה" (שולח אוטומטית ל-Portfolio)

4. Risk Manager

Account Size (עדכני מה-Portfolio)
Max Risk per Trade % (ברירת מחדל 1%)
Max Daily Risk %
Max Correlation % (בין מניות)

נוסחה מרכזית (Position Size):
text=ROUND( (AccountSize * RiskPercent) / (EntryPrice - StopPrice) , 0)
כולל המרה אוטומטית בין ₪ לדולר (שער חליפין Live).
5. Stock Analyzer (Day/Swing)
הזן סמל → מקבל:

מחיר Live + Volume + ATR(14)
52w High/Low
Beta
P/E, EPS (אם זמין)
Margin of Safety (פשוט)
התראה אם המחיר מתחת/מעל רמה טכנית שהגדרת

6. Journal

תאריך, סמל, כניסה/יציאה, R-multiple, תמונה של הגרף (Insert Image)
סיבה לכניסה + פסיכולוגיה
Win Rate, Expectancy, Average R (QUERY אוטומטי)

7. Settings

Account Size
Risk % defaults
Broker fees
מס יסף threshold
API Key (אם צריך)
צבעי עיצוב + הגדרות התראות

חיבור נתונים בזמן אמת (החלק החשוב ביותר ל-MVP)
המלצה מומלצת 2026 (מהירה + אמינה + חינם):

למניות ארה"ב → =GOOGLEFINANCE("NASDAQ:AAPL","price") (מתעדכן כל כמה שניות)
למניות TASE + כל מה ש-GOOGLEFINANCE לא מספיק → פונקציה מותאמת ב-Apps Script שמושכת מ-Yahoo Finance (תומך מצוין ב-TASE עם סיומת .TA)

קוד Apps Script מוכן לשימוש (העתק-הדבק):
JavaScriptfunction getLivePrice(ticker) {
  // ticker יכול להיות: "AAPL" או "TEVA.TA" או "NVDA"
  const url = `https://query1.finance.yahoo.com/v7/finance/quote?symbols=${ticker}`;
  try {
    const response = UrlFetchApp.fetch(url, {muteHttpExceptions: true});
    const data = JSON.parse(response.getContentText());
    return data.quoteResponse.result[0].regularMarketPrice;
  } catch (e) {
    return "Error";
  }
}

השתמש כך: =getLivePrice("TEVA.TA") או =getLivePrice("NASDAQ:AAPL")
מתעדכן אוטומטית בכל רענון (או עם Trigger כל 1-5 דקות)

אופציה 2 (אפילו יותר קלה):
התקן את Add-on "Alpha Vantage Market Data" מגוגל וורקספייס – יש לו פונקציות מוכנות + תמיכה ב-TASE.
עיצוב מקצועי (כדי שזה ירגיש כמו כלי רציני)

צבעים: ירוק/אדום עדין + כחול כהה (כמו TradingView)
Conditional Formatting חזק (למשל: P&L > 2% = ירוק כהה)
Slicers + Filters בכל טבלה
Charts מותאמים + Sparklines
הגן על Sheets רגישים (רק אתה יכול לערוך)
Freeze Panes + Header נעוץ

צעדים לבנייה (תוך שעה-שעתיים)

צור Google Sheet חדש → שנה שם ל-"StockTrader_MVP_אריק"
הוסף את 7 השמות של Sheets
בנה את הטבלאות לפי הסדר (מתחיל ב-Settings → Risk Manager → Trade Calculator)
העתק את קוד ה-Apps Script (Extensions → Apps Script)
הוסף Triggers: "onOpen" + Time-driven every 5 minutes
בדוק עם 2-3 מניות (אחת TASE + אחת US)

