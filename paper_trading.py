"""
TradeIQ Paper Trading Dashboard
Multi-user paper trading system with daily status tracking
"""

import streamlit as st
from lib.auth import require_login, show_logout_button, get_current_user_id
from lib.supabase_client import get_supabase_client
from datetime import date, timedelta
import pandas as pd
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==========================================
# PAGE CONFIGURATION
# ==========================================

st.set_page_config(
    page_title="TradeIQ - Paper Trading",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .metric-card {
        background: #0e0e1c;
        border: 1px solid #2a2a48;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
    }
    .metric-value {
        font-size: 32px;
        font-weight: 900;
        color: #2DD4A0;
    }
    .metric-label {
        font-size: 12px;
        color: #9090B8;
        margin-top: 8px;
        text-transform: uppercase;
    }
    .status-won {
        background: #2DD4A018;
        color: #2DD4A0;
        padding: 4px 8px;
        border-radius: 4px;
        font-weight: 700;
    }
    .status-lost {
        background: #E05F5F18;
        color: #E05F5F;
        padding: 4px 8px;
        border-radius: 4px;
        font-weight: 700;
    }
    .status-pending {
        background: #C8A96E18;
        color: #C8A96E;
        padding: 4px 8px;
        border-radius: 4px;
        font-weight: 700;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# MAIN APP
# ==========================================

def main():
    """Main app logic"""

    # Check authentication
    if not require_login():
        return

    user_id = get_current_user_id()
    supabase = get_supabase_client()

    # Sidebar
    with st.sidebar:
        st.title("📊 TradeIQ")
        st.write(f"**Paper Trading System**")
        st.divider()

        # Navigation
        page = st.radio(
            "Navigation",
            ["📈 Dashboard", "📝 Log Trade", "✏️ Manage Trades", "📊 Analytics"],
            label_visibility="collapsed"
        )

        st.divider()
        show_logout_button()

    # ==========================================
    # PAGE: DASHBOARD
    # ==========================================

    if page == "📈 Dashboard":
        st.title("📈 Trading Dashboard")

        # Get today's stats
        daily_stats = supabase.get_daily_stats(user_id)

        if daily_stats["success"]:
            # KPI Row 1
            col1, col2, col3, col4, col5 = st.columns(5)

            with col1:
                st.metric("Total Trades", daily_stats["total"], delta=None)

            with col2:
                st.metric("✅ Wins", daily_stats["wins"])

            with col3:
                st.metric("❌ Losses", daily_stats["losses"])

            with col4:
                st.metric("⏳ Pending", daily_stats["pending"])

            with col5:
                win_rate = daily_stats["win_rate"]
                st.metric("Win Rate", f"{win_rate:.1f}%")

            st.divider()

            # KPI Row 2
            col1, col2, col3 = st.columns(3)

            with col1:
                pnl = daily_stats["total_pnl"]
                pnl_color = "🟢" if pnl >= 0 else "🔴"
                st.metric("Total P&L", f"{pnl_color} ${pnl:,.2f}")

            with col2:
                roi = daily_stats["avg_roi"]
                roi_color = "🟢" if roi >= 0 else "🔴"
                st.metric("Avg ROI", f"{roi_color} {roi:.2f}%")

            with col3:
                st.metric("Date", daily_stats["date"])

            st.divider()

            # Trades Table
            st.subheader("Today's Trades")

            if daily_stats["trades"]:
                trades_df = pd.DataFrame(daily_stats["trades"])
                trades_df = trades_df[[
                    "ticker", "pnl", "roi_percent", "daily_status", "notes"
                ]].rename(columns={
                    "ticker": "📊 Ticker",
                    "pnl": "P&L",
                    "roi_percent": "ROI %",
                    "daily_status": "Status",
                    "notes": "Notes"
                })

                st.dataframe(trades_df, use_container_width=True, hide_index=True)
            else:
                st.info("📭 No trades yet. Log your first trade!")

        else:
            st.error(f"❌ Failed to load dashboard: {daily_stats.get('error')}")

    # ==========================================
    # PAGE: LOG TRADE
    # ==========================================

    elif page == "📝 Log Trade":
        st.title("📝 Log New Trade")

        with st.form("log_trade_form"):
            col1, col2 = st.columns(2)

            with col1:
                ticker = st.text_input(
                    "Stock Ticker",
                    placeholder="AAPL, TEVA.TA, etc.",
                    max_chars=10
                ).upper()

                entry_price = st.number_input(
                    "Entry Price ($)",
                    min_value=0.01,
                    step=0.01,
                    format="%.2f"
                )

                position_size = st.number_input(
                    "Position Size (shares)",
                    min_value=1,
                    step=1,
                    value=100
                )

            with col2:
                exit_price = st.number_input(
                    "Exit Price ($) - Optional",
                    min_value=0.0,
                    step=0.01,
                    format="%.2f",
                    help="Leave blank if trade is still open"
                )

                entry_reason = st.text_area(
                    "Entry Reason / Notes",
                    placeholder="Why did you enter this trade?",
                    height=80
                )

            submitted = st.form_submit_button("Log Trade", use_container_width=True, type="primary")

            if submitted:
                if not ticker or entry_price <= 0 or position_size <= 0:
                    st.error("❌ Please fill in all required fields")
                else:
                    # Log the trade
                    result = supabase.log_paper_trade(
                        user_id=user_id,
                        ticker=ticker,
                        entry_price=entry_price,
                        position_size=position_size,
                        entry_reason=entry_reason
                    )

                    if result["success"]:
                        trade_id = result["trade"]["id"]
                        st.success("✅ Trade logged!")

                        # If exit price provided, close it
                        if exit_price > 0:
                            close_result = supabase.close_paper_trade(trade_id, exit_price)
                            if close_result["success"]:
                                st.success("✅ Trade closed!")

                                # Ask if user wants to save
                                if st.button("💾 Save to Dashboard", use_container_width=True):
                                    save_result = supabase.save_trade_to_dashboard(
                                        user_id=user_id,
                                        paper_trade_id=trade_id,
                                        entry_price=entry_price,
                                        exit_price=exit_price,
                                        position_size=position_size,
                                        notes=entry_reason
                                    )
                                    if save_result["success"]:
                                        st.success("✅ Trade saved to dashboard!")
                                        st.rerun()
                    else:
                        st.error(f"❌ Failed to log trade: {result.get('error')}")

    # ==========================================
    # PAGE: MANAGE TRADES
    # ==========================================

    elif page == "✏️ Manage Trades":
        st.title("✏️ Manage Saved Trades")

        # Get saved trades
        trades_result = supabase.get_user_saved_trades(user_id)

        if trades_result["success"] and trades_result["trades"]:
            trades = trades_result["trades"]

            # Filter by status
            status_filter = st.selectbox(
                "Filter by Status",
                ["All", "Won", "Lost", "Pending"],
                key="status_filter"
            )

            if status_filter != "All":
                trades = [t for t in trades if t["daily_status"].lower() == status_filter.lower()]

            # Display trades
            for trade in trades:
                with st.container():
                    col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 1])

                    with col1:
                        st.write(f"**{trade['paper_trade_id'][:8]}...** - {trade['notes'][:50] if trade['notes'] else 'No notes'}")

                    with col2:
                        pnl = trade.get("pnl", 0)
                        pnl_color = "🟢" if pnl >= 0 else "🔴"
                        st.write(f"{pnl_color} ${pnl:,.2f}")

                    with col3:
                        roi = trade.get("roi_percent", 0)
                        st.write(f"{roi:.2f}%")

                    with col4:
                        status = trade["daily_status"]
                        if st.button(
                            status.upper(),
                            key=f"status_{trade['id']}",
                            help="Click to change status"
                        ):
                            # Cycle through statuses
                            status_cycle = {"won": "lost", "lost": "pending", "pending": "won"}
                            new_status = status_cycle.get(status, "pending")
                            update_result = supabase.update_trade_status(trade['id'], new_status)
                            if update_result["success"]:
                                st.success(f"✅ Status updated to {new_status.upper()}")
                                st.rerun()

                    with col5:
                        if st.button("🗑️", key=f"delete_{trade['id']}"):
                            del_result = supabase.delete_trade(trade['id'])
                            if del_result["success"]:
                                st.success("✅ Trade deleted!")
                                st.rerun()

                    st.divider()

        else:
            st.info("📭 No saved trades yet. Log and save a trade first!")

    # ==========================================
    # PAGE: ANALYTICS
    # ==========================================

    elif page == "📊 Analytics":
        st.title("📊 Monthly Analytics")

        monthly_result = supabase.get_monthly_summary(user_id)

        if monthly_result["success"]:
            col1, col2 = st.columns(2)

            with col1:
                st.metric("Total Trades (All Time)", monthly_result["total_trades"])

            with col2:
                st.metric("Total P&L (All Time)", f"${monthly_result['total_pnl']:,.2f}")

            st.divider()
            st.subheader("Monthly Summary")

            if monthly_result["monthly"]:
                monthly_df = pd.DataFrame(monthly_result["monthly"])
                st.dataframe(monthly_df, use_container_width=True, hide_index=True)

                # Charts
                col1, col2 = st.columns(2)

                with col1:
                    st.bar_chart(
                        monthly_df.set_index("month")["win_rate"],
                        title="Win Rate by Month"
                    )

                with col2:
                    st.bar_chart(
                        monthly_df.set_index("month")["pnl"],
                        title="P&L by Month"
                    )
            else:
                st.info("📭 No data yet. Log some trades first!")

        else:
            st.error(f"❌ Failed to load analytics: {monthly_result.get('error')}")


if __name__ == "__main__":
    main()
