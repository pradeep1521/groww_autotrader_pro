"""
TradingView / ChartInk Webhook Integration
==========================================
Receive external signals (TradingView alerts, ChartInk, Pine Script)
and auto-execute trades — the #1 feature of every algo platform.
Also includes a built-in signal simulator & live webhook log.
"""

import streamlit as st
import json
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path

st.set_page_config(page_title="Webhooks", page_icon="📡", layout="wide")

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
.webhook-card {
  background:#12122a; border:1px solid #ffd20025; border-radius:12px; padding:1.2rem 1.4rem;
}
.signal-card {
  background:#12122a; border:1px solid #00c85330; border-radius:10px; padding:.8rem 1rem; margin-bottom:.4rem;
}
.signal-card.sell { border-color:#ff525230; }
.sig-badge {
  display:inline-block; padding:2px 10px; border-radius:12px;
  font-size:.72rem; font-weight:700;
}
.sig-buy  { background:#00c85320; color:#00c853; }
.sig-sell { background:#ff525220; color:#ff5252; }
.code-block { background:#0a0a1a; border:1px solid #ffffff15; border-radius:8px; padding:1rem; }
code { color:#ffd200 !important; }
[data-testid="stMetric"] { background:#12122a; border:1px solid #ffffff10; border-radius:10px; padding:.8rem; }
[data-testid="stMetricValue"] { color:#ffd200 !important; font-size:1.4rem !important; font-weight:700 !important; }
</style>
""", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────────────────
if "webhook_signals" not in st.session_state:
    st.session_state["webhook_signals"] = []
if "webhook_enabled" not in st.session_state:
    st.session_state["webhook_enabled"] = False
if "webhook_auto_execute" not in st.session_state:
    st.session_state["webhook_auto_execute"] = False

# ── Signal file path (used by background server) ──────────────────────────────
_SIGNAL_FILE = Path(__file__).parent.parent / "logs" / "webhook_signals.json"
_SIGNAL_FILE.parent.mkdir(exist_ok=True)

def _load_file_signals():
    """Load signals written by the background webhook server."""
    if not _SIGNAL_FILE.exists():
        return []
    try:
        return json.loads(_SIGNAL_FILE.read_text())
    except:
        return []

def _save_file_signals(signals):
    _SIGNAL_FILE.write_text(json.dumps(signals, indent=2, default=str))

def _process_signal(payload: dict, auto_execute: bool = False) -> dict:
    """Parse a webhook payload into a normalized trade signal."""
    # TradingView standard fields
    action   = str(payload.get("action", payload.get("side","BUY"))).upper()
    symbol   = str(payload.get("symbol", payload.get("ticker","RELIANCE-EQ")))
    qty      = int(float(payload.get("qty", payload.get("quantity", payload.get("contracts", 1)))))
    price    = float(payload.get("price", payload.get("ltp", 0)))
    order_tp = str(payload.get("order_type", payload.get("type","MARKET"))).upper()
    exchange = str(payload.get("exchange","NSE")).upper()
    strategy = str(payload.get("strategy", payload.get("strategy_name","Webhook")))
    comment  = str(payload.get("comment", payload.get("message","")))

    signal = {
        "id":           str(uuid.uuid4())[:8],
        "received_at":  datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "action":       action,
        "symbol":       symbol,
        "qty":          qty,
        "price":        price,
        "order_type":   order_tp,
        "exchange":     exchange,
        "strategy":     strategy,
        "comment":      comment,
        "raw":          payload,
        "status":       "PENDING",
        "executed":     False,
        "error":        None,
    }

    if auto_execute:
        signal = _execute_signal(signal)

    return signal

def _execute_signal(signal: dict) -> dict:
    """Execute a signal — paper or real depending on mode."""
    try:
        client = st.session_state.get("kotak_client")
        paper  = st.session_state.get("paper_mode", False)

        if client is None or not client.is_authenticated():
            signal["status"] = "SKIPPED – not authenticated"
            signal["error"]  = "Kotak Neo client not connected. Go to 🦁 Kotak Neo tab first."
            return signal

        if paper:
            # Paper mode – simulate via _paper_add equivalent
            positions = st.session_state.setdefault("paper_positions", [])
            exec_price = signal["price"] if signal["price"] > 0 else 0
            positions.append({
                "symbol":      signal["symbol"],
                "exchange":    signal["exchange"],
                "side":        signal["action"],
                "qty":         signal["qty"],
                "avg_price":   exec_price,
                "ltp":         exec_price,
                "product":     "MIS",
                "order_type":  signal["order_type"],
                "status":      "OPEN",
                "realized_pnl": 0.0,
                "timestamp":   signal["received_at"][:19],
            })
            signal["status"]   = "PAPER EXECUTED"
            signal["executed"] = True
        else:
            # Real execution via Kotak Neo
            from kotak_neo.models import (Order, OrderSide, OrderType as NeoOT,
                                           ProductType, Exchange as NeoEx, Validity)
            _SIDE = {"BUY": OrderSide.BUY, "SELL": OrderSide.SELL}
            _OT   = {"MARKET": NeoOT.MARKET, "LIMIT": NeoOT.LIMIT,
                     "SL": NeoOT.STOP_LOSS, "SL-M": NeoOT.STOP_LOSS_M}
            _EX   = {"NSE": NeoEx.NSE, "BSE": NeoEx.BSE, "NFO": NeoEx.NFO,
                     "BFO": NeoEx.BFO, "MCX": NeoEx.MCX}
            order = Order(
                exchange=_EX.get(signal["exchange"], NeoEx.NSE),
                trading_symbol=signal["symbol"],
                side=_SIDE.get(signal["action"], OrderSide.BUY),
                order_type=_OT.get(signal["order_type"], NeoOT.MARKET),
                product=ProductType.MIS,
                quantity=signal["qty"],
                price=signal["price"],
                validity=Validity.DAY)
            resp = client.place_order(order)
            signal["status"]    = f"LIVE EXECUTED · {resp.order_id}"
            signal["order_id"]  = resp.order_id
            signal["executed"]  = True
    except Exception as e:
        signal["status"] = "FAILED"
        signal["error"]  = str(e)
    return signal

# ─────────────────────────────────────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────────────────────────────────────
st.markdown(
    "<h2 style='color:#ffd200;margin:0;font-weight:800;'>📡 Webhooks & Signal Integration</h2>"
    "<div style='color:#8892a4;font-size:.85rem;'>TradingView · ChartInk · Pine Script · "
    "Any HTTP POST → auto-execute on Kotak Neo</div>",
    unsafe_allow_html=True)
st.markdown("<hr style='border-color:#ffffff10;margin:.5rem 0 1rem;'>", unsafe_allow_html=True)

tab_setup, tab_sim, tab_log, tab_srv = st.tabs([
    "⚙️ Setup & Format", "🧪 Signal Simulator", "📋 Signal Log", "🖥️ Webhook Server"
])

# ═══════════════════════════════════════════════════════════════
# TAB 1 – Setup & Format
# ═══════════════════════════════════════════════════════════════
with tab_setup:
    col1, col2 = st.columns(2, gap="large")

    with col1:
        st.markdown('<div class="rule-header">📋 TradingView Alert Setup</div>', unsafe_allow_html=True)
        st.markdown("""
<div class="webhook-card">
<b style="color:#ffd200;">Step 1</b> — Start the Webhook Server (see the 🖥️ tab)<br><br>
<b style="color:#ffd200;">Step 2</b> — Expose via ngrok (local) or deploy on a VPS:<br>
<code>ngrok http 8502</code><br><br>
<b style="color:#ffd200;">Step 3</b> — In TradingView alert, set <b>Webhook URL</b> to:<br>
<code>https://YOUR-URL/webhook</code><br><br>
<b style="color:#ffd200;">Step 4</b> — Set the <b>Message</b> JSON body:<br>
</div>""", unsafe_allow_html=True)
        st.code('''{
  "action":     "BUY",
  "symbol":     "RELIANCE-EQ",
  "exchange":   "NSE",
  "qty":        10,
  "order_type": "MARKET",
  "price":      0,
  "strategy":   "{{strategy.order.id}}",
  "comment":    "{{strategy.order.comment}}"
}''', language="json")

        st.markdown('<div class="rule-header">📋 ChartInk / Pine Script Format</div>', unsafe_allow_html=True)
        st.code('''{
  "action":   "{{plot_0}}",
  "symbol":   "{{ticker}}",
  "exchange": "NSE",
  "qty":      5,
  "price":    {{close}}
}''', language="json")

    with col2:
        st.markdown('<div class="rule-header">🔑 Supported Fields</div>', unsafe_allow_html=True)
        fields = [
            ("action / side",  "BUY or SELL", "Required"),
            ("symbol / ticker","NSE trading symbol e.g. RELIANCE-EQ", "Required"),
            ("exchange",       "NSE / BSE / NFO / BFO / MCX", "Optional (default NSE)"),
            ("qty / quantity / contracts", "Number of shares/lots", "Optional (default 1)"),
            ("price / ltp",    "Limit price; 0 = MARKET order", "Optional"),
            ("order_type / type","MARKET / LIMIT / SL / SL-M","Optional (default MARKET)"),
            ("strategy / strategy_name","Strategy name tag","Optional"),
            ("comment / message","Free-text note","Optional"),
        ]
        st.dataframe(pd.DataFrame(fields, columns=["Field","Description","Required?"]),
                     hide_index=True, use_container_width=True)

        st.markdown('<div class="rule-header">⚙️ Execution Settings</div>', unsafe_allow_html=True)
        wh_auto = st.toggle("Auto-execute incoming signals",
                            value=st.session_state["webhook_auto_execute"],
                            help="When ON, signals are immediately executed (paper or live depending on mode)")
        st.session_state["webhook_auto_execute"] = wh_auto

        paper = st.session_state.get("paper_mode", False)
        if wh_auto:
            mode_str = "📝 PAPER MODE" if paper else "⚡ LIVE MODE"
            color    = "#ffd200" if paper else "#00c853"
            st.markdown(
                f'<div style="background:#12122a;border:1px solid {color}40;border-radius:8px;'
                f'padding:.6rem 1rem;color:{color};font-weight:700;font-size:.85rem;">'
                f'Signals will execute in {mode_str} · Toggle paper mode in 🦁 Kotak Neo tab</div>',
                unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════
# TAB 2 – Signal Simulator
# ═══════════════════════════════════════════════════════════════
with tab_sim:
    st.markdown('<div class="rule-header">🧪 Simulate / Test a Signal</div>', unsafe_allow_html=True)
    st.caption("Paste a JSON payload (TradingView format) or use the form to build one.")

    sim_col1, sim_col2 = st.columns([3, 2], gap="large")

    with sim_col1:
        payload_mode = st.radio("Input mode", ["Form", "Raw JSON"], horizontal=True, key="wh_sim_mode")

        if payload_mode == "Raw JSON":
            raw_json = st.text_area("Paste JSON payload", height=180, key="wh_raw_json",
                value='{\n  "action": "BUY",\n  "symbol": "RELIANCE-EQ",\n  "exchange": "NSE",\n  "qty": 5,\n  "order_type": "MARKET",\n  "price": 0,\n  "strategy": "Test"\n}')
            try:
                payload = json.loads(raw_json)
                st.success("Valid JSON ✓", icon="✅")
            except json.JSONDecodeError as e:
                st.error(f"Invalid JSON: {e}", icon="❌")
                payload = {}
        else:
            f1, f2 = st.columns(2)
            with f1:
                sim_action   = st.selectbox("Action", ["BUY","SELL"], key="sim_act")
                sim_symbol   = st.text_input("Symbol", "RELIANCE-EQ", key="sim_sym")
                sim_exchange = st.selectbox("Exchange", ["NSE","BSE","NFO","BFO","MCX"], key="sim_exch")
            with f2:
                sim_qty   = st.number_input("Qty", 1, 10000, 5, key="sim_qty")
                sim_ot    = st.selectbox("Order Type", ["MARKET","LIMIT","SL","SL-M"], key="sim_ot")
                sim_price = st.number_input("Price (0=MARKET)", 0.0, step=0.5, key="sim_price")
            sim_strategy = st.text_input("Strategy tag", "TradingView Alert", key="sim_strat")
            payload = {
                "action": sim_action, "symbol": sim_symbol, "exchange": sim_exchange,
                "qty": sim_qty, "order_type": sim_ot, "price": sim_price,
                "strategy": sim_strategy
            }

    with sim_col2:
        if payload:
            st.markdown("**Parsed signal preview:**")
            sig_preview = _process_signal(payload)
            side_color = "#00c853" if sig_preview["action"] == "BUY" else "#ff5252"
            st.markdown(f"""
<div class="webhook-card">
  <span class="sig-badge {'sig-buy' if sig_preview['action']=='BUY' else 'sig-sell'}">{sig_preview['action']}</span>
  <span style="color:#e0e0e0;font-size:.9rem;margin-left:8px;font-weight:700;">{sig_preview['symbol']}</span>
  <span style="color:#8892a4;font-size:.78rem;margin-left:6px;">{sig_preview['exchange']}</span><br>
  <div style="margin-top:.5rem;color:#8892a4;font-size:.78rem;">
    Qty: <b style="color:#e0e0e0;">{sig_preview['qty']}</b> ·
    Type: <b style="color:#e0e0e0;">{sig_preview['order_type']}</b> ·
    Price: <b style="color:#ffd200;">{'MARKET' if sig_preview['price']==0 else f'₹{sig_preview["price"]:,.2f}'}</b>
  </div>
  <div style="margin-top:.3rem;color:#5a6580;font-size:.72rem;">{sig_preview['strategy']}</div>
</div>""", unsafe_allow_html=True)

        auto = st.session_state["webhook_auto_execute"]
        btn_label = "📡 Send & Auto-Execute" if auto else "📡 Send (Log Only)"
        if st.button(btn_label, use_container_width=True, type="primary", key="wh_send"):
            if payload:
                sig = _process_signal(payload, auto_execute=auto)
                st.session_state["webhook_signals"].insert(0, sig)
                if sig["executed"]:
                    st.success(f"Signal executed: {sig['status']}", icon="✅")
                    st.balloons()
                elif sig["error"]:
                    st.error(sig["error"], icon="❌")
                else:
                    st.info("Signal logged (auto-execute is OFF).", icon="📋")
            else:
                st.error("Fix the JSON first.", icon="❌")


# ═══════════════════════════════════════════════════════════════
# TAB 3 – Signal Log
# ═══════════════════════════════════════════════════════════════
with tab_log:
    signals = st.session_state["webhook_signals"]

    lh1, lh2, lh3 = st.columns([5, 2, 2])
    with lh1:
        st.markdown('<div class="rule-header">📋 Received Signals</div>', unsafe_allow_html=True)
    with lh2:
        if st.button("🔄 Refresh", use_container_width=True, key="wh_refresh"):
            # Pull in any signals written by the background server
            file_sigs = _load_file_signals()
            existing_ids = {s["id"] for s in signals}
            new_sigs = [s for s in file_sigs if s.get("id") not in existing_ids]
            if new_sigs:
                auto = st.session_state["webhook_auto_execute"]
                for ns in new_sigs:
                    if auto and not ns.get("executed"):
                        ns = _execute_signal(ns)
                    st.session_state["webhook_signals"].insert(0, ns)
                st.toast(f"{len(new_sigs)} new signal(s) loaded", icon="📡")
            st.rerun()
    with lh3:
        if st.button("🗑️ Clear Log", use_container_width=True, type="secondary", key="wh_clear"):
            st.session_state["webhook_signals"] = []
            _SIGNAL_FILE.write_text("[]")
            st.rerun()

    # Metrics
    total  = len(signals)
    exed   = sum(1 for s in signals if s.get("executed"))
    buys   = sum(1 for s in signals if s.get("action") == "BUY")
    sells  = sum(1 for s in signals if s.get("action") == "SELL")
    failed = sum(1 for s in signals if s.get("status") == "FAILED")

    m1,m2,m3,m4,m5 = st.columns(5)
    with m1: st.metric("Total Signals", total)
    with m2: st.metric("Executed",      exed)
    with m3: st.metric("BUY",           buys)
    with m4: st.metric("SELL",          sells)
    with m5: st.metric("Failed",        failed)

    if not signals:
        st.info("No signals received yet. Use the Simulator tab to test.", icon="📡")
    else:
        for sig in signals[:50]:
            action_cls = "signal-card" if sig["action"] == "BUY" else "signal-card sell"
            badge_cls  = "sig-buy" if sig["action"] == "BUY" else "sig-sell"
            status_color = "#00c853" if sig.get("executed") else ("#ff5252" if sig.get("status")=="FAILED" else "#ffd200")
            err_html = f'<div style="color:#ff5252;font-size:.72rem;margin-top:.2rem;">{sig["error"]}</div>' if sig.get("error") else ""
            st.markdown(f"""
<div class="{action_cls}">
  <div style="display:flex;justify-content:space-between;align-items:start;">
    <div>
      <span class="sig-badge {badge_cls}">{sig['action']}</span>
      <b style="color:#e0e0e0;margin-left:8px;">{sig['symbol']}</b>
      <span style="color:#8892a4;font-size:.78rem;margin-left:6px;">{sig['exchange']} · {sig['qty']} qty</span>
      <span style="color:#8892a4;font-size:.72rem;margin-left:6px;">{sig['order_type']}</span>
    </div>
    <div style="text-align:right;">
      <div style="color:{status_color};font-size:.75rem;font-weight:700;">{sig['status']}</div>
      <div style="color:#5a6580;font-size:.68rem;">{sig['received_at']}</div>
    </div>
  </div>
  <div style="color:#8892a4;font-size:.72rem;margin-top:.2rem;">{sig['strategy']}{' · '+sig['comment'] if sig['comment'] else ''}</div>
  {err_html}
</div>""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════
# TAB 4 – Background Server
# ═══════════════════════════════════════════════════════════════
with tab_srv:
    st.markdown('<div class="rule-header">🖥️ Webhook HTTP Server</div>', unsafe_allow_html=True)
    st.info(
        "**How it works:** A lightweight HTTP server runs on port **8502** to receive POST requests "
        "from TradingView or any external system. Incoming signals are written to a log file and "
        "picked up by this page on next refresh.",
        icon="ℹ️")

    srv_col1, srv_col2 = st.columns(2, gap="large")
    with srv_col1:
        st.markdown("""
<div class="webhook-card">
<b style="color:#ffd200;">Start the webhook server (separate terminal):</b><br><br>
<code>cd groww_autotrader_pro</code><br>
<code>python webhook_receiver.py</code><br><br>
<b style="color:#ffd200;">Expose locally via ngrok:</b><br>
<code>ngrok http 8502</code><br><br>
Then copy the <b style="color:#ffd200;">https://xxxx.ngrok.io</b> URL and
use it as your TradingView webhook URL:<br>
<code>https://xxxx.ngrok.io/webhook</code>
</div>""", unsafe_allow_html=True)

    with srv_col2:
        st.markdown('<div class="rule-header">🧪 Test with curl</div>', unsafe_allow_html=True)
        st.code('''curl -X POST http://localhost:8502/webhook \\
  -H "Content-Type: application/json" \\
  -d \'{"action":"BUY","symbol":"RELIANCE-EQ",
       "exchange":"NSE","qty":5,
       "order_type":"MARKET","price":0}\'
''', language="bash")

        st.markdown('<div class="rule-header">📁 Signal file location</div>', unsafe_allow_html=True)
        st.code(str(_SIGNAL_FILE), language="text")
        if _SIGNAL_FILE.exists():
            st.success(f"Signal file exists ({_SIGNAL_FILE.stat().st_size} bytes)", icon="✅")
        else:
            st.warning("Signal file not yet created (no signals received)", icon="⚠️")

# ── import needed in this file ───────────────────────────────────────────────
import pandas as pd
