# Supabase Setup Guide — Paper Trading

## Prerequisites

1. ✅ Supabase account (free tier OK)
2. ✅ Project created
3. ✅ Get: `SUPABASE_URL` + `SUPABASE_ANON_KEY`

---

## Step 1: Run Migration

In Supabase Dashboard → SQL Editor:

1. Copy entire contents of: `supabase/migrations/001_paper_trading_schema.sql`
2. Paste into new query
3. Run
4. Verify all tables created

**Tables to verify:**
- `users`
- `paper_trades`
- `saved_trades`
- `daily_status_log`

---

## Step 2: Environment Variables

Create/update `.env.local` in project root:

```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key-here
```

---

## Step 3: Auth Setup (trade_app.py)

Add login check at top of trade_app.py:

```python
from supabase import create_client, Client

# Supabase Auth
SUPABASE_URL = st.secrets.get("SUPABASE_URL")
SUPABASE_KEY = st.secrets.get("SUPABASE_ANON_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Check if user logged in
if "user" not in st.session_state:
    with st.container():
        st.header("📈 TradeIQ — Paper Trading")
        col1, col2 = st.columns(2)
        with col1:
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            if st.button("Sign In", use_container_width=True):
                try:
                    user = supabase.auth.sign_in_with_password(
                        {"email": email, "password": password}
                    )
                    st.session_state.user = user.user
                    st.session_state.session = user.session
                    st.rerun()
                except Exception as e:
                    st.error(f"Login failed: {e}")
        with col2:
            reg_email = st.text_input("Register Email")
            reg_password = st.text_input("Register Password", type="password")
            if st.button("Sign Up", use_container_width=True):
                try:
                    user = supabase.auth.sign_up(
                        {"email": reg_email, "password": reg_password}
                    )
                    st.success("Signed up! Please sign in.")
                except Exception as e:
                    st.error(f"Signup failed: {e}")
    st.stop()

# User is logged in
user_id = st.session_state.user.id
st.sidebar.write(f"👤 {st.session_state.user.email}")
if st.sidebar.button("Sign Out"):
    supabase.auth.sign_out()
    st.session_state.clear()
    st.rerun()
```

---

## Step 4: API Functions (Create `lib/supabase_client.py`)

```python
import os
from supabase import create_client, Client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

class PaperTrading:
    @staticmethod
    def log_trade(user_id: str, ticker: str, entry_price: float,
                  position_size: int, entry_reason: str = None):
        """Log a trade (always saved, user can save later)"""
        data = supabase.table("paper_trades").insert({
            "user_id": user_id,
            "ticker": ticker,
            "entry_price": entry_price,
            "entry_date": "NOW()",
            "position_size": position_size,
            "entry_reason": entry_reason,
            "status": "open"
        }).execute()
        return data.data[0] if data.data else None

    @staticmethod
    def save_trade(user_id: str, paper_trade_id: str,
                   exit_price: float, notes: str = None):
        """Save trade to dashboard after exit"""
        # Update paper_trades to closed
        supabase.table("paper_trades").update({
            "exit_price": exit_price,
            "exit_date": "NOW()",
            "status": "closed",
            "is_saved": True
        }).eq("id", paper_trade_id).execute()

        # Insert into saved_trades
        pnl = (exit_price - entry_price) * position_size
        roi = ((exit_price - entry_price) / entry_price) * 100

        saved = supabase.table("saved_trades").insert({
            "user_id": user_id,
            "paper_trade_id": paper_trade_id,
            "daily_status": "pending",
            "pnl": pnl,
            "roi_percent": roi,
            "notes": notes
        }).execute()
        return saved.data[0] if saved.data else None

    @staticmethod
    def update_daily_status(saved_trade_id: str, status: str):
        """Update trade status (won/lost)"""
        supabase.table("saved_trades").update({
            "daily_status": status
        }).eq("id", saved_trade_id).execute()

    @staticmethod
    def get_user_dashboard(user_id: str):
        """Get dashboard data"""
        daily = supabase.rpc("user_daily_summary", {"user_id": user_id}).execute()
        monthly = supabase.rpc("user_monthly_summary", {"user_id": user_id}).execute()
        trades = supabase.table("saved_trades")\
            .select("*")\
            .eq("user_id", user_id)\
            .order("saved_date", desc=True)\
            .execute()
        return {
            "daily": daily.data,
            "monthly": monthly.data,
            "trades": trades.data
        }
```

---

## Step 5: Streamlit Integration

After login, add Paper Trading tab:

```python
tab1, tab2, tab3 = st.tabs(["📊 Calculator", "📈 Paper Trading", "📝 Journal"])

with tab2:
    st.header("Paper Trading Dashboard")

    dashboard = PaperTrading.get_user_dashboard(user_id)

    # KPI Cards
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Trades", len(dashboard["trades"]))
    with col2:
        wins = sum(1 for t in dashboard["trades"] if t["daily_status"] == "won")
        st.metric("Wins", wins)
    with col3:
        total_pnl = sum(t["pnl"] for t in dashboard["trades"] if t["pnl"])
        st.metric("Total P&L", f"${total_pnl:,.2f}")
    with col4:
        win_rate = (wins / len(dashboard["trades"]) * 100) if dashboard["trades"] else 0
        st.metric("Win Rate", f"{win_rate:.1f}%")

    # Trades Table
    st.dataframe(dashboard["trades"], use_container_width=True)
```

---

## Deployment Checklist

- [ ] Migration ran successfully
- [ ] Environment variables set in Streamlit Cloud
- [ ] Login flow tested locally
- [ ] Trade logging works
- [ ] Dashboard loads data
- [ ] Daily status updates work
- [ ] Multi-user isolation verified (RLS)

---

**Ready to proceed with Phase 2 (APIs)?**
