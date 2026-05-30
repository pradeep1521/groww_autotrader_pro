"""
No-Code Strategy Builder
=========================
Visual condition-block builder — like AlgoTest/Streak Strategy Builder.
Build entry/exit rules without writing a single line of code.
"""

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
import json
from datetime import datetime, timedelta
from indicators import (
    calculate_rsi, calculate_macd, calculate_bollinger_bands,
    calculate_sma, calculate_ema, calculate_atr, calculate_adx
)

st.set_page_config(page_title="Strategy Builder", page_icon="🏗️", layout="wide")

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.stApp { background:#0d0d1a; }
[data-testid="stSidebar"] { background:linear-gradient(160deg,#0d0d1a,#1a1a2e); }
[data-testid="stSidebar"] * { color:#c0caf5 !important; }
.block-container { padding-top:1.2rem !important; }
.cond-card {
  background:#12122a; border:1px solid #ffd20025;
  border-radius:10px; padding:.8rem 1rem; margin-bottom:.5rem;
}
.cond-and { color:#ffd200; font-weight:700; font-size:.75rem;
  text-align:center; margin:.2rem 0; }
.rule-header {
  font-size:1rem; font-weight:700; color:#ffd200;
  border-left:3px solid #ffd200; padding-left:8px; margin:.8rem 0 .4rem;
}
.strat-card {
  background:linear-gradient(135deg,#12122a,#1a1a35);
  border:1px solid #ffd20030; border-radius:12px; padding:1.2rem;
}
[data-testid="stMetric"] { background:#12122a; border:1px solid #ffffff10; border-radius:10px; padding:.8rem; }
[data-testid="stMetricValue"] { color:#ffd200 !important; font-size:1.4rem !important; font-weight:700 !important; }
</style>
""", unsafe_allow_html=True)

# ── Constants ─────────────────────────────────────────────────────────────────
INDICATORS = ["RSI", "MACD Line", "MACD Signal", "MACD Histogram",
              "Bollinger Upper", "Bollinger Middle", "Bollinger Lower",
              "SMA", "EMA", "ATR", "ADX", "Price (Close)", "Price (Open)",
              "Price (High)", "Price (Low)", "Volume"]
CONDITIONS  = ["crosses above", "crosses below", "is above", "is below",
               "is equal to", "increases by %", "decreases by %"]
POPULAR_SYM = ["RELIANCE.NS","TCS.NS","INFY.NS","HDFCBANK.NS","ICICIBANK.NS",
               "SBIN.NS","WIPRO.NS","AXISBANK.NS","BAJFINANCE.NS","^NSEI"]

# ── Session state ─────────────────────────────────────────────────────────────
if "sb_entry_conditions" not in st.session_state:
    st.session_state["sb_entry_conditions"] = []
if "sb_exit_conditions" not in st.session_state:
    st.session_state["sb_exit_conditions"] = []
if "sb_strategies" not in st.session_state:
    st.session_state["sb_strategies"] = []

# ── Helpers ───────────────────────────────────────────────────────────────────
def _add_cond(key):
    st.session_state[key].append({
        "indicator": "RSI", "period": 14, "condition": "is below",
        "ref_type": "Value", "ref_value": 30.0, "ref_indicator": "RSI",
        "ref_period": 14, "logic": "AND"
    })

def _del_cond(key, idx):
    st.session_state[key].pop(idx)

def _get_indicator_series(df, ind, period):
    c = df["Close"]
    if ind == "RSI":             return calculate_rsi(c, period)
    if ind == "MACD Line":       return calculate_macd(c)[0]
    if ind == "MACD Signal":     return calculate_macd(c)[1]
    if ind == "MACD Histogram":  return calculate_macd(c)[2]
    if ind == "Bollinger Upper": return calculate_bollinger_bands(c, period)[0]
    if ind == "Bollinger Middle": return calculate_bollinger_bands(c, period)[1]
    if ind == "Bollinger Lower": return calculate_bollinger_bands(c, period)[2]
    if ind == "SMA":             return calculate_sma(c, period)
    if ind == "EMA":             return calculate_ema(c, period)
    if ind == "ATR":             return calculate_atr(df["High"], df["Low"], c, period)
    if ind == "ADX":             return calculate_adx(df["High"], df["Low"], c, period)
    if ind == "Price (Close)":   return c
    if ind == "Price (Open)":    return df["Open"]
    if ind == "Price (High)":    return df["High"]
    if ind == "Price (Low)":     return df["Low"]
    if ind == "Volume":          return df["Volume"].astype(float)
    return c

def _eval_condition(series_a, cond, val_series):
    """Return boolean Series for a single condition."""
    if cond == "crosses above":
        return (series_a > val_series) & (series_a.shift(1) <= val_series.shift(1))
    if cond == "crosses below":
        return (series_a < val_series) & (series_a.shift(1) >= val_series.shift(1))
    if cond == "is above":
        return series_a > val_series
    if cond == "is below":
        return series_a < val_series
    if cond == "is equal to":
        return abs(series_a - val_series) < 0.01
    if cond == "increases by %":
        return (series_a - series_a.shift(1)) / series_a.shift(1).abs() * 100 >= val_series
    if cond == "decreases by %":
        return (series_a.shift(1) - series_a) / series_a.shift(1).abs() * 100 >= val_series
    return pd.Series(False, index=series_a.index)

def _apply_conditions(df, conditions):
    """Return combined boolean Series from all conditions."""
    if not conditions:
        return pd.Series(False, index=df.index)
    combined = None
    for c in conditions:
        s_a = _get_indicator_series(df, c["indicator"], int(c.get("period", 14)))
        if c["ref_type"] == "Value":
            s_b = pd.Series(c["ref_value"], index=df.index)
        else:
            s_b = _get_indicator_series(df, c["ref_indicator"], int(c.get("ref_period", 14)))
        sig = _eval_condition(s_a, c["condition"], s_b)
        if combined is None:
            combined = sig
        elif c["logic"] == "AND":
            combined = combined & sig
        else:
            combined = combined | sig
    return combined.fillna(False)

def _run_backtest(df, entry_sig, exit_sig, sl_pct, target_pct, side="BUY"):
    """Simple signal-based backtest. Returns trades list + equity curve."""
    trades = []
    equity = [100000.0]
    cash   = 100000.0
    in_pos = False
    entry_price = 0.0
    qty = 0
    for i in range(1, len(df)):
        price = float(df["Close"].iloc[i])
        if not in_pos and entry_sig.iloc[i]:
            qty = int(cash * 0.95 / price)
            if qty < 1:
                equity.append(cash)
                continue
            entry_price = price
            cash -= qty * price
            in_pos = True
            trades.append({"entry_date": df.index[i], "entry": entry_price,
                           "exit_date": None, "exit": None, "pnl": None, "result": None})
        elif in_pos:
            pnl_pct = (price - entry_price) / entry_price * 100 * (1 if side == "BUY" else -1)
            hit_exit = exit_sig.iloc[i]
            hit_sl     = pnl_pct <= -sl_pct
            hit_target = pnl_pct >= target_pct
            if hit_exit or hit_sl or hit_target:
                pnl_val = (price - entry_price) * qty * (1 if side == "BUY" else -1)
                cash += qty * price
                trades[-1].update({
                    "exit_date": df.index[i], "exit": price,
                    "pnl": pnl_val,
                    "result": "WIN" if pnl_val > 0 else "LOSS",
                    "reason": "Target" if hit_target else ("SL" if hit_sl else "Signal")
                })
                in_pos = False
        equity.append(cash + (qty * price if in_pos else 0))
    # Close open trade at end
    if in_pos and trades:
        price = float(df["Close"].iloc[-1])
        pnl_val = (price - entry_price) * qty
        cash += qty * price
        trades[-1].update({"exit_date": df.index[-1], "exit": price,
                           "pnl": pnl_val, "result": "WIN" if pnl_val > 0 else "LOSS",
                           "reason": "End of period"})
    return trades, equity

# ─────────────────────────────────────────────────────────────────────────────
# Page
# ─────────────────────────────────────────────────────────────────────────────
st.markdown(
    "<h2 style='color:#ffd200;margin:0;font-weight:800;'>🏗️ Strategy Builder</h2>"
    "<div style='color:#8892a4;font-size:.85rem;'>Build, backtest & deploy strategies "
    "without writing code  ·  Like AlgoTest Strategy Builder</div>",
    unsafe_allow_html=True)
st.markdown("<hr style='border-color:#ffffff10;margin:.5rem 0 1rem;'>", unsafe_allow_html=True)

left, right = st.columns([2, 3], gap="large")

# ═══════════════════════════════════════════════════════════════
# LEFT: Builder panel
# ═══════════════════════════════════════════════════════════════
with left:
    st.markdown('<div class="rule-header">📋 Strategy Settings</div>', unsafe_allow_html=True)
    strategy_name = st.text_input("Strategy Name", "My Strategy #1", key="sb_name")

    sc1, sc2 = st.columns(2)
    with sc1:
        sym_mode = st.radio("Symbol", ["Popular", "Custom"], horizontal=True, key="sb_sym_mode")
        if sym_mode == "Popular":
            symbol = st.selectbox("", POPULAR_SYM, key="sb_sym_pop", label_visibility="collapsed")
        else:
            symbol = st.text_input("Custom (Yahoo format)", "RELIANCE.NS", key="sb_sym_cust",
                                   label_visibility="collapsed")
    with sc2:
        period_map = {"1 Month": "1mo", "3 Months": "3mo", "6 Months": "6mo", "1 Year": "1y", "2 Years": "2y"}
        period_lbl = st.selectbox("Backtest Period", list(period_map.keys()), index=2, key="sb_period")
        interval   = st.selectbox("Candle Size", ["1d","1h","30m","15m"], key="sb_interval")
        side       = st.radio("Direction", ["BUY","SELL"], horizontal=True, key="sb_side")

    sl_pct, tgt_pct = st.columns(2)
    with sl_pct:
        sl  = st.number_input("Stop Loss %", 0.5, 20.0, 3.0, 0.5, key="sb_sl")
    with tgt_pct:
        tgt = st.number_input("Target %",    0.5, 50.0, 6.0, 0.5, key="sb_tgt")

    # ── Entry Conditions ─────────────────────────────────────────
    st.markdown('<div class="rule-header">🟢 Entry Conditions</div>', unsafe_allow_html=True)

    for i, c in enumerate(st.session_state["sb_entry_conditions"]):
        with st.container():
            if i > 0:
                c["logic"] = st.radio(f"", ["AND","OR"], horizontal=True,
                                       key=f"en_logic_{i}", index=0 if c["logic"]=="AND" else 1,
                                       label_visibility="collapsed")
            e1, e2, e3, e4 = st.columns([3, 1, 2, 2])
            with e1:
                c["indicator"] = st.selectbox("Indicator", INDICATORS,
                    index=INDICATORS.index(c["indicator"]), key=f"en_ind_{i}",
                    label_visibility="collapsed")
            with e2:
                c["period"] = st.number_input("Period", 1, 200,
                    int(c.get("period",14)), key=f"en_per_{i}", label_visibility="collapsed")
            with e3:
                c["condition"] = st.selectbox("Condition", CONDITIONS,
                    index=CONDITIONS.index(c["condition"]), key=f"en_cond_{i}",
                    label_visibility="collapsed")
            with e4:
                ref_type = st.radio("", ["Value","Indicator"], horizontal=True,
                                    key=f"en_rt_{i}", label_visibility="collapsed",
                                    index=0 if c["ref_type"]=="Value" else 1)
                c["ref_type"] = ref_type
            if ref_type == "Value":
                c["ref_value"] = st.number_input("Value", value=float(c.get("ref_value",30.0)),
                    key=f"en_rv_{i}", label_visibility="collapsed")
            else:
                ri1, ri2 = st.columns(2)
                with ri1:
                    c["ref_indicator"] = st.selectbox("Ref Indicator", INDICATORS,
                        index=INDICATORS.index(c.get("ref_indicator","SMA")),
                        key=f"en_ri_{i}", label_visibility="collapsed")
                with ri2:
                    c["ref_period"] = st.number_input("Ref Period", 1, 200,
                        int(c.get("ref_period",50)), key=f"en_rp_{i}", label_visibility="collapsed")
            if st.button("✖ Remove", key=f"en_del_{i}", type="secondary"):
                _del_cond("sb_entry_conditions", i)
                st.rerun()
            st.markdown("<hr style='border-color:#ffffff08;margin:.2rem 0;'>", unsafe_allow_html=True)

    if st.button("➕ Add Entry Condition", use_container_width=True, key="en_add"):
        _add_cond("sb_entry_conditions")
        st.rerun()

    # ── Exit Conditions ──────────────────────────────────────────
    st.markdown('<div class="rule-header">🔴 Exit Conditions  <span style="color:#8892a4;font-size:.75rem;">(optional · SL/Target always active)</span></div>',
                unsafe_allow_html=True)

    for i, c in enumerate(st.session_state["sb_exit_conditions"]):
        with st.container():
            if i > 0:
                c["logic"] = st.radio("", ["AND","OR"], horizontal=True,
                    key=f"ex_logic_{i}", label_visibility="collapsed",
                    index=0 if c["logic"]=="AND" else 1)
            x1, x2, x3, x4 = st.columns([3, 1, 2, 2])
            with x1:
                c["indicator"] = st.selectbox("", INDICATORS,
                    index=INDICATORS.index(c["indicator"]), key=f"ex_ind_{i}",
                    label_visibility="collapsed")
            with x2:
                c["period"] = st.number_input("", 1, 200, int(c.get("period",14)),
                    key=f"ex_per_{i}", label_visibility="collapsed")
            with x3:
                c["condition"] = st.selectbox("", CONDITIONS,
                    index=CONDITIONS.index(c["condition"]), key=f"ex_cond_{i}",
                    label_visibility="collapsed")
            with x4:
                ref_type = st.radio("", ["Value","Indicator"], horizontal=True,
                    key=f"ex_rt_{i}", label_visibility="collapsed",
                    index=0 if c["ref_type"]=="Value" else 1)
                c["ref_type"] = ref_type
            if ref_type == "Value":
                c["ref_value"] = st.number_input("", value=float(c.get("ref_value",70.0)),
                    key=f"ex_rv_{i}", label_visibility="collapsed")
            else:
                ri1, ri2 = st.columns(2)
                with ri1:
                    c["ref_indicator"] = st.selectbox("", INDICATORS,
                        index=INDICATORS.index(c.get("ref_indicator","SMA")),
                        key=f"ex_ri_{i}", label_visibility="collapsed")
                with ri2:
                    c["ref_period"] = st.number_input("", 1, 200,
                        int(c.get("ref_period",50)), key=f"ex_rp_{i}", label_visibility="collapsed")
            if st.button("✖ Remove", key=f"ex_del_{i}", type="secondary"):
                _del_cond("sb_exit_conditions", i)
                st.rerun()
            st.markdown("<hr style='border-color:#ffffff08;margin:.2rem 0;'>", unsafe_allow_html=True)

    if st.button("➕ Add Exit Condition", use_container_width=True, key="ex_add"):
        _add_cond("sb_exit_conditions")
        st.rerun()

    # ── Prebuilt templates ───────────────────────────────────────
    st.markdown('<div class="rule-header">⚡ Quick Templates</div>', unsafe_allow_html=True)
    tmpl = st.selectbox("Load template", ["— select —",
        "RSI Reversal (oversold bounce)",
        "MACD Crossover (momentum)",
        "Bollinger Breakout",
        "EMA Golden Cross",
        "ADX Trend + RSI entry"], key="sb_template")

    if st.button("Load Template", use_container_width=True, key="sb_load_tmpl"):
        templates = {
            "RSI Reversal (oversold bounce)": {
                "entry": [{"indicator":"RSI","period":14,"condition":"crosses above",
                           "ref_type":"Value","ref_value":30.0,"ref_indicator":"RSI","ref_period":14,"logic":"AND"}],
                "exit":  [{"indicator":"RSI","period":14,"condition":"crosses above",
                           "ref_type":"Value","ref_value":70.0,"ref_indicator":"RSI","ref_period":14,"logic":"AND"}],
                "sl":3.0,"tgt":8.0
            },
            "MACD Crossover (momentum)": {
                "entry": [{"indicator":"MACD Line","period":12,"condition":"crosses above",
                           "ref_type":"Indicator","ref_value":0.0,"ref_indicator":"MACD Signal","ref_period":9,"logic":"AND"}],
                "exit":  [{"indicator":"MACD Line","period":12,"condition":"crosses below",
                           "ref_type":"Indicator","ref_value":0.0,"ref_indicator":"MACD Signal","ref_period":9,"logic":"AND"}],
                "sl":3.0,"tgt":7.0
            },
            "Bollinger Breakout": {
                "entry": [{"indicator":"Price (Close)","period":20,"condition":"crosses above",
                           "ref_type":"Indicator","ref_value":0.0,"ref_indicator":"Bollinger Upper","ref_period":20,"logic":"AND"}],
                "exit":  [{"indicator":"Price (Close)","period":20,"condition":"crosses below",
                           "ref_type":"Indicator","ref_value":0.0,"ref_indicator":"Bollinger Middle","ref_period":20,"logic":"AND"}],
                "sl":2.0,"tgt":5.0
            },
            "EMA Golden Cross": {
                "entry": [{"indicator":"EMA","period":20,"condition":"crosses above",
                           "ref_type":"Indicator","ref_value":0.0,"ref_indicator":"EMA","ref_period":50,"logic":"AND"}],
                "exit":  [{"indicator":"EMA","period":20,"condition":"crosses below",
                           "ref_type":"Indicator","ref_value":0.0,"ref_indicator":"EMA","ref_period":50,"logic":"AND"}],
                "sl":4.0,"tgt":10.0
            },
            "ADX Trend + RSI entry": {
                "entry": [
                    {"indicator":"ADX","period":14,"condition":"is above",
                     "ref_type":"Value","ref_value":25.0,"ref_indicator":"ADX","ref_period":14,"logic":"AND"},
                    {"indicator":"RSI","period":14,"condition":"is below",
                     "ref_type":"Value","ref_value":45.0,"ref_indicator":"RSI","ref_period":14,"logic":"AND"},
                ],
                "exit": [{"indicator":"RSI","period":14,"condition":"is above",
                          "ref_type":"Value","ref_value":65.0,"ref_indicator":"RSI","ref_period":14,"logic":"AND"}],
                "sl":3.5,"tgt":9.0
            },
        }
        if tmpl in templates:
            t = templates[tmpl]
            st.session_state["sb_entry_conditions"] = t["entry"]
            st.session_state["sb_exit_conditions"]  = t["exit"]
            st.session_state["sb_sl"]  = t["sl"]
            st.session_state["sb_tgt"] = t["tgt"]
            st.success(f"Template '{tmpl}' loaded!", icon="⚡")
            st.rerun()

    # ── Action buttons ───────────────────────────────────────────
    st.markdown("<div style='height:.5rem;'></div>", unsafe_allow_html=True)
    b1, b2 = st.columns(2)
    with b1:
        run_btn = st.button("▶️ Run Backtest", use_container_width=True, type="primary", key="sb_run")
    with b2:
        save_btn = st.button("💾 Save Strategy", use_container_width=True, key="sb_save")

    if save_btn:
        strategy_obj = {
            "name": strategy_name,
            "symbol": symbol,
            "side": side,
            "sl_pct": sl,
            "target_pct": tgt,
            "entry_conditions": st.session_state["sb_entry_conditions"],
            "exit_conditions": st.session_state["sb_exit_conditions"],
            "created": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
        st.session_state["sb_strategies"].append(strategy_obj)
        st.success(f"Strategy '{strategy_name}' saved!", icon="💾")


# ═══════════════════════════════════════════════════════════════
# RIGHT: Backtest results
# ═══════════════════════════════════════════════════════════════
with right:
    if run_btn:
        if not st.session_state["sb_entry_conditions"]:
            st.warning("Add at least one entry condition first.", icon="⚠️")
        else:
            with st.spinner(f"Downloading {symbol} data & running backtest…"):
                try:
                    df = yf.download(symbol, period=period_map[period_lbl],
                                     interval=interval, progress=False, auto_adjust=True)
                    if df.empty:
                        st.error("No data for this symbol/interval.", icon="❌")
                    else:
                        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
                        entry_sig = _apply_conditions(df, st.session_state["sb_entry_conditions"])
                        exit_sig  = _apply_conditions(df, st.session_state["sb_exit_conditions"])
                        trades, equity = _run_backtest(df, entry_sig, exit_sig, sl, tgt, side)
                        st.session_state["sb_last_trades"] = trades
                        st.session_state["sb_last_equity"] = equity
                        st.session_state["sb_last_df"]     = df
                        st.session_state["sb_last_entry"]  = entry_sig
                        st.session_state["sb_last_exit"]   = exit_sig
                except Exception as e:
                    st.error(f"Backtest failed: {e}", icon="❌")

    trades  = st.session_state.get("sb_last_trades", [])
    equity  = st.session_state.get("sb_last_equity", [])
    df_hist = st.session_state.get("sb_last_df")

    if trades and equity:
        completed = [t for t in trades if t.get("pnl") is not None]
        total_pnl  = sum(t["pnl"] for t in completed)
        win_trades = [t for t in completed if t["result"] == "WIN"]
        win_rate   = len(win_trades) / len(completed) * 100 if completed else 0
        avg_win    = np.mean([t["pnl"] for t in win_trades]) if win_trades else 0
        loss_trades = [t for t in completed if t["result"] == "LOSS"]
        avg_loss   = abs(np.mean([t["pnl"] for t in loss_trades])) if loss_trades else 1
        profit_factor = (sum(t["pnl"] for t in win_trades) /
                         abs(sum(t["pnl"] for t in loss_trades or [{"pnl":-1}]))) if loss_trades else float("inf")
        max_dd = 0.0
        peak   = equity[0]
        for e in equity:
            if e > peak: peak = e
            dd = (peak - e) / peak * 100
            if dd > max_dd: max_dd = dd

        m1,m2,m3,m4,m5 = st.columns(5)
        with m1: st.metric("Total P&L",     f"₹{total_pnl:,.0f}")
        with m2: st.metric("Win Rate",      f"{win_rate:.1f}%")
        with m3: st.metric("Trades",        len(completed))
        with m4: st.metric("Profit Factor", f"{profit_factor:.2f}")
        with m5: st.metric("Max Drawdown",  f"-{max_dd:.1f}%")

        # Equity curve
        eq_dates = [df_hist.index[min(i, len(df_hist)-1)] for i in range(len(equity))]
        fig_eq = go.Figure()
        fig_eq.add_trace(go.Scatter(
            x=eq_dates, y=equity, mode="lines", name="Equity",
            line=dict(color="#ffd200", width=2),
            fill="tozeroy", fillcolor="rgba(255,210,0,0.06)"))
        fig_eq.update_layout(
            title="Equity Curve", paper_bgcolor="#0d0d1a", plot_bgcolor="#12122a",
            font_color="#e0e0e0", height=260,
            xaxis=dict(gridcolor="#ffffff10"), yaxis=dict(gridcolor="#ffffff10"),
            margin=dict(l=40,r=20,t=40,b=30))
        st.plotly_chart(fig_eq, use_container_width=True)

        # Price + signals chart
        if df_hist is not None:
            entry_s = st.session_state.get("sb_last_entry")
            exit_s  = st.session_state.get("sb_last_exit")
            fig_p = go.Figure()
            fig_p.add_trace(go.Candlestick(
                x=df_hist.index, open=df_hist["Open"], high=df_hist["High"],
                low=df_hist["Low"], close=df_hist["Close"], name="Price",
                increasing_line_color="#00c853", decreasing_line_color="#ff5252"))
            if entry_s is not None:
                e_idx = df_hist[entry_s].index
                fig_p.add_trace(go.Scatter(
                    x=e_idx, y=df_hist.loc[e_idx,"Low"] * 0.99,
                    mode="markers", name="Entry",
                    marker=dict(color="#00c853", symbol="triangle-up", size=10)))
            if exit_s is not None and exit_s.any():
                x_idx = df_hist[exit_s].index
                fig_p.add_trace(go.Scatter(
                    x=x_idx, y=df_hist.loc[x_idx,"High"] * 1.01,
                    mode="markers", name="Exit",
                    marker=dict(color="#ff5252", symbol="triangle-down", size=10)))
            fig_p.update_layout(
                title=f"{symbol} – Entry/Exit Signals",
                paper_bgcolor="#0d0d1a", plot_bgcolor="#12122a",
                font_color="#e0e0e0", height=340,
                xaxis=dict(gridcolor="#ffffff10", rangeslider=dict(visible=False)),
                yaxis=dict(gridcolor="#ffffff10"),
                margin=dict(l=40,r=20,t=40,b=30))
            st.plotly_chart(fig_p, use_container_width=True)

        # Trade log
        with st.expander("📋 Trade Log", expanded=False):
            if completed:
                rows = [{
                    "Entry Date": str(t["entry_date"])[:10],
                    "Entry ₹":    f"₹{t['entry']:,.2f}",
                    "Exit Date":  str(t["exit_date"])[:10],
                    "Exit ₹":     f"₹{t['exit']:,.2f}",
                    "P&L ₹":      f"₹{t['pnl']:+,.2f}",
                    "Result":     t["result"],
                    "Reason":     t.get("reason","")
                } for t in completed]
                df_trades = pd.DataFrame(rows)
                st.dataframe(df_trades, hide_index=True, use_container_width=True)
            else:
                st.info("No completed trades in this period.")
    else:
        st.markdown("""
<div style="background:#12122a;border:1px solid #ffd20020;border-radius:12px;
padding:3rem;text-align:center;margin-top:2rem;">
  <div style="font-size:3rem;">🏗️</div>
  <div style="color:#ffd200;font-size:1.1rem;font-weight:700;margin-top:.5rem;">
    Build your strategy on the left
  </div>
  <div style="color:#8892a4;font-size:.85rem;margin-top:.3rem;">
    Add entry &amp; exit conditions · Set SL/Target · Click ▶️ Run Backtest
  </div>
  <div style="color:#5a6580;font-size:.78rem;margin-top:1rem;">
    💡 Tip: Use ⚡ Quick Templates to start fast
  </div>
</div>""", unsafe_allow_html=True)

# ── Saved strategies ──────────────────────────────────────────────────────────
if st.session_state["sb_strategies"]:
    st.markdown("<hr style='border-color:#ffffff10;margin:1.5rem 0 .8rem;'>", unsafe_allow_html=True)
    st.markdown('<div style="color:#ffd200;font-weight:700;font-size:1rem;">💾 Saved Strategies</div>',
                unsafe_allow_html=True)
    for i, s in enumerate(st.session_state["sb_strategies"]):
        with st.expander(f"📋 {s['name']}  ·  {s['symbol']}  ·  {s['created']}"):
            st.code(json.dumps(s, indent=2), language="json")
            if st.button("Load", key=f"load_saved_{i}"):
                st.session_state["sb_entry_conditions"] = s["entry_conditions"]
                st.session_state["sb_exit_conditions"]  = s["exit_conditions"]
                st.rerun()
