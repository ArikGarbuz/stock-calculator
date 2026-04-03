"""
app.py — Stock Decision Support Agent
Streamlit Dashboard | עברית | Dark Mode
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time

from data.market_data import get_price_history, get_current_quote, get_company_name, is_valid_ticker
from calculators.technical_calc import add_indicators
from calculators.sentiment_scorer import combine_signals
from calculators.trade_calc import calc_atr, evaluate_trade
from agents.news_scout import get_news
from agents.social_pulse import get_social_pulse
from agents.trade_calculator import parse_price_from_text, auto_suggest_stop

# ─── הגדרות עמוד ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Stock Decision Agent",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── CSS מותאם ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Dark mode base */
    .stApp { background-color: #0e1117; color: #e0e0e0; }
    .stSidebar { background-color: #161b22; }

    /* Metric cards */
    [data-testid="metric-container"] {
        background: #1c2333;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 12px;
    }
    [data-testid="metric-container"] label { color: #8b949e !important; font-size: 13px; }
    [data-testid="metric-container"] [data-testid="stMetricValue"] { font-size: 22px; font-weight: 700; }

    /* Signal card */
    .signal-card {
        border-radius: 10px;
        padding: 18px 24px;
        text-align: center;
        font-size: 28px;
        font-weight: 800;
        margin: 8px 0;
    }

    /* News item */
    .news-item {
        background: #161b22;
        border-left: 4px solid #30363d;
        border-radius: 6px;
        padding: 10px 14px;
        margin: 6px 0;
        font-size: 14px;
    }

    /* Section headers */
    .section-header {
        font-size: 16px;
        font-weight: 700;
        color: #58a6ff;
        margin: 16px 0 8px 0;
        border-bottom: 1px solid #21262d;
        padding-bottom: 4px;
    }

    /* RTL support for Hebrew */
    [dir="rtl"] { text-align: right; }
    .hebrew { direction: rtl; text-align: right; }
</style>
""", unsafe_allow_html=True)

# ─── Session State ────────────────────────────────────────────────────────────
if "watchlist" not in st.session_state:
    st.session_state.watchlist = ["AAPL", "NVDA", "TEVA.TA"]
if "current_ticker" not in st.session_state:
    st.session_state.current_ticker = "AAPL"
if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = 0.0

# ─── Sidebar ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📈 Stock Agent")
    st.markdown("---")

    # חיפוש טיקר
    st.markdown("**הזן סמל מניה**")
    col_input, col_go = st.columns([3, 1])
    with col_input:
        ticker_input = st.text_input("", value="", placeholder="AAPL / TEVA.TA", label_visibility="collapsed")
    with col_go:
        if st.button("Go", use_container_width=True) and ticker_input.strip():
            t = ticker_input.strip().upper()
            with st.spinner("בודק..."):
                if is_valid_ticker(t):
                    st.session_state.current_ticker = t
                    if t not in st.session_state.watchlist:
                        st.session_state.watchlist.append(t)
                else:
                    st.error(f"הסמל '{t}' לא נמצא")

    st.markdown("---")

    # Watchlist
    st.markdown("**Watchlist**")
    for i, wt in enumerate(list(st.session_state.watchlist)):
        col_w, col_x = st.columns([4, 1])
        with col_w:
            is_active = wt == st.session_state.current_ticker
            btn_label = f"**{wt}**" if is_active else wt
            if st.button(btn_label, key=f"wl_{i}", use_container_width=True):
                st.session_state.current_ticker = wt
        with col_x:
            if st.button("−", key=f"rm_{i}"):
                st.session_state.watchlist.pop(i)
                if st.session_state.current_ticker == wt:
                    st.session_state.current_ticker = st.session_state.watchlist[0] if st.session_state.watchlist else "AAPL"
                st.rerun()

    st.markdown("---")

    # טווח זמן
    st.markdown("**טווח זמן**")
    period_label = st.radio(
        "", ["1D", "5D", "1M", "3M", "1Y", "MAX"],
        index=3, horizontal=True, label_visibility="collapsed"
    )

    st.markdown("---")

    # רענון
    col_r1, col_r2 = st.columns(2)
    with col_r1:
        if st.button("רענן", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    with col_r2:
        auto_refresh = st.toggle("אוטו", value=False)

    if auto_refresh:
        refresh_interval = st.slider("שניות", 15, 60, 30)
        now = time.time()
        if now - st.session_state.last_refresh >= refresh_interval:
            st.session_state.last_refresh = now
            st.cache_data.clear()
            st.rerun()

    st.markdown("---")
    st.caption(f"טיקר פעיל: **{st.session_state.current_ticker}**")

# ─── Main Area ────────────────────────────────────────────────────────────────
ticker = st.session_state.current_ticker

# כותרת
try:
    company_name = get_company_name(ticker)
except Exception:
    company_name = ticker

st.markdown(f"# {company_name} &nbsp; `{ticker}`")

# ─── טעינת נתונים ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=60)
def load_market_data(ticker, period_label):
    df = get_price_history(ticker, period_label)
    df = add_indicators(df)
    return df

@st.cache_data(ttl=30)
def load_quote(ticker):
    return get_current_quote(ticker)

@st.cache_data(ttl=300)
def load_news(ticker):
    return get_news(ticker)

@st.cache_data(ttl=300)
def load_social(ticker):
    return get_social_pulse(ticker)

try:
    quote = load_quote(ticker)
except Exception as e:
    st.error(f"שגיאה בטעינת מחיר: {e}")
    st.stop()

try:
    df = load_market_data(ticker, period_label)
except Exception as e:
    st.error(f"שגיאה בטעינת היסטוריה: {e}")
    st.stop()

# ─── Metric Cards ─────────────────────────────────────────────────────────────
currency = quote.get("currency", "USD")
change_color = "normal" if quote["change"] >= 0 else "inverse"

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("מחיר נוכחי", f"{quote['price']:,.2f} {currency}")
with col2:
    sign = "+" if quote["change"] >= 0 else ""
    st.metric("שינוי", f"{sign}{quote['change']:,.2f}", delta=f"{sign}{quote['change_pct']:.2f}%")
with col3:
    vol = quote["volume"]
    vol_str = f"{vol/1_000_000:.1f}M" if vol >= 1_000_000 else f"{vol/1_000:.0f}K" if vol >= 1_000 else str(vol)
    st.metric("Volume", vol_str)
with col4:
    st.metric("גבוה / נמוך", f"{quote['high']:,.2f} / {quote['low']:,.2f}")

# ─── טאבים ────────────────────────────────────────────────────────────────────
tab_chart, tab_data, tab_signals, tab_compare, tab_trade = st.tabs(["📊 גרף", "📋 נתונים", "🎯 סיגנל", "🔄 השוואה", "🧮 מחשבון עסקה"])

# ══════════════════════ TAB 1: גרף ════════════════════════════════════════════
with tab_chart:
    chart_type = st.radio("סוג גרף", ["Candlestick", "Line"], horizontal=True)

    # גרף ראשי + RSI + MACD
    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        row_heights=[0.6, 0.2, 0.2],
        vertical_spacing=0.03,
        subplot_titles=("מחיר", "RSI", "MACD"),
    )

    close = df["Close"].squeeze()
    if chart_type == "Candlestick":
        fig.add_trace(go.Candlestick(
            x=df.index, open=df["Open"].squeeze(), high=df["High"].squeeze(),
            low=df["Low"].squeeze(), close=close,
            increasing_line_color="#00C853", decreasing_line_color="#D50000",
            name="מחיר", showlegend=False
        ), row=1, col=1)
    else:
        fig.add_trace(go.Scatter(
            x=df.index, y=close, mode="lines",
            line=dict(color="#58a6ff", width=2), name="מחיר"
        ), row=1, col=1)

    # SMA lines
    if "SMA_50" in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, y=df["SMA_50"].squeeze(), mode="lines",
            line=dict(color="#FF9800", width=1.5, dash="dot"), name="SMA 50"
        ), row=1, col=1)
    if "SMA_200" in df.columns and len(df) >= 200:
        fig.add_trace(go.Scatter(
            x=df.index, y=df["SMA_200"].squeeze(), mode="lines",
            line=dict(color="#9C27B0", width=1.5, dash="dash"), name="SMA 200"
        ), row=1, col=1)

    # RSI
    if "RSI" in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, y=df["RSI"].squeeze(), mode="lines",
            line=dict(color="#64FFDA", width=1.5), name="RSI", showlegend=False
        ), row=2, col=1)
        fig.add_hline(y=70, line_dash="dot", line_color="#D50000", row=2, col=1)
        fig.add_hline(y=30, line_dash="dot", line_color="#00C853", row=2, col=1)

    # MACD
    if "MACD" in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, y=df["MACD"].squeeze(), mode="lines",
            line=dict(color="#58a6ff", width=1.5), name="MACD", showlegend=False
        ), row=3, col=1)
        fig.add_trace(go.Scatter(
            x=df.index, y=df["MACD_Signal"].squeeze(), mode="lines",
            line=dict(color="#FF9800", width=1.5), name="Signal", showlegend=False
        ), row=3, col=1)
        colors_hist = ["#00C853" if v >= 0 else "#D50000" for v in df["MACD_Hist"].squeeze()]
        fig.add_trace(go.Bar(
            x=df.index, y=df["MACD_Hist"].squeeze(),
            marker_color=colors_hist, name="Histogram", showlegend=False
        ), row=3, col=1)

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0e1117",
        plot_bgcolor="#0e1117",
        height=700,
        margin=dict(l=0, r=0, t=30, b=0),
        xaxis_rangeslider_visible=False,
        legend=dict(orientation="h", y=1.02, x=0),
    )
    fig.update_xaxes(showgrid=True, gridcolor="#21262d")
    fig.update_yaxes(showgrid=True, gridcolor="#21262d")

    st.plotly_chart(fig, use_container_width=True)

# ══════════════════════ TAB 2: נתונים ════════════════════════════════════════
with tab_data:
    display_cols = [c for c in ["Open", "High", "Low", "Close", "Volume", "SMA_50", "SMA_200", "RSI", "MACD"] if c in df.columns]
    display_df = df[display_cols].tail(20).copy()
    display_df.index = display_df.index.strftime("%Y-%m-%d %H:%M")

    st.dataframe(
        display_df.style.format({
            "Open": "{:.2f}", "High": "{:.2f}", "Low": "{:.2f}", "Close": "{:.2f}",
            "Volume": "{:,.0f}", "SMA_50": "{:.2f}", "SMA_200": "{:.2f}",
            "RSI": "{:.1f}", "MACD": "{:.4f}",
        }).background_gradient(cmap="RdYlGn", subset=["Close", "RSI"]),
        use_container_width=True, height=420
    )

    # Export
    csv = df[display_cols].to_csv(index=True).encode("utf-8-sig")
    st.download_button(
        label="הורד CSV",
        data=csv,
        file_name=f"{ticker}_{period_label}.csv",
        mime="text/csv",
    )

# ══════════════════════ TAB 3: סיגנל ═════════════════════════════════════════
with tab_signals:
    if st.button("סרוק חדשות וסנטימנט", type="primary", use_container_width=True, key="scan_btn"):
        st.session_state["signal_loaded"] = True
        st.cache_data.clear()

    news_score = 0.0
    social_score = 0.0

    if st.session_state.get("signal_loaded") and st.session_state.get("current_ticker") == ticker:
        col_news, col_social = st.columns(2)

        # ─── News Scout ───────────────────────────────────────────────────────
        with col_news:
            st.markdown('<div class="section-header">📰 News Scout</div>', unsafe_allow_html=True)
            with st.spinner("טוען חדשות..."):
                try:
                    news_data = load_news(ticker)
                except Exception as e:
                    news_data = {"error": str(e)}

            if news_data.get("error"):
                st.warning(news_data["error"])
            else:
                news_score = news_data.get("aggregate_score", 0.0)
                for h in news_data.get("headlines", []):
                    sc = h["score"]
                    hcolor = "#00C853" if sc > 0.1 else "#D50000" if sc < -0.1 else "#FF9800"
                    url = h.get("url", "#")
                    title = h.get("title", "")
                    source = h.get("source", "")
                    st.markdown(
                        f'<div class="news-item">'
                        f'<span style="color:{hcolor};font-weight:700;">[{sc:+.2f}]</span> '
                        f'<a href="{url}" target="_blank" style="color:#e0e0e0;text-decoration:none;">{title}</a>'
                        f'<br><small style="color:#8b949e;">{source}</small>'
                        f'</div>',
                        unsafe_allow_html=True
                    )
                st.metric("ציון News Scout", f"{news_score:+.2f}")

        # ─── Social Pulse ─────────────────────────────────────────────────────
        with col_social:
            st.markdown('<div class="section-header">📱 Social Pulse</div>', unsafe_allow_html=True)
            with st.spinner("טוען סנטימנט חברתי..."):
                try:
                    social_data = load_social(ticker)
                except Exception as e:
                    social_data = {"aggregate_score": 0.0, "error": str(e)}

            social_score = social_data.get("aggregate_score", 0.0)

            st_data = social_data.get("stocktwits", {})
            if st_data.get("available") and st_data.get("total_messages", 0) > 0:
                bull = st_data.get("bullish", 0)
                total_msg = st_data.get("total_messages", 1)
                bull_pct = round(bull / total_msg * 100) if total_msg > 0 else 0
                st.markdown(f"**StockTwits** — {total_msg} הודעות")
                st.progress(bull_pct / 100, text=f"Bullish {bull_pct}% | Bearish {100-bull_pct}%")

            ape_data = social_data.get("apewisdom", {})
            if ape_data.get("available") and ape_data.get("mentions_24h", 0) > 0:
                st.markdown(f"**ApeWisdom** — {ape_data['mentions_24h']} מנציונס | #{ape_data['rank']}")

            reddit_data = social_data.get("reddit", {})
            if reddit_data.get("available") and reddit_data.get("mentions", 0) > 0:
                st.markdown(f"**Reddit** — {reddit_data['mentions']} פוסטים | {reddit_data['score']:+.2f}")
            elif not reddit_data.get("available"):
                st.caption("Reddit: הוסף מפתחות ב-.env")

            st.metric("ציון Social Pulse", f"{social_score:+.2f}")

    else:
        st.info("לחץ על 'סרוק חדשות וסנטימנט' לקבלת ניתוח מלא")
        news_score = 0.0
        social_score = 0.0

    # ─── Signal Card ─────────────────────────────────────────────────────────
    st.markdown("---")
    signal = combine_signals(news_score, social_score)
    score = signal["score"]
    label = signal["label"]
    color = signal["color"]

    st.markdown(
        f'<div class="signal-card" style="background:{color}22;border:2px solid {color};">'
        f'<div style="color:#8b949e;font-size:14px;font-weight:400;margin-bottom:4px;">סיגנל מסחר מצטבר</div>'
        f'<div style="color:{color};">{label}</div>'
        f'<div style="font-size:16px;color:#e0e0e0;font-weight:400;margin-top:4px;">ציון: {score:+.2f}</div>'
        f'</div>',
        unsafe_allow_html=True
    )

    # Gauge chart
    gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        domain={"x": [0, 1], "y": [0, 1]},
        gauge={
            "axis": {"range": [-1, 1], "tickcolor": "#8b949e"},
            "bar": {"color": color},
            "bgcolor": "#1c2333",
            "steps": [
                {"range": [-1, -0.3], "color": "#3a1010"},
                {"range": [-0.3, 0.3], "color": "#2a2100"},
                {"range": [0.3, 1], "color": "#0a2a0a"},
            ],
            "threshold": {"line": {"color": color, "width": 4}, "thickness": 0.75, "value": score},
        },
        title={"text": "Composite Score", "font": {"color": "#8b949e", "size": 14}},
        number={"font": {"color": color, "size": 32}},
    ))
    gauge.update_layout(
        paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
        height=280, margin=dict(l=20, r=20, t=40, b=20),
        font={"color": "#e0e0e0"},
    )
    st.plotly_chart(gauge, use_container_width=True)

# ══════════════════════ TAB 4: השוואה ════════════════════════════════════════
with tab_compare:
    st.markdown("**השווה בין מניות**")
    compare_input = st.text_input("הזן סמלים מופרדים בפסיק", value="AAPL,MSFT,NVDA", placeholder="AAPL,MSFT,TEVA.TA")

    if st.button("השווה"):
        tickers_to_compare = [t.strip().upper() for t in compare_input.split(",") if t.strip()]
        fig_cmp = go.Figure()
        for ct in tickers_to_compare[:5]:
            try:
                df_c = get_price_history(ct, period_label)
                close_c = df_c["Close"].squeeze()
                # נרמול ל-100
                normalized = (close_c / close_c.iloc[0]) * 100
                fig_cmp.add_trace(go.Scatter(
                    x=df_c.index, y=normalized, mode="lines", name=ct
                ))
            except Exception:
                st.warning(f"לא ניתן לטעון: {ct}")

        fig_cmp.update_layout(
            template="plotly_dark", paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
            height=450, margin=dict(l=0, r=0, t=30, b=0),
            yaxis_title="% שינוי (נרמול ל-100)",
            xaxis_title="תאריך",
        )
        fig_cmp.update_xaxes(showgrid=True, gridcolor="#21262d")
        fig_cmp.update_yaxes(showgrid=True, gridcolor="#21262d")
        st.plotly_chart(fig_cmp, use_container_width=True)

# ══════════════════════ TAB 5: מחשבון עסקה ═══════════════════════════════════
with tab_trade:
    st.markdown("### 🧮 מחשבון כדאיות עסקה")
    st.caption("בדוק R:R, גודל פוזיציה ו-Breakeven לפני כניסה לעסקה")

    col_in, col_out = st.columns([1, 1], gap="large")

    with col_in:
        st.markdown('<div class="section-header">קלטים</div>', unsafe_allow_html=True)

        # מחיר כניסה — auto-fill
        default_entry = quote.get("price", 0.0)
        trade_entry = st.number_input("מחיר כניסה", value=float(default_entry), step=0.5, format="%.2f")

        # חילוץ יעד / סטופ מטקסט חופשי (מה-News Agent)
        st.markdown("**חילוץ מחיר מטקסט News Agent** (אופציונלי)")
        target_text = st.text_input("טקסט ליעד", placeholder='למשל: "resistance at $270"', key="target_text")
        stop_text   = st.text_input("טקסט לסטופ",  placeholder='למשל: "support at $248"',    key="stop_text")

        parsed_target = parse_price_from_text(target_text) if target_text else None
        parsed_stop   = parse_price_from_text(stop_text)   if stop_text   else None

        # ATR לסטופ אוטומטי
        try:
            _atr_val = calc_atr(df)
            suggested_stop = auto_suggest_stop(trade_entry, _atr_val)
        except Exception:
            _atr_val = None
            suggested_stop = round(trade_entry * 0.97, 2)

        st.markdown("---")
        default_target = parsed_target if parsed_target else round(trade_entry * 1.06, 2)
        default_stop   = parsed_stop   if parsed_stop   else suggested_stop

        trade_target   = st.number_input("יעד (Target)", value=float(default_target), step=0.5, format="%.2f")
        trade_stop     = st.number_input("סטופ לוס",     value=float(default_stop),   step=0.5, format="%.2f")

        if _atr_val:
            st.caption(f"ATR(14) = {_atr_val:.2f} | סטופ מוצע: {suggested_stop:.2f} (1.5×ATR)")

        st.markdown("---")
        risk_mode = st.radio("מצב סיכון", ["סכום קבוע ($)", "אחוז מהתיק (%)"], horizontal=True)
        if risk_mode == "סכום קבוע ($)":
            trade_risk = st.number_input("סיכון בעסקה ($)", value=100.0, step=10.0)
            trade_portfolio = None
        else:
            trade_portfolio = st.number_input("גודל תיק ($)", value=10000.0, step=500.0)
            trade_risk_pct  = st.slider("% סיכון", 0.5, 3.0, 1.0, step=0.25)
            trade_risk = trade_portfolio * (trade_risk_pct / 100)
            st.caption(f"סיכון = {trade_risk:.2f}$")

        trade_commission = st.number_input("עמלה לצד ($)", value=5.0, step=1.0)
        trade_spread     = st.number_input("ספרד (%)",      value=0.1,  step=0.05, format="%.2f") / 100

        calc_btn = st.button("חשב עסקה ⚡", use_container_width=True, type="primary")

    # ─── תוצאה ────────────────────────────────────────────────────────────────
    with col_out:
        st.markdown('<div class="section-header">תוצאה</div>', unsafe_allow_html=True)

        if calc_btn:
            try:
                if trade_entry <= 0:
                    st.error("מחיר כניסה חייב להיות חיובי")
                elif trade_target <= trade_entry:
                    st.error("היעד חייב להיות מעל מחיר הכניסה")
                elif trade_stop >= trade_entry:
                    st.error("הסטופ לוס חייב להיות מתחת למחיר הכניסה")
                else:
                    result = evaluate_trade(
                        entry=trade_entry,
                        target=trade_target,
                        stop_loss=trade_stop,
                        risk_amount=trade_risk,
                        portfolio_value=trade_portfolio,
                        commission=trade_commission,
                        spread_pct=trade_spread,
                        atr=_atr_val,
                        ticker=ticker,
                    )

                    # Banner GO / NO-GO
                    is_go = result["rr"]["rr_ratio"] >= 2.0
                    banner_color = "#00C853" if is_go else "#D50000"
                    banner_bg    = "#00C85322" if is_go else "#D5000022"
                    verdict_emoji = "GO ✅" if is_go else "NO-GO ❌"
                    st.markdown(
                        f'<div class="signal-card" style="background:{banner_bg};border:2px solid {banner_color};">'
                        f'<div style="color:{banner_color};font-size:36px;">{verdict_emoji}</div>'
                        f'<div style="font-size:14px;color:#8b949e;margin-top:4px;">{result["verdict_reason"]}</div>'
                        f'</div>',
                        unsafe_allow_html=True
                    )

                    # R:R Gauge
                    rr_val = min(result["rr"]["rr_ratio"], 5.0)
                    gauge_rr = go.Figure(go.Indicator(
                        mode="gauge+number",
                        value=rr_val,
                        domain={"x": [0, 1], "y": [0, 1]},
                        number={"suffix": "x", "font": {"color": banner_color, "size": 28}},
                        title={"text": "R:R Ratio", "font": {"color": "#8b949e", "size": 13}},
                        gauge={
                            "axis": {"range": [0, 5], "tickcolor": "#8b949e"},
                            "bar": {"color": banner_color},
                            "bgcolor": "#1c2333",
                            "steps": [
                                {"range": [0, 1], "color": "#3a1010"},
                                {"range": [1, 2], "color": "#2a2100"},
                                {"range": [2, 5], "color": "#0a2a0a"},
                            ],
                            "threshold": {"line": {"color": "#ffffff", "width": 2}, "thickness": 0.75, "value": 2},
                        },
                    ))
                    gauge_rr.update_layout(
                        paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
                        height=220, margin=dict(l=10, r=10, t=40, b=10),
                        font={"color": "#e0e0e0"},
                    )
                    st.plotly_chart(gauge_rr, use_container_width=True)

                    # Markdown Table
                    st.markdown(result["markdown_table"])

            except ValueError as e:
                st.error(f"שגיאת חישוב: {e}")
            except Exception as e:
                st.error(f"שגיאה: {e}")
        else:
            st.info("מלא את הקלטים ולחץ **חשב עסקה** לקבלת ניתוח מלא")
            st.markdown("""
**מה המחשבון בודק:**
- **R:R** — יחס סיכוי:סיכון (GO אם ≥ 1:2)
- **גודל פוזיציה** — כמה מניות לפי הסיכון שהגדרת
- **Breakeven** — מחיר המינימום לרווח אחרי עמלות
- **ATR** — תנודתיות יומית ממוצעת (לקביעת סטופ)

**טיפ:** הדבק טקסט מהחדשות בשדות "חילוץ מטקסט" לחיסכון בזמן.
""")

# ─── Footer ───────────────────────────────────────────────────────────────────
st.markdown("---")
st.caption("לצרכים אישיים בלבד. אינו ייעוץ השקעות. | נתונים: Yahoo Finance, Marketaux, Finnhub, StockTwits")
