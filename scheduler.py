"""
scheduler.py — TradeIQ Daily Sales Automation
מריץ את sales_manager.py בזמנים קבועים.

הפעלה:
  python scheduler.py

זמנים:
  08:00 — מחזור בוקר (leads + pipeline check)
  20:00 — מחזור ערב + דוח Telegram
  ראשון בחודש 09:00 — מחקר שוק מלא
"""

import sys
import os
import logging
from datetime import datetime

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(__file__))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("data/sales/scheduler.log"),
    ]
)
log = logging.getLogger("TradeIQ.Scheduler")


def morning_cycle():
    """08:00 — ציד לידים + בדיקת pipeline."""
    log.info("=== Morning cycle started ===")
    try:
        from agents.sales_manager import run_daily_cycle
        result = run_daily_cycle(send_telegram=False, verbose=False)
        decisions = result.get("decisions", [])
        high = [d for d in decisions if d.get("priority") == "HIGH"]
        log.info(f"Morning cycle done. Leads: {result['agents']['leads']['new_leads_added']}, High-priority decisions: {len(high)}")
    except Exception as e:
        log.error(f"Morning cycle failed: {e}")


def evening_cycle():
    """20:00 — מחזור מלא + דוח Telegram."""
    log.info("=== Evening cycle started ===")
    try:
        from agents.sales_manager import run_daily_cycle
        result = run_daily_cycle(send_telegram=True, verbose=False)
        log.info(f"Evening cycle done. Telegram: {result.get('telegram_sent', False)}")
    except Exception as e:
        log.error(f"Evening cycle failed: {e}")


def weekly_market_research():
    """ראשון בשבוע 09:00 — מחקר שוק."""
    log.info("=== Weekly market research ===")
    try:
        from agents.sales_manager import run_weekly_market_research
        run_weekly_market_research(send_telegram=True)
        log.info("Market research done")
    except Exception as e:
        log.error(f"Market research failed: {e}")


def main():
    scheduler = BlockingScheduler(timezone="Asia/Jerusalem")

    scheduler.add_job(morning_cycle,        CronTrigger(hour=8,  minute=0), id="morning")
    scheduler.add_job(evening_cycle,        CronTrigger(hour=20, minute=0), id="evening")
    scheduler.add_job(weekly_market_research, CronTrigger(day_of_week="mon", hour=9, minute=0), id="weekly_research")

    log.info("TradeIQ Scheduler started")
    log.info("  08:00 — Morning cycle (leads + pipeline)")
    log.info("  20:00 — Evening cycle + Telegram report")
    log.info("  Monday 09:00 — Market research")
    log.info("Press Ctrl+C to stop")

    try:
        scheduler.start()
    except KeyboardInterrupt:
        log.info("Scheduler stopped")


if __name__ == "__main__":
    main()
