"""
Supabase Client — Paper Trading Backend
Handles all database operations with error handling
"""

import streamlit as st
from supabase import create_client, Client
from datetime import datetime, date
from typing import Optional, List, Dict
import logging

logger = logging.getLogger(__name__)

class SupabaseClient:
    def __init__(self):
        """Initialize Supabase client from secrets"""
        self.url = st.secrets.get("supabase_url")
        self.key = st.secrets.get("supabase_anon_key")

        if not self.url or not self.key:
            raise ValueError("Missing SUPABASE_URL or SUPABASE_ANON_KEY in secrets")

        self.client: Client = create_client(self.url, self.key)

    # ==========================================
    # PAPER TRADES (Log all trades)
    # ==========================================

    def log_paper_trade(self, user_id: str, ticker: str, entry_price: float,
                        position_size: int, entry_reason: Optional[str] = None) -> Dict:
        """
        Log a paper trade (always saved to paper_trades table)
        User can decide later whether to save to dashboard
        """
        try:
            data = {
                "user_id": user_id,
                "ticker": ticker,
                "entry_price": float(entry_price),
                "entry_date": datetime.now().isoformat(),
                "position_size": int(position_size),
                "entry_reason": entry_reason,
                "status": "open"
            }

            result = self.client.table("paper_trades").insert(data).execute()

            if result.data:
                logger.info(f"Trade logged: {ticker} @ {entry_price}")
                return {"success": True, "trade": result.data[0]}
            else:
                return {"success": False, "error": "No data returned"}

        except Exception as e:
            logger.error(f"Error logging trade: {e}")
            return {"success": False, "error": str(e)}

    def close_paper_trade(self, trade_id: str, exit_price: float) -> Dict:
        """Mark trade as closed with exit price"""
        try:
            data = {
                "exit_price": float(exit_price),
                "exit_date": datetime.now().isoformat(),
                "status": "closed"
            }

            result = self.client.table("paper_trades")\
                .update(data)\
                .eq("id", trade_id)\
                .execute()

            if result.data:
                logger.info(f"Trade closed: {trade_id}")
                return {"success": True, "trade": result.data[0]}
            else:
                return {"success": False, "error": "Trade not found"}

        except Exception as e:
            logger.error(f"Error closing trade: {e}")
            return {"success": False, "error": str(e)}

    # ==========================================
    # SAVED TRADES (Dashboard trades)
    # ==========================================

    def save_trade_to_dashboard(self, user_id: str, paper_trade_id: str,
                                 entry_price: float, exit_price: float,
                                 position_size: int, notes: Optional[str] = None) -> Dict:
        """
        Save a paper trade to dashboard (saved_trades table)
        Calculates P&L and ROI automatically
        """
        try:
            # Calculate P&L
            pnl = (float(exit_price) - float(entry_price)) * int(position_size)
            roi_percent = ((float(exit_price) - float(entry_price)) / float(entry_price)) * 100

            data = {
                "user_id": user_id,
                "paper_trade_id": paper_trade_id,
                "daily_status": "pending",  # User will mark as won/lost
                "pnl": round(pnl, 2),
                "roi_percent": round(roi_percent, 4),
                "notes": notes,
                "saved_date": datetime.now().isoformat()
            }

            result = self.client.table("saved_trades").insert(data).execute()

            if result.data:
                logger.info(f"Trade saved to dashboard: {paper_trade_id}")
                return {"success": True, "saved_trade": result.data[0]}
            else:
                return {"success": False, "error": "No data returned"}

        except Exception as e:
            logger.error(f"Error saving trade: {e}")
            return {"success": False, "error": str(e)}

    def update_trade_status(self, saved_trade_id: str, status: str) -> Dict:
        """
        Update daily status of saved trade
        Status: 'won', 'lost', or 'pending'
        """
        if status not in ['won', 'lost', 'pending']:
            return {"success": False, "error": f"Invalid status: {status}"}

        try:
            data = {"daily_status": status}

            result = self.client.table("saved_trades")\
                .update(data)\
                .eq("id", saved_trade_id)\
                .execute()

            if result.data:
                logger.info(f"Trade status updated: {saved_trade_id} → {status}")
                return {"success": True, "trade": result.data[0]}
            else:
                return {"success": False, "error": "Trade not found"}

        except Exception as e:
            logger.error(f"Error updating status: {e}")
            return {"success": False, "error": str(e)}

    # ==========================================
    # DASHBOARD (Queries & Aggregation)
    # ==========================================

    def get_user_saved_trades(self, user_id: str, limit: int = 50) -> Dict:
        """Get all saved trades for user (most recent first)"""
        try:
            result = self.client.table("saved_trades")\
                .select("*")\
                .eq("user_id", user_id)\
                .order("saved_date", desc=True)\
                .limit(limit)\
                .execute()

            return {"success": True, "trades": result.data or []}

        except Exception as e:
            logger.error(f"Error fetching trades: {e}")
            return {"success": False, "trades": [], "error": str(e)}

    def get_daily_stats(self, user_id: str, trade_date: Optional[date] = None) -> Dict:
        """
        Get daily statistics
        If trade_date not provided, use today
        """
        try:
            if not trade_date:
                trade_date = date.today()

            # Fetch all saved trades for the day
            result = self.client.table("saved_trades")\
                .select("*")\
                .eq("user_id", user_id)\
                .gte("saved_date", f"{trade_date}T00:00:00")\
                .lte("saved_date", f"{trade_date}T23:59:59")\
                .execute()

            trades = result.data or []

            # Calculate stats
            total = len(trades)
            wins = sum(1 for t in trades if t.get("daily_status") == "won")
            losses = sum(1 for t in trades if t.get("daily_status") == "lost")
            pending = sum(1 for t in trades if t.get("daily_status") == "pending")

            total_pnl = sum(t.get("pnl", 0) for t in trades if t.get("pnl"))
            avg_roi = sum(t.get("roi_percent", 0) for t in trades) / total if total > 0 else 0

            return {
                "success": True,
                "date": str(trade_date),
                "total": total,
                "wins": wins,
                "losses": losses,
                "pending": pending,
                "win_rate": (wins / total * 100) if total > 0 else 0,
                "total_pnl": round(total_pnl, 2),
                "avg_roi": round(avg_roi, 2),
                "trades": trades
            }

        except Exception as e:
            logger.error(f"Error fetching daily stats: {e}")
            return {
                "success": False,
                "error": str(e),
                "total": 0,
                "wins": 0,
                "losses": 0,
                "trades": []
            }

    def get_monthly_summary(self, user_id: str) -> Dict:
        """Get monthly performance summary"""
        try:
            result = self.client.table("saved_trades")\
                .select("*")\
                .eq("user_id", user_id)\
                .order("saved_date", desc=True)\
                .limit(1000)  # Get last 1000 trades
                .execute()

            trades = result.data or []

            # Group by month
            monthly = {}
            for trade in trades:
                month = trade.get("saved_date", "").split("T")[0][:7]  # YYYY-MM
                if month not in monthly:
                    monthly[month] = {
                        "total": 0,
                        "wins": 0,
                        "losses": 0,
                        "pnl": 0,
                        "trades": []
                    }

                monthly[month]["total"] += 1
                if trade.get("daily_status") == "won":
                    monthly[month]["wins"] += 1
                elif trade.get("daily_status") == "lost":
                    monthly[month]["losses"] += 1

                if trade.get("pnl"):
                    monthly[month]["pnl"] += trade["pnl"]

                monthly[month]["trades"].append(trade)

            # Calculate monthly stats
            monthly_stats = []
            for month_key in sorted(monthly.keys(), reverse=True):
                m = monthly[month_key]
                win_rate = (m["wins"] / m["total"] * 100) if m["total"] > 0 else 0
                monthly_stats.append({
                    "month": month_key,
                    "total": m["total"],
                    "wins": m["wins"],
                    "losses": m["losses"],
                    "win_rate": round(win_rate, 1),
                    "pnl": round(m["pnl"], 2)
                })

            return {
                "success": True,
                "monthly": monthly_stats,
                "total_trades": sum(m["total"] for m in monthly_stats),
                "total_pnl": round(sum(m["pnl"] for m in monthly_stats), 2)
            }

        except Exception as e:
            logger.error(f"Error fetching monthly summary: {e}")
            return {"success": False, "error": str(e), "monthly": []}

    # ==========================================
    # UTILITY FUNCTIONS
    # ==========================================

    def delete_trade(self, saved_trade_id: str) -> Dict:
        """Delete a saved trade from dashboard"""
        try:
            result = self.client.table("saved_trades")\
                .delete()\
                .eq("id", saved_trade_id)\
                .execute()

            logger.info(f"Trade deleted: {saved_trade_id}")
            return {"success": True}

        except Exception as e:
            logger.error(f"Error deleting trade: {e}")
            return {"success": False, "error": str(e)}


# ==========================================
# Singleton Instance
# ==========================================

@st.cache_resource
def get_supabase_client() -> SupabaseClient:
    """Get cached Supabase client instance"""
    return SupabaseClient()
