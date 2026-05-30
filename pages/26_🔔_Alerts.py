"""
Alerts Manager – Price & Technical Alerts with Telegram Integration
====================================================================
Create price alerts (above/below) · Technical alerts (RSI, MACD crossover, BB)
Alert log with timestamps · Telegram bot integration
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import yfinance as yf
import uuid
from datetime import datetime

st.set_page_config(page_title="Alerts", page_icon="🔔", layout="wide")

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.stApp { background:#0d0d1a; }
[data-testid="stSidebar"] { background:linear-gradient(160deg,#0d0d1a,#1a1a2e); }
[data-testid="stSidebar"] * { color:#c0caf5 !important; }
.block-container { padding-top:1.2rem !important; }
.rule-header {
  font-size:1rem; font-weight:700; color:#ffd200;
  border-left:3px solid #ffd200; padding-left:8px; margin:.8rem 0 .5rem;
}
.alert-card {
  background:#12122a; border:1px solid #ffffff10; border-radius:10px;
  padding:.8rem 1rem; margin-bottom:.4rem;
  display:flex; justify-content:space-between; align-items:center;
}
.alert-card.triggered { border-color:#ffd20050; background:#1a1a0d; }
.alert-card.active    { border-color:#00c85330; }
.alert-card.fired     { border-color:#a78bfa50; background:#0f0d1a; }
.badge {
  display:inline-block; padding:2px 10px; border-radius:12px;
  font-size:.72rem; font-weight:700;
}
.badge-active    { background:#00c85320; color:#00c853; }
.badge-triggered { background:#ffd20020; color:#ffd200; }
.badge-fired     { background:#a78bfa20; color:#a78bfa; }
[data-testid="stMetric"] { background:#12122a; border:1px solid #ffffff10; border-radius:10px; padding:.8rem; }
[data-testid="stMetricValue"] { color:#ffd200 !important; font-size:1.4rem !important; font-weight:700 !important; }
</style>
""", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────────────────
if "price_alerts" not in st.session_state:
    st.session_state["price_alerts"] = []
if "alert_log" not in st.session_state:
    st.session_state["alert_log"] = []

# ── NIFTY50 symbol map ────────────────────────────────────────────────────────
_SYMBOLS = {
    "NIFTY 50":"^NSEI","BANKNIFTY":"^NSEBANK",
    "RELIANCE":"RELIANCE.NS","TCS":"TCS.NS","HDFCBANK":"HDFCBANK.NS",
    "INFY":"INFY.NS","ICICIBANK":"ICICIBANK.NS","HINDUNILVR":"HINDUNILVR.NS",
    "SBIN":"SBIN.NS","AXISBANK":"AXISBANK.NS","BAJFINANCE":"BAJFINANCE.NS",
    "BHARTIARTL":"BHARTIARTL.NS","LT":"LT.NS","KOTAKBANK":"KOTAKBANK.NS",
    "ITC":"ITC.NS","MARUTI":"MARUTI.NS","WIPRO":"WIPRO.NS","HCLTECH":"HCLTECH.NS",
    "TITAN":"TITAN.NS","NESTLEIND":"NESTLEIND.NS","ULTRACEMCO":"ULTRACEMCO.NS",
    "ASIANPAINT":"ASIANPAINT.NS","NTPC":"NTPC.NS","ONGC":"ONGC.NS",
    "POWERGRID":"POWERGRID.NS","SUNPHARMA":"SUNPHARMA.NS",
}

@st.cache_data(ttl=60, show_spinner=False)
def _ltp(yf_symbol: str) -> float:
    try:
        t = yf.Ticker(yf_symbol)
        hist = t.history(period="1d", interval="1m")
        return float(hist["Close"].iloc[-1]) if not hist.empty else 0.0
    except:
        return 0.0

@st.cache_data(ttl=300, show_spinner=False)
def _hist(yf_symbol: str, period: str = "3mo") -> pd.DataFrame:
    try:
        return yf.download(yf_symbol, period=period, progress=False, auto_adjust=True)
    except:
        return pd.DataFrame()

def _calc_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain  = delta.clip(lower=0).rolling(period).mean()
    loss  = (-delta.clip(upper=0)).rolling(period).mean()
    rs    = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def _calc_macd_line(series: pd.Series) -> pd.Series:
    return series.ewm(span=12).mean() - series.ewm(span=26).mean()

def _calc_macd_signal(series: pd.Series) -> pd.Series:
    return _calc_macd_line(series).ewm(span=9).mean()

def _check_alert(alert: dict, ltp: float, df: pd.DataFrame) -> bool:
    """Return True if alert condition is met."""
    kind = alert["kind"]
    if kind == "price_above":
        return ltp >= alert["threshold"]
    if kind == "price_below":
        return ltp <= alert["threshold"]
    if df is None or df.empty:
        return False
    close = df["Close"].squeeze()
    if kind == "rsi_above":
        rsi = _calc_rsi(close).iloc[-1]
        return rsi >= alert["threshold"]
    if kind == "rsi_below":
        rsi = _calc_rsi(close).iloc[-1]
        return rsi <= alert["threshold"]
    if kind == "macd_bullish_cross":
        macd   = _calc_macd_line(close)
        signal = _calc_macd_signal(close)
        return macd.iloc[-1] > signal.iloc[-1] and macd.iloc[-2] <= signal.iloc[-2]
    if kind == "macd_bearish_cross":
        macd   = _calc_macd_line(close)
        signal = _calc_macd_signal(close)
        return macd.iloc[-1] < signal.iloc[-1] and macd.iloc[-2] >= signal.iloc[-2]
    if kind == "bb_breakout_above":
        sma = close.rolling(20).mean()
        std = close.rolling(20).std()
        return ltp > (sma.iloc[-1] + 2 * std.iloc[-1])
    if kind == "bb_breakdown_below":
        sma = close.rolling(20).mean()
        std = close.rolling(20).std()
        return ltp < (sma.iloc[-1] - 2 * std.iloc[-1])
    if kind == "ema_cross_above":
        ema_f = close.ewm(span=int(alert.get("fast",9))).mean()
        ema_s = close.ewm(span=int(alert.get("slow",21))).mean()
        return ema_f.iloc[-1] > ema_s.iloc[-1] and ema_f.iloc[-2] <= ema_s.iloc[-2]
    if kind == "ema_cross_below":
        ema_f = close.ewm(span=int(alert.get("fast",9))).mean()
        ema_s = close.ewm(span=int(alert.get("slow",21))).mean()
        return ema_f.iloc[-1] < ema_s.iloc[-1] and ema_f.iloc[-2] >= ema_s.iloc[-2]
    return False

def _fire_alert(alert: dict, ltp: float):
    """Mark alert as fired, log it, optionally send Telegram."""
    msg = (f"🔔 ALERT: {alert['symbol']} — {alert['label']}"
           f"\nCurrent: ₹{ltp:,.2f}  |  Threshold: {alert.get('threshold','')}"
           f"\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    st.session_state["alert_log"].insert(0, {
        "time":    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "symbol":  alert["symbol"],
        "label":   alert["label"],
        "ltp":     ltp,
        "threshold": alert.get("threshold",""),
        "message": msg,
    })
    # Telegram
    tg_token = st.session_state.get("telegram_token","")
    tg_chat  = st.session_state.get("telegram_chat_id","")
    if tg_token and tg_chat:
        try:
            import requests
            requests.post(
                f"https://api.telegram.org/bot{tg_token}/sendMessage",
                json={"chat_id": tg_chat, "text": msg, "parse_mode": "Markdown"},
                timeout=5)
        except:
            pass


# ─────────────────────────────────────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────────────────────────────────────
st.markdown(
    "<h2 style='color:#ffd200;margin:0;font-weight:800;'>🔔 Alerts Manager</h2>"
    "<div style='color:#8892a4;font-size:.85rem;'>Price · RSI · MACD · Bollinger Bands · "
    "EMA Cross · Telegram notifications</div>",
    unsafe_allow_html=True)
st.markdown("<hr style='border-color:#ffffff10;margin:.5rem 0 1rem;'>", unsafe_allow_html=True)

tab_create, tab_active, tab_log, tab_tg = st.tabs([
    "➕ Create Alert", "📋 Active Alerts", "📜 Alert History", "📱 Telegram"
])

# ═══════════════════════════════════════════════════════════════
# TAB 1 – Create Alert
# ═══════════════════════════════════════════════════════════════
with tab_create:
    st.markdown('<div class="rule-header">➕ New Alert</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2, gap="large")

    with c1:
        sym_name = st.selectbox("Symbol", list(_SYMBOLS.keys()), key="al_sym")
        yf_sym   = _SYMBOLS[sym_name]

        alert_type = st.selectbox("Alert Type", [
            "── Price Alerts ──",
            "Price Crosses Above",
            "Price Crosses Below",
            "── Technical Alerts ──",
            "RSI Overbought (above threshold)",
            "RSI Oversold (below threshold)",
            "MACD Bullish Crossover",
            "MACD Bearish Crossover",
            "Bollinger Breakout (above upper band)",
            "Bollinger Breakdown (below lower band)",
            "EMA Bullish Cross (fast > slow)",
            "EMA Bearish Cross (fast < slow)",
        ], key="al_type")

        _KIND_MAP = {
            "Price Crosses Above":                "price_above",
            "Price Crosses Below":                "price_below",
            "RSI Overbought (above threshold)":   "rsi_above",
            "RSI Oversold (below threshold)":     "rsi_below",
            "MACD Bullish Crossover":             "macd_bullish_cross",
            "MACD Bearish Crossover":             "macd_bearish_cross",
            "Bollinger Breakout (above upper band)": "bb_breakout_above",
            "Bollinger Breakdown (below lower band)":"bb_breakdown_below",
            "EMA Bullish Cross (fast > slow)":    "ema_cross_above",
            "EMA Bearish Cross (fast < slow)":    "ema_cross_below",
        }
        kind = _KIND_MAP.get(alert_type)

    with c2:
        threshold = None
        fast, slow = 9, 21

        if alert_type.startswith("──"):
            st.info("Please select an alert type.", icon="👈")
        elif "Price" in alert_type:
            ltp_val = _ltp(yf_sym)
            st.info(f"Current price: ₹{ltp_val:,.2f}", icon="💹")
            threshold = st.number_input("Price threshold (₹)", 0.0, step=1.0,
                                        value=ltp_val, key="al_price_thresh")
        elif "RSI" in alert_type:
            threshold = st.number_input("RSI threshold", 0.0, 100.0,
                                        value=70.0 if "Overbought" in alert_type else 30.0,
                                        step=1.0, key="al_rsi_thresh")
        elif "MACD" in alert_type or "Bollinger" in alert_type:
            st.info("No threshold needed — uses standard indicator settings.", icon="ℹ️")
            threshold = 0
        elif "EMA" in alert_type:
            fast = st.number_input("Fast EMA period", 5, 50, 9, step=1, key="al_ema_fast")
            slow = st.number_input("Slow EMA period", 10, 200, 21, step=1, key="al_ema_slow")
            threshold = 0

        note = st.text_input("Note (optional)", "", key="al_note",
                             placeholder="e.g. Buy setup, targets 2100")
        repeat = st.toggle("Repeat alert (re-arm after firing)", False, key="al_repeat")

        if kind and st.button("🔔 Create Alert", type="primary", key="al_create"):
            alert = {
                "id":        str(uuid.uuid4())[:8],
                "symbol":    sym_name,
                "yf_symbol": yf_sym,
                "kind":      kind,
                "label":     alert_type,
                "threshold": threshold,
                "fast":      fast,
                "slow":      slow,
                "note":      note,
                "repeat":    repeat,
                "created_at":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "status":    "active",
                "fired_at":  None,
            }
            st.session_state["price_alerts"].append(alert)
            st.success(f"Alert created for {sym_name}!", icon="✅")
            st.rerun()

    # Quick alert templates
    st.markdown('<div class="rule-header">⚡ Quick Templates</div>', unsafe_allow_html=True)
    qt_cols = st.columns(4)
    templates = [
        ("RSI Overbought NIFTY",   "NIFTY 50",    "rsi_above",           70,   "RSI Overbought (above threshold)"),
        ("RSI Oversold RELIANCE",  "RELIANCE",     "rsi_below",           30,   "RSI Oversold (below threshold)"),
        ("MACD Cross HDFCBANK",    "HDFCBANK",     "macd_bullish_cross",  0,    "MACD Bullish Crossover"),
        ("BB Breakout TCS",        "TCS",          "bb_breakout_above",   0,    "Bollinger Breakout (above upper band)"),
    ]
    for col, (label, sym, kind_, thr, type_label) in zip(qt_cols, templates):
        with col:
            if st.button(f"+ {label}", use_container_width=True, key=f"qt_{kind_}_{sym}"):
                alert = {
                    "id":         str(uuid.uuid4())[:8],
                    "symbol":     sym,
                    "yf_symbol":  _SYMBOLS[sym],
                    "kind":       kind_,
                    "label":      type_label,
                    "threshold":  thr,
                    "fast":       9, "slow": 21,
                    "note":       "Quick template",
                    "repeat":     False,
                    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "status":     "active",
                    "fired_at":   None,
                }
                st.session_state["price_alerts"].append(alert)
                st.success(f"Alert created: {label}", icon="✅")
                st.rerun()

# ═══════════════════════════════════════════════════════════════
# TAB 2 – Active Alerts
# ═══════════════════════════════════════════════════════════════
with tab_active:
    alerts = st.session_state["price_alerts"]
    active = [a for a in alerts if a["status"] == "active"]

    ac1, ac2, ac3 = st.columns([5,2,1])
    with ac1:
        st.markdown(f'<div class="rule-header">📋 Active Alerts ({len(active)})</div>',
                    unsafe_allow_html=True)
    with ac2:
        if st.button("🔍 Check All Now", use_container_width=True, key="al_check_all"):
            fired_count = 0
            for i, alert in enumerate(st.session_state["price_alerts"]):
                if alert["status"] != "active":
                    continue
                ltp_val = _ltp(alert["yf_symbol"])
                df_h    = _hist(alert["yf_symbol"], "3mo") if "rsi" in alert["kind"] or "macd" in alert["kind"] or "bb" in alert["kind"] or "ema" in alert["kind"] else None
                if _check_alert(alert, ltp_val, df_h):
                    _fire_alert(alert, ltp_val)
                    fired_count += 1
                    if not alert["repeat"]:
                        st.session_state["price_alerts"][i]["status"]   = "fired"
                        st.session_state["price_alerts"][i]["fired_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if fired_count:
                st.success(f"{fired_count} alert(s) fired!", icon="🔔")
            else:
                st.info("No alerts triggered.", icon="✅")
            st.rerun()
    with ac3:
        if st.button("🗑️ Clear", key="al_clear_all", use_container_width=True):
            st.session_state["price_alerts"] = []
            st.rerun()

    if not active:
        st.info("No active alerts. Create one in the ➕ Create Alert tab.", icon="🔔")
    else:
        for i, alert in enumerate(alerts):
            if alert["status"] != "active":
                continue
            idx = alerts.index(alert)
            c_l, c_r = st.columns([7,1])
            with c_l:
                thr_str = (f"threshold: {alert['threshold']:.2f}"
                           if alert.get("threshold") not in (None, 0, "") else "")
                st.markdown(
                    f'<div class="alert-card active">'
                    f'  <div>'
                    f'    <span class="badge badge-active">ACTIVE</span>'
                    f'    <b style="color:#e0e0e0;margin-left:8px;">{alert["symbol"]}</b>'
                    f'    <span style="color:#8892a4;font-size:.78rem;margin-left:6px;">'
                    f'    {alert["label"]} {thr_str}</span><br>'
                    f'    <span style="color:#5a6580;font-size:.7rem;">'
                    f'    Created {alert["created_at"]}  ·  {"🔁 Repeating" if alert["repeat"] else "Once"}'
                    f'    {" · "+alert["note"] if alert["note"] else ""}</span>'
                    f'  </div>'
                    f'</div>',
                    unsafe_allow_html=True)
            with c_r:
                if st.button("✕", key=f"del_al_{alert['id']}", help="Delete alert"):
                    st.session_state["price_alerts"].pop(idx)
                    st.rerun()

    # Fired alerts
    fired = [a for a in alerts if a["status"] == "fired"]
    if fired:
        st.markdown(f'<div class="rule-header">🔔 Fired Alerts ({len(fired)})</div>',
                    unsafe_allow_html=True)
        for alert in fired:
            st.markdown(
                f'<div class="alert-card fired">'
                f'  <span class="badge badge-fired">FIRED</span>'
                f'  <b style="color:#e0e0e0;margin-left:8px;">{alert["symbol"]}</b>'
                f'  <span style="color:#8892a4;font-size:.78rem;margin-left:6px;">{alert["label"]}</span>'
                f'  <span style="color:#5a6580;font-size:.7rem;margin-left:auto;">{alert["fired_at"]}</span>'
                f'</div>',
                unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
# TAB 3 – Alert History / Log
# ═══════════════════════════════════════════════════════════════
with tab_log:
    log = st.session_state["alert_log"]
    st.markdown(f'<div class="rule-header">📜 Alert History ({len(log)} events)</div>',
                unsafe_allow_html=True)

    lhc1, lhc2 = st.columns([5,1])
    with lhc2:
        if st.button("🗑️ Clear History", key="al_clear_log", use_container_width=True):
            st.session_state["alert_log"] = []
            st.rerun()

    if not log:
        st.info("No alerts have fired yet.", icon="📋")
    else:
        for ev in log[:50]:
            st.markdown(
                f'<div style="background:#12122a;border:1px solid #a78bfa20;border-radius:8px;'
                f'padding:.6rem 1rem;margin-bottom:.3rem;">'
                f'<div style="display:flex;justify-content:space-between;">'
                f'  <div>'
                f'    <span style="color:#ffd200;font-weight:700;">🔔 {ev["symbol"]}</span>'
                f'    <span style="color:#8892a4;font-size:.78rem;margin-left:8px;">{ev["label"]}</span>'
                f'  </div>'
                f'  <span style="color:#5a6580;font-size:.72rem;">{ev["time"]}</span>'
                f'</div>'
                f'<div style="color:#c0caf5;font-size:.8rem;margin-top:.2rem;">'
                f'LTP: ₹{ev["ltp"]:,.2f}'
                f'{" · Threshold: "+str(ev["threshold"]) if ev["threshold"] else ""}'
                f'</div></div>',
                unsafe_allow_html=True)

        if len(log) > 0:
            df_log = pd.DataFrame(log)[["time","symbol","label","ltp","threshold"]]
            with st.expander("📋 Download as CSV"):
                st.dataframe(df_log, hide_index=True, use_container_width=True)
                csv = df_log.to_csv(index=False)
                st.download_button("⬇️ Download CSV", csv, "alert_history.csv", "text/csv")

# ═══════════════════════════════════════════════════════════════
# TAB 4 – Telegram
# ═══════════════════════════════════════════════════════════════
with tab_tg:
    st.markdown('<div class="rule-header">📱 Telegram Notifications</div>', unsafe_allow_html=True)
    st.info("When configured, fired alerts are automatically sent to your Telegram chat.", icon="📱")

    tg_col1, tg_col2 = st.columns(2, gap="large")
    with tg_col1:
        tg_token = st.text_input(
            "Bot Token", value=st.session_state.get("telegram_token",""),
            type="password", key="tg_token_inp",
            help="Get from @BotFather on Telegram")
        if tg_token:
            st.session_state["telegram_token"] = tg_token

        tg_chat = st.text_input(
            "Chat ID", value=st.session_state.get("telegram_chat_id",""),
            key="tg_chat_inp",
            help="Your chat_id (use @userinfobot to find it)")
        if tg_chat:
            st.session_state["telegram_chat_id"] = tg_chat

        if st.button("🧪 Send Test Message", key="tg_test", type="primary"):
            if tg_token and tg_chat:
                try:
                    import requests
                    resp = requests.post(
                        f"https://api.telegram.org/bot{tg_token}/sendMessage",
                        json={"chat_id": tg_chat,
                              "text": "✅ Groww AutoTrader Pro — Telegram alerts configured!",
                              "parse_mode": "Markdown"},
                        timeout=10)
                    if resp.ok:
                        st.success("Test message sent!", icon="✅")
                    else:
                        st.error(f"Telegram error: {resp.text}", icon="❌")
                except Exception as e:
                    st.error(f"Error: {e}", icon="❌")
            else:
                st.error("Enter bot token and chat ID first.", icon="❌")

    with tg_col2:
        st.markdown("""
<div style="background:#12122a;border:1px solid #ffffff10;border-radius:12px;padding:1.2rem;">
<b style="color:#ffd200;">Setup Guide</b><br><br>
<b>Step 1:</b> Open Telegram → search <code>@BotFather</code><br>
Send <code>/newbot</code> → get your <b>Bot Token</b><br><br>
<b>Step 2:</b> Find your Chat ID:<br>
Open <code>@userinfobot</code> → it shows your ID<br><br>
<b>Step 3:</b> Start your bot by sending any message to it<br><br>
<b>Alert format sent:</b><br>
<code>🔔 ALERT: RELIANCE — Price Crosses Above<br>
Current: ₹2,450  |  Threshold: 2400<br>
2025-01-15 10:32:45</code>
</div>""", unsafe_allow_html=True)
