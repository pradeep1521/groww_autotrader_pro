"""
OI Analysis – PCR, Max Pain, OI Heatmap
=========================================
Options Open Interest analysis for NIFTY / BANKNIFTY / any F&O stock.
Data sourced from NSE public option-chain API.
Features: OI by strike, OI change, PCR, Max Pain, support/resistance zones.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import requests
import json
from datetime import datetime, timedelta

st.set_page_config(page_title="OI Analysis", page_icon="🌡️", layout="wide")

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
.metric-card {
  background:#12122a; border:1px solid #ffffff10; border-radius:12px;
  padding:1rem 1.2rem; text-align:center;
}
.metric-value { font-size:1.6rem; font-weight:800; }
.metric-label { font-size:.78rem; color:#8892a4; margin-top:.2rem; }
[data-testid="stMetric"] { background:#12122a; border:1px solid #ffffff10; border-radius:10px; padding:.8rem; }
[data-testid="stMetricValue"] { color:#ffd200 !important; font-size:1.4rem !important; font-weight:700 !important; }
.oi-card {
  background:#12122a; border:1px solid #ffffff10; border-radius:12px; padding:1.2rem;
}
.zone-bearish { color:#ff5252; font-weight:700; }
.zone-bullish { color:#00c853; font-weight:700; }
</style>
""", unsafe_allow_html=True)

# ── NSE API helpers ────────────────────────────────────────────────────────────
_NSE_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/120.0.0.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://www.nseindia.com/",
}

@st.cache_data(ttl=120, show_spinner=False)
def _fetch_nse_option_chain(symbol: str, is_index: bool = True) -> dict | None:
    """Fetch option chain JSON from NSE (cached 2 min)."""
    session = requests.Session()
    try:
        # Must visit main page first to get cookies
        session.get("https://www.nseindia.com", headers=_NSE_HEADERS, timeout=10)
        if is_index:
            url = f"https://www.nseindia.com/api/option-chain-indices?symbol={symbol}"
        else:
            url = f"https://www.nseindia.com/api/option-chain-equities?symbol={symbol}"
        resp = session.get(url, headers=_NSE_HEADERS, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return {"error": str(e)}

def _parse_option_chain(data: dict, expiry_filter: str | None = None) -> tuple[pd.DataFrame, float, list[str]]:
    """Parse raw NSE JSON into a DataFrame with OI by strike."""
    records = data.get("records", {})
    spot    = records.get("underlyingValue", 0.0)
    expiries = records.get("expiryDates", [])

    rows = []
    for item in records.get("data", []):
        exp = item.get("expiryDate", "")
        if expiry_filter and exp != expiry_filter:
            continue
        strike = item.get("strikePrice", 0)
        ce = item.get("CE", {})
        pe = item.get("PE", {})
        rows.append({
            "strike":      strike,
            "expiry":      exp,
            "ce_oi":       ce.get("openInterest", 0),
            "ce_oi_chg":   ce.get("changeinOpenInterest", 0),
            "ce_vol":      ce.get("totalTradedVolume", 0),
            "ce_iv":       ce.get("impliedVolatility", 0),
            "ce_ltp":      ce.get("lastPrice", 0),
            "pe_oi":       pe.get("openInterest", 0),
            "pe_oi_chg":   pe.get("changeinOpenInterest", 0),
            "pe_vol":      pe.get("totalTradedVolume", 0),
            "pe_iv":       pe.get("impliedVolatility", 0),
            "pe_ltp":      pe.get("lastPrice", 0),
        })
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values("strike").reset_index(drop=True)
    return df, spot, expiries

def _calc_pcr(df: pd.DataFrame) -> float:
    total_ce = df["ce_oi"].sum()
    total_pe = df["pe_oi"].sum()
    return round(total_pe / total_ce, 3) if total_ce > 0 else 0.0

def _calc_max_pain(df: pd.DataFrame) -> float:
    """Max Pain = strike with minimum total loss for options sellers."""
    strikes = df["strike"].values
    ce_oi   = df["ce_oi"].values
    pe_oi   = df["pe_oi"].values
    losses  = []
    for s in strikes:
        call_loss = sum(max(s - k, 0) * oi for k, oi in zip(strikes, ce_oi))
        put_loss  = sum(max(k - s, 0) * oi for k, oi in zip(strikes, pe_oi))
        losses.append(call_loss + put_loss)
    return float(strikes[int(np.argmin(losses))]) if losses else 0.0

def _build_demo_data(symbol: str) -> tuple[pd.DataFrame, float, list[str]]:
    """Demo data when NSE is unavailable."""
    if symbol == "NIFTY":
        spot   = 22350.0
        center = 22350
    elif symbol == "BANKNIFTY":
        spot   = 47200.0
        center = 47200
    else:
        spot   = 1000.0
        center = 1000

    step    = 50 if symbol == "NIFTY" else 100
    strikes = list(range(center - 15*step, center + 16*step, step))
    rng     = np.random.default_rng(42)
    rows    = []
    for k in strikes:
        dist  = abs(k - center)
        mult  = max(1, 20 - dist//step)
        rows.append({
            "strike":    k,
            "expiry":    "25-Jan-2025",
            "ce_oi":     int(rng.integers(50, 500) * mult),
            "ce_oi_chg": int(rng.integers(-100, 200)),
            "ce_vol":    int(rng.integers(100, 3000)),
            "ce_iv":     round(float(rng.uniform(12, 25)), 2),
            "ce_ltp":    round(max(0, (center - k) + float(rng.uniform(-20, 50))), 2),
            "pe_oi":     int(rng.integers(50, 500) * (21 - mult)),
            "pe_oi_chg": int(rng.integers(-100, 200)),
            "pe_vol":    int(rng.integers(100, 3000)),
            "pe_iv":     round(float(rng.uniform(12, 25)), 2),
            "pe_ltp":    round(max(0, (k - center) + float(rng.uniform(-20, 50))), 2),
        })
    return pd.DataFrame(rows), spot, ["25-Jan-2025", "30-Jan-2025", "27-Feb-2025"]


# ─────────────────────────────────────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────────────────────────────────────
st.markdown(
    "<h2 style='color:#ffd200;margin:0;font-weight:800;'>🌡️ OI Analysis</h2>"
    "<div style='color:#8892a4;font-size:.85rem;'>PCR · Max Pain · OI Heatmap · "
    "Support & Resistance from Open Interest</div>",
    unsafe_allow_html=True)
st.markdown("<hr style='border-color:#ffffff10;margin:.5rem 0 1rem;'>", unsafe_allow_html=True)

# ── Controls ──────────────────────────────────────────────────────────────────
ctrl_col1, ctrl_col2, ctrl_col3, ctrl_col4 = st.columns([2, 2, 2, 1])
with ctrl_col1:
    oi_symbol = st.selectbox("Symbol", [
        "NIFTY","BANKNIFTY","FINNIFTY","MIDCPNIFTY",
        "RELIANCE","TCS","HDFCBANK","INFY","ICICIBANK",
        "SBIN","AXISBANK","BHARTIARTL","LT","WIPRO",
    ], key="oi_sym")
with ctrl_col2:
    use_live = st.toggle("Live NSE data", True, key="oi_live",
                         help="Fetch live data from NSE. Off = demo data.")
with ctrl_col3:
    strikes_n = st.slider("Strikes to show (±ATM)", 5, 20, 10, key="oi_strikes")
with ctrl_col4:
    if st.button("🔄 Refresh", use_container_width=True, key="oi_refresh"):
        st.cache_data.clear()
        st.rerun()

# ── Load data ─────────────────────────────────────────────────────────────────
is_index = oi_symbol in ("NIFTY","BANKNIFTY","FINNIFTY","MIDCPNIFTY")

if use_live:
    with st.spinner(f"Fetching {oi_symbol} option chain from NSE …"):
        raw = _fetch_nse_option_chain(oi_symbol, is_index)
else:
    raw = None

use_demo = False
if raw is None or "error" in (raw or {}):
    use_demo = True
    if use_live and raw:
        st.warning(
            f"NSE API unavailable: {raw.get('error','Unknown error')} — "
            "showing demo data. NSE often requires a browser session cookie.",
            icon="⚠️")
    full_df, spot, expiries = _build_demo_data(oi_symbol)
else:
    _, spot, expiries = _parse_option_chain(raw)
    full_df = pd.DataFrame()   # filled after expiry selection

# Expiry selector
with ctrl_col2:
    if not use_demo and expiries:
        expiry = st.selectbox("Expiry", expiries[:6], key="oi_expiry")
    else:
        expiry = "25-Jan-2025"

if use_demo:
    df = full_df.copy()
else:
    df, spot, _ = _parse_option_chain(raw, expiry)

if df.empty:
    st.error("No data available for the selected symbol/expiry.")
    st.stop()

# Filter to ±N strikes around ATM
atm_idx  = (df["strike"] - spot).abs().idxmin()
atm      = df.loc[atm_idx, "strike"]
lo_idx   = max(0, atm_idx - strikes_n)
hi_idx   = min(len(df)-1, atm_idx + strikes_n)
df_view  = df.iloc[lo_idx:hi_idx+1].reset_index(drop=True)

# ── Key Metrics ───────────────────────────────────────────────────────────────
pcr       = _calc_pcr(df_view)
max_pain  = _calc_max_pain(df_view)
total_ce  = df_view["ce_oi"].sum()
total_pe  = df_view["pe_oi"].sum()
resistance_strike = df_view.loc[df_view["ce_oi"].idxmax(), "strike"]
support_strike    = df_view.loc[df_view["pe_oi"].idxmax(), "strike"]

pcr_color = "#00c853" if pcr > 1.2 else ("#ff5252" if pcr < 0.8 else "#ffd200")
pcr_label = "Bullish" if pcr > 1.2 else ("Bearish" if pcr < 0.8 else "Neutral")

st.markdown("### 📊 Key Metrics")
m1,m2,m3,m4,m5,m6 = st.columns(6)
with m1:
    st.markdown(f'<div class="metric-card"><div class="metric-value" style="color:#ffd200;">₹{spot:,.1f}</div><div class="metric-label">Spot Price</div></div>', unsafe_allow_html=True)
with m2:
    st.markdown(f'<div class="metric-card"><div class="metric-value" style="color:{pcr_color};">{pcr}</div><div class="metric-label">PCR · {pcr_label}</div></div>', unsafe_allow_html=True)
with m3:
    st.markdown(f'<div class="metric-card"><div class="metric-value" style="color:#a78bfa;">₹{max_pain:,.0f}</div><div class="metric-label">Max Pain</div></div>', unsafe_allow_html=True)
with m4:
    st.markdown(f'<div class="metric-card"><div class="metric-value" style="color:#ff5252;">₹{resistance_strike:,.0f}</div><div class="metric-label">Resistance (Max CE OI)</div></div>', unsafe_allow_html=True)
with m5:
    st.markdown(f'<div class="metric-card"><div class="metric-value" style="color:#00c853;">₹{support_strike:,.0f}</div><div class="metric-label">Support (Max PE OI)</div></div>', unsafe_allow_html=True)
with m6:
    dist = round((max_pain - spot) / spot * 100, 2)
    dist_color = "#00c853" if dist > 0 else "#ff5252"
    st.markdown(f'<div class="metric-card"><div class="metric-value" style="color:{dist_color};">{dist:+.2f}%</div><div class="metric-label">Spot → Max Pain</div></div>', unsafe_allow_html=True)

st.markdown("---")

# ── Chart tabs ────────────────────────────────────────────────────────────────
tab_oi, tab_oichg, tab_pcr, tab_iv, tab_tbl = st.tabs([
    "📊 OI by Strike", "🔄 OI Change", "📈 PCR Trend", "🌊 IV Skew", "📋 Full Table"
])

# ── OI Bar Chart ──────────────────────────────────────────────────────────────
with tab_oi:
    fig = go.Figure()
    colors_ce = ["#ff5252cc" if k >= spot else "#ff525255" for k in df_view["strike"]]
    colors_pe = ["#00c85355" if k >= spot else "#00c853cc" for k in df_view["strike"]]

    fig.add_trace(go.Bar(
        name="CE (Call) OI", x=df_view["strike"],
        y=df_view["ce_oi"] / 1e5,
        marker_color=colors_ce, text=None, yaxis="y"))
    fig.add_trace(go.Bar(
        name="PE (Put) OI", x=df_view["strike"],
        y=df_view["pe_oi"] / 1e5,
        marker_color=colors_pe, yaxis="y2"))

    fig.add_vline(x=float(spot), line_color="#ffd200", line_dash="dash",
                  annotation_text=f"Spot {spot:,.0f}", annotation_position="top right",
                  annotation_font_color="#ffd200")
    fig.add_vline(x=float(max_pain), line_color="#a78bfa", line_dash="dot",
                  annotation_text=f"MaxPain {max_pain:,.0f}",
                  annotation_position="top left", annotation_font_color="#a78bfa")

    fig.update_layout(
        title=f"{oi_symbol} – Open Interest by Strike ({expiry})",
        barmode="overlay", plot_bgcolor="#0d0d1a", paper_bgcolor="#12122a",
        font_color="#c0caf5", height=480,
        yaxis=dict(title="CE OI (Lakh)", gridcolor="#ffffff10", side="left"),
        yaxis2=dict(title="PE OI (Lakh)", overlaying="y", side="right", gridcolor="#ffffff05"),
        xaxis=dict(tickangle=-45, gridcolor="#ffffff10"),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
        margin=dict(t=50, b=40, l=60, r=60))
    st.plotly_chart(fig, use_container_width=True)

    st.caption("🔴 Red bars = Call OI (resistance zones)  ·  🟢 Green bars = Put OI (support zones)")

# ── OI Change ─────────────────────────────────────────────────────────────────
with tab_oichg:
    fig2 = make_subplots(rows=1, cols=2, subplot_titles=("CE OI Change", "PE OI Change"),
                         shared_yaxes=True)

    ce_colors = ["#ff5252" if v >= 0 else "#00c853" for v in df_view["ce_oi_chg"]]
    pe_colors = ["#00c853" if v >= 0 else "#ff5252" for v in df_view["pe_oi_chg"]]

    fig2.add_trace(go.Bar(x=df_view["ce_oi_chg"]/1e3, y=df_view["strike"],
                          orientation="h", name="CE Chg", marker_color=ce_colors), row=1, col=1)
    fig2.add_trace(go.Bar(x=df_view["pe_oi_chg"]/1e3, y=df_view["strike"],
                          orientation="h", name="PE Chg", marker_color=pe_colors), row=1, col=2)

    for row in [1, 2]:
        fig2.add_hline(y=float(spot), line_color="#ffd200", line_dash="dash", row=1, col=row)
        fig2.add_hline(y=float(max_pain), line_color="#a78bfa", line_dash="dot", row=1, col=row)

    fig2.update_layout(
        plot_bgcolor="#0d0d1a", paper_bgcolor="#12122a",
        font_color="#c0caf5", height=500,
        xaxis=dict(title="Change ('000)", gridcolor="#ffffff10"),
        xaxis2=dict(title="Change ('000)", gridcolor="#ffffff10"),
        yaxis=dict(gridcolor="#ffffff10"),
        showlegend=False,
        margin=dict(t=50, b=40, l=60, r=30))
    st.plotly_chart(fig2, use_container_width=True)
    st.caption("Positive = fresh OI buildup  ·  Negative = unwinding")

# ── PCR Trend (simulated time-series) ─────────────────────────────────────────
with tab_pcr:
    st.info("PCR trend requires intraday snapshots. Showing synthetic intraday PCR.", icon="ℹ️")

    rng  = np.random.default_rng(99)
    times = pd.date_range(datetime.today().replace(hour=9, minute=15), periods=75, freq="5min")
    pcr_series = np.clip(pcr + rng.normal(0, 0.05, 75).cumsum() * 0.02, 0.4, 2.5)
    fig3 = go.Figure()
    fig3.add_trace(go.Scatter(x=times, y=pcr_series, mode="lines",
                              line=dict(color="#ffd200", width=2), name="PCR"))
    fig3.add_hline(y=1.2, line_color="#00c853", line_dash="dash",
                   annotation_text="Bullish (>1.2)", annotation_font_color="#00c853")
    fig3.add_hline(y=0.8, line_color="#ff5252", line_dash="dash",
                   annotation_text="Bearish (<0.8)", annotation_font_color="#ff5252")
    fig3.add_hline(y=1.0, line_color="#ffffff30", line_dash="dot")
    fig3.update_layout(
        title="Put-Call Ratio (Intraday)", plot_bgcolor="#0d0d1a", paper_bgcolor="#12122a",
        font_color="#c0caf5", height=380,
        yaxis=dict(title="PCR", gridcolor="#ffffff10"),
        xaxis=dict(gridcolor="#ffffff10"),
        margin=dict(t=50, b=40, l=60, r=30))
    st.plotly_chart(fig3, use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("""
**PCR Interpretation:**
| PCR | Sentiment |
|-----|-----------|
| > 1.5 | Extremely Bullish (extreme fear) |
| 1.2–1.5 | Bullish |
| 0.8–1.2 | Neutral |
| 0.5–0.8 | Bearish |
| < 0.5 | Extremely Bearish |
""")
    with c2:
        current_pcr = pcr_series[-1]
        if current_pcr > 1.2:
            sentiment, color = "🟢 Bullish", "#00c853"
        elif current_pcr < 0.8:
            sentiment, color = "🔴 Bearish", "#ff5252"
        else:
            sentiment, color = "🟡 Neutral", "#ffd200"
        st.markdown(
            f'<div class="oi-card" style="margin-top:1rem;">'
            f'<div style="color:#8892a4;font-size:.8rem;">Current PCR</div>'
            f'<div style="font-size:2.2rem;font-weight:800;color:{color};">{current_pcr:.3f}</div>'
            f'<div style="font-size:1rem;color:{color};">{sentiment}</div></div>',
            unsafe_allow_html=True)

# ── IV Skew ────────────────────────────────────────────────────────────────────
with tab_iv:
    fig4 = go.Figure()
    fig4.add_trace(go.Scatter(x=df_view["strike"], y=df_view["ce_iv"],
                              mode="lines+markers", name="CE IV",
                              line=dict(color="#ff5252", width=2),
                              marker=dict(size=5)))
    fig4.add_trace(go.Scatter(x=df_view["strike"], y=df_view["pe_iv"],
                              mode="lines+markers", name="PE IV",
                              line=dict(color="#00c853", width=2),
                              marker=dict(size=5)))
    fig4.add_vline(x=float(spot), line_color="#ffd200", line_dash="dash",
                   annotation_text=f"Spot", annotation_font_color="#ffd200")
    fig4.update_layout(
        title="IV Skew (Implied Volatility by Strike)",
        plot_bgcolor="#0d0d1a", paper_bgcolor="#12122a",
        font_color="#c0caf5", height=400,
        yaxis=dict(title="IV %", gridcolor="#ffffff10"),
        xaxis=dict(title="Strike", gridcolor="#ffffff10"),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
        margin=dict(t=50, b=40, l=60, r=30))
    st.plotly_chart(fig4, use_container_width=True)
    st.caption("Steep IV skew to the left = Put premium expensive = bearish hedging activity")

# ── Full Table ─────────────────────────────────────────────────────────────────
with tab_tbl:
    st.markdown('<div class="rule-header">Full Option Chain</div>', unsafe_allow_html=True)
    table_df = df_view[[
        "ce_oi","ce_oi_chg","ce_vol","ce_iv","ce_ltp",
        "strike",
        "pe_ltp","pe_iv","pe_vol","pe_oi_chg","pe_oi"
    ]].rename(columns={
        "ce_oi":"CE OI","ce_oi_chg":"CE Chg","ce_vol":"CE Vol","ce_iv":"CE IV","ce_ltp":"CE LTP",
        "strike":"Strike",
        "pe_ltp":"PE LTP","pe_iv":"PE IV","pe_vol":"PE Vol","pe_oi_chg":"PE Chg","pe_oi":"PE OI"
    })

    def _hl_strike(row):
        styles = [""] * len(row)
        strike_idx = list(row.index).index("Strike")
        if abs(row["Strike"] - spot) <= 50:
            styles[strike_idx] = "background-color:#ffd20020;font-weight:700;color:#ffd200"
        return styles

    styled = (table_df.style
              .apply(_hl_strike, axis=1)
              .format({
                  "CE OI": "{:,.0f}", "CE Chg": "{:+,.0f}", "CE Vol": "{:,.0f}",
                  "CE IV": "{:.1f}%", "CE LTP": "₹{:.2f}",
                  "Strike": "₹{:,.0f}",
                  "PE LTP": "₹{:.2f}", "PE IV": "{:.1f}%", "PE Vol": "{:,.0f}",
                  "PE Chg": "{:+,.0f}", "PE OI": "{:,.0f}"
              })
              .background_gradient(subset=["CE OI"], cmap="Reds")
              .background_gradient(subset=["PE OI"], cmap="Greens"))

    st.dataframe(styled, use_container_width=True, hide_index=True, height=500)

    if use_demo:
        st.caption("⚠️ Showing demo / synthetic data. Enable 'Live NSE data' for real figures.")

# ── Footer legend ─────────────────────────────────────────────────────────────
st.markdown("---")
fc1, fc2, fc3 = st.columns(3)
with fc1:
    st.markdown(f'<div class="oi-card"><b style="color:#ff5252;">Resistance:</b> ₹{resistance_strike:,.0f} (highest CE OI buildup)</div>', unsafe_allow_html=True)
with fc2:
    st.markdown(f'<div class="oi-card"><b style="color:#a78bfa;">Max Pain:</b> ₹{max_pain:,.0f} (strike where sellers lose least)</div>', unsafe_allow_html=True)
with fc3:
    st.markdown(f'<div class="oi-card"><b style="color:#00c853;">Support:</b> ₹{support_strike:,.0f} (highest PE OI buildup)</div>', unsafe_allow_html=True)
