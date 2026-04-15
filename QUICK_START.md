# Paper Trading System — Quick Start (5 Minutes)

**Goal:** Get the paper trading system running locally in 5 minutes.

---

## Prerequisites

✅ You have:
- Python 3.9+ installed
- Git installed
- A Supabase account (free tier OK, sign up at supabase.com)

---

## Step 1: Clone & Install (2 minutes)

```bash
# Navigate to project
cd "C:\Users\arikg\projects\stock calculator"

# Install dependencies
pip install -r requirements.txt
```

**Expected output:** Installs streamlit, pandas, supabase, etc.

---

## Step 2: Get Supabase Credentials (1 minute)

1. Go to https://supabase.com and sign in
2. Create new project (or use existing)
3. Go to **Settings** → **API**
4. Copy these two values:
   - `Project URL` (example: `https://abcdefgh.supabase.co`)
   - `Anon Key` (example: `eyJhbGciOi...` — very long string)

---

## Step 3: Create Secrets File (1 minute)

Create `.streamlit/secrets.toml` in project root:

```toml
supabase_url = "https://your-project-url.supabase.co"
supabase_anon_key = "your-very-long-anon-key-here"
```

**Important:** Never commit this file to Git (already in `.gitignore`)

---

## Step 4: Run Migration (1 minute)

1. In Supabase Dashboard → **SQL Editor**
2. Click "New Query"
3. Copy all contents of: `supabase/migrations/001_paper_trading_schema.sql`
4. Paste into editor
5. Click **Run**

**Expected:** All tables created with no errors

---

## Step 5: Start App (immediate)

```bash
streamlit run paper_trading.py
```

**Expected output:**
```
  You can now view your Streamlit app in your browser.

  Local URL: http://localhost:8501
```

Open http://localhost:8501 in your browser.

---

## Test It (2 minutes)

### 1. Create Account
- Go to "Sign Up" tab
- Email: `test@example.com`
- Password: `password123`
- Click "Sign Up"

### 2. Sign In
- Go to "Sign In" tab
- Same email/password
- Click "Sign In"

### 3. Log a Trade
- Go to "Log Trade" page
- Ticker: `AAPL`
- Entry Price: `150.00`
- Position Size: `100`
- Exit Price: `155.00`
- Click "Log Trade"
- Click "Save to Dashboard"

### 4. Check Dashboard
- Go to "Dashboard" page
- You should see:
  - Total Trades: 1
  - Wins: 0 (pending)
  - P&L: $500.00
  - ROI: 3.33%

### 5. Update Status
- Go to "Manage Trades" page
- Click the status button (should say "PENDING")
- Change to "WON"

### 6. View Analytics
- Go to "Analytics" page
- Should show 1 trade this month
- Win rate: 100%

---

## ✅ Success!

If you got here without errors, **the system is working!**

---

## Deployment (When Ready)

See **DEPLOYMENT_GUIDE.md** for full Streamlit Cloud setup.

Quick version:
1. Push to GitHub
2. Go to streamlit.io/cloud
3. Deploy from repo
4. Add secrets
5. Done!

---

## Troubleshooting

### ❌ "Missing SUPABASE_URL"
- Check `.streamlit/secrets.toml` exists
- Verify values are correct (copy/paste from Supabase again)
- Restart: `Ctrl+C` and `streamlit run paper_trading.py`

### ❌ "Connection refused"
- Verify SUPABASE_URL is correct format (https://...)
- Check migration ran successfully in Supabase

### ❌ "Cannot find module 'supabase'"
- Run: `pip install supabase python-jwt -U`

### ❌ Can't sign up
- In Supabase → Settings → Auth → Email provider must be enabled
- Check no duplicate email in signup

---

## Next Steps

1. **Local Testing:** Follow TESTING_CHECKLIST.md (65 tests)
2. **Deployment:** Follow DEPLOYMENT_GUIDE.md
3. **Documentation:** Read IMPLEMENTATION_SUMMARY.md for full overview

---

## Support

- **Docs:** See DEPLOYMENT_GUIDE.md and SUPABASE_SETUP.md
- **Issues:** Check browser console (F12 → Console tab) for errors
- **Database:** Check Supabase SQL Editor for data

---

**Time Elapsed:** 5-10 minutes
**Status:** ✅ Ready to test!

