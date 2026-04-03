# app.py — entry point redirect to trade_app.py (main dashboard)
import os
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "trade_app.py")).read())
