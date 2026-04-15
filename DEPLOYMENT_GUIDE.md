# Deployment Guide — Paper Trading System v3.5

## Overview

This guide covers deploying the Paper Trading System to Streamlit Cloud with Supabase as the backend.

**Architecture:**
- **Frontend:** Streamlit (paper_trading.py) on Streamlit Cloud
- **Backend:** Supabase PostgreSQL with RLS
- **Auth:** Supabase native auth (email/password)

---

## Prerequisites

✅ Completed before deployment:
- Supabase project created
- Migration run (001_paper_trading_schema.sql)
- Local testing passed (TESTING_CHECKLIST.md)
- GitHub repo with all code
- Telegram bot token configured (optional)

---

## Deployment Steps

### STEP 1: Prepare Supabase

#### 1a. Create Supabase Project
1. Go to https://supabase.com
2. Sign in or create account (free tier OK)
3. Click "New Project"
4. Fill in:
   - Project Name: `tradeiq` (or your name)
   - Database Password: Generate strong password (save it!)
   - Region: Choose closest to you
5. Click "Create new project" (wait ~2 min)

#### 1b. Get API Keys
1. Go to Project Settings → API
2. Copy these values (you'll need them):
   - **Project URL** (SUPABASE_URL)
   - **Anon Key** (SUPABASE_ANON_KEY)
   - **Service Role Key** (for migrations only, not needed in app)

**Example:**
```
SUPABASE_URL = https://abcdefgh.supabase.co
SUPABASE_ANON_KEY = eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

#### 1c. Run Migration
1. In Supabase Dashboard, go to **SQL Editor**
2. Click "New Query"
3. Copy entire contents of: `supabase/migrations/001_paper_trading_schema.sql`
4. Paste into SQL editor
5. Click "Run" (or Ctrl+Enter)
6. Should complete with no errors

**Verify tables exist:**
```sql
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;
```

Expected output:
```
daily_status_log
paper_trades
saved_trades
users
```

---

### STEP 2: Push Code to GitHub

#### 2a. Create GitHub Repository (if not exists)
```bash
cd "C:\Users\arikg\projects\stock calculator"
git status

# If no git repo:
git init
git config user.name "Your Name"
git config user.email "your@email.com"
git add .
git commit -m "Initial commit: Paper trading system v3.5"
git branch -M main
```

#### 2b. Create GitHub Remote
1. Go to https://github.com/new
2. Create repo named `stock-calculator` (or existing)
3. Copy SSH/HTTPS URL
4. Add remote:
```bash
git remote add origin https://github.com/YOUR_USERNAME/stock-calculator.git
git push -u origin main
```

---

### STEP 3: Deploy to Streamlit Cloud

#### 3a. Connect Streamlit Cloud
1. Go to https://streamlit.io/cloud
2. Click "Sign up with GitHub" (or create account)
3. Authorize Streamlit to access your repos
4. Click "New app"

#### 3b. Fill Deployment Form
- **GitHub repo:** YOUR_USERNAME/stock-calculator
- **Branch:** main
- **Main file path:** paper_trading.py
- Click "Deploy"

*First deployment takes ~5 minutes. Streamlit installs dependencies from requirements.txt*

#### 3c. Add Secrets
After deployment starts, click app → Settings (⚙️) → Secrets:

Paste this into secrets editor:
```toml
# Supabase Configuration
supabase_url = "https://your-project.supabase.co"
supabase_anon_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

# Optional: Telegram notifications
telegram_bot_token = "your-token-here"
telegram_chat_id = "your-chat-id"
```

Save secrets → app redeploys automatically

---

### STEP 4: First-Time Setup in Production

#### 4a. Access App
URL will be: `https://[app-name].streamlit.app`

#### 4b. Create First Account
1. Go to "Sign Up" tab
2. Email: `your@email.com`
3. Password: `secure_password_min_6_chars`
4. Click "Sign Up"

#### 4c. Sign In
1. Go to "Sign In" tab
2. Same email/password
3. Should see dashboard with 0 trades

#### 4d. Test Functionality
1. **Log Trade:** Create a test trade (AAPL, entry $150, exit $160)
2. **Dashboard:** Should show 1 pending trade
3. **Manage Trades:** Status should cycle Won → Lost → Pending
4. **Analytics:** Should show monthly summary

---

## Configuration

### Environment Variables Checklist

In Streamlit Cloud Secrets (Settings → Secrets):
- [ ] `supabase_url` — Project URL from Step 1b
- [ ] `supabase_anon_key` — Anon key from Step 1b
- [ ] `telegram_bot_token` (optional) — For Telegram notifications
- [ ] `telegram_chat_id` (optional) — Your Telegram chat ID

### Local Development (Optional)

Create `.streamlit/secrets.toml` locally:
```toml
supabase_url = "https://your-project.supabase.co"
supabase_anon_key = "eyJ..."
telegram_bot_token = "optional"
telegram_chat_id = "optional"
```

Then run locally:
```bash
streamlit run paper_trading.py
```

---

## Post-Deployment Verification

### Checklist

- [ ] App loads at Streamlit Cloud URL
- [ ] Sign up works (create test account)
- [ ] Sign in works (with new account)
- [ ] Dashboard shows 0 trades
- [ ] Can log a trade
- [ ] Trade appears in dashboard
- [ ] Can save trade (if logged with exit price)
- [ ] Can update trade status
- [ ] Can delete trade
- [ ] Multi-user isolation works (sign in with 2nd account, see different data)
- [ ] Analytics page loads
- [ ] No error messages in browser console (F12 → Console)

---

## Monitoring & Troubleshooting

### App Status
1. Go to https://share.streamlit.io
2. Click your app
3. View deployment logs (top right corner)

### Common Issues

#### ❌ "Missing SUPABASE_URL or SUPABASE_ANON_KEY"
- **Fix:** Check Secrets in Settings. Keys must match exactly.
- Redeploy: Settings → Reboot script

#### ❌ "Connection refused" / Database errors
- **Fix:** Check SUPABASE_URL is correct (should be https://...)
- Run migration again in Supabase SQL Editor

#### ❌ "Invalid API Key" after login
- **Fix:** Verify SUPABASE_ANON_KEY in Secrets (not Service Key)
- Check Supabase → Settings → API → Anon Key

#### ❌ "RLS policy violation"
- **Fix:** Ensure RLS policies created in migration
- Check Supabase → Database → RLS on each table

#### ❌ "Internal error during sign up"
- **Fix:** In Supabase → Settings → Auth, ensure Email provider is enabled
- Check for duplicate email in previous sign ups

### View Logs
```bash
# Local development
streamlit run paper_trading.py  # Logs appear in terminal

# Streamlit Cloud
# Go to https://share.streamlit.io → click app → Logs (top right)
```

---

## Performance Tuning

### Dashboard Load Time
If dashboard is slow (> 3s):

1. **Add query caching** (already in supabase_client.py via @st.cache_resource)
2. **Limit trades returned:** Modify `get_user_saved_trades()` limit
3. **Use database indexes** (already created in migration)

### Concurrent Users
Supabase free tier: ~50 concurrent connections OK

For 100+ users: Consider Streamlit Teams plan + Supabase Pro

---

## Scaling Considerations

### Current Limits
- Supabase Free: 500MB database, 5GB bandwidth/month
- Streamlit Cloud Free: 3 apps, 1GB storage
- Good for: 5-50 active users

### When to Scale
- 100+ trades/day → Consider Supabase Pro ($25/mo)
- 50+ concurrent users → Consider Streamlit Teams ($20/mo)
- Need dedicated infra → Switch to Supabase managed or AWS RDS

---

## Backup & Recovery

### Database Backups
Supabase automatically backs up daily (free tier, 7-day retention)

**Manual backup:**
```bash
# From Supabase → Database → Backups
# Click "Create backup" → Download
```

### Restore Migration
If database corrupted:
1. Delete all tables in Supabase
2. Run migration again (same SQL)
3. App will reconnect automatically

---

## Security Checklist

- [ ] Never commit `.streamlit/secrets.toml` to GitHub
- [ ] Never log API keys in error messages
- [ ] RLS policies enabled on all tables (verified in migration)
- [ ] SUPABASE_ANON_KEY used (not Service Key)
- [ ] User passwords min 6 characters (enforced in UI)
- [ ] HTTPS only (Streamlit Cloud automatic)
- [ ] No sensitive data in trade notes
- [ ] Multi-user isolation tested (different users see different data)

---

## Version Control & Updates

### Deploying Updates
After code changes:

```bash
git add .
git commit -m "Feature: Add CSV export"
git push origin main
```

Streamlit Cloud auto-detects push → redeploys (1-2 min)

### Database Schema Changes
If adding columns to tables:

1. Create new migration: `supabase/migrations/002_*.sql`
2. Run in Supabase SQL Editor
3. Update `supabase_client.py` methods if needed
4. Commit and push

---

## Rollback Plan

If critical issue in production:

1. **Immediate:** Revert code commit
   ```bash
   git revert HEAD
   git push origin main
   # Streamlit redeploys old version (1-2 min)
   ```

2. **Restore database:** Use Supabase backup
   ```
   Supabase → Database → Backups → Restore
   ```

---

## Monitoring & Alerts (Future)

Add Telegram notifications for:
- [ ] Trade errors
- [ ] Daily summary
- [ ] Weekly analytics
- [ ] Database quota warnings

*See: agents/sales_manager.py for Telegram integration example*

---

## Support & Troubleshooting

### Resources
- Supabase Docs: https://supabase.com/docs
- Streamlit Docs: https://docs.streamlit.io
- GitHub Issues: https://github.com/YOUR_USERNAME/stock-calculator/issues

### Contact
For issues, create GitHub issue with:
- Error message (full text)
- Steps to reproduce
- Screenshots if visual issue
- Browser/OS info

---

## Completion Checklist

Deployment is complete when:

- [x] Supabase project created
- [x] Migration executed
- [x] API keys obtained
- [x] GitHub repo updated
- [x] Streamlit Cloud app deployed
- [x] Secrets configured
- [x] First user created
- [x] Trade workflow tested
- [x] Multi-user verified
- [x] Analytics working
- [x] No errors in logs
- [x] Performance acceptable
- [x] Security checklist passed

---

**Deployment Date:** ___________
**Deployed By:** ___________
**App URL:** https://[your-app].streamlit.app
**Status:** ✅ LIVE

---

## Next Steps (v3.6+)

- [ ] CSV export functionality
- [ ] Trade notes full-text search
- [ ] Portfolio allocation visualization
- [ ] Trade duration tracking
- [ ] Email alerts for large wins/losses
- [ ] Mobile app companion
- [ ] API endpoint for external integrations

