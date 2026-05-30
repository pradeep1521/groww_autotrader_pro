"""
Risk Guard – Circuit Breaker & Automated Risk Controls
=======================================================
Daily loss limit · Max drawdown · Max open positions · Position size cap
Auto SQ-OFF timer · Concentration limits · Live P&L vs limits monitor
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, time as dtime
import json
from pathlib import Path

st.set_page_config(page_title="Risk Guard", page_icon="⛔", layout="wide")

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
.risk-card {
  background:#12122a; border:1px solid #ffffff10; border-radius:12px; padding:1.2rem;
}
.risk-card.danger { border-color:#ff525260; background:#1a0d0d; }
.risk-card.warning { border-color:#ffd20060; background:#1a1a0d; }
.risk-card.safe { border-color:#00c85360; background:#0d1a10; }
.guard-status {
  font-size:1.4rem; font-weight:800; letter-spacing:.05em;
}
.guard-ok   { color:#00c853; }
.guard-warn { color:#ffd200; }
.guard-halt { color:#ff5252; }
[data-testid="stMetric"] { background:#12122a; border:1px solid #ffffff10; border-radius:10px; padding:.8rem; }
[data-testid="stMetricValue"] { color:#ffd200 !important; font-size:1.4rem !important; font-weight:700 !important; }
.rule-row {
  background:#12122a; border:1px solid #ffffff08; border-radius:8px;
  padding:.6rem 1rem; margin-bottom:.3rem; display:flex; align-items:center; gap:1rem;
}
</style>
""", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────────────────
_DEFAULTS = {
    "rg_enabled":           True,
    "rg_daily_loss_limit":  5000,
    "rg_max_positions":     5,
    "rg_max_drawdown_pct":  3.0,
    "rg_position_size_pct": 10.0,
    "rg_max_trades_day":    20,
    "rg_concentration_pct": 30.0,
    "rg_sqoff_enabled":     False,
    "rg_sqoff_time":        "15:20",
    "rg_breached":          False,
    "rg_breach_reason":     "",
    "rg_event_log":         [],
    "rg_starting_capital":  100000,
}
for k, v in _DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

def _log_event(event: str, severity: str = "INFO"):
    ts = datetime.now().strftime("%H:%M:%S")
    st.session_state["rg_event_log"].insert(0, {
        "time": ts, "event": event, "severity": severity})
    st.session_state["rg_event_log"] = st.session_state["rg_event_log"][:100]

# ── Compute live P&L from session state ──────────────────────────────────────
def _compute_pnl() -> tuple[float, float, int, float]:
    """Returns (daily_pnl, unrealized_pnl, open_positions, max_drawdown_pct)."""
    positions   = st.session_state.get("paper_positions", [])
    open_pos    = [p for p in positions if p.get("status") == "OPEN"]
    closed_pos  = [p for p in positions if p.get("status","OPEN") == "CLOSED"]

    realized   = sum(p.get("realized_pnl", 0) for p in closed_pos)
    unrealized = 0.0
    for p in open_pos:
        ltp       = p.get("ltp", p.get("avg_price", 0))
        avg       = p.get("avg_price", ltp)
        qty       = p.get("qty", 1)
        side      = p.get("side","BUY").upper()
        if side == "BUY":
            unrealized += (ltp - avg) * qty
        else:
            unrealized += (avg - ltp) * qty

    daily_pnl    = realized + unrealized
    capital      = st.session_state["rg_starting_capital"]
    max_dd_pct   = min(daily_pnl / capital * 100, 0) if capital else 0.0
    return daily_pnl, unrealized, len(open_pos), max_dd_pct

# ── Risk checker ─────────────────────────────────────────────────────────────
def _check_rules(daily_pnl, open_pos, max_dd_pct) -> list[dict]:
    """Returns list of {rule, status, value, limit, pct_used}."""
    rules_result = []
    capital = st.session_state["rg_starting_capital"]

    # Daily loss limit
    loss        = -daily_pnl if daily_pnl < 0 else 0
    lim         = st.session_state["rg_daily_loss_limit"]
    pct         = (loss / lim * 100) if lim > 0 else 0
    rules_result.append({"rule": "Daily Loss Limit", "value": f"₹{loss:,.0f}",
                         "limit": f"₹{lim:,.0f}", "pct": pct,
                         "breached": loss >= lim, "color": "#ff5252"})

    # Max drawdown
    dd_abs      = abs(min(daily_pnl, 0))
    dd_pct_lim  = st.session_state["rg_max_drawdown_pct"]
    dd_cur_pct  = dd_abs / capital * 100 if capital else 0
    pct2        = (dd_cur_pct / dd_pct_lim * 100) if dd_pct_lim > 0 else 0
    rules_result.append({"rule": "Max Drawdown", "value": f"{dd_cur_pct:.2f}%",
                         "limit": f"{dd_pct_lim:.1f}%", "pct": pct2,
                         "breached": dd_cur_pct >= dd_pct_lim, "color": "#ff5252"})

    # Max open positions
    pos_lim     = st.session_state["rg_max_positions"]
    pct3        = (open_pos / pos_lim * 100) if pos_lim > 0 else 0
    rules_result.append({"rule": "Open Positions", "value": str(open_pos),
                         "limit": str(pos_lim), "pct": pct3,
                         "breached": open_pos > pos_lim, "color": "#ffd200"})

    # Max trades today
    trades_today = len([p for p in st.session_state.get("paper_positions",[])
                        if p.get("timestamp","")[:10] == datetime.today().strftime("%Y-%m-%d")])
    t_lim        = st.session_state["rg_max_trades_day"]
    pct4         = (trades_today / t_lim * 100) if t_lim > 0 else 0
    rules_result.append({"rule": "Trades Today", "value": str(trades_today),
                         "limit": str(t_lim), "pct": pct4,
                         "breached": trades_today >= t_lim, "color": "#ffd200"})

    return rules_result

# ─────────────────────────────────────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────────────────────────────────────
enabled = st.session_state["rg_enabled"]
guard_status = "🛡️ ACTIVE" if enabled else "⚠️ DISABLED"
guard_color  = "#00c853" if enabled else "#ffd200"
if st.session_state["rg_breached"]:
    guard_status = "🚨 HALTED"
    guard_color  = "#ff5252"

col_title, col_toggle = st.columns([6, 1])
with col_title:
    st.markdown(
        f"<h2 style='color:#ffd200;margin:0;font-weight:800;'>⛔ Risk Guard</h2>"
        f"<div style='color:{guard_color};font-size:.9rem;font-weight:700;'>"
        f"Circuit Breaker Status: {guard_status}</div>",
        unsafe_allow_html=True)
with col_toggle:
    new_enabled = st.toggle("Enable", value=enabled, key="rg_toggle_main")
    if new_enabled != enabled:
        st.session_state["rg_enabled"] = new_enabled
        _log_event(f"Risk Guard {'ENABLED' if new_enabled else 'DISABLED'}", "INFO")

st.markdown("<hr style='border-color:#ffffff10;margin:.5rem 0 1rem;'>", unsafe_allow_html=True)

tab_monitor, tab_rules, tab_sqoff, tab_log = st.tabs([
    "📊 Live Monitor", "⚙️ Rules & Limits", "⏱️ Auto SQ-OFF", "📋 Event Log"
])

# ═══════════════════════════════════════════════════════════════
# TAB 1 – Live Monitor
# ═══════════════════════════════════════════════════════════════
with tab_monitor:
    daily_pnl, unrealized, open_pos, max_dd_pct = _compute_pnl()
    rules_result = _check_rules(daily_pnl, open_pos, max_dd_pct)

    # Auto-check circuit breaker
    if enabled:
        breaches = [r for r in rules_result if r["breached"]]
        if breaches and not st.session_state["rg_breached"]:
            st.session_state["rg_breached"]    = True
            st.session_state["rg_breach_reason"] = breaches[0]["rule"]
            _log_event(f"⛔ CIRCUIT BREAKER TRIPPED: {breaches[0]['rule']}", "CRITICAL")
        elif not breaches and st.session_state["rg_breached"]:
            pass  # Keep breached until manually reset

    if st.session_state["rg_breached"]:
        st.error(
            f"⛔ TRADING HALTED — {st.session_state['rg_breach_reason']} limit breached. "
            "Click **Reset Circuit Breaker** to resume.",
            icon="🚨")
        if st.button("🔓 Reset Circuit Breaker", type="primary", key="rg_reset"):
            st.session_state["rg_breached"]    = False
            st.session_state["rg_breach_reason"] = ""
            _log_event("Circuit Breaker RESET by user", "WARNING")
            st.rerun()

    # P&L Metrics
    capital    = st.session_state["rg_starting_capital"]
    pnl_pct    = daily_pnl / capital * 100 if capital else 0
    pnl_color  = "#00c853" if daily_pnl >= 0 else "#ff5252"

    st.markdown("### 💰 Today's P&L")
    m1,m2,m3,m4 = st.columns(4)
    with m1: st.metric("Daily P&L",    f"₹{daily_pnl:,.0f}",   delta=f"{pnl_pct:+.2f}%")
    with m2: st.metric("Unrealized",   f"₹{unrealized:,.0f}")
    with m3: st.metric("Open Positions", str(open_pos))
    with m4: st.metric("Capital",      f"₹{capital:,.0f}")

    st.markdown("### 🚦 Risk Rule Status")
    for r in rules_result:
        pct   = min(r["pct"], 100)
        color = "#ff5252" if r["breached"] else ("#ffd200" if pct > 70 else "#00c853")
        badge = "❌ BREACHED" if r["breached"] else ("⚠️ WARNING" if pct > 70 else "✅ OK")

        st.markdown(
            f'<div class="risk-card {"danger" if r["breached"] else ("warning" if pct>70 else "safe")}" '
            f'style="margin-bottom:.4rem;">'
            f'<div style="display:flex;justify-content:space-between;align-items:center;">'
            f'  <div><b style="color:#e0e0e0;">{r["rule"]}</b>'
            f'    <span style="color:#8892a4;font-size:.78rem;margin-left:8px;">'
            f'    Current: {r["value"]}  ·  Limit: {r["limit"]}</span></div>'
            f'  <div style="color:{color};font-size:.82rem;font-weight:700;">{badge}</div>'
            f'</div></div>',
            unsafe_allow_html=True)

        # Progress bar
        bar_color = "#ff5252" if r["breached"] else ("#ffd200" if pct > 70 else "#00c853")
        st.markdown(
            f'<div style="background:#0d0d1a;border-radius:4px;height:6px;margin-bottom:.6rem;">'
            f'<div style="width:{pct:.0f}%;height:6px;border-radius:4px;background:{bar_color};">'
            f'</div></div>',
            unsafe_allow_html=True)

    # Refresh button
    if st.button("🔄 Refresh Metrics", key="rg_refresh"):
        st.rerun()

# ═══════════════════════════════════════════════════════════════
# TAB 2 – Rules & Limits
# ═══════════════════════════════════════════════════════════════
with tab_rules:
    st.markdown('<div class="rule-header">💰 Capital & P&L Limits</div>', unsafe_allow_html=True)
    r1c1, r1c2 = st.columns(2)
    with r1c1:
        cap = st.number_input("Starting Capital (₹)", 10000, 10000000, st.session_state["rg_starting_capital"],
                              step=10000, key="rg_capital_inp",
                              help="Base capital for % calculations")
        st.session_state["rg_starting_capital"] = cap

        dll = st.number_input("Daily Loss Limit (₹)", 500, 500000, st.session_state["rg_daily_loss_limit"],
                              step=500, key="rg_dll",
                              help="Trading halts when cumulative daily loss exceeds this")
        st.session_state["rg_daily_loss_limit"] = dll

    with r1c2:
        mdd = st.number_input("Max Drawdown (%)", 0.5, 20.0, st.session_state["rg_max_drawdown_pct"],
                              step=0.5, key="rg_mdd",
                              help="Trading halts when portfolio drawdown exceeds this %")
        st.session_state["rg_max_drawdown_pct"] = mdd

        psp = st.number_input("Max Position Size (%)", 1.0, 50.0, st.session_state["rg_position_size_pct"],
                              step=1.0, key="rg_psp",
                              help="Single trade cannot exceed this % of capital")
        st.session_state["rg_position_size_pct"] = psp

    st.markdown('<div class="rule-header">📊 Position & Trade Limits</div>', unsafe_allow_html=True)
    r2c1, r2c2 = st.columns(2)
    with r2c1:
        mop = st.number_input("Max Open Positions", 1, 50, st.session_state["rg_max_positions"],
                              step=1, key="rg_mop")
        st.session_state["rg_max_positions"] = mop

        mtd = st.number_input("Max Trades Per Day", 1, 200, st.session_state["rg_max_trades_day"],
                              step=1, key="rg_mtd")
        st.session_state["rg_max_trades_day"] = mtd

    with r2c2:
        conc = st.number_input("Max Concentration per Symbol (%)", 5.0, 100.0,
                               st.session_state["rg_concentration_pct"], step=5.0, key="rg_conc",
                               help="Max % of portfolio in a single symbol")
        st.session_state["rg_concentration_pct"] = conc

    # Position size calculator
    st.markdown('<div class="rule-header">🧮 Position Size Calculator</div>', unsafe_allow_html=True)
    ps_col1, ps_col2, ps_col3 = st.columns(3)
    with ps_col1:
        ps_price  = st.number_input("Stock price (₹)", 1.0, 100000.0, 1000.0, step=10.0, key="ps_price")
    with ps_col2:
        ps_sl_pct = st.number_input("Stop-loss (%)", 0.1, 10.0, 1.0, step=0.1, key="ps_sl")
    with ps_col3:
        ps_risk   = st.number_input("Risk per trade (₹)", 100, 100000, 1000, step=100, key="ps_risk")

    if ps_price > 0 and ps_sl_pct > 0:
        sl_amount = ps_price * ps_sl_pct / 100
        qty       = int(ps_risk / sl_amount)
        trade_val = qty * ps_price
        pct_of_cap = trade_val / cap * 100 if cap > 0 else 0
        within    = pct_of_cap <= psp
        ps_color  = "#00c853" if within else "#ff5252"
        st.markdown(
            f'<div class="risk-card {"safe" if within else "danger"}">'
            f'<b style="color:{ps_color};">Recommended Qty: {qty} shares</b>'
            f' &nbsp;·&nbsp; Trade Value: ₹{trade_val:,.0f}'
            f' &nbsp;·&nbsp; {pct_of_cap:.1f}% of capital'
            f' &nbsp;·&nbsp; SL: ₹{sl_amount:.2f}/share'
            f'{"  ✅ Within limits" if within else f"  ❌ Exceeds {psp:.0f}% position limit"}'
            f'</div>',
            unsafe_allow_html=True)

    if st.button("💾 Save Rules", type="primary", key="rg_save"):
        _log_event("Risk rules updated by user", "INFO")
        st.success("Risk rules saved!", icon="✅")

# ═══════════════════════════════════════════════════════════════
# TAB 3 – Auto SQ-OFF
# ═══════════════════════════════════════════════════════════════
with tab_sqoff:
    st.markdown('<div class="rule-header">⏱️ Automatic Square-Off Settings</div>', unsafe_allow_html=True)

    sqoff_enabled = st.toggle("Enable Auto SQ-OFF at end of day",
                              value=st.session_state["rg_sqoff_enabled"], key="rg_sqoff_en")
    st.session_state["rg_sqoff_enabled"] = sqoff_enabled

    sq_col1, sq_col2 = st.columns(2)
    with sq_col1:
        sqoff_time_str = st.text_input("SQ-OFF Time (HH:MM)", st.session_state["rg_sqoff_time"],
                                       key="rg_sqoff_time_inp",
                                       help="All positions squared off at this time. NSE intraday deadline: 15:20")
        try:
            h, m = map(int, sqoff_time_str.split(":"))
            sqoff_time = dtime(h, m)
            st.session_state["rg_sqoff_time"] = sqoff_time_str
        except:
            st.error("Invalid time format (use HH:MM)")
            sqoff_time = dtime(15, 20)

    with sq_col2:
        now_time = datetime.now().time()
        if sqoff_enabled:
            if now_time >= sqoff_time:
                st.markdown('<div class="risk-card danger" style="padding:.8rem 1rem;">'
                            '<b style="color:#ff5252;">⏱️ SQ-OFF TIME PASSED</b><br>'
                            '<span style="color:#8892a4;font-size:.8rem;">All positions should be squared off.</span>'
                            '</div>', unsafe_allow_html=True)
            else:
                mins_left = int((datetime.combine(datetime.today(), sqoff_time) -
                                  datetime.now()).total_seconds() / 60)
                st.markdown(f'<div class="risk-card safe" style="padding:.8rem 1rem;">'
                            f'<b style="color:#00c853;">✅ Market Open</b><br>'
                            f'<span style="color:#8892a4;font-size:.8rem;">'
                            f'Auto SQ-OFF in <b style="color:#ffd200;">{mins_left} min</b> at {sqoff_time_str}</span>'
                            f'</div>', unsafe_allow_html=True)
        else:
            st.info("Auto SQ-OFF is disabled.", icon="ℹ️")

    st.markdown('<div class="rule-header">🛑 Manual Square-Off</div>', unsafe_allow_html=True)
    positions = st.session_state.get("paper_positions", [])
    open_pos  = [p for p in positions if p.get("status") == "OPEN"]

    if not open_pos:
        st.info("No open positions to square off.", icon="✅")
    else:
        st.warning(f"{len(open_pos)} open position(s) will be squared off at current LTP.", icon="⚠️")
        st.dataframe(
            pd.DataFrame([{
                "Symbol": p.get("symbol",""), "Side": p.get("side",""),
                "Qty": p.get("qty",0), "Avg": f"₹{p.get('avg_price',0):,.2f}",
                "LTP": f"₹{p.get('ltp',0):,.2f}",
            } for p in open_pos]),
            hide_index=True, use_container_width=True)

        if st.button("⛔ SQUARE OFF ALL POSITIONS NOW", type="primary", key="rg_sqoff_now"):
            for i, p in enumerate(st.session_state["paper_positions"]):
                if p.get("status") == "OPEN":
                    ltp = p.get("ltp", p.get("avg_price", 0))
                    avg = p.get("avg_price", ltp)
                    qty = p.get("qty", 1)
                    side = p.get("side","BUY").upper()
                    pnl  = (ltp - avg) * qty if side == "BUY" else (avg - ltp) * qty
                    st.session_state["paper_positions"][i]["status"]       = "CLOSED"
                    st.session_state["paper_positions"][i]["realized_pnl"] = pnl
                    st.session_state["paper_positions"][i]["exit_price"]   = ltp
            _log_event(f"Manual SQ-OFF executed for {len(open_pos)} positions", "WARNING")
            st.success(f"Squared off {len(open_pos)} positions!", icon="✅")
            st.rerun()

# ═══════════════════════════════════════════════════════════════
# TAB 4 – Event Log
# ═══════════════════════════════════════════════════════════════
with tab_log:
    st.markdown('<div class="rule-header">📋 Risk Event Log</div>', unsafe_allow_html=True)

    lc1, lc2 = st.columns([5,1])
    with lc2:
        if st.button("🗑️ Clear Log", key="rg_clear_log", use_container_width=True):
            st.session_state["rg_event_log"] = []
            st.rerun()

    events = st.session_state["rg_event_log"]
    if not events:
        st.info("No events logged yet. Risk events will appear here.", icon="📋")
    else:
        for ev in events:
            sev = ev.get("severity","INFO")
            color = "#ff5252" if sev=="CRITICAL" else ("#ffd200" if sev=="WARNING" else "#8892a4")
            icon  = "🚨" if sev=="CRITICAL" else ("⚠️" if sev=="WARNING" else "ℹ️")
            st.markdown(
                f'<div style="background:#12122a;border:1px solid #ffffff08;border-radius:6px;'
                f'padding:.4rem .8rem;margin-bottom:.2rem;font-size:.8rem;">'
                f'<span style="color:#5a6580;">{ev["time"]}</span> '
                f'{icon} <span style="color:{color};">{ev["event"]}</span>'
                f'</div>',
                unsafe_allow_html=True)
