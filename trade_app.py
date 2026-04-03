"""
trade_app.py — מחשבון עסקה עצמאי
הרצה: streamlit run trade_app.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime

from data.market_data import get_current_quote, get_price_history, get_company_name, get_market_status
from calculators.trade_calc import calc_atr, evaluate_trade, evaluate_trade_v3
from calculators.technical_calc import calc_rsi, calc_macd
from calculators.sentiment_scorer import combine_signals
from calculators.support_resistance import get_support_resistance
from agents.trade_calculator import parse_price_from_text, auto_suggest_stop
from agents.news_scout import get_news
from agents.social_pulse import get_social_pulse
from data.user_data import (
    load_watchlist, save_watchlist, add_to_watchlist, remove_from_watchlist,
    load_journal, save_trade, delete_trade, journal_summary
)

try:
    from streamlit_autorefresh import st_autorefresh
except ImportError:
    st_autorefresh = None

# ─── הגדרות ─────────────────────────────────────────────────────────────────
st.set_page_config(page_title="מחשבון עסקה", page_icon="🧮", layout="wide")

st.markdown("""
<style>
  /* ── Google Font: Heebo (Hebrew-first, elegant) ── */
  @import url('https://fonts.googleapis.com/css2?family=Heebo:wght@300;400;500;600;700;900&display=swap');

  /* ── Palette ──
     bg-base      #07070f   deep navy-black
     bg-surface   #0e0e1c   card background
     bg-elevated  #14142a   hover / input
     border       #1e1e38   subtle border
     gold         #C8A96E   warm gold accent
     gold-dim     #7a6540   muted gold
     text-primary #EDE8E0   warm off-white
     text-muted   #6E6E92   muted purple-gray
     text-faint   #38384E   very muted
     go-green     #2DD4A0   mint green
     no-red       #E05F5F   soft red
     up           #2DD4A0
     down         #E05F5F
  ── */

  html, body, .stApp {
      background-color: #060610 !important;
      color: #F0ECE6 !important;
      font-family: 'Heebo', 'Segoe UI', sans-serif !important;
      font-weight: 400;
      letter-spacing: 0.01em;
      font-size: 18px;
  }

  /* ── Hide Streamlit chrome ── */
  #MainMenu, footer, header { visibility: hidden; }
  .block-container { padding-top: 1.5rem !important; padding-bottom: 3rem !important; max-width: 960px !important; margin: 0 auto !important; }

  /* ── Page title ── */
  h1, h2, h3 {
      font-family: 'Heebo', sans-serif !important;
      font-weight: 700 !important;
      color: #EDE8E0 !important;
      letter-spacing: -0.02em;
  }

  /* ── Ticker input + button row ── */
  .stTextInput input {
      background: #10101e !important;
      border: 1px solid #2a2a48 !important;
      border-radius: 10px !important;
      color: #F0ECE6 !important;
      font-family: 'Heebo', sans-serif !important;
      font-size: 20px !important;
      padding: 10px 16px !important;
      transition: border-color 0.2s;
  }
  .stTextInput input:focus {
      border-color: #C8A96E !important;
      box-shadow: 0 0 0 3px #C8A96E28 !important;
  }

  /* ── Number inputs ── */
  .stNumberInput input {
      background: #10101e !important;
      border: 1px solid #2a2a48 !important;
      border-radius: 8px !important;
      color: #F0ECE6 !important;
      font-family: 'Heebo', sans-serif !important;
      font-size: 18px !important;
  }
  .stNumberInput input:focus {
      border-color: #C8A96E !important;
      box-shadow: 0 0 0 3px #C8A96E22 !important;
  }

  /* ── Primary button ── */
  .stButton > button[kind="primary"] {
      background: linear-gradient(135deg, #C8A96E, #a07840) !important;
      color: #07070f !important;
      font-family: 'Heebo', sans-serif !important;
      font-weight: 700 !important;
      font-size: 17px !important;
      border: none !important;
      border-radius: 10px !important;
      padding: 10px 24px !important;
      letter-spacing: 0.04em;
      transition: opacity 0.2s, transform 0.1s;
  }
  .stButton > button[kind="primary"]:hover { opacity: 0.88; transform: translateY(-1px); }

  /* ── Secondary buttons ── */
  .stButton > button:not([kind="primary"]) {
      background: #0e0e1c !important;
      color: #EDE8E0 !important;
      border: 1px solid #1e1e38 !important;
      border-radius: 8px !important;
      font-family: 'Heebo', sans-serif !important;
  }

  /* ── Metric cards ── */
  [data-testid="metric-container"] {
      background: #10101e;
      border: 1px solid #2a2a48;
      border-radius: 12px;
      padding: 18px 20px;
      transition: border-color 0.2s;
  }
  [data-testid="metric-container"]:hover { border-color: #C8A96E66; }
  [data-testid="metric-container"] label {
      color: #9090B8 !important;
      font-family: 'Heebo', sans-serif !important;
      font-size: 14px !important;
      font-weight: 600 !important;
      text-transform: uppercase;
      letter-spacing: 1.2px;
  }
  [data-testid="stMetricValue"] {
      color: #F0ECE6 !important;
      font-family: 'Heebo', sans-serif !important;
      font-size: 26px !important;
      font-weight: 700 !important;
  }
  [data-testid="stMetricDelta"] { font-family: 'Heebo', sans-serif !important; }

  /* ── Radio buttons ── */
  .stRadio label { color: #EDE8E0 !important; font-family: 'Heebo', sans-serif !important; }
  .stRadio [data-testid="stMarkdownContainer"] p { color: #6E6E92 !important; }

  /* ── Slider ── */
  .stSlider [data-testid="stThumbValue"] { color: #C8A96E !important; }
  .stSlider [role="slider"] { background: #C8A96E !important; }

  /* ── Divider ── */
  hr { border-color: #2a2a48 !important; margin: 24px 0 !important; }

  /* ── Expander ── */
  .streamlit-expanderHeader {
      background: #10101e !important;
      border: 1px solid #2a2a48 !important;
      border-radius: 8px !important;
      color: #9090B8 !important;
      font-family: 'Heebo', sans-serif !important;
      font-size: 16px !important;
  }
  .streamlit-expanderContent {
      background: #10101e !important;
      border: 1px solid #2a2a48 !important;
      border-top: none !important;
  }

  /* ── Caption / small text ── */
  .stCaption, small, [data-testid="stCaptionContainer"] {
      color: #9090B8 !important;
      font-family: 'Heebo', sans-serif !important;
      font-size: 15px !important;
  }

  /* ── Error / Warning ── */
  .stAlert { border-radius: 10px !important; font-family: 'Heebo', sans-serif !important; }

  /* ── Custom components ── */
  .price-strip {
      background: #10101e;
      border: 1px solid #2a2a48;
      border-radius: 14px;
      padding: 22px 28px;
      margin: 12px 0 0 0;
      display: flex;
      gap: 36px;
      align-items: center;
      flex-wrap: wrap;
  }
  .price-strip-item { display: flex; flex-direction: column; gap: 4px; }
  .price-strip-label {
      font-size: 13px;
      font-weight: 600;
      color: #9090B8;
      text-transform: uppercase;
      letter-spacing: 1.4px;
  }
  .big-price {
      font-size: 48px;
      font-weight: 900;
      color: #F5F2EE;
      letter-spacing: -0.03em;
      line-height: 1;
  }
  .price-change { font-size: 21px; font-weight: 700; }
  .stat-value { font-size: 20px; font-weight: 700; color: #F5F2EE; }
  .gold { color: #D4B87A; }

  .data-strip {
      background: #10101e;
      border: 1px solid #2a2a48;
      border-top: none;
      border-radius: 0 0 14px 14px;
      padding: 14px 28px;
      margin-bottom: 16px;
      display: flex;
      gap: 0;
      flex-wrap: wrap;
  }
  .data-strip-item {
      flex: 1;
      min-width: 100px;
      padding: 0 16px;
      border-right: 1px solid #2a2a48;
  }
  .data-strip-item:first-child { padding-left: 0; }
  .data-strip-item:last-child  { border-right: none; }
  .ds-label {
      font-size: 12px;
      font-weight: 700;
      color: #9090B8;
      text-transform: uppercase;
      letter-spacing: 1.5px;
      margin-bottom: 5px;
  }
  .ds-main { font-size: 18px; font-weight: 700; color: #F5F2EE; }
  .ds-sub  { font-size: 14px; color: #9090B8; margin-top: 1px; }
  .trend-arrow { font-size: 14px; margin-right: 2px; }

  .section-label {
      font-size: 13px;
      font-weight: 700;
      color: #D4B87A;
      text-transform: uppercase;
      letter-spacing: 2px;
      margin: 22px 0 12px 0;
      padding-bottom: 7px;
      border-bottom: 1px solid #2a2a48;
  }

  .hint {
      font-size: 14px;
      color: #9090B8;
      margin-top: 4px;
      font-style: italic;
  }

  .result-banner {
      border-radius: 14px;
      padding: 28px 32px;
      text-align: center;
      margin: 16px 0;
      backdrop-filter: blur(4px);
  }
  .verdict-label {
      font-size: 55px;
      font-weight: 900;
      letter-spacing: -0.02em;
      line-height: 1.1;
  }
  .verdict-reason {
      font-size: 17px;
      color: #9090B8;
      margin-top: 8px;
      font-weight: 400;
      letter-spacing: 0.02em;
  }

  /* ── Agent section ── */
  .agent-card {
      background: #10101e;
      border: 1px solid #2a2a48;
      border-radius: 14px;
      padding: 20px 24px;
      margin-bottom: 10px;
  }
  .agent-title {
      font-size: 13px;
      font-weight: 700;
      color: #D4B87A;
      text-transform: uppercase;
      letter-spacing: 2px;
      margin-bottom: 14px;
      padding-bottom: 9px;
      border-bottom: 1px solid #2a2a48;
  }
  .news-row {
      display: flex;
      align-items: flex-start;
      gap: 12px;
      padding: 10px 0;
      border-bottom: 1px solid #1e1e32;
  }
  .news-row:last-child { border-bottom: none; }
  .news-score {
      font-size: 15px;
      font-weight: 700;
      min-width: 46px;
      text-align: center;
      padding: 3px 7px;
      border-radius: 5px;
      letter-spacing: 0.03em;
      flex-shrink: 0;
      margin-top: 1px;
  }
  .news-text { font-size: 16px; color: #F0ECE6; line-height: 1.5; }
  .news-source { font-size: 13px; color: #9090B8; margin-top: 3px; letter-spacing: 0.03em; }
  .sentiment-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 9px 0;
      border-bottom: 1px solid #1e1e32;
      font-size: 16px;
  }
  .sentiment-row:last-child { border-bottom: none; }
  .sentiment-label { color: #9090B8; font-size: 14px; letter-spacing: 0.04em; }
  .sentiment-value { color: #F0ECE6; font-weight: 600; }
  .signal-pill {
      display: inline-block;
      padding: 6px 16px;
      border-radius: 20px;
      font-size: 15px;
      font-weight: 700;
      letter-spacing: 0.05em;
      text-transform: uppercase;
  }

  /* ── Scrollbar ── */
  ::-webkit-scrollbar { width: 6px; }
  ::-webkit-scrollbar-track { background: #060610; }
  ::-webkit-scrollbar-thumb { background: #2a2a48; border-radius: 3px; }

  /* ── Sidebar ── */
  [data-testid="stSidebar"] {
      background: #0a0a16 !important;
      border-right: 1px solid #2a2a48 !important;
  }
  [data-testid="stSidebar"] .block-container {
      max-width: 100% !important; padding: 1rem 1rem !important;
  }
  .watch-row {
      display: flex; align-items: center; justify-content: space-between;
      padding: 10px 0; border-bottom: 1px solid #1e1e32;
  }
  .watch-left  { display: flex; flex-direction: column; gap: 3px; }
  .watch-ticker { font-weight: 700; font-size: 16px; color: #F0ECE6; letter-spacing: 0.02em; }
  .watch-name   { font-size: 12px; color: #5a5a7a; letter-spacing: 0.04em; }
  .watch-right { display: flex; flex-direction: column; align-items: flex-end; gap: 3px; }
  .watch-price  { font-size: 15px; font-weight: 600; color: #F0ECE6; }
  .watch-change { font-size: 13px; font-weight: 700; }
  .sb-label {
      font-size: 12px; font-weight: 700; color: #D4B87A;
      letter-spacing: 2px; text-transform: uppercase;
      padding-bottom: 9px; border-bottom: 1px solid #2a2a48;
      margin-bottom: 6px;
  }
  .sb-divider { height: 1px; background: #2a2a48; margin: 14px 0; }

  /* ── Journal KPI cards ── */
  .journal-kpi { display: flex; gap: 12px; margin-bottom: 24px; flex-wrap: wrap; }
  .kpi-card {
      flex: 1; min-width: 100px; background: #10101e;
      border: 1px solid #2a2a48; border-radius: 10px;
      padding: 16px 16px; text-align: center;
  }
  .kpi-num  { font-size: 35px; font-weight: 900; color: #D4B87A; letter-spacing: -0.02em; line-height: 1; }
  .kpi-lbl  { font-size: 12px; color: #9090B8; letter-spacing: 1.5px; text-transform: uppercase; margin-top: 6px; }

  /* ── Live price pulse ── */
  @keyframes price-pulse {
    0%   { opacity: 1; }
    50%  { opacity: 0.65; }
    100% { opacity: 1; }
  }
  .price-live { animation: price-pulse 3s ease-in-out infinite; }

  /* ── Section divider ── */
  .section-divider {
      height: 1px;
      background: linear-gradient(to right, transparent, #2a2a48 30%, #2a2a48 70%, transparent);
      margin: 20px 0;
  }

  /* ── Compact header bar ── */
  .top-bar {
      display: flex; align-items: center; gap: 20px; flex-wrap: wrap;
      padding-bottom: 14px; border-bottom: 1px solid #1e1e38; margin-bottom: 18px;
  }
  .top-bar-brand {
      font-size: 12px; font-weight: 700; color: #C8A96E;
      letter-spacing: 2.5px; text-transform: uppercase;
  }
  .top-bar-ticker { font-size: 23px; font-weight: 900; color: #EDE8E0; letter-spacing: -0.02em; }
  .top-bar-company { font-size: 14px; color: #6E6E92; margin-top: 2px; }
  .top-bar-price { font-size: 26px; font-weight: 900; color: #EDE8E0; letter-spacing: -0.02em; }
  .top-bar-change { font-size: 15px; font-weight: 600; margin-top: 3px; }

  /* ── Trust badge pills ── */
  .badge-row { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 12px; }
  .badge-pill {
      display: inline-flex; align-items: center; gap: 5px;
      background: #10101e; border: 1px solid #2a2a48; border-radius: 20px;
      padding: 5px 12px; font-size: 13px; color: #9090B8;
      font-family: 'Heebo', sans-serif; letter-spacing: 0.04em;
  }

  /* ── 52W range bar ── */
  .range-track {
      position: relative; height: 4px; background: #1e1e38;
      border-radius: 2px; margin: 8px 0 4px 0;
  }
  .range-fill { position: absolute; left: 0; top: 0; height: 100%; background: #C8A96E44; border-radius: 2px; }
  .range-dot  {
      position: absolute; top: 50%; transform: translate(-50%, -50%);
      width: 8px; height: 8px; background: #C8A96E; border-radius: 50%;
      box-shadow: 0 0 6px #C8A96E88;
  }
  .range-labels { display: flex; justify-content: space-between; font-size: 10px; color: #38384E; }

  /* ── Glow pulse animation for result banner ── */
  @keyframes glow-pulse {
    0%   { box-shadow: 0 0 40px var(--banner-color, #2DD4A0)18; }
    50%  { box-shadow: 0 0 60px var(--banner-color, #2DD4A0)35; }
    100% { box-shadow: 0 0 40px var(--banner-color, #2DD4A0)18; }
  }
  .result-banner.animated { animation: glow-pulse 2s ease-in-out infinite; }

  /* ── R:R visual bar ── */
  .rr-bar-wrap { margin: 14px 0 6px 0; }
  .rr-bar-track {
      position: relative; height: 6px; border-radius: 3px; overflow: visible;
      background: linear-gradient(to right, #E05F5F 0%, #E05F5F 50%, #2DD4A0 50%, #2DD4A0 100%);
  }
  .rr-bar-marker {
      position: absolute; top: 50%; transform: translate(-50%, -50%);
      width: 12px; height: 12px; background: #C8A96E; border-radius: 50%;
      border: 2px solid #07070f; box-shadow: 0 0 8px #C8A96E;
  }
  .rr-bar-labels { display: flex; justify-content: space-between; font-size: 10px; color: #38384E; margin-top: 4px; }

  /* ── Sentiment gauge ── */
  .gauge-wrap { margin: 14px 0 10px 0; }
  .gauge-track {
      position: relative; height: 8px; border-radius: 4px;
      background: linear-gradient(to right, #E05F5F 0%, #E05F5F 30%, #C8A96E 30%, #C8A96E 70%, #2DD4A0 70%, #2DD4A0 100%);
  }
  .gauge-pointer {
      position: absolute; top: -4px; transform: translateX(-50%);
      width: 4px; height: 16px; background: #EDE8E0; border-radius: 2px;
      box-shadow: 0 0 6px #EDE8E088;
  }
  .gauge-labels { display: flex; justify-content: space-between; font-size: 10px; color: #6E6E92; margin-top: 5px; }

  /* ── Profit/loss summary row ── */
  .pnl-row {
      display: flex; gap: 16px; margin: 16px 0 10px 0;
  }
  .pnl-card {
      flex: 1; background: #10101e; border: 1px solid #2a2a48;
      border-radius: 12px; padding: 18px 22px; text-align: center;
  }
  .pnl-label { font-size: 13px; color: #9090B8; letter-spacing: 1.2px; text-transform: uppercase; margin-bottom: 8px; }
  .pnl-value { font-size: 37px; font-weight: 900; letter-spacing: -0.02em; line-height: 1; }

  /* ── Chart range tabs ── */
  div[data-testid="stHorizontalBlock"] .stButton > button {
      padding: 4px 14px !important; font-size: 14px !important;
      border-radius: 6px !important; min-height: 0 !important;
  }

  /* ── Market status badge ── */
  .market-badge {
      display: inline-flex; align-items: center; gap: 5px;
      padding: 3px 9px; border-radius: 10px;
      font-size: 10px; font-weight: 700; letter-spacing: 1.2px;
      text-transform: uppercase; white-space: nowrap;
  }
  .market-badge.open   { background:#0b2318; color:#2DD4A0; border:1px solid #2DD4A044; }
  .market-badge.pre    { background:#221a06; color:#C8A96E; border:1px solid #C8A96E44; }
  .market-badge.post   { background:#221306; color:#E09050; border:1px solid #E0905044; }
  .market-badge.closed { background:#1a0c0c; color:#E05F5F; border:1px solid #E05F5F33; }
  .market-dot {
      width:6px; height:6px; border-radius:50%; display:inline-block; flex-shrink:0;
  }
  .market-dot.open   { background:#2DD4A0; animation:price-pulse 2s ease-in-out infinite; }
  .market-dot.pre    { background:#C8A96E; }
  .market-dot.post   { background:#E09050; }
  .market-dot.closed { background:#E05F5F; }
  .next-open-label {
      font-size:11px; color:#6E6E92; margin-top:2px; letter-spacing:0.02em;
  }
  .ext-price-row {
      display:flex; align-items:center; gap:8px; margin-top:5px;
      padding-top:5px; border-top:1px solid #1e1e38;
  }
  .ext-price-tag {
      font-size:10px; font-weight:700; letter-spacing:1px; text-transform:uppercase;
      color:#6E6E92;
  }
  .ext-price-val { font-size:16px; font-weight:700; color:#F0ECE6; }
  .ext-price-chg { font-size:12px; font-weight:600; }

  /* ── Ticker search bar — elegant centered ── */
  div[data-testid="stTextInput"] input[aria-label="Ticker Symbol"] {
      font-size: 26px !important;
      font-weight: 700 !important;
      text-align: center !important;
      letter-spacing: 0.08em !important;
      padding: 14px 20px !important;
      border: 2px solid #2a2a48 !important;
      border-radius: 14px !important;
  }
  div[data-testid="stTextInput"] input[aria-label="Ticker Symbol"]:focus {
      border-color: #C8A96E !important;
      box-shadow: 0 0 0 4px #C8A96E18 !important;
  }
</style>
""", unsafe_allow_html=True)

# ─── Session State ────────────────────────────────────────────────────────────
if "calc_ticker" not in st.session_state:
    st.session_state["calc_ticker"] = "AAPL"
if "quote" not in st.session_state:
    st.session_state["quote"] = None
if "df5d" not in st.session_state:
    st.session_state["df5d"] = None
if "atr" not in st.session_state:
    st.session_state["atr"] = None
if "agents_ticker" not in st.session_state:
    st.session_state["agents_ticker"] = None
if "news_data" not in st.session_state:
    st.session_state["news_data"] = None
if "social_data" not in st.session_state:
    st.session_state["social_data"] = None
if "chart_range" not in st.session_state:
    st.session_state["chart_range"] = "5D"
if "watchlist" not in st.session_state:
    st.session_state["watchlist"] = load_watchlist()
if "journal_open" not in st.session_state:
    st.session_state["journal_open"] = False
if "last_result" not in st.session_state:
    st.session_state["last_result"] = None

# ─── Sidebar ─────────────────────────────────────────────────────────────────
@st.cache_data(ttl=60)
def _load_watch_quote(t):
    try:
        return get_current_quote(t)
    except Exception:
        return None

with st.sidebar:
    st.markdown('<div class="sb-label">Watchlist</div>', unsafe_allow_html=True)

    wl = st.session_state["watchlist"]
    if not wl:
        st.markdown('<div style="font-size:11px;color:#38384E;padding:6px 0;">No tickers yet — add one below.</div>',
                    unsafe_allow_html=True)

    for _wt in list(wl):
        _wq = _load_watch_quote(_wt)
        if _wq:
            _wchg    = _wq.get("change_pct", 0)
            _wcur    = "₪" if _wt.endswith(".TA") else "$"
            _wcolor  = "#2DD4A0" if _wchg >= 0 else "#E05F5F"
            _warrow  = "▲" if _wchg >= 0 else "▼"
            _wsign   = "+" if _wchg >= 0 else ""
            _wprice  = f"{_wcur}{_wq['price']:,.2f}"
        else:
            _wcolor, _warrow, _wsign, _wchg, _wprice = "#38384E", "—", "", 0, "—"

        _col_info, _col_btns = st.columns([3, 2])
        with _col_info:
            st.markdown(
                f'<div class="watch-left">'
                f'<span class="watch-ticker">{_wt}</span>'
                f'<span class="watch-price">{_wprice}</span>'
                f'<span class="watch-change" style="color:{_wcolor};">{_warrow} {_wsign}{_wchg:.1f}%</span>'
                f'</div>',
                unsafe_allow_html=True
            )
        with _col_btns:
            if st.button("Load", key=f"wl_load_{_wt}", use_container_width=True):
                st.session_state["calc_ticker"] = _wt
                st.session_state["quote"]  = None
                st.session_state["df5d"]   = None
                st.session_state["atr"]    = None
                st.session_state["chart_range"] = "5D"
                st.rerun()
            if st.button("✕", key=f"wl_rm_{_wt}", use_container_width=True):
                st.session_state["watchlist"] = remove_from_watchlist(_wt)
                st.rerun()

    st.markdown('<div class="sb-divider"></div>', unsafe_allow_html=True)
    _new_wt = st.text_input("Add ticker", placeholder="AAPL / TEVA.TA", key="wl_add_input",
                            label_visibility="collapsed")
    if st.button("+ Add to Watchlist", use_container_width=True, key="wl_add_btn"):
        if _new_wt.strip():
            st.session_state["watchlist"] = add_to_watchlist(_new_wt.strip().upper())
            st.rerun()

    st.markdown('<div class="sb-divider"></div>', unsafe_allow_html=True)

    # Journal summary
    _jsum = journal_summary()
    st.markdown('<div class="sb-label">Trade Journal</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div style="font-size:12px;color:#EDE8E0;padding:4px 0;">'
        f'Total: <b style="color:#C8A96E;">{_jsum["total"]}</b> &nbsp;·&nbsp; '
        f'GO: <b style="color:#2DD4A0;">{_jsum["go_count"]}</b> &nbsp;·&nbsp; '
        f'NO-GO: <b style="color:#E05F5F;">{_jsum["nogo_count"]}</b>'
        f'</div>'
        f'<div style="font-size:11px;color:#6E6E92;margin-top:3px;">'
        f'Today: {_jsum["today_count"]} &nbsp;·&nbsp; Avg R:R {_jsum["avg_rr"]}'
        f'</div>',
        unsafe_allow_html=True
    )
    st.markdown("<div style='margin-top:8px;'></div>", unsafe_allow_html=True)
    if st.button("Open Journal", use_container_width=True, key="open_journal"):
        st.session_state["journal_open"] = True
        st.rerun()

    st.markdown('<div style="height:60px;"></div>', unsafe_allow_html=True)
    st.markdown(
        '<div style="font-size:9px;color:#38384E;text-align:center;letter-spacing:0.04em;">'
        'Trade Calculator v1.0<br/>For informational purposes only.</div>',
        unsafe_allow_html=True
    )

# ─── Journal View (full-page swap) ───────────────────────────────────────────
if st.session_state["journal_open"]:
    st.markdown(
        '<div class="top-bar">'
        '<span class="top-bar-brand">Trading Desk</span>'
        '<span style="font-size:20px;font-weight:900;color:#EDE8E0;">Trade Journal</span>'
        '</div>',
        unsafe_allow_html=True
    )
    if st.button("← Back to Calculator", key="close_journal"):
        st.session_state["journal_open"] = False
        st.rerun()

    _jsum = journal_summary()
    go_pct_color = "#2DD4A0" if _jsum["go_pct"] >= 60 else "#E05F5F" if _jsum["go_pct"] < 40 else "#C8A96E"
    st.markdown(
        f'<div class="journal-kpi">'
        f'<div class="kpi-card"><div class="kpi-num">{_jsum["total"]}</div><div class="kpi-lbl">Total Trades</div></div>'
        f'<div class="kpi-card"><div class="kpi-num" style="color:{go_pct_color};">{_jsum["go_pct"]}%</div><div class="kpi-lbl">GO Rate</div></div>'
        f'<div class="kpi-card"><div class="kpi-num">{_jsum["avg_rr"]:.1f}</div><div class="kpi-lbl">Avg R:R</div></div>'
        f'<div class="kpi-card"><div class="kpi-num">{_jsum["best_rr"]:.1f}</div><div class="kpi-lbl">Best R:R</div></div>'
        f'<div class="kpi-card"><div class="kpi-num">{_jsum["today_count"]}</div><div class="kpi-lbl">Today</div></div>'
        f'</div>',
        unsafe_allow_html=True
    )

    _journal = load_journal()
    if not _journal:
        st.markdown(
            '<div style="text-align:center;padding:48px;color:#38384E;font-size:14px;">'
            'No saved trades yet.<br/>Calculate a trade and click "Save to Journal".'
            '</div>',
            unsafe_allow_html=True
        )
    else:
        import pandas as pd
        _df_journal = pd.DataFrame(_journal)
        _display_cols = ["timestamp", "ticker", "entry", "target", "stop", "rr_ratio", "shares", "risk", "verdict", "news_score", "social_score"]
        _display_cols = [c for c in _display_cols if c in _df_journal.columns]
        _rename = {
            "timestamp": "Date", "ticker": "Ticker", "entry": "Entry",
            "target": "Target", "stop": "Stop", "rr_ratio": "R:R",
            "shares": "Shares", "risk": "Risk $", "verdict": "Verdict",
            "news_score": "News", "social_score": "Social"
        }
        _df_show = _df_journal[_display_cols].rename(columns=_rename)
        if "Date" in _df_show.columns:
            _df_show["Date"] = _df_show["Date"].str[:16]

        def _row_style(row):
            bg = "background-color: rgba(45,212,160,0.06)" if row.get("Verdict") == "GO" \
                 else "background-color: rgba(224,95,95,0.06)"
            return [bg] * len(row)

        st.dataframe(
            _df_show.style.apply(_row_style, axis=1),
            use_container_width=True, height=420
        )

        st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
        st.markdown('<div style="font-size:11px;color:#6E6E92;margin-bottom:8px;">Delete a trade entry by ID:</div>', unsafe_allow_html=True)
        _del_col1, _del_col2 = st.columns([3, 1])
        with _del_col1:
            _del_id = st.text_input("Trade ID", placeholder="e.g. a3f7bc12", key="del_id", label_visibility="collapsed")
        with _del_col2:
            if st.button("Delete", key="del_btn", type="primary"):
                if _del_id.strip():
                    delete_trade(_del_id.strip())
                    st.success("Entry deleted.")
                    st.rerun()

    st.stop()

# ─── Header + Search ─────────────────────────────────────────────────────────
st.markdown("""
<div style="margin-bottom:20px;">
  <div class="top-bar">
    <div>
      <div class="top-bar-brand">Trading Desk</div>
      <div style="font-size:26px;font-weight:900;color:#EDE8E0;letter-spacing:-0.03em;line-height:1.1;">Trade Calculator</div>
    </div>
    <div class="badge-row" style="margin-top:0;align-self:center;">
      <span class="badge-pill">📈 Yahoo Finance</span>
      <span class="badge-pill">📰 News Scout</span>
      <span class="badge-pill">💬 Social Pulse</span>
      <span class="badge-pill">📊 ATR · R:R</span>
    </div>
  </div>
  <div style="font-size:12px;color:#6E6E92;font-weight:300;">
    Live market data &nbsp;·&nbsp; AI sentiment scan &nbsp;·&nbsp; GO / NO-GO in seconds
  </div>
</div>
""", unsafe_allow_html=True)

st.markdown(
    '<div style="text-align:center;margin:4px 0 8px;">'
    '<span style="font-size:12px;color:#9090B8;letter-spacing:2px;text-transform:uppercase;">'
    'Enter Stock Symbol</span></div>',
    unsafe_allow_html=True
)
_tc1, _tc2, _tc3 = st.columns([1, 3, 1])
with _tc2:
    ticker_input = st.text_input(
        "Ticker Symbol",
        value=st.session_state["calc_ticker"],
        placeholder="🔍   AAPL  /  TEVA.TA",
        label_visibility="collapsed",
    )
_bl1, _bl2, _bl3, _bl4, _bl5 = st.columns([1, 2, 1, 2, 1])
with _bl2:
    load_btn = st.button("Load →", use_container_width=True, type="primary")
with _bl4:
    _in_wl = ticker_input.strip().upper() in st.session_state["watchlist"]
    _wl_label = "✓ Watching" if _in_wl else "+ Watch"
    if st.button(_wl_label, use_container_width=True, key="toggle_watch"):
        t_upper = ticker_input.strip().upper()
        if t_upper:
            if _in_wl:
                st.session_state["watchlist"] = remove_from_watchlist(t_upper)
            else:
                st.session_state["watchlist"] = add_to_watchlist(t_upper)
            st.rerun()

if load_btn and ticker_input.strip():
    st.session_state["calc_ticker"] = ticker_input.strip().upper()
    st.session_state["quote"] = None
    st.session_state["df5d"] = None
    st.session_state["atr"] = None
    st.session_state["chart_range"] = "5D"
    st.session_state["last_result"] = None

ticker = st.session_state["calc_ticker"]

# ─── טעינת נתוני שוק ─────────────────────────────────────────────────────────
@st.cache_data(ttl=30)
def _load_quote(t):
    return get_current_quote(t)

@st.cache_data(ttl=60)
def _load_history(t):
    return get_price_history(t, "5D")

@st.cache_data(ttl=180)
def _load_history_1m(t):
    return get_price_history(t, "1M")

@st.cache_data(ttl=300)
def _load_history_6m(t):
    return get_price_history(t, "6M")

@st.cache_data(ttl=120)
def _load_market_status(t):
    return get_market_status(t)

@st.cache_data(ttl=300)
def _load_sr(t):
    return get_support_resistance(t)

def _fmt_vol(v):
    """פורמט נפח: 1.2M / 450K / 12K"""
    if v >= 1_000_000:
        return f"{v/1_000_000:.1f}M"
    elif v >= 1_000:
        return f"{v/1_000:.0f}K"
    return str(int(v))

def _trend_pct(df_close, days):
    """% שינוי מחיר בX ימי מסחר אחרונים. None אם אין מספיק נתונים."""
    s = df_close.squeeze().dropna()
    if len(s) < days + 1:
        return None
    past = float(s.iloc[-(days + 1)])
    now  = float(s.iloc[-1])
    return (now - past) / past * 100 if past else None

try:
    quote   = _load_quote(ticker)
    df5d    = _load_history(ticker)
    df6m    = _load_history_6m(ticker)
    atr_val = calc_atr(df5d)
    sr_data = _load_sr(ticker)
    company = get_company_name(ticker)
    mkt     = _load_market_status(ticker)
except Exception as e:
    st.error(f"Error loading data for **{ticker}**: {e}")
    st.stop()

# ── RSI + MACD ────────────────────────────────────────────────────────────────
try:
    _rsi_series = calc_rsi(df6m["Close"].squeeze())
    _rsi_val    = round(float(_rsi_series.dropna().iloc[-1]), 1)
    _macd_data  = calc_macd(df6m["Close"].squeeze())
    _macd_hist  = float(_macd_data["histogram"].dropna().iloc[-1])
except Exception:
    _rsi_val = None
    _macd_hist = None

_rsi_color  = "#E05F5F" if (_rsi_val or 50) >= 70 else "#2DD4A0" if (_rsi_val or 50) <= 30 else "#C8A96E"
_macd_color = "#2DD4A0" if (_macd_hist or 0) >= 0 else "#E05F5F"
_macd_sign  = "+" if (_macd_hist or 0) >= 0 else "-"

# ── Auto-refresh when market is open ─────────────────────────────────────────
if st_autorefresh and mkt.get("is_open"):
    st_autorefresh(interval=60000, key="live_refresh")

currency   = "₪" if ticker.endswith(".TA") else "$"
price      = quote["price"]
change     = quote["change"]
change_pct = quote["change_pct"]
day_high   = quote["high"]
day_low    = quote["low"]
year_high  = quote.get("year_high")
year_low   = quote.get("year_low")
suggested_stop = auto_suggest_stop(price, atr_val)

# ── נפח מסחר ─────────────────────────────────────────────────────────────────
vol_today = int(quote.get("volume", 0))
vol_series = df6m["Volume"].squeeze().dropna()
vol_avg_3m = int(vol_series.iloc[-63:].mean())  if len(vol_series) >= 63 else int(vol_series.mean())
vol_avg_6m = int(vol_series.mean())
vol_vs_3m  = (vol_today / vol_avg_3m - 1) * 100 if vol_avg_3m else 0

# ── מגמות מחיר ───────────────────────────────────────────────────────────────
close_series = df6m["Close"]
trend_30 = _trend_pct(close_series, 21)   # ~21 ימי מסחר = חודש
trend_60 = _trend_pct(close_series, 42)
trend_90 = _trend_pct(close_series, 63)

# ─── רצועת מחיר ──────────────────────────────────────────────────────────────
chg_color = "#2DD4A0" if change >= 0 else "#E05F5F"
chg_arrow = "▲" if change >= 0 else "▼"
sign = "+" if change >= 0 else ""

# ── Market status badge ────────────────────────────────────────────────────────
_state = mkt.get("state", "UNKNOWN")
_badge_map = {
    "REGULAR": ("open",   "● Open"),
    "PRE":     ("pre",    "Pre-Market"),
    "POST":    ("post",   "After-Hours"),
    "CLOSED":  ("closed", "Closed"),
}
_badge_cls, _badge_lbl = _badge_map.get(_state, ("closed", _state))
_market_badge_html = (
    f'<span class="market-badge {_badge_cls}">'
    f'<span class="market-dot {_badge_cls}"></span>'
    f'{_badge_lbl}</span>'
)
_next_open_html = ""
if mkt.get("next_open"):
    _next_open_html = f'<div class="next-open-label">{mkt["next_open"]}</div>'

# ── Pre / After-hours price ────────────────────────────────────────────────────
# PRE state: prefer pre_price; if no pre-market trading yet fall back to yesterday's post_price
if _state == "PRE":
    if mkt.get("pre_price"):
        _ext_p   = mkt.get("pre_price")
        _ext_pct = mkt.get("pre_chg_pct")
        _ext_tag = "Pre-Market"
    elif mkt.get("post_price"):
        _ext_p   = mkt.get("post_price")
        _ext_pct = mkt.get("post_chg_pct")
        _ext_tag = "After-Hours"
    else:
        _ext_p = _ext_pct = _ext_tag = None
else:
    _ext_p   = mkt.get("post_price")
    _ext_pct = mkt.get("post_chg_pct")
    _ext_tag = "After-Hours" if _ext_p else None

# If ext price available → it becomes the MAIN displayed price; regular close shown below
_has_ext = bool(_ext_p and _ext_tag)
_disp_price  = _ext_p   if _has_ext else price
_disp_pct    = _ext_pct if _has_ext else change_pct
_disp_change = (_ext_p - price) if _has_ext else change
_disp_color  = "#2DD4A0" if (_disp_pct or 0) >= 0 else "#E05F5F"
_disp_arrow  = "▲" if (_disp_pct or 0) >= 0 else "▼"
_disp_sign   = "+" if (_disp_pct or 0) >= 0 else ""

# Sub-row: last close (only when showing ext price)
_ext_price_html = ""
if _has_ext:
    _ext_price_html = (
        f'<div class="ext-price-row">'
        f'<span class="ext-price-tag">Last Close</span>'
        f'<span class="ext-price-val" style="color:#9090B8;">{currency}{price:,.2f}</span>'
        f'</div>'
    )

# helpers for data strip
def _trend_html(pct, label):
    if pct is None:
        return (f'<div class="data-strip-item">'
                f'<div class="ds-label">{label}</div>'
                f'<div class="ds-main" style="color:#38384E;">—</div>'
                f'</div>')
    color  = "#2DD4A0" if pct >= 0 else "#E05F5F"
    arrow  = "▲" if pct >= 0 else "▼"
    sign_s = "+" if pct >= 0 else ""
    return (f'<div class="data-strip-item">'
            f'<div class="ds-label">{label}</div>'
            f'<div class="ds-main" style="color:{color};">'
            f'<span class="trend-arrow">{arrow}</span>{sign_s}{pct:.1f}%</div>'
            f'</div>')

vol_color = "#2DD4A0" if vol_vs_3m >= 0 else "#E05F5F"
vol_sign  = "+" if vol_vs_3m >= 0 else ""

# 52W range bar HTML
def _range_bar_html(yr_low, yr_high, current):
    if not yr_low or not yr_high or yr_high <= yr_low:
        return ""
    pct_pos   = max(0, min(100, (current - yr_low) / (yr_high - yr_low) * 100))
    pct_above = (current - yr_low) / yr_low * 100 if yr_low else 0
    return (
        f'<div class="price-strip-item" style="flex:1;min-width:120px;">'
        f'<div class="price-strip-label">52W Range</div>'
        f'<div class="range-track">'
        f'<div class="range-fill" style="width:{pct_pos:.1f}%;"></div>'
        f'<div class="range-dot"  style="left:{pct_pos:.1f}%;"></div>'
        f'</div>'
        f'<div class="range-labels">'
        f'<span>{currency}{yr_low:,.0f}</span>'
        f'<span>{currency}{yr_high:,.0f}</span>'
        f'</div>'
        f'<div style="font-size:9px;color:#C8A96E;margin-top:1px;">+{pct_above:.1f}% above 52W low</div>'
        f'</div>'
    )

st.markdown(
    # ── שורה 1: מחיר + High/Low + ATR ──────────────────────────────────────
    f'<div class="price-strip" style="border-radius:14px 14px 0 0;margin-bottom:0;">'

    f'<div class="price-strip-item" style="flex:1;min-width:160px;">'
    f'<div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">'
    f'<div class="price-strip-label">{company}</div>'
    f'{_market_badge_html}'
    f'</div>'
    f'<div class="big-price price-live">{currency}{_disp_price:,.2f}</div>'
    f'<div class="price-change" style="color:{_disp_color};margin-top:4px;">'
    f'{_disp_arrow} {_disp_sign}{_disp_change:.2f} '
    f'<span style="font-weight:400;font-size:14px;">({_disp_sign}{_disp_pct:.2f}%)</span></div>'
    f'{_ext_price_html}'
    f'{_next_open_html}'
    f'</div>'

    f'<div style="width:1px;background:#1e1e38;align-self:stretch;margin:0 4px;"></div>'

    f'<div class="price-strip-item">'
    f'<div class="price-strip-label">Day High</div>'
    f'<div class="stat-value">{currency}{day_high:,.2f}</div>'
    f'</div>'

    f'<div class="price-strip-item">'
    f'<div class="price-strip-label">Day Low</div>'
    f'<div class="stat-value">{currency}{day_low:,.2f}</div>'
    f'</div>'

    f'<div class="price-strip-item">'
    f'<div class="price-strip-label">ATR 14</div>'
    f'<div class="stat-value gold">{currency}{atr_val:,.2f}</div>'
    f'</div>'

    + _range_bar_html(year_low, year_high, price) +

    f'</div>'

    # ── שורה 2: נפח + מגמות ──────────────────────────────────────────────────
    f'<div class="data-strip">'

    f'<div class="data-strip-item" style="padding-left:0;">'
    f'<div class="ds-label">Today Volume</div>'
    f'<div class="ds-main">{_fmt_vol(vol_today)}</div>'
    f'<div class="ds-sub" style="color:{vol_color};">{vol_sign}{vol_vs_3m:.0f}% vs 3M avg</div>'
    f'</div>'

    f'<div class="data-strip-item">'
    f'<div class="ds-label">Avg Vol 3M</div>'
    f'<div class="ds-main">{_fmt_vol(vol_avg_3m)}</div>'
    f'</div>'

    f'<div class="data-strip-item">'
    f'<div class="ds-label">Avg Vol 6M</div>'
    f'<div class="ds-main">{_fmt_vol(vol_avg_6m)}</div>'
    f'</div>'

    + _trend_html(trend_30, "30D Trend")
    + _trend_html(trend_60, "60D Trend")
    + _trend_html(trend_90, "90D Trend")

    + (
        f'<div class="data-strip-item">'
        f'<div class="ds-label">RSI 14</div>'
        f'<div class="ds-main" style="color:{_rsi_color};">{_rsi_val if _rsi_val is not None else "—"}</div>'
        f'</div>'
        f'<div class="data-strip-item">'
        f'<div class="ds-label">MACD</div>'
        f'<div class="ds-main" style="color:{_macd_color};">'
        + (f'{_macd_sign}{abs(_macd_hist):.2f}' if _macd_hist is not None else '—') +
        f'</div>'
        f'</div>'
    )

    + f'</div>',
    unsafe_allow_html=True
)

# ─── גרף מחיר עם tabs ────────────────────────────────────────────────────────
_range_labels = {"5D": "5 Days", "1M": "1 Month", "3M": "3 Months"}
tab_cols = st.columns(len(_range_labels) + 4)  # push tabs to the right
for _i, (_rng, _lbl) in enumerate(_range_labels.items()):
    with tab_cols[_i + 4]:
        _is_active = st.session_state["chart_range"] == _rng
        if st.button(_lbl, key=f"range_{_rng}",
                     type="primary" if _is_active else "secondary",
                     use_container_width=True):
            st.session_state["chart_range"] = _rng
            st.rerun()

_chart_range = st.session_state["chart_range"]
_df_chart = {"5D": df5d, "1M": _load_history_1m(ticker), "3M": df6m}.get(_chart_range, df5d)

# SMA-20
_close_c = _df_chart["Close"].squeeze()
_sma20   = _close_c.rolling(20).mean()

# Volume colors
_vol_c  = _df_chart["Volume"].squeeze()
_c_open = _df_chart["Open"].squeeze()
_c_cls  = _df_chart["Close"].squeeze()
_vol_colors = ["rgba(45,212,160,0.33)" if c >= o else "rgba(224,95,95,0.33)" for c, o in zip(_c_cls, _c_open)]

fig_mini = make_subplots(rows=2, cols=1, shared_xaxes=True,
                         row_heights=[0.72, 0.28], vertical_spacing=0.02)
fig_mini.add_trace(go.Candlestick(
    x=_df_chart.index,
    open=_df_chart["Open"].squeeze(), high=_df_chart["High"].squeeze(),
    low=_df_chart["Low"].squeeze(), close=_c_cls,
    increasing_line_color="#2DD4A0", decreasing_line_color="#E05F5F",
    showlegend=False, name="מחיר"
), row=1, col=1)
fig_mini.add_trace(go.Scatter(
    x=_df_chart.index, y=_sma20,
    line=dict(color="#C8A96E", width=1), opacity=0.7,
    showlegend=False, name="SMA 20"
), row=1, col=1)
fig_mini.add_trace(go.Bar(
    x=_df_chart.index, y=_vol_c, marker_color=_vol_colors,
    showlegend=False, name="נפח"
), row=2, col=1)
fig_mini.update_layout(
    template="plotly_dark", paper_bgcolor="#07070f", plot_bgcolor="#0e0e1c",
    height=260, margin=dict(l=0, r=0, t=6, b=0),
    xaxis=dict(showgrid=False, rangeslider_visible=False, tickfont=dict(color="#6E6E92", size=10)),
    xaxis2=dict(showgrid=False, tickfont=dict(color="#6E6E92", size=9)),
    yaxis=dict(showgrid=True, gridcolor="#1a1a30", side="right", tickfont=dict(color="#6E6E92", size=10)),
    yaxis2=dict(showgrid=False, side="right", tickfont=dict(color="#38384E", size=9)),
)
st.plotly_chart(fig_mini, use_container_width=True, key="mini_chart")

# ══════════════════════════════════════════════════════════════════════════════
# ─── סוכני בינה מלאכותית ─────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-label">AI Intelligence Scan</div>', unsafe_allow_html=True)

col_scan, col_scan_info = st.columns([2, 3])
with col_scan:
    scan_btn = st.button("Scan News & Sentiment", use_container_width=True, type="primary", key="scan_agents")
with col_scan_info:
    if st.session_state["agents_ticker"] == ticker and st.session_state["news_data"]:
        st.markdown('<div class="hint" style="padding-top:10px;">✓ Results cached — click again to refresh</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="hint" style="padding-top:10px;">News Scout + Social Pulse will scan and show a combined signal</div>', unsafe_allow_html=True)

if scan_btn:
    with st.spinner("News Scout scanning headlines..."):
        try:
            st.session_state["news_data"] = get_news(ticker)
        except Exception as e:
            st.session_state["news_data"] = {"error": str(e)}
    with st.spinner("Social Pulse analyzing social media..."):
        try:
            st.session_state["social_data"] = get_social_pulse(ticker)
        except Exception as e:
            st.session_state["social_data"] = {"aggregate_score": 0.0, "error": str(e)}
    st.session_state["agents_ticker"] = ticker

# ─── Agent Results ────────────────────────────────────────────────────────────
news_score = 0.0
social_score = 0.0
comb_score = 0.0
agent_target_suggestion = None

if st.session_state["agents_ticker"] == ticker and st.session_state["news_data"]:
    news_data   = st.session_state["news_data"]
    social_data = st.session_state["social_data"] or {}

    news_score   = news_data.get("aggregate_score", 0.0)
    social_score = social_data.get("aggregate_score", 0.0)

    col_ag1, col_ag2 = st.columns(2, gap="medium")

    # ── News Scout ────────────────────────────────────────────────────────────
    with col_ag1:
        headlines = news_data.get("headlines", [])
        # נסה לחלץ יעד מהכותרת הראשונה
        for h in headlines:
            p = parse_price_from_text(h.get("title", ""))
            if p and p > price * 0.95:
                agent_target_suggestion = p
                break

        news_rows = ""
        for h in headlines:
            sc = h.get("score", 0.0)
            if sc > 0.1:
                sc_color, sc_bg = "#2DD4A0", "#2DD4A018"
            elif sc < -0.1:
                sc_color, sc_bg = "#E05F5F", "#E05F5F18"
            else:
                sc_color, sc_bg = "#C8A96E", "#C8A96E18"
            title  = h.get("title", "")[:90] + ("…" if len(h.get("title","")) > 90 else "")
            source = h.get("source", "")
            url    = h.get("url", "#")
            news_rows += (
                f'<div class="news-row">'
                f'<div class="news-score" style="color:{sc_color};background:{sc_bg};">{sc:+.2f}</div>'
                f'<div>'
                f'<div class="news-text"><a href="{url}" target="_blank" '
                f'style="color:#EDE8E0;text-decoration:none;">{title}</a></div>'
                f'<div class="news-source">{source}</div>'
                f'</div></div>'
            )
        if news_data.get("error"):
            news_rows = f'<div class="hint">{news_data["error"]}</div>'

        score_color = "#2DD4A0" if news_score > 0.1 else "#E05F5F" if news_score < -0.1 else "#C8A96E"
        st.markdown(
            f'<div class="agent-card">'
            f'<div class="agent-title">📰 News Scout'
            f'<span style="float:left;color:{score_color};font-size:13px;font-weight:700;">{news_score:+.2f}</span></div>'
            f'{news_rows}'
            f'</div>',
            unsafe_allow_html=True
        )

    # ── Social Pulse ─────────────────────────────────────────────────────────
    with col_ag2:
        st_data     = social_data.get("stocktwits", {})
        ape_data    = social_data.get("apewisdom", {})
        reddit_data = social_data.get("reddit", {})

        rows_html = ""
        if st_data.get("available") and st_data.get("total_messages", 0) > 0:
            bull = st_data.get("bullish", 0)
            tot  = st_data.get("total_messages", 1)
            bp   = round(bull / tot * 100)
            bar_green = f'<div style="height:4px;background:#2DD4A055;border-radius:2px;margin-top:4px;">' \
                        f'<div style="width:{bp}%;height:100%;background:#2DD4A0;border-radius:2px;"></div></div>'
            rows_html += (
                f'<div class="sentiment-row"><span class="sentiment-label">StockTwits</span>'
                f'<span class="sentiment-value">{bp}% Bullish</span></div>'
                + bar_green
            )
        if ape_data.get("available") and ape_data.get("mentions_24h", 0) > 0:
            rows_html += (
                f'<div class="sentiment-row"><span class="sentiment-label">ApeWisdom Rank</span>'
                f'<span class="sentiment-value">#{ape_data["rank"]} · {ape_data["mentions_24h"]} mentions</span></div>'
            )
        if reddit_data.get("available") and reddit_data.get("mentions", 0) > 0:
            rs = reddit_data["score"]
            rc = "#2DD4A0" if rs > 0 else "#E05F5F"
            rows_html += (
                f'<div class="sentiment-row"><span class="sentiment-label">Reddit</span>'
                f'<span class="sentiment-value" style="color:{rc};">{rs:+.2f} · {reddit_data["mentions"]} posts</span></div>'
            )
        if not rows_html:
            rows_html = '<div class="hint">No social data — add API keys to .env</div>'

        sc_color = "#2DD4A0" if social_score > 0.1 else "#E05F5F" if social_score < -0.1 else "#C8A96E"
        st.markdown(
            f'<div class="agent-card">'
            f'<div class="agent-title">📱 Social Pulse'
            f'<span style="float:left;color:{sc_color};font-size:13px;font-weight:700;">{social_score:+.2f}</span></div>'
            f'{rows_html}'
            f'</div>',
            unsafe_allow_html=True
        )

    # ── סיגנל משולב ──────────────────────────────────────────────────────────
    combined = combine_signals(news_score, social_score)
    comb_score = combined["score"]
    comb_label = combined["label"]
    comb_color = combined["color"]
    pill_bg = comb_color + "22"

    if agent_target_suggestion:
        target_hint = f"  ·  Target extracted from news: <b>{currency}{agent_target_suggestion:.2f}</b>"
    else:
        target_hint = ""

    # ── Sentiment gauge (Phase 4) ─────────────────────────────────────────
    gauge_pct = max(0, min(100, (comb_score + 1) / 2 * 100))
    st.markdown(
        f'<div style="background:#0e0e1c;border:1px solid #1e1e38;border-radius:12px;'
        f'padding:16px 20px;margin:4px 0 8px 0;">'
        f'<div style="display:flex;justify-content:space-between;align-items:flex-end;margin-bottom:10px;">'
        f'<div style="font-size:10px;color:#6E6E92;letter-spacing:1.5px;text-transform:uppercase;">Combined AI Signal</div>'
        f'<div style="font-size:22px;font-weight:900;color:{comb_color};letter-spacing:-0.02em;">{comb_score:+.2f}</div>'
        f'</div>'
        f'<div class="gauge-track">'
        f'<div class="gauge-pointer" style="left:{gauge_pct:.1f}%;"></div>'
        f'</div>'
        f'<div class="gauge-labels"><span>Sell</span><span>Neutral</span><span>Buy</span></div>'
        f'<div style="margin-top:8px;display:flex;justify-content:space-between;align-items:center;">'
        f'<div style="font-size:12px;color:#EDE8E0;">News {news_score:+.2f} · Social {social_score:+.2f}{target_hint}</div>'
        f'<div class="signal-pill" style="color:{comb_color};background:{pill_bg};border:1px solid {comb_color}44;">'
        f'{comb_label}</div>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True
    )

st.markdown("---")

# ─── מחשבון עסקה v3 ──────────────────────────────────────────────────────────
st.markdown('<div class="section-label">Trade Calculator</div>', unsafe_allow_html=True)

_col_a, _col_b, _col_c, _col_d = st.columns([2, 1, 1, 1])
with _col_a:
    account_size = st.number_input(f"Account Size ({currency})", value=5000.0, step=500.0, format="%.0f", key="account_size")
with _col_b:
    pct_inv_input = st.number_input("% Investing", value=100.0, min_value=1.0, max_value=100.0, step=5.0, format="%.0f", key="pct_inv")
with _col_c:
    direction = st.selectbox("Direction", ["LONG", "SHORT"], key="direction")
with _col_d:
    commission = st.number_input(f"Commission ({currency})", value=7.0, step=1.0, format="%.0f", key="comm")

_col_e, _col_f, _col_g = st.columns(3)
with _col_e:
    entry = st.number_input(f"Entry Price ({currency})", value=float(price), step=0.5, format="%.2f", key="entry")
with _col_f:
    stop = st.number_input(f"Stop Loss ({currency})", value=float(suggested_stop), step=0.5, format="%.2f", key="stop")
    st.markdown(f'<div class="hint">מוצע: {currency}{suggested_stop:.2f} (1.5 × ATR)</div>', unsafe_allow_html=True)
with _col_g:
    default_target = float(agent_target_suggestion) if agent_target_suggestion else round(float(price) * 1.06, 2)
    target = st.number_input(f"Target ({currency})", value=default_target, step=0.5, format="%.2f", key="target")
    if agent_target_suggestion:
        st.markdown(f'<div class="hint">נחלץ מחדשות ע"י News Scout</div>', unsafe_allow_html=True)

# Preview row
import math as _math
_planned = account_size * pct_inv_input / 100
_shares_preview = _math.floor(_planned / entry) if entry > 0 else 0
st.markdown(
    f'<div style="background:#0e0e1c;border:1px solid #2a2a48;border-radius:8px;'
    f'padding:10px 16px;margin:8px 0;display:flex;gap:32px;">'
    f'<span style="font-size:13px;color:#9090B8;">Planned Investment: '
    f'<b style="color:#C8A96E;">{currency}{_planned:,.0f}</b></span>'
    f'<span style="font-size:13px;color:#9090B8;">Shares to buy: '
    f'<b style="color:#C8A96E;">{_shares_preview}</b></span>'
    f'<span style="font-size:13px;color:#9090B8;">Direction: '
    f'<b style="color:{"#2DD4A0" if direction == "LONG" else "#E05F5F"};">{direction}</b></span>'
    f'</div>',
    unsafe_allow_html=True
)

# ─── Calculate button ─────────────────────────────────────────────────────────
st.markdown("")
calc_btn = st.button("⚡ Calculate Trade", use_container_width=True, type="primary", key="calc")

# ─── תוצאות ──────────────────────────────────────────────────────────────────
if calc_btn:
    errors = []
    if direction == "LONG":
        if target <= entry:
            errors.append("Target must be above entry price (LONG)")
        if stop >= entry:
            errors.append("Stop loss must be below entry price (LONG)")
    else:
        if target >= entry:
            errors.append("Target must be below entry price (SHORT)")
        if stop <= entry:
            errors.append("Stop loss must be above entry price (SHORT)")
    if account_size <= 0:
        errors.append("Account size must be positive")

    if errors:
        for e in errors:
            st.error(e)
    else:
        try:
            result = evaluate_trade_v3(
                ticker=ticker,
                direction=direction,
                account_size=account_size,
                pct_investing=pct_inv_input / 100,
                entry=entry,
                stop=stop,
                target=target,
                commission=commission,
            )

            is_go        = result["verdict"] == "GO"
            rr_ratio     = result["rr"]
            shares       = result["shares"]
            gross_profit = result["gross_profit"]
            net_profit   = result["net_profit"]
            profit_pct   = result["profit_pct"]
            risk_total   = result["risk_total"]
            gross_loss   = risk_total

            banner_color  = "#2DD4A0" if is_go else "#E05F5F"
            banner_glow   = "#2DD4A015" if is_go else "#E05F5F15"
            verdict_text  = "GO" if is_go else "NO-GO"
            verdict_icon  = "✦" if is_go else "✕"

            pct_to_target = abs(target - entry) / entry * 100
            pct_to_stop   = abs(entry - stop)   / entry * 100

            # R:R bar marker position (clamped 0–100% for 0–4 range)
            rr_pct = min(100, rr_ratio / 4 * 100)

            st.markdown("---")

            # ── Banner (Phase 5) ──────────────────────────────────────────────
            st.markdown(
                f'<div class="result-banner animated" style="'
                f'background:linear-gradient(135deg,{banner_glow},{banner_color}08);'
                f'border:1px solid {banner_color}55;'
                f'--banner-color:{banner_color};">'
                f'<div style="font-size:11px;font-weight:700;color:{banner_color};'
                f'letter-spacing:3px;text-transform:uppercase;margin-bottom:8px;">Recommendation</div>'
                f'<div class="verdict-label" style="color:{banner_color};font-size:56px;">'
                f'{verdict_icon} &nbsp; {verdict_text}</div>'
                f'<div class="verdict-reason">{result["verdict_reason"]}</div>'
                f'<div style="margin-top:8px;font-size:12px;color:#6E6E92;">'
                f'Entry {currency}{entry:,.2f} &nbsp;·&nbsp; '
                f'Target +{pct_to_target:.1f}% &nbsp;·&nbsp; '
                f'Stop -{pct_to_stop:.1f}%'
                + (f' &nbsp;·&nbsp; AI Sentiment {comb_score:+.2f}' if (news_score != 0.0 or social_score != 0.0) else "") +
                f'</div>'
                # R:R progress bar
                f'<div class="rr-bar-wrap">'
                f'<div style="font-size:9px;color:#6E6E92;letter-spacing:1px;margin-bottom:4px;">R:R RATIO</div>'
                f'<div class="rr-bar-track">'
                f'<div class="rr-bar-marker" style="left:{rr_pct:.1f}%;"></div>'
                f'</div>'
                f'<div class="rr-bar-labels"><span>0</span><span>1</span><span style="color:#C8A96E;font-weight:700;">GO ≥ 2</span><span>3</span><span>4+</span></div>'
                f'</div>'
                f'</div>',
                unsafe_allow_html=True
            )

            # ── Income Forecast ───────────────────────────────────────────────
            _income_html = (
                f'<div style="background:#10101e;border:1px solid #2a2a48;border-radius:14px;'
                f'padding:22px 26px;margin:16px 0;">'
                f'<div style="font-size:11px;font-weight:700;color:#C8A96E;letter-spacing:2px;'
                f'text-transform:uppercase;margin-bottom:16px;padding-bottom:8px;'
                f'border-bottom:1px solid #2a2a48;">📊 Income Forecast</div>'
                # stats row
                f'<div style="display:flex;gap:24px;flex-wrap:wrap;margin-bottom:16px;">'
                f'<div><div style="font-size:11px;color:#9090B8;margin-bottom:4px;letter-spacing:1px;">SHARES</div>'
                f'<div style="font-size:22px;font-weight:700;color:#F0ECE6;">{shares}</div></div>'
                f'<div><div style="font-size:11px;color:#9090B8;margin-bottom:4px;letter-spacing:1px;">INVESTED</div>'
                f'<div style="font-size:22px;font-weight:700;color:#F0ECE6;">{currency}{result["actual_investment"]:,.0f}</div></div>'
                f'<div><div style="font-size:11px;color:#9090B8;margin-bottom:4px;letter-spacing:1px;">MAX RISK</div>'
                f'<div style="font-size:22px;font-weight:700;color:#E05F5F;">{currency}{risk_total:,.0f}</div></div>'
                f'<div><div style="font-size:11px;color:#9090B8;margin-bottom:4px;letter-spacing:1px;">GROSS PROFIT</div>'
                f'<div style="font-size:22px;font-weight:700;color:#2DD4A0;">+{currency}{gross_profit:,.0f}</div></div>'
                f'<div><div style="font-size:11px;color:#9090B8;margin-bottom:4px;letter-spacing:1px;">COMMISSION</div>'
                f'<div style="font-size:22px;font-weight:700;color:#E05F5F;">-{currency}{result["commission_total"]:,.0f}</div></div>'
                f'<div><div style="font-size:11px;color:#9090B8;margin-bottom:4px;letter-spacing:1px;">NET PROFIT</div>'
                f'<div style="font-size:24px;font-weight:900;color:#2DD4A0;">+{currency}{net_profit:,.0f}'
                f'<span style="font-size:15px;color:#9090B8;font-weight:400;"> (+{profit_pct:.1f}%)</span></div></div>'
                f'</div>'
                f'<div style="border-top:1px solid #2a2a48;margin-bottom:14px;"></div>'
                f'<div style="font-size:11px;font-weight:700;color:#C8A96E;letter-spacing:2px;'
                f'text-transform:uppercase;margin-bottom:10px;">🎯 Exit Tiers</div>'
            )
            for _tier in result["exit_tiers"]:
                _tc = "#2DD4A0" if _tier["profit"] > 0 else "#E05F5F"
                _income_html += (
                    f'<div style="display:flex;justify-content:space-between;align-items:center;'
                    f'padding:7px 0;border-bottom:1px solid #16162a;">'
                    f'<span style="font-size:13px;color:#9090B8;min-width:70px;">{_tier["pct"]}% exit</span>'
                    f'<span style="font-size:13px;color:#EDE8E0;">{int(_tier["shares"])} shares @ '
                    f'{currency}{_tier["price"]:,.2f}</span>'
                    f'<span style="font-size:15px;font-weight:700;color:{_tc};">+{currency}{_tier["profit"]:,.0f}'
                    f'<span style="font-size:12px;color:#6E6E92;font-weight:400;"> '
                    f'(+{_tier["pct_return"]:.1f}%)</span></span>'
                    f'</div>'
                )
            _income_html += f'</div>'
            st.markdown(_income_html, unsafe_allow_html=True)

            # ── Metric summary row ────────────────────────────────────────────
            col_m1, col_m2, col_m3 = st.columns(3)
            with col_m1:
                st.metric("R:R", result["rr_formatted"])
            with col_m2:
                st.metric("Shares", f"{shares}")
            with col_m3:
                st.metric("Total Invested", f"{currency}{result['actual_investment']:,.0f}")

            # ── Chart with zone fills + levels (Phase 3 + 5) ─────────────────
            fig2 = make_subplots(rows=2, cols=1, shared_xaxes=True,
                                 row_heights=[0.72, 0.28], vertical_spacing=0.02)
            _df2    = _df_chart  # use whatever range user had selected
            _open2  = _df2["Open"].squeeze()
            _cls2   = _df2["Close"].squeeze()
            _vols2  = _df2["Volume"].squeeze()
            _vcols2 = ["rgba(45,212,160,0.33)" if c >= o else "rgba(224,95,95,0.33)" for c, o in zip(_cls2, _open2)]
            _sma2   = _cls2.rolling(20).mean()

            fig2.add_trace(go.Candlestick(
                x=_df2.index,
                open=_open2, high=_df2["High"].squeeze(),
                low=_df2["Low"].squeeze(), close=_cls2,
                increasing_line_color="#2DD4A0", decreasing_line_color="#E05F5F",
                showlegend=False,
            ), row=1, col=1)
            fig2.add_trace(go.Scatter(
                x=_df2.index, y=_sma2,
                line=dict(color="#C8A96E", width=1), opacity=0.6,
                showlegend=False, name="SMA 20"
            ), row=1, col=1)
            fig2.add_trace(go.Bar(
                x=_df2.index, y=_vols2, marker_color=_vcols2,
                showlegend=False
            ), row=2, col=1)

            # Zone fills
            fig2.add_hrect(y0=entry, y1=target, fillcolor="#2DD4A0", opacity=0.05,
                           line_width=0, row=1, col=1)
            fig2.add_hrect(y0=stop,  y1=entry,  fillcolor="#E05F5F", opacity=0.05,
                           line_width=0, row=1, col=1)

            fig2.add_hline(y=entry, line_color="#C8A96E", line_width=1.5, line_dash="dot",
                          annotation_text=f"Entry {currency}{entry:.2f}",
                          annotation_position="right",
                          annotation_font=dict(color="#C8A96E", size=11), row=1, col=1)
            fig2.add_hline(y=target, line_color="#2DD4A0", line_width=1.5, line_dash="dash",
                          annotation_text=f"Target {currency}{target:.2f}",
                          annotation_position="right",
                          annotation_font=dict(color="#2DD4A0", size=11), row=1, col=1)
            fig2.add_hline(y=stop, line_color="#E05F5F", line_width=1.5, line_dash="dash",
                          annotation_text=f"Stop {currency}{stop:.2f}",
                          annotation_position="right",
                          annotation_font=dict(color="#E05F5F", size=11), row=1, col=1)
            fig2.update_layout(
                template="plotly_dark", paper_bgcolor="#07070f", plot_bgcolor="#0e0e1c",
                height=320, margin=dict(l=0, r=90, t=16, b=0),
                xaxis=dict(showgrid=False, rangeslider_visible=False,
                           tickfont=dict(color="#6E6E92", size=10)),
                xaxis2=dict(showgrid=False, tickfont=dict(color="#6E6E92", size=9)),
                yaxis=dict(showgrid=True, gridcolor="#1a1a30", side="right",
                           tickfont=dict(color="#6E6E92", size=10)),
                yaxis2=dict(showgrid=False, side="right", tickfont=dict(color="#38384E", size=9)),
                title=dict(text="Price Window — Trade Levels",
                           font=dict(size=12, color="#6E6E92", family="Heebo")),
            )
            st.plotly_chart(fig2, use_container_width=True)

            # ── Save to Journal ───────────────────────────────────────────────
            st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
            save_col, _ = st.columns([1, 3])
            with save_col:
                if st.button("💾 Save to Journal", key="save_trade", use_container_width=True):
                    save_trade({
                        "ticker":       ticker,
                        "direction":    direction,
                        "entry":        entry,
                        "target":       target,
                        "stop":         stop,
                        "rr_ratio":     round(rr_ratio, 2),
                        "shares":       shares,
                        "invested":     round(result["actual_investment"], 2),
                        "net_profit":   round(net_profit, 2),
                        "profit_pct":   round(profit_pct, 2),
                        "risk":         round(gross_loss, 2),
                        "verdict":      "GO" if is_go else "NO-GO",
                        "news_score":   round(news_score, 2),
                        "social_score": round(social_score, 2),
                    })
                    st.success("✓ Saved to journal")
                    st.rerun()

            # ── Detailed breakdown ────────────────────────────────────────────
            with st.expander("Full Calculation Breakdown"):
                _detail_rows = [
                    ("Ticker",         ticker),
                    ("Direction",      direction),
                    ("Account Size",   f"{currency}{result['account_size']:,.0f}"),
                    ("% Investing",    f"{result['pct_investing']:.0f}%"),
                    ("Planned Invest", f"{currency}{result['planned_investment']:,.0f}"),
                    ("Actual Invest",  f"{currency}{result['actual_investment']:,.0f}"),
                    ("Shares",         str(shares)),
                    ("Entry",          f"{currency}{entry:,.2f}"),
                    ("Stop Loss",      f"{currency}{stop:,.2f}"),
                    ("Target",         f"{currency}{target:,.2f}"),
                    ("Risk / Share",   f"{currency}{result['risk_per_share']:,.4f}"),
                    ("Reward / Share", f"{currency}{result['reward_per_share']:,.4f}"),
                    ("R:R",            result["rr_formatted"]),
                    ("Total Risk",     f"{currency}{risk_total:,.2f}"),
                    ("Gross Profit",   f"+{currency}{gross_profit:,.2f}"),
                    ("Commission",     f"-{currency}{result['commission_total']:,.2f}"),
                    ("Net Profit",     f"+{currency}{net_profit:,.2f}"),
                    ("Return on Inv",  f"+{profit_pct:.2f}%"),
                ]
                _tbl = "| פרמטר | ערך |\n|---|---|\n"
                for k, v in _detail_rows:
                    _tbl += f"| {k} | **{v}** |\n"
                st.markdown(_tbl)

        except ValueError as e:
            st.error(f"Calculation error: {e}")

# ─── פאנל תמיכה/התנגדות (תחתית העמוד) ───────────────────────────────────────
st.markdown("---")
_sr_levels = (sr_data or {}).get("levels", [])
if _sr_levels:
    _sr_price = (sr_data or {}).get("current_price") or price
    _rows_sr  = ""
    _cp_inserted = False
    for _lvl in _sr_levels:
        _lp = _lvl["price"]
        _lt = _lvl.get("type", "neutral")
        _lg = _lvl.get("group", "")
        _ln = _lvl["name"]
        if not _cp_inserted and _lp < _sr_price:
            _cp_inserted = True
            _rows_sr += (
                f'<div style="display:flex;justify-content:space-between;align-items:center;'
                f'padding:8px 12px;background:#C8A96E12;border-radius:6px;margin:5px 0;">'
                f'<span style="font-size:12px;font-weight:700;color:#C8A96E;">◆ CURRENT PRICE</span>'
                f'<span style="font-size:15px;font-weight:900;color:#C8A96E;">{currency}{_sr_price:,.2f}</span>'
                f'<span style="font-size:11px;color:#C8A96E88;">NOW</span>'
                f'</div>'
            )
        _color = "#E05F5F" if _lt == "resistance" else "#2DD4A0" if _lt == "support" else "#C8A96E"
        _lbl   = "התנגדות" if _lt == "resistance" else "תמיכה" if _lt == "support" else "—"
        _rows_sr += (
            f'<div style="display:flex;justify-content:space-between;align-items:center;'
            f'padding:5px 4px;border-bottom:1px solid #16162a;">'
            f'<div style="display:flex;align-items:center;gap:8px;min-width:0;">'
            f'<span style="color:{_color};font-size:9px;">●</span>'
            f'<span style="font-size:13px;color:#EDE8E0;white-space:nowrap;">{_ln}</span>'
            f'<span style="font-size:10px;color:#6E6E92;background:#14142a;border-radius:4px;'
            f'padding:1px 6px;white-space:nowrap;">{_lg}</span>'
            f'</div>'
            f'<div style="display:flex;align-items:center;gap:14px;flex-shrink:0;">'
            f'<span style="font-size:15px;font-weight:700;color:{_color};">{currency}{_lp:,.2f}</span>'
            f'<span style="font-size:11px;color:{_color};min-width:56px;text-align:right;">{_lbl}</span>'
            f'</div>'
            f'</div>'
        )
    if not _cp_inserted:
        _rows_sr = (
            f'<div style="display:flex;justify-content:space-between;align-items:center;'
            f'padding:8px 12px;background:#C8A96E12;border-radius:6px;margin:0 0 6px 0;">'
            f'<span style="font-size:12px;font-weight:700;color:#C8A96E;">◆ CURRENT PRICE</span>'
            f'<span style="font-size:15px;font-weight:900;color:#C8A96E;">{currency}{_sr_price:,.2f}</span>'
            f'<span style="font-size:11px;color:#C8A96E88;">NOW</span>'
            f'</div>'
        ) + _rows_sr
    st.markdown(
        f'<div style="background:#10101e;border:1px solid #2a2a48;border-radius:12px;'
        f'padding:18px 22px;margin:12px 0 16px 0;">'
        f'<div style="font-size:11px;font-weight:700;color:#C8A96E;letter-spacing:2px;'
        f'text-transform:uppercase;margin-bottom:12px;padding-bottom:8px;'
        f'border-bottom:1px solid #2a2a48;">Support &amp; Resistance — 10 מדדים</div>'
        f'{_rows_sr}'
        f'</div>',
        unsafe_allow_html=True
    )

# ─── Footer (Phase 6) ─────────────────────────────────────────────────────────
_updated = datetime.now().strftime("%H:%M:%S")
st.markdown(f"""
<div style="margin-top:48px;padding-top:20px;border-top:1px solid #1e1e38;">
  <div style="display:flex;flex-wrap:wrap;gap:8px;justify-content:center;margin-bottom:12px;">
    <span class="badge-pill">📈 Yahoo Finance</span>
    <span class="badge-pill">📰 Marketaux News</span>
    <span class="badge-pill">📡 Finnhub</span>
    <span class="badge-pill">💬 Reddit · ApeWisdom</span>
    <span class="badge-pill">🤖 NLTK Sentiment</span>
  </div>
  <div style="text-align:center;font-size:10px;color:#38384E;letter-spacing:0.05em;line-height:1.8;">
    Last updated: {_updated} &nbsp;·&nbsp;
    For informational purposes only &nbsp;·&nbsp; Not investment advice
    <br/>Trade Calculator v1.0
  </div>
</div>
""", unsafe_allow_html=True)
