# Supabase Schema — Paper Trading System

## Tables Overview

```
┌─────────────────────────────────────────┐
│ users                                   │ ← Authenticated via Supabase Auth
├─────────────────────────────────────────┤
│ id (UUID, PK)                          │
│ email (TEXT, unique)                   │
│ created_at (TIMESTAMP)                 │
│ updated_at (TIMESTAMP)                 │
└─────────────────────────────────────────┘
           ↓ (foreign key)
┌─────────────────────────────────────────┐
│ paper_trades (ALL trades, logged)       │
├─────────────────────────────────────────┤
│ id (UUID, PK)                          │
│ user_id (UUID, FK → users.id)          │
│ ticker (TEXT)                          │
│ entry_price (DECIMAL)                  │
│ exit_price (DECIMAL, nullable)         │
│ entry_date (TIMESTAMP)                 │
│ exit_date (TIMESTAMP, nullable)        │
│ position_size (INTEGER)                │
│ entry_reason (TEXT, notes)             │
│ status (ENUM: 'open', 'closed')        │
│ created_at (TIMESTAMP)                 │
│ updated_at (TIMESTAMP)                 │
│ is_saved (BOOLEAN, default: false)     │
└─────────────────────────────────────────┘
           ↓ (one-to-one, when saved)
┌─────────────────────────────────────────┐
│ saved_trades (Dashboard trades)         │
├─────────────────────────────────────────┤
│ id (UUID, PK)                          │
│ user_id (UUID, FK → users.id)          │
│ paper_trade_id (UUID, FK → paper_trades.id) │
│ daily_status (ENUM: 'won', 'lost', 'pending') │
│ pnl (DECIMAL) ← calculated from prices │
│ roi_percent (DECIMAL)                  │
│ notes (TEXT)                           │
│ saved_date (TIMESTAMP)                 │
│ created_at (TIMESTAMP)                 │
│ updated_at (TIMESTAMP)                 │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ daily_status_log (History tracking)     │
├─────────────────────────────────────────┤
│ id (UUID, PK)                          │
│ saved_trade_id (UUID, FK)              │
│ status (ENUM: 'won', 'lost', 'pending')│
│ pnl (DECIMAL)                          │
│ roi_percent (DECIMAL)                  │
│ checked_date (DATE)                    │
│ created_at (TIMESTAMP)                 │
└─────────────────────────────────────────┘
```

---

## Detailed Tables

### 1. `users` (Supabase Auth)
```sql
CREATE TABLE users (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  email TEXT UNIQUE NOT NULL,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);
```
**RLS:** Each user can only read/write their own records.

---

### 2. `paper_trades` (All trades, optional save)
```sql
CREATE TABLE paper_trades (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

  -- Stock info
  ticker TEXT NOT NULL,

  -- Entry
  entry_price DECIMAL(12,2) NOT NULL,
  entry_date TIMESTAMP NOT NULL,
  entry_reason TEXT,

  -- Exit (nullable until closed)
  exit_price DECIMAL(12,2),
  exit_date TIMESTAMP,

  -- Trade details
  position_size INTEGER NOT NULL,
  status ENUM ('open', 'closed') DEFAULT 'open',

  -- Metadata
  is_saved BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_paper_trades_user_id ON paper_trades(user_id);
CREATE INDEX idx_paper_trades_ticker ON paper_trades(ticker);
CREATE INDEX idx_paper_trades_status ON paper_trades(status);
CREATE INDEX idx_paper_trades_created_at ON paper_trades(created_at);
```

**RLS:**
```sql
-- Users see only their trades
CREATE POLICY "users_see_own_trades"
  ON paper_trades FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "users_insert_own_trades"
  ON paper_trades FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "users_update_own_trades"
  ON paper_trades FOR UPDATE
  USING (auth.uid() = user_id);

CREATE POLICY "users_delete_own_trades"
  ON paper_trades FOR DELETE
  USING (auth.uid() = user_id);
```

---

### 3. `saved_trades` (Dashboard trades)
```sql
CREATE TABLE saved_trades (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  paper_trade_id UUID NOT NULL REFERENCES paper_trades(id) ON DELETE CASCADE,

  -- Daily tracking
  daily_status ENUM ('won', 'lost', 'pending') DEFAULT 'pending',

  -- P&L calculated
  pnl DECIMAL(12,2) GENERATED ALWAYS AS
    (exit_price IS NOT NULL ?
      ((exit_price - entry_price) * position_size) : NULL) STORED,
  roi_percent DECIMAL(8,4) GENERATED ALWAYS AS
    (exit_price IS NOT NULL ?
      (((exit_price - entry_price) / entry_price) * 100) : NULL) STORED,

  notes TEXT,
  saved_date TIMESTAMP DEFAULT NOW(),
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_saved_trades_user_id ON saved_trades(user_id);
CREATE INDEX idx_saved_trades_daily_status ON saved_trades(daily_status);
CREATE INDEX idx_saved_trades_saved_date ON saved_trades(saved_date);
```

**RLS:** Same as paper_trades (user isolation)

---

### 4. `daily_status_log` (History)
```sql
CREATE TABLE daily_status_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  saved_trade_id UUID NOT NULL REFERENCES saved_trades(id) ON DELETE CASCADE,

  status ENUM ('won', 'lost', 'pending') NOT NULL,
  pnl DECIMAL(12,2),
  roi_percent DECIMAL(8,4),
  checked_date DATE NOT NULL,

  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_daily_status_log_saved_trade_id
  ON daily_status_log(saved_trade_id);
CREATE INDEX idx_daily_status_log_checked_date
  ON daily_status_log(checked_date);
```

---

## Views for Dashboard Aggregation

```sql
-- Daily summary
CREATE VIEW user_daily_summary AS
SELECT
  user_id,
  DATE(saved_date) as trade_date,
  COUNT(*) as total_trades,
  SUM(CASE WHEN daily_status = 'won' THEN 1 ELSE 0 END) as wins,
  SUM(CASE WHEN daily_status = 'lost' THEN 1 ELSE 0 END) as losses,
  SUM(pnl) as daily_pnl,
  AVG(roi_percent) as avg_roi
FROM saved_trades
GROUP BY user_id, DATE(saved_date);

-- Monthly summary
CREATE VIEW user_monthly_summary AS
SELECT
  user_id,
  DATE_TRUNC('month', saved_date) as month,
  COUNT(*) as total_trades,
  SUM(CASE WHEN daily_status = 'won' THEN 1 ELSE 0 END) as wins,
  SUM(pnl) as monthly_pnl,
  (SUM(CASE WHEN daily_status = 'won' THEN 1 ELSE 0 END) * 100.0 / COUNT(*)) as win_rate
FROM saved_trades
GROUP BY user_id, DATE_TRUNC('month', saved_date);
```

---

## Security & Performance

✅ **RLS Policies** — Each user isolated
✅ **Indexes** — Fast queries on user_id, ticker, date
✅ **Foreign Keys** — Data integrity
✅ **Generated Columns** — P&L calculated automatically
✅ **Audit Trail** — created_at, updated_at timestamps

---

## Data Flow

```
trade_app.py (User enters trade)
  ↓
POST /api/paper-trades
  ↓
Supabase: INSERT into paper_trades (all trades logged)
  ↓
[Daily Review]
  ↓
User chooses: SAVE or DISCARD
  ↓
IF SAVE:
  POST /api/trades/{id}/save
    ↓
    INSERT into saved_trades (dashboard trades)
    ↓
    UPDATE daily_status based on exit_price
```

---

**Ready to implement? Approve schema design.**
