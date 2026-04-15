-- Migration: Paper Trading System Schema
-- Date: 2026-04-15
-- Description: Multi-user paper trading with daily status tracking

-- ==========================================
-- 1. ENUMS
-- ==========================================

CREATE TYPE trade_status AS ENUM ('open', 'closed');
CREATE TYPE daily_status AS ENUM ('won', 'lost', 'pending');

-- ==========================================
-- 2. USERS TABLE (references auth.users)
-- ==========================================

CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  email TEXT UNIQUE NOT NULL,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Enable RLS
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

CREATE POLICY "users_see_own_data"
  ON users FOR SELECT
  USING (auth.uid() = id);

-- ==========================================
-- 3. PAPER_TRADES TABLE (ALL trades)
-- ==========================================

CREATE TABLE IF NOT EXISTS paper_trades (
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
  status trade_status DEFAULT 'open',

  -- Metadata
  is_saved BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_paper_trades_user_id
  ON paper_trades(user_id);
CREATE INDEX IF NOT EXISTS idx_paper_trades_ticker
  ON paper_trades(ticker);
CREATE INDEX IF NOT EXISTS idx_paper_trades_status
  ON paper_trades(status);
CREATE INDEX IF NOT EXISTS idx_paper_trades_created_at
  ON paper_trades(created_at DESC);

-- RLS
ALTER TABLE paper_trades ENABLE ROW LEVEL SECURITY;

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

-- ==========================================
-- 4. SAVED_TRADES TABLE (Dashboard trades)
-- ==========================================

CREATE TABLE IF NOT EXISTS saved_trades (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  paper_trade_id UUID NOT NULL REFERENCES paper_trades(id) ON DELETE CASCADE,

  -- Daily tracking
  daily_status daily_status DEFAULT 'pending',

  -- P&L (calculated from paper_trades)
  pnl DECIMAL(12,2),
  roi_percent DECIMAL(8,4),

  notes TEXT,
  saved_date TIMESTAMP DEFAULT NOW(),
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_saved_trades_user_id
  ON saved_trades(user_id);
CREATE INDEX IF NOT EXISTS idx_saved_trades_daily_status
  ON saved_trades(daily_status);
CREATE INDEX IF NOT EXISTS idx_saved_trades_saved_date
  ON saved_trades(saved_date DESC);

-- RLS
ALTER TABLE saved_trades ENABLE ROW LEVEL SECURITY;

CREATE POLICY "users_see_own_saved_trades"
  ON saved_trades FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "users_insert_own_saved_trades"
  ON saved_trades FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "users_update_own_saved_trades"
  ON saved_trades FOR UPDATE
  USING (auth.uid() = user_id);

CREATE POLICY "users_delete_own_saved_trades"
  ON saved_trades FOR DELETE
  USING (auth.uid() = user_id);

-- ==========================================
-- 5. DAILY_STATUS_LOG TABLE (History)
-- ==========================================

CREATE TABLE IF NOT EXISTS daily_status_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  saved_trade_id UUID NOT NULL REFERENCES saved_trades(id) ON DELETE CASCADE,

  status daily_status NOT NULL,
  pnl DECIMAL(12,2),
  roi_percent DECIMAL(8,4),
  checked_date DATE NOT NULL,

  created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_daily_status_log_saved_trade_id
  ON daily_status_log(saved_trade_id);
CREATE INDEX IF NOT EXISTS idx_daily_status_log_checked_date
  ON daily_status_log(checked_date DESC);

-- RLS (inherit from saved_trades via foreign key)
ALTER TABLE daily_status_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY "users_see_own_status_log"
  ON daily_status_log FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM saved_trades
      WHERE saved_trades.id = daily_status_log.saved_trade_id
      AND saved_trades.user_id = auth.uid()
    )
  );

-- ==========================================
-- 6. DASHBOARD VIEWS
-- ==========================================

CREATE OR REPLACE VIEW user_daily_summary AS
SELECT
  user_id,
  DATE(saved_date) as trade_date,
  COUNT(*) as total_trades,
  SUM(CASE WHEN daily_status = 'won' THEN 1 ELSE 0 END) as wins,
  SUM(CASE WHEN daily_status = 'lost' THEN 1 ELSE 0 END) as losses,
  SUM(CASE WHEN daily_status = 'pending' THEN 1 ELSE 0 END) as pending,
  SUM(pnl) as daily_pnl,
  ROUND(AVG(roi_percent), 2) as avg_roi
FROM saved_trades
GROUP BY user_id, DATE(saved_date);

CREATE OR REPLACE VIEW user_monthly_summary AS
SELECT
  user_id,
  DATE_TRUNC('month', saved_date)::DATE as month_start,
  COUNT(*) as total_trades,
  SUM(CASE WHEN daily_status = 'won' THEN 1 ELSE 0 END) as wins,
  SUM(CASE WHEN daily_status = 'lost' THEN 1 ELSE 0 END) as losses,
  SUM(pnl) as monthly_pnl,
  ROUND(
    (SUM(CASE WHEN daily_status = 'won' THEN 1 ELSE 0 END)::NUMERIC / COUNT(*)) * 100,
    2
  ) as win_rate_percent
FROM saved_trades
GROUP BY user_id, DATE_TRUNC('month', saved_date);

-- ==========================================
-- 7. SEED DATA (optional)
-- ==========================================

-- (None for now - users created via auth)

-- ==========================================
-- END MIGRATION
-- ==========================================
