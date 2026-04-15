# Paper Trading System — Testing Checklist

## Phase 4: Quality Assurance & Deployment (9-12h window)

---

## A. LOCAL TESTING (Dev Environment)

### 1. Database Connection
- [ ] Supabase project created and accessible
- [ ] Migration (001_paper_trading_schema.sql) executed successfully
- [ ] All 4 tables exist: `users`, `paper_trades`, `saved_trades`, `daily_status_log`
- [ ] Views created: `user_daily_summary`, `user_monthly_summary`
- [ ] RLS policies enabled and verified

**Verification command:**
```bash
# Check tables exist
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;

# Check RLS policies
SELECT * FROM pg_policies;
```

---

### 2. Authentication Flow

**Login Page:**
- [ ] Email field accepts valid email format
- [ ] Password field accepts min 6 characters
- [ ] Sign In button works with correct credentials
- [ ] Error message shows for incorrect credentials
- [ ] Sign Up tab creates new account
- [ ] Password confirmation validation works
- [ ] Existing email error shows correctly
- [ ] Session persists after refresh
- [ ] Logout button clears session

**Local test:**
```bash
streamlit run paper_trading.py
# Create test account: test@example.com / password123
# Login should work
# Logout should clear session
```

---

### 3. Dashboard Page

**KPI Metrics (Row 1):**
- [ ] "Total Trades" shows 0 for new user
- [ ] "Wins" counter working
- [ ] "Losses" counter working
- [ ] "Pending" counter working
- [ ] "Win Rate" calculation correct (0% for new user)

**KPI Metrics (Row 2):**
- [ ] "Total P&L" shows $0.00 for new user
- [ ] P&L color correct (🟢 green for positive, 🔴 red for negative)
- [ ] "Avg ROI" calculation correct
- [ ] "Date" shows today's date

**Trades Table:**
- [ ] Empty state message shows ("No trades yet")
- [ ] After logging trades, table displays data
- [ ] Columns: Ticker, P&L, ROI %, Status, Notes
- [ ] Sorting works (by P&L or ROI)
- [ ] Status badges styled correctly (won=green, lost=red, pending=yellow)

---

### 4. Log Trade Page

**Form Validation:**
- [ ] Ticker field: uppercase conversion works (AAPL, MSFT, TEVA.TA)
- [ ] Entry Price: min value 0.01 enforced
- [ ] Position Size: min value 1 enforced
- [ ] Entry Reason: optional field works
- [ ] Exit Price: optional, can be left blank

**Trade Logging (without exit price):**
- [ ] Click "Log Trade" with valid data
- [ ] Success message shows ✅
- [ ] Trade created in `paper_trades` table
- [ ] Status is "open" in database
- [ ] User can log multiple trades

**Trade Closure (with exit price):**
- [ ] Log trade with exit price filled in
- [ ] Trade closes automatically
- [ ] "Save to Dashboard" button appears
- [ ] Click "Save to Dashboard"
- [ ] Trade moves to `saved_trades` table
- [ ] Status defaults to "pending"
- [ ] P&L calculation correct: (exit - entry) × shares
- [ ] ROI calculation correct: ((exit - entry) / entry) × 100

**Example test case:**
```
Ticker: AAPL
Entry: $150.00
Exit: $153.00
Shares: 100
Expected P&L: $300.00
Expected ROI: 2.0%
```

---

### 5. Manage Trades Page

**Trade Display:**
- [ ] All saved trades load
- [ ] Trade ID truncated to 8 chars
- [ ] Notes column shows first 50 chars
- [ ] P&L displays with currency
- [ ] ROI % shows 2 decimal places
- [ ] Status button shows current status

**Status Cycling:**
- [ ] Won → Lost → Pending → Won cycle works
- [ ] Click status button updates trade
- [ ] Success message shows
- [ ] Database reflects change immediately

**Filtering:**
- [ ] "Filter by Status" dropdown works
- [ ] "All" shows all trades
- [ ] "Won" shows only won trades
- [ ] "Lost" shows only lost trades
- [ ] "Pending" shows only pending trades

**Delete Functionality:**
- [ ] 🗑️ button present for each trade
- [ ] Click delete shows success message
- [ ] Trade removed from table
- [ ] Database reflects deletion
- [ ] Paper trade still exists (only saved_trade deleted)

---

### 6. Analytics Page

**Metrics Display:**
- [ ] "Total Trades (All Time)" shows correct count
- [ ] "Total P&L (All Time)" shows correct total

**Monthly Summary Table:**
- [ ] Table shows data grouped by month
- [ ] Columns: month, total, wins, losses, win_rate, pnl
- [ ] Data correctly aggregated by month

**Charts:**
- [ ] Win Rate chart displays (bar chart)
- [ ] P&L chart displays (bar chart)
- [ ] Charts update when new trades saved
- [ ] Empty state message shows if no data

**Test scenario (5 trades):**
- Log 5 trades with mix of wins/losses
- Wait for dashboard to update
- Verify aggregations:
  - Total trades = 5
  - Win rate = (wins/5) × 100
  - Monthly P&L = sum of all P&L

---

## B. MULTI-USER TESTING

### 1. User Isolation (RLS Policies)

**Test Case 1: Create two users**
```
User A: alice@example.com / password123
User B: bob@example.com / password123
```

**Steps:**
- [ ] User A logs in, logs 3 trades
- [ ] User B logs in, logs 2 different trades
- [ ] User A dashboard shows only their 3 trades
- [ ] User B dashboard shows only their 2 trades
- [ ] User A cannot see User B's trades (check database if necessary)
- [ ] Each user's P&L and win rate calculated separately

**Verification (Supabase SQL):**
```sql
-- As User A (admin), check both users' data
SELECT user_id, COUNT(*) FROM saved_trades GROUP BY user_id;
-- Should show: User A has 3, User B has 2
```

---

### 2. Session Independence

- [ ] Open paper_trading.py in two browser tabs
- [ ] Log in as User A in Tab 1
- [ ] Log in as User B in Tab 2
- [ ] User A logs a trade in Tab 1
- [ ] User B should NOT see User A's trade in Tab 2
- [ ] Logout in Tab 1, User B should still be logged in Tab 2

---

### 3. Concurrent Operations

- [ ] User A logs trade (5s to update)
- [ ] User B logs trade simultaneously
- [ ] Both trades appear in respective dashboards
- [ ] No data corruption or overlap
- [ ] P&L calculations independent

---

## C. DATA INTEGRITY TESTING

### 1. Calculation Accuracy

**P&L Calculation:**
```
Input: Entry=$100, Exit=$110, Shares=50
Expected: (110-100) × 50 = $500 ✓
```

**ROI Calculation:**
```
Input: Entry=$100, Exit=$110
Expected: ((110-100)/100) × 100 = 10% ✓
```

- [ ] P&L calculation matches manual math
- [ ] ROI calculation matches manual math
- [ ] Decimals handled correctly (2 places for $, 4 places for %)

---

### 2. Date/Time Handling

- [ ] Today's date displays correctly in dashboard
- [ ] Trade timestamps stored in UTC
- [ ] Daily aggregation filters by correct date
- [ ] Monthly grouping uses correct month boundaries

---

### 3. Edge Cases

**Negative P&L:**
- [ ] Entry=$150, Exit=$140, Shares=100
- [ ] P&L = -$1,000 ✅
- [ ] Shows 🔴 red indicator
- [ ] ROI shows negative %

**Large Numbers:**
- [ ] Entry=$5000, Exit=$5500, Shares=1000
- [ ] P&L = $500,000 (formatted with commas)
- [ ] ROI = 10% (handles correctly)

**Fractional Shares (if supported):**
- [ ] Position size = 10.5 shares
- [ ] P&L calculation includes decimal
- [ ] Display shows correct precision

**Zero Entry Price:**
- [ ] Form prevents entry of 0 (min_value=0.01)
- [ ] ✅ Validation works

---

## D. ERROR HANDLING

- [ ] Missing Supabase credentials → shows error
- [ ] Network timeout → shows error message
- [ ] Invalid email format → rejected by form
- [ ] Duplicate email signup → "Email already registered" error
- [ ] Unauthorized access → redirected to login
- [ ] Trade not found → error message displayed
- [ ] Database connection lost → graceful error

---

## E. UI/UX TESTING

**Visual Polish:**
- [ ] Dark mode consistent across pages
- [ ] Sidebar navigation clear and responsive
- [ ] Status badges color-coded (won=🟢, lost=🔴, pending=🟡)
- [ ] Metric cards styled nicely with borders
- [ ] Tables readable and sortable
- [ ] Buttons have hover states
- [ ] No layout shifts or jank

**Mobile Responsiveness (if applicable):**
- [ ] Dashboard KPIs stack vertically on mobile
- [ ] Table columns wrap or scroll
- [ ] Buttons remain clickable
- [ ] Forms are mobile-friendly

---

## F. PERFORMANCE TESTING

- [ ] Dashboard loads in < 2 seconds
- [ ] Adding trade completes in < 1 second
- [ ] Status update visible within 1 second
- [ ] Analytics page loads even with 1000+ trades
- [ ] Logout happens instantly
- [ ] No console errors in browser dev tools

---

## G. DEPLOYMENT READINESS

- [ ] All secrets configured (SUPABASE_URL, SUPABASE_ANON_KEY)
- [ ] requirements.txt includes all dependencies
- [ ] No hardcoded credentials in code
- [ ] Environment variables used correctly
- [ ] Migration can be run fresh on production database
- [ ] RLS policies tested with multiple users
- [ ] Error messages appropriate for end users
- [ ] Logging enabled for debugging

---

## H. FINAL CHECKLIST

- [ ] **All A-G tests passed**
- [ ] **No critical bugs**
- [ ] **Documentation complete**
- [ ] **Ready for Streamlit Cloud deployment**
- [ ] **Telegram notification working** (optional)

---

## Test Results Summary

**Date:** ___________
**Tester:** ___________
**Result:** ✅ PASSED / ❌ FAILED

| Test Category | Status | Notes |
|---|---|---|
| Database Connection | ✅ | All tables created |
| Authentication | ✅ | Login/signup working |
| Dashboard | ✅ | KPIs displaying correctly |
| Log Trade | ✅ | Trade creation working |
| Manage Trades | ✅ | Status cycling working |
| Analytics | ✅ | Monthly data aggregating |
| Multi-User | ✅ | RLS policies enforced |
| Data Integrity | ✅ | Calculations accurate |
| Error Handling | ✅ | Graceful error messages |
| UI/UX | ✅ | Dark mode, responsive |
| Performance | ✅ | < 2s dashboard load |
| Deployment Ready | ✅ | All secrets configured |

---

## Known Issues / Improvements for v3.6+

- [ ] Add trade history export (CSV)
- [ ] Performance: Add caching for monthly aggregations
- [ ] Add trade notes full-text search
- [ ] Add portfolio allocation pie chart
- [ ] Add trade duration tracking (entry to close)
- [ ] Add largest win/loss badges

---

**Ready for deployment to Streamlit Cloud?** ✅ YES / ❌ NO

