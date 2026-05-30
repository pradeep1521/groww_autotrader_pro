"""
Kotak Neo – NeoTrade Platform
==============================
Full-featured dedicated trading UI built on the Kotak Neo API.
  • Zero brokerage on all Trade API orders
  • Auto-TOTP login (no manual code entry)
  • Real-time quotes (REST + WebSocket)
  • All order types: MKT / LIMIT / SL / SL-M
  • GTT orders, option chain, basket orders
"""

import sys, os, time, threading
from datetime import datetime
from pathlib import Path

import streamlit as st
import pandas as pd

_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT / "kotak_neo_python"))

st.set_page_config(
    page_title="Kotak Neo – NeoTrade",
    page_icon="🦁",
    layout="wide",
)

# ─────────────────────────────────────────────────────────────────────────────
# Global CSS  –  dark trading terminal theme
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── Sidebar ── */
[data-testid="stSidebar"] {
  background: linear-gradient(160deg,#1a0a00 0%,#2d1100 50%,#1a0a00 100%);
  border-right: 1px solid #f7971e30;
}
[data-testid="stSidebar"] * { color: #f5c87a !important; }

/* ── Body background ── */
.stApp { background: #0d0d1a; }
.block-container { padding-top: 1.4rem !important; }

/* ── Tabs ── */
[data-testid="stTabs"] [data-baseweb="tab"] {
  background: #12122a;
  border-radius: 8px 8px 0 0;
  padding: 8px 20px;
  color: #8892a4;
  font-weight: 600;
  font-size: .85rem;
  border: 1px solid #ffffff10;
  border-bottom: none;
}
[data-testid="stTabs"] [data-baseweb="tab"][aria-selected="true"] {
  background: #1e1e40;
  color: #ffd200 !important;
  border-color: #ffd20030;
}

/* ── Metric cards ── */
[data-testid="stMetric"] {
  background: #12122a;
  border: 1px solid #ffffff10;
  border-radius: 12px;
  padding: 1rem 1.2rem;
}
[data-testid="stMetricLabel"] { color: #8892a4 !important; font-size:.78rem; }
[data-testid="stMetricValue"] { color: #ffd200 !important; font-size:1.6rem; font-weight:700; }

/* ── Dataframes ── */
[data-testid="stDataFrame"] { border-radius: 10px; overflow: hidden; }

/* ── Buttons ── */
.stButton > button {
  border-radius: 8px;
  font-weight: 600;
  transition: all .2s;
}
.stButton > button:hover { transform: translateY(-1px); box-shadow: 0 4px 12px #ffd20020; }

/* ── Input fields ── */
.stTextInput > div > input,
.stNumberInput > div > input,
.stTextArea > div > textarea,
.stSelectbox > div > div {
  background: #12122a !important;
  border-color: #ffffff15 !important;
  color: #e0e0e0 !important;
  border-radius: 8px !important;
}

/* ── Status badge ── */
.status-live {
  display:inline-flex; align-items:center; gap:6px;
  background:#00c85315; border:1px solid #00c85340;
  color:#00c853; border-radius:20px;
  padding:4px 14px; font-size:.82rem; font-weight:700;
}
.status-offline {
  display:inline-flex; align-items:center; gap:6px;
  background:#ff525215; border:1px solid #ff525240;
  color:#ff5252; border-radius:20px;
  padding:4px 14px; font-size:.82rem; font-weight:700;
}
.dot-live {
  width:8px; height:8px; border-radius:50%;
  background:#00c853; animation: pulse 2s infinite;
}
@keyframes pulse { 0%,100%{opacity:1;} 50%{opacity:.4;} }

/* ── Price panel ── */
.price-panel {
  background: linear-gradient(135deg,#12122a,#1a1a35);
  border:2px solid #ffd20030; border-radius:14px;
  padding:1.4rem 1.8rem; margin-bottom:1rem;
}
.price-panel .sym  { color:#8892a4; font-size:.8rem; font-weight:700; letter-spacing:.05em; }
.price-panel .ltp  { font-size:2.4rem; font-weight:800; color:#ffd200; line-height:1; margin:.3rem 0; }
.price-panel .chg-p{ color:#00c853; font-weight:700; font-size:1rem; }
.price-panel .chg-n{ color:#ff5252; font-weight:700; font-size:1rem; }
.price-panel .row  { display:flex; gap:28px; flex-wrap:wrap; margin-top:.6rem; }
.price-panel .lbl  { color:#8892a4; font-size:.72rem; font-weight:600; text-transform:uppercase; letter-spacing:.04em; }
.price-panel .val  { color:#e0e0e0; font-size:.88rem; font-weight:600; }
.price-panel .bid  { color:#00c853 !important; }
.price-panel .ask  { color:#ff5252 !important; }
.price-panel .ohlc { color:#5a6580; font-size:.72rem; margin-top:.5rem; }

/* ── Order preview card ── */
.order-card {
  background:#12122a; border:1px solid #ffffff12;
  border-radius:12px; padding:1.2rem 1.4rem;
}
.order-card .oc-lbl { color:#8892a4; font-size:.72rem; font-weight:700; letter-spacing:.04em; text-transform:uppercase; }
.order-card .oc-val { color:#e0e0e0; font-size:.95rem; font-weight:600; margin-bottom:.5rem; }
.order-card .oc-buy  { color:#00c853; font-size:1.1rem; font-weight:800; }
.order-card .oc-sell { color:#ff5252; font-size:1.1rem; font-weight:800; }
.order-card .oc-zero { color:#00c853; font-weight:700; }

/* ── Section headers ── */
.sec-header {
  font-size:1.1rem; font-weight:700; color:#ffd200;
  border-left:3px solid #ffd200; padding-left:10px;
  margin: 1rem 0 .6rem;
}

/* ── Info / setup cards ── */
.setup-card {
  background:#12122a; border:1px solid #ffd20020;
  border-radius:12px; padding:1.4rem;
}
.setup-card code {
  background:#1e1e40; color:#ffd200;
  border-radius:4px; padding:2px 6px;
}

/* ── PnL green/red ── */
.pnl-pos { color:#00c853; font-weight:700; }
.pnl-neg { color:#ff5252; font-weight:700; }

/* ── GTT card ── */
.gtt-card {
  background:#12122a; border:1px solid #ffffff12;
  border-radius:10px; padding:1rem 1.2rem; margin-bottom:.5rem;
}

/* ── Chain rows ── */
.atm-row { background:#ffd20015 !important; }

/* Scrollbar ── */
::-webkit-scrollbar { width:4px; height:4px; }
::-webkit-scrollbar-thumb { background:#ffd20040; border-radius:4px; }

/* ── Paper trading ── */
.paper-banner {
  background: linear-gradient(90deg,#1a1a00,#2a2000);
  border:2px solid #ffd20060; border-radius:12px;
  padding:.8rem 1.4rem; margin-bottom:1rem;
  display:flex; align-items:center; gap:12px;
}
.paper-banner .pb-label {
  color:#ffd200; font-weight:800; font-size:.95rem; letter-spacing:.06em;
}
.paper-banner .pb-sub { color:#8892a4; font-size:.78rem; }
.paper-pos-card {
  background:#12122a; border:1px solid #ffd20020;
  border-radius:12px; padding:1.2rem 1.4rem; margin-bottom:.5rem;
}
.paper-pnl-pos { color:#00c853; font-weight:700; font-size:1rem; }
.paper-pnl-neg { color:#ff5252; font-weight:700; font-size:1rem; }
.paper-mode-badge {
  display:inline-flex; align-items:center; gap:6px;
  background:#ffd20018; border:1px solid #ffd20050;
  color:#ffd200; border-radius:20px;
  padding:4px 14px; font-size:.82rem; font-weight:700;
}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Session helpers
# ─────────────────────────────────────────────────────────────────────────────
def _client():
    return st.session_state.get("kotak_client")

def _live() -> bool:
    c = _client()
    return c is not None and c.is_authenticated()

def _paper_mode() -> bool:
    return st.session_state.get("paper_mode", False)

def _paper_positions() -> list:
    return st.session_state.setdefault("paper_positions", [])

def _paper_add(symbol, exchange, side, qty, exec_price, order_type, product):
    """Record a simulated paper trade."""
    pos = _paper_positions()
    # Check if a matching open position exists (same symbol+exchange+side) → add to it
    for p in pos:
        if p["symbol"] == symbol and p["exchange"] == exchange and p["status"] == "OPEN":
            if p["side"] == side:
                # Average in
                total_qty  = p["qty"] + qty
                p["avg_price"] = (p["avg_price"] * p["qty"] + exec_price * qty) / total_qty
                p["qty"] = total_qty
                return
            else:
                # Opposite side → close position
                close_qty = min(p["qty"], qty)
                pnl = (exec_price - p["avg_price"]) * close_qty * (1 if p["side"] == "BUY" else -1)
                p["qty"]     -= close_qty
                p["realized_pnl"] = p.get("realized_pnl", 0) + pnl
                if p["qty"] == 0:
                    p["status"] = "CLOSED"
                remaining = qty - close_qty
                if remaining > 0:
                    pos.append({"symbol": symbol, "exchange": exchange,
                                "side": side, "qty": remaining,
                                "avg_price": exec_price, "ltp": exec_price,
                                "product": product, "order_type": order_type,
                                "status": "OPEN", "realized_pnl": 0.0,
                                "timestamp": datetime.now().strftime("%H:%M:%S")})
                return
    # New position
    pos.append({"symbol": symbol, "exchange": exchange,
                "side": side, "qty": qty,
                "avg_price": exec_price, "ltp": exec_price,
                "product": product, "order_type": order_type,
                "status": "OPEN", "realized_pnl": 0.0,
                "timestamp": datetime.now().strftime("%H:%M:%S")})

# ─────────────────────────────────────────────────────────────────────────────
# Page header
# ─────────────────────────────────────────────────────────────────────────────
h1, h2, h3 = st.columns([5, 2, 1])
with h1:
    st.markdown(
        "<h2 style='color:#ffd200;margin:0;font-weight:800;'>🦁 NeoTrade</h2>"
        "<div style='color:#8892a4;font-size:.85rem;margin-top:2px;'>"
        "Powered by Kotak Neo API · ₹0 brokerage · NSE / BSE / NFO / MCX</div>",
        unsafe_allow_html=True,
    )
with h2:
    if _live():
        user = st.session_state.get("neo_username", "")
        if _paper_mode():
            st.markdown(
                '<div class="paper-mode-badge" style="margin-top:12px;">📝 PAPER MODE</div>',
                unsafe_allow_html=True)
        else:
            st.markdown(
                f'<div class="status-live" style="margin-top:12px;">'
                f'<span class="dot-live"></span> LIVE · {user}</div>',
                unsafe_allow_html=True)
    else:
        st.markdown(
            '<div class="status-offline" style="margin-top:12px;">⚪ Not connected</div>',
            unsafe_allow_html=True)
with h3:
    if _live():
        # Paper mode toggle
        st.session_state["paper_mode"] = st.toggle(
            "📝 Paper",
            value=st.session_state.get("paper_mode", False),
            key="paper_toggle",
            help="Paper mode: orders are simulated with real live prices. No real money at risk.",
        )
        if st.button("Logout", key="main_logout"):
            _client().logout()
            del st.session_state["kotak_client"]
            st.rerun()

st.markdown("<hr style='border-color:#ffffff10;margin:.5rem 0 1rem;'>",
            unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# Tabs
# ─────────────────────────────────────────────────────────────────────────────
TAB_SETUP, TAB_PAPER, TAB_DASH, TAB_TRADE, TAB_GTT, TAB_CHAIN, TAB_QUOTES, TAB_HIST = st.tabs([
    "🔐 Login",
    "📝 Paper Trading",
    "📊 Dashboard",
    "⚡ Trade",
    "⏰ GTT",
    "📈 Option Chain",
    "💹 Quotes",
    "📋 History",
])

# ════════════════════════════════════════════════════════════════════════════
# TAB 1 – LOGIN
# ════════════════════════════════════════════════════════════════════════════
with TAB_SETUP:
    if _live():
        st.markdown(
            f'''<div style="background:#00c85312;border:1px solid #00c85340;border-radius:12px;
            padding:1.2rem 1.6rem;max-width:600px;">
            <div style="color:#00c853;font-size:1.1rem;font-weight:700;">✅ Connected as
            {st.session_state.get("neo_username","")}</div>
            <div style="color:#8892a4;font-size:.85rem;margin-top:.3rem;">
            Session is active. Switch to Dashboard or Trade tab to get started.</div>
            </div>''', unsafe_allow_html=True)
        st.stop()

    st.markdown(
        '<div class="sec-header">Connect Your Kotak Neo Account</div>',
        unsafe_allow_html=True)

    left, right = st.columns([1, 1], gap="large")

    with left:
        st.markdown("""
        <div class="setup-card">
        <b style="color:#ffd200;">What you need:</b><br><br>
        <b style="color:#e0e0e0;">1. Kotak Neo demat account</b><br>
        <span style="color:#8892a4;font-size:.85rem;">Open at kotakneo.com if you don't have one</span><br><br>
        <b style="color:#e0e0e0;">2. Developer Consumer Key</b><br>
        <span style="color:#8892a4;font-size:.85rem;">Create a free app at
        <a href="https://developers.kotaksecurities.com" style="color:#ffd200;">
        developers.kotaksecurities.com</a></span><br><br>
        <b style="color:#e0e0e0;">3. TOTP Seed (base-32 secret)</b><br>
        <span style="color:#8892a4;font-size:.85rem;">Open Google Authenticator → tap Kotak entry →
        "Copy secret".<br>Looks like: <code>JBSWY3DPEHPK3PXP</code></span><br><br>
        <div style="background:#ffd20012;border:1px solid #ffd20030;border-radius:8px;
        padding:.7rem 1rem;margin-top:.5rem;">
        🤖 <b style="color:#ffd200;">Auto-TOTP:</b>
        <span style="color:#e0e0e0;font-size:.85rem;"> The 6-digit code is generated automatically
        every 30s. You never need to enter it manually.</span>
        </div>
        </div>
        """, unsafe_allow_html=True)

    with right:
        env_key  = os.getenv("KOTAK_CONSUMER_KEY", "")
        env_user = os.getenv("KOTAK_USERNAME", "")
        env_seed = os.getenv("KOTAK_TOTP_SEED", "")

        consumer_key = st.text_input("Consumer Key",
            value=st.session_state.get("neo_consumer_key", env_key),
            placeholder="Your developer app consumer key")
        username = st.text_input("User ID",
            value=st.session_state.get("neo_username", env_user),
            placeholder="e.g. AB1234")
        password = st.text_input("Password", type="password",
            placeholder="Kotak Neo login password")
        totp_seed = st.text_input("TOTP Seed",
            type="password",
            value=st.session_state.get("neo_totp_seed", env_seed),
            placeholder="Base-32 secret from authenticator app")

        save_env = st.checkbox("Remember in .env for next session")

        col_a, col_b = st.columns(2)
        with col_a:
            login_btn = st.button("🔐 Login", use_container_width=True, type="primary")
        with col_b:
            test_btn = st.button("🧪 Test TOTP", use_container_width=True)

    if test_btn:
        if not totp_seed:
            st.error("Enter your TOTP seed first.", icon="❌")
        else:
            try:
                import pyotp
                code = pyotp.TOTP(totp_seed.strip().replace(" ", "")).now()
                secs = 30 - (int(time.time()) % 30)
                st.success(f"✅ Seed valid!  Current code: **`{code}`**  (refreshes in {secs}s)", icon="🔢")
            except Exception as e:
                st.error(f"Invalid TOTP seed: {e}", icon="❌")

    if login_btn:
        if not all([consumer_key, username, password, totp_seed]):
            st.error("All four fields are required.", icon="❌")
        else:
            try:
                from kotak_neo.client import KotakNeoClient
                with st.spinner("Authenticating with Kotak Neo…"):
                    c = KotakNeoClient(
                        consumer_key = consumer_key.strip(),
                        username     = username.strip(),
                        password     = password,
                        totp_seed    = totp_seed.strip().replace(" ", ""),
                        auto_refresh = True,
                    )
                    c.login()
                st.session_state.update({
                    "kotak_client":     c,
                    "neo_consumer_key": consumer_key,
                    "neo_username":     username,
                    "neo_totp_seed":    totp_seed,
                })
                if save_env:
                    ep = _ROOT / ".env"
                    lines = ep.read_text().splitlines() if ep.exists() else []
                    upd = {"KOTAK_CONSUMER_KEY": consumer_key.strip(),
                           "KOTAK_USERNAME": username.strip(),
                           "KOTAK_TOTP_SEED": totp_seed.strip().replace(" ", "")}
                    for k, v in upd.items():
                        lines = [f"{k}={v}" if l.startswith(k+"=") else l for l in lines]
                        if k not in [l.split("=")[0] for l in lines if "=" in l]:
                            lines.append(f"{k}={v}")
                    ep.write_text("\n".join(lines) + "\n")
                    st.toast("Credentials saved to .env", icon="💾")
                st.success(f"✅ Logged in as **{username}**", icon="🦁")
                st.balloons()
                st.rerun()
            except ImportError:
                st.error("kotak_neo package not found. Run: `pip install -r kotak_neo_python/requirements.txt`", icon="📦")
            except Exception as exc:
                st.error(f"Login failed: {exc}", icon="❌")


# ════════════════════════════════════════════════════════════════════════════
# TAB 2 – PAPER TRADING
# ════════════════════════════════════════════════════════════════════════════
with TAB_PAPER:
    if not _live():
        st.markdown(
            '''<div style="background:#ff525210;border:1px solid #ff525230;border-radius:10px;
            padding:1rem 1.4rem;max-width:500px;">
            🔐 <b style="color:#ff5252;">Authentication required.</b>
            <span style="color:#8892a4;"> Login first – paper trading uses your real Kotak Neo
            live prices, but no real money is ever placed.</span></div>''',
            unsafe_allow_html=True)
        st.stop()

    client = _client()

    # ── Banner ───────────────────────────────────────────────────────────────
    st.markdown("""
<div class="paper-banner">
  <div style="font-size:2rem;">📝</div>
  <div>
    <div class="pb-label">PAPER TRADING MODE</div>
    <div class="pb-sub">
      Orders are <b style="color:#ffd200;">simulated</b> using real Kotak Neo live prices.
      No real money. No exchange submission. Perfect for strategy testing.
    </div>
  </div>
</div>""", unsafe_allow_html=True)

    # ── Master switch ────────────────────────────────────────────────────────
    pm_col, _, reset_col = st.columns([3, 4, 2])
    with pm_col:
        st.session_state["paper_mode"] = st.toggle(
            "📝 Enable Paper Trading Mode",
            value=st.session_state.get("paper_mode", False),
            key="paper_tab_toggle",
            help="When ON, the Trade tab simulates orders instead of sending them to the exchange.")
    with reset_col:
        if st.button("🗑️ Reset Portfolio", use_container_width=True, type="secondary",
                     help="Clear all simulated positions and P&L"):
            st.session_state["paper_positions"] = []
            st.success("Paper portfolio reset.", icon="✅")
            st.rerun()

    if _paper_mode():
        st.info("🟡 **Paper mode is ON.** Switch to the ⚡ Trade tab to place simulated orders.", icon="📝")
    else:
        st.warning("Paper mode is **OFF**. Toggle above to activate, then trade in the ⚡ Trade tab.", icon="⚠️")

    st.markdown("<hr style='border-color:#ffffff10;margin:.8rem 0;'>", unsafe_allow_html=True)

    positions = _paper_positions()
    open_pos  = [p for p in positions if p["status"] == "OPEN"]
    closed_pos = [p for p in positions if p["status"] == "CLOSED"]

    # ── Fetch live LTPs for all open positions ───────────────────────────────
    def _refresh_paper_ltps():
        for p in open_pos:
            try:
                qs = client.get_quote([f'{p["exchange"]}:{p["symbol"]}'])
                if qs:
                    p["ltp"] = float(getattr(qs[0], "ltp", p["ltp"]) or p["ltp"])
            except:
                pass

    # ── Portfolio summary metrics ────────────────────────────────────────────
    ph1, ph2, ph3 = st.columns([5, 2, 2])
    with ph1:
        st.markdown('<div class="sec-header">Paper Portfolio</div>', unsafe_allow_html=True)
    with ph2:
        if st.button("📡 Refresh LTPs", use_container_width=True, key="paper_refresh"):
            _refresh_paper_ltps()
            st.toast("Live prices updated.", icon="📡")

    if not open_pos and not closed_pos:
        st.markdown("""
<div style="background:#12122a;border:1px solid #ffd20020;border-radius:12px;
padding:2rem;text-align:center;">
  <div style="font-size:2.5rem;">📝</div>
  <div style="color:#8892a4;margin-top:.5rem;">No paper trades yet.</div>
  <div style="color:#5a6580;font-size:.82rem;margin-top:.3rem;">
    Enable paper mode above, then go to the ⚡ Trade tab and place a simulated order.
  </div>
</div>""", unsafe_allow_html=True)
    else:
        # Summary row
        total_unrealised = 0.0
        total_realised   = 0.0
        for p in open_pos:
            mult = 1 if p["side"] == "BUY" else -1
            total_unrealised += (p["ltp"] - p["avg_price"]) * p["qty"] * mult
        for p in positions:
            total_realised += p.get("realized_pnl", 0.0)

        total_pnl = total_unrealised + total_realised
        m1, m2, m3, m4 = st.columns(4)
        with m1: st.metric("📂 Open Positions", len(open_pos))
        with m2: st.metric("✅ Closed Trades",  len(closed_pos))
        with m3:
            st.metric("📈 Unrealised P&L",
                      f"₹{total_unrealised:+,.2f}",
                      delta=f"{total_unrealised:+,.2f}")
        with m4:
            st.metric("💰 Total P&L (incl. closed)",
                      f"₹{total_pnl:+,.2f}",
                      delta=f"{total_pnl:+,.2f}")

        st.markdown("<div style='height:.5rem;'></div>", unsafe_allow_html=True)

        # ── Open positions table ─────────────────────────────────────────────
        if open_pos:
            st.markdown('<div class="sec-header">Open Paper Positions</div>', unsafe_allow_html=True)
            rows = []
            for p in open_pos:
                mult   = 1 if p["side"] == "BUY" else -1
                unreal = (p["ltp"] - p["avg_price"]) * p["qty"] * mult
                unreal_pct = (unreal / (p["avg_price"] * p["qty"])) * 100 if p["avg_price"] else 0
                pnl_str = f"₹{unreal:+,.2f}  ({unreal_pct:+.2f}%)"
                rows.append({
                    "Symbol":       p["symbol"],
                    "Exchange":     p["exchange"],
                    "Side":         p["side"],
                    "Qty":          p["qty"],
                    "Avg Price":    f"₹{p['avg_price']:,.2f}",
                    "LTP":          f"₹{p['ltp']:,.2f}",
                    "Unrealised P&L": pnl_str,
                    "Product":      p["product"],
                    "Entered":      p["timestamp"],
                })
            df = pd.DataFrame(rows)
            st.dataframe(df, hide_index=True, use_container_width=True)

            # Quick close button
            st.markdown('<div class="sec-header" style="font-size:.9rem;">Quick Close Position</div>',
                        unsafe_allow_html=True)
            qc1, qc2, qc3 = st.columns([3, 2, 2])
            with qc1:
                close_sym = st.selectbox(
                    "Position",
                    [f'{p["side"]} {p["qty"]} {p["symbol"]} @ {p["exchange"]}'
                     for p in open_pos],
                    key="paper_close_sel",
                    label_visibility="collapsed",
                )
            with qc2:
                close_idx = [f'{p["side"]} {p["qty"]} {p["symbol"]} @ {p["exchange"]}'
                             for p in open_pos].index(close_sym)
                close_pos_obj = open_pos[close_idx]
                # Get live price for closing
                try:
                    cqs = client.get_quote([f'{close_pos_obj["exchange"]}:{close_pos_obj["symbol"]}'])
                    close_ltp = float(getattr(cqs[0], "ltp", close_pos_obj["ltp"]) or close_pos_obj["ltp"]) if cqs else close_pos_obj["ltp"]
                except:
                    close_ltp = close_pos_obj["ltp"]
                st.markdown(f"<div style='color:#ffd200;font-size:.9rem;padding-top:8px;'>"
                            f"LTP: ₹{close_ltp:,.2f}</div>", unsafe_allow_html=True)
            with qc3:
                if st.button("🔴 Close at LTP", use_container_width=True, key="paper_close_btn"):
                    opposite = "SELL" if close_pos_obj["side"] == "BUY" else "BUY"
                    _paper_add(
                        close_pos_obj["symbol"], close_pos_obj["exchange"],
                        opposite, close_pos_obj["qty"], close_ltp,
                        "MARKET", close_pos_obj["product"])
                    st.success(
                        f"✅ Closed {close_pos_obj['qty']} × {close_pos_obj['symbol']} "
                        f"@ ₹{close_ltp:,.2f}", icon="📝")
                    st.rerun()

        # ── Closed trades table ──────────────────────────────────────────────
        if closed_pos:
            st.markdown('<div class="sec-header">Closed Paper Trades</div>', unsafe_allow_html=True)
            crows = []
            for p in closed_pos:
                crows.append({
                    "Symbol":       p["symbol"],
                    "Exchange":     p["exchange"],
                    "Side":         p["side"],
                    "Realised P&L": f"₹{p.get('realized_pnl',0):+,.2f}",
                    "Product":      p["product"],
                    "Closed":       p["timestamp"],
                })
            st.dataframe(pd.DataFrame(crows), hide_index=True, use_container_width=True)


# ════════════════════════════════════════════════════════════════════════════
# TAB 3 – DASHBOARD
# ════════════════════════════════════════════════════════════════════════════
with TAB_DASH:
    if not _live():
        st.markdown(
            '''<div style="background:#ff525210;border:1px solid #ff525230;border-radius:10px;
            padding:1rem 1.4rem;max-width:440px;">
            🔐 <b style="color:#ff5252;">Not connected.</b>
            <span style="color:#8892a4;"> Go to the <b>Login</b> tab first.</span></div>''',
            unsafe_allow_html=True)
        st.stop()

    client = _client()

    dh1, dh2 = st.columns([5, 1])
    with dh1:
        st.markdown('<div class="sec-header">Account Overview</div>', unsafe_allow_html=True)
    with dh2:
        if st.button("🔄 Refresh", key="dash_ref", use_container_width=True):
            st.rerun()

    # Margins row
    try:
        m = client.get_margins()
        c1, c2, c3, c4 = st.columns(4)
        with c1: st.metric("💰 Available Cash",   f"₹{m.available_cash:,.0f}")
        with c2: st.metric("📊 Available Margin", f"₹{m.available_margin:,.0f}")
        with c3: st.metric("🔒 Used Margin",       f"₹{m.used_margin:,.0f}")
        with c4: st.metric("💼 Total Equity",      f"₹{m.total_equity:,.0f}")
    except Exception as e:
        st.error(f"Margin fetch failed: {e}", icon="⚠️")

    st.markdown("<div style='height:.8rem;'></div>", unsafe_allow_html=True)

    d1, d2, d3 = st.tabs(["📈 Positions", "🏛️ Holdings", "📋 Orders"])

    with d1:
        try:
            pos = client.get_positions()
            if not pos:
                st.info("No open positions today.", icon="📭")
            else:
                total_pnl = 0
                rows = []
                for p in pos:
                    total_pnl += p.pnl
                    rows.append({
                        "Symbol":   p.trading_symbol,
                        "Exch":     p.exchange,
                        "Side":     p.side,
                        "Qty":      p.quantity,
                        "Avg":     f"₹{p.avg_price:.2f}",
                        "LTP":     f"₹{p.ltp:.2f}",
                        "P&L":     f"₹{p.pnl:,.2f}",
                        "Product":  p.product,
                    })
                df = pd.DataFrame(rows)
                # Colour P&L cells
                def _colour_pnl(val):
                    try:
                        v = float(str(val).replace(",","").replace("₹",""))
                        return "color:#00c853;font-weight:700" if v>=0 else "color:#ff5252;font-weight:700"
                    except: return ""
                st.dataframe(
                    df.style.applymap(_colour_pnl, subset=["P&L"]),
                    hide_index=True, use_container_width=True)
                col_pnl, _ = st.columns([1, 4])
                with col_pnl:
                    st.metric("Total Unrealised P&L", f"₹{total_pnl:,.2f}",
                              delta_color="normal" if total_pnl>=0 else "inverse")
        except Exception as e:
            st.error(f"Positions error: {e}", icon="⚠️")

    with d2:
        try:
            hld = client.get_holdings()
            if not hld:
                st.info("No demat holdings.", icon="📭")
            else:
                rows = [{"Symbol": h.trading_symbol, "Qty": h.quantity,
                         "Avg Cost": f"₹{h.avg_price:.2f}", "LTP": f"₹{h.ltp:.2f}",
                         "P&L": f"₹{h.pnl:,.2f}", "P&L %": f"{h.pnl_pct:+.2f}%",
                         "Pledged": h.pledged_qty} for h in hld]
                st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
        except Exception as e:
            st.error(f"Holdings error: {e}", icon="⚠️")

    with d3:
        try:
            orders = client.get_order_book()
            if not orders:
                st.info("No orders today.", icon="📭")
            else:
                rows = []
                for o in orders:
                    rows.append({"ID": o.order_id, "Symbol": o.trading_symbol,
                        "Side": o.side, "Qty": o.quantity,
                        "Price": f"₹{o.price:.2f}" if o.price else "MKT",
                        "Type": o.order_type, "Product": o.product,
                        "Status": str(getattr(o.status, "value", o.status)),
                        "Time": str(o.order_timestamp)[:16] if o.order_timestamp else "—"})
                st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

                open_ids = [o.order_id for o in orders
                            if str(getattr(o.status,"value",o.status)).upper()
                            in ("OPEN","TRIGGER PENDING")]
                if open_ids:
                    st.markdown('<div class="sec-header">Cancel Order</div>', unsafe_allow_html=True)
                    cid = st.selectbox("Select open order", open_ids, key="dash_cancel_sel")
                    if st.button("❌ Cancel", key="dash_cancel_btn", type="secondary"):
                        try:
                            client.cancel_order(cid)
                            st.success(f"Order {cid} cancelled.", icon="✅")
                            st.rerun()
                        except Exception as ce:
                            st.error(str(ce), icon="❌")
        except Exception as e:
            st.error(f"Orders error: {e}", icon="⚠️")


# ════════════════════════════════════════════════════════════════════════════
# TAB 3 – TRADE
# ════════════════════════════════════════════════════════════════════════════
with TAB_TRADE:
    if not _live():
        st.markdown(
            '''<div style="background:#ff525210;border:1px solid #ff525230;border-radius:10px;
            padding:1rem 1.4rem;max-width:440px;">
            🔐 <b style="color:#ff5252;">Not connected.</b>
            <span style="color:#8892a4;"> Login first.</span></div>''',
            unsafe_allow_html=True)
        st.stop()

    client = _client()

    def _quote_for(symbol, exchange):
        try:
            qs = client.get_quote([f"{exchange}:{symbol}"])
            if qs:
                q = qs[0]
                ltp   = float(getattr(q,"ltp",0) or 0)
                bid   = float(getattr(q,"bid",0) or 0)
                ask   = float(getattr(q,"ask",0) or 0)
                open_ = float(getattr(q,"open",0) or 0)
                high  = float(getattr(q,"high",0) or 0)
                low   = float(getattr(q,"low",0) or 0)
                close = float(getattr(q,"close",0) or 0)
                vol   = int(float(getattr(q,"volume",0) or 0))
                oi    = int(float(getattr(q,"oi",0) or 0))
                chg   = ltp - close if close else 0.0
                chgp  = chg/close*100 if close else 0.0
                return dict(ltp=ltp, bid=bid, ask=ask, open=open_,
                            high=high, low=low, close=close,
                            volume=vol, oi=oi, change=chg, change_pct=chgp)
        except: pass
        return None

    POPULAR = ["RELIANCE-EQ","TCS-EQ","INFY-EQ","HDFCBANK-EQ","ICICIBANK-EQ",
               "SBIN-EQ","WIPRO-EQ","LT-EQ","AXISBANK-EQ","BAJFINANCE-EQ",
               "KOTAKBANK-EQ","MARUTI-EQ","TITAN-EQ","NESTLEIND-EQ","ASIANPAINT-EQ"]

    st.markdown('<div class="sec-header">Place Order – ₹0 Brokerage</div>', unsafe_allow_html=True)

    # ── Row 1: symbol selector + exchange + product + fetch button ──────────
    r1, r2, r3, r4 = st.columns([3, 2, 2, 2])
    with r1:
        sym_mode = st.radio("Symbol mode", ["Popular", "Custom"], horizontal=True, label_visibility="collapsed", key="tr_sym_mode")
        if sym_mode == "Popular":
            symbol = st.selectbox("Symbol", POPULAR, key="tr_sym_pop", label_visibility="collapsed")
        else:
            symbol = st.text_input("Custom Symbol", placeholder="e.g. NIFTY25JUN2424800CE", key="tr_sym_custom", label_visibility="collapsed")
    with r2:
        exchange = st.selectbox("Exchange", ["NSE","BSE","NFO","BFO","MCX","CDS"], key="tr_exch")
    with r3:
        product  = st.selectbox("Product", ["MIS – Intraday","CNC – Delivery","NRML – F&O"], key="tr_prod")
        product_code = product.split()[0]
    with r4:
        st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)
        fetch_btn = st.button("📡 Get Live Price", use_container_width=True, key="tr_fetch", type="secondary")

    if fetch_btn and symbol:
        with st.spinner("Fetching…"):
            qq = _quote_for(symbol, exchange)
        if qq:
            st.session_state["tr_quote"]    = qq
            st.session_state["tr_quote_sym"]= symbol
        else:
            st.session_state["tr_quote"]    = {"ltp":243.50,"bid":243.25,"ask":243.75,
                                                "open":235.,"high":255.,"low":230.,"close":238.,
                                                "volume":125000,"oi":4500000,"change":5.5,"change_pct":2.31}
            st.session_state["tr_quote_sym"]= symbol
            st.toast("Live price unavailable – showing demo data", icon="🟡")

    # ── Price Panel ──────────────────────────────────────────────────────────
    q     = st.session_state.get("tr_quote")
    q_sym = st.session_state.get("tr_quote_sym","")
    if q and q_sym:
        cs = "chg-p" if q["change"]>=0 else "chg-n"
        sg = "+" if q["change"]>=0 else ""
        st.markdown(f"""
<div class="price-panel">
  <div class="sym">📡 {q_sym} · {exchange} · LIVE</div>
  <div style="display:flex;align-items:baseline;gap:14px;margin:.3rem 0;">
    <div class="ltp">₹{q["ltp"]:,.2f}</div>
    <div class="{cs}">{sg}{q["change"]:.2f} ({sg}{q["change_pct"]:.2f}%)</div>
  </div>
  <div class="row">
    <div><div class="lbl">Bid</div><div class="val bid">₹{q["bid"]:,.2f}</div></div>
    <div><div class="lbl">Ask</div><div class="val ask">₹{q["ask"]:,.2f}</div></div>
    <div><div class="lbl">Spread</div><div class="val">₹{abs(q["ask"]-q["bid"]):.2f}</div></div>
    <div><div class="lbl">OI</div><div class="val">{q["oi"]:,}</div></div>
    <div><div class="lbl">Volume</div><div class="val">{q["volume"]:,}</div></div>
  </div>
  <div class="ohlc">O ₹{q["open"]:,.2f} &nbsp;H ₹{q["high"]:,.2f} &nbsp;L ₹{q["low"]:,.2f} &nbsp;C ₹{q["close"]:,.2f}</div>
</div>""", unsafe_allow_html=True)

    # ── Order form + preview ─────────────────────────────────────────────────
    form_col, prev_col = st.columns([3, 2], gap="large")

    with form_col:
        with st.form("neo_order_form"):
            fc1, fc2 = st.columns(2)
            with fc1:
                side        = st.radio("Side", ["BUY","SELL"], horizontal=True)
                order_type  = st.selectbox("Order Type", ["MARKET","LIMIT","SL","SL-M"])
                validity    = st.selectbox("Validity", ["DAY","IOC"])
            with fc2:
                qty     = st.number_input("Quantity", min_value=1, value=1, step=1)
                default_px = (q["ltp"] if q and order_type not in ("MARKET","SL-M") else 0.0)
                price   = st.number_input("Price (₹)  — 0 for MARKET", min_value=0.0,
                                          value=default_px, step=0.05,
                                          help="Auto-filled from live LTP")
                trig    = (st.number_input("Trigger Price (₹)", min_value=0.0, value=0.0, step=0.05)
                           if order_type in ("SL","SL-M") else 0.0)

            confirm  = st.checkbox("✅  I confirm the order details")
            place_btn = st.form_submit_button(
                f"{'🟢 BUY' if side=='BUY' else '🔴 SELL'} {qty} × {symbol or '?'} @ {order_type}",
                type="primary", use_container_width=True, disabled=not confirm)

    with prev_col:
        ltp = q["ltp"] if q else 0
        use_p = price if price > 0 else ltp
        est_val = use_p * qty if use_p else 0
        side_cl = "oc-buy" if side == "BUY" else "oc-sell"
        paper_badge = (
            '<div style="background:#ffd20018;border:1px solid #ffd20050;border-radius:8px;'
            'padding:4px 10px;color:#ffd200;font-size:.75rem;font-weight:700;'
            'display:inline-block;margin-bottom:.6rem;">📝 PAPER SIMULATION – no real money</div>'
        ) if _paper_mode() else ""
        st.markdown(f"""
<div class="order-card">
  {paper_badge}
  <div style="margin-bottom:.8rem;">
    <span class="{side_cl}">{side}</span>
    <span style="background:#ffffff12;border-radius:6px;padding:2px 8px;
    font-size:.75rem;color:#8892a4;margin-left:8px;">{order_type}</span>
  </div>
  <div class="oc-lbl">Symbol</div><div class="oc-val">{symbol or "—"}</div>
  <div class="oc-lbl">Exchange · Product</div>
  <div class="oc-val">{exchange} · {product_code}</div>
  <div class="oc-lbl">Quantity</div><div class="oc-val">{qty:,}</div>
  <div class="oc-lbl">{"LTP (MARKET)" if order_type == "MARKET" else "Limit Price"}</div>
  <div class="oc-val">₹{use_p:,.2f}</div>
  <div class="oc-lbl">Estimated Value</div>
  <div class="oc-val" style="font-size:1.1rem;color:#ffd200;">₹{est_val:,.2f}</div>
  <div style="margin-top:.8rem;padding-top:.8rem;border-top:1px solid #ffffff10;">
    <span class="oc-lbl">Brokerage: </span>
    <span class="oc-zero" style="font-size:.9rem;">₹0.00</span>
  </div>
</div>""", unsafe_allow_html=True)

        # Margin check (skip in paper mode – no real margin consumed)
        if not _paper_mode():
            try:
                m = client.get_margins()
                req = use_p * qty * 0.2
                if m.available_margin < req:
                    st.warning(f"Low margin: ₹{m.available_margin:,.0f} available", icon="⚠️")
                else:
                    st.success(f"Margin OK: ₹{m.available_margin:,.0f}", icon="✅")
            except: pass
        else:
            st.info("No real margin consumed in paper mode.", icon="📝")

    # ── Paper mode banner (shown in Trade tab) ────────────────────────────
    if _paper_mode():
        st.markdown("""
<div class="paper-banner" style="margin-bottom:.6rem;">
  <div style="font-size:1.4rem;">📝</div>
  <div>
    <span class="pb-label">PAPER MODE ACTIVE</span>
    <span class="pb-sub" style="margin-left:10px;">
      Orders below will be <b style="color:#ffd200;">simulated</b> using the live price —
      no real money will be placed. Switch off in the 📝 Paper Trading tab.
    </span>
  </div>
</div>""", unsafe_allow_html=True)

    # ── Execute ────────────────────────────────────────────────────────────
    if place_btn:
        if not symbol:
            st.error("Select or enter a symbol.", icon="❌")
        elif _paper_mode():
            # ── PAPER EXECUTION ──────────────────────────────────────────
            with st.spinner("Fetching live price for simulation…"):
                live_q = _quote_for(symbol, exchange)
            if live_q:
                exec_price = live_q["ltp"]
            elif price > 0:
                exec_price = price
                st.toast("Live price unavailable – using entered price for simulation", icon="🟡")
            else:
                st.error("Cannot simulate: no live price and no limit price entered.", icon="❌")
                exec_price = None

            if exec_price:
                _paper_add(symbol, exchange, side, qty, exec_price, order_type, product_code)
                pnl_side = "bought" if side == "BUY" else "sold"
                st.success(
                    f"📝 **Paper order simulated!**  {side} {qty} × **{symbol}** "
                    f"@ ₹{exec_price:,.2f}  ·  {pnl_side} for ₹{exec_price*qty:,.2f}  ·  "
                    f"No real money placed.",
                    icon="📝")
                st.balloons()
                st.session_state.pop("tr_quote", None)
                st.session_state.pop("tr_quote_sym", None)
        else:
            # ── REAL EXECUTION ────────────────────────────────────────────
            pre = _quote_for(symbol, exchange)
            if pre and order_type == "LIMIT" and price > 0:
                dev = abs(price - pre["ltp"]) / pre["ltp"] * 100
                if dev > 5:
                    st.warning(f"⚠️ Limit ₹{price:.2f} is {dev:.1f}% from LTP ₹{pre['ltp']:.2f}")
            try:
                from kotak_neo.models import Order, OrderSide, OrderType as NeoOT, ProductType, Exchange as NeoEx, Validity as NeoVal
                _SIDE = {"BUY": OrderSide.BUY, "SELL": OrderSide.SELL}
                _OT   = {"MARKET": NeoOT.MARKET, "LIMIT": NeoOT.LIMIT,
                         "SL": NeoOT.STOP_LOSS, "SL-M": NeoOT.STOP_LOSS_M}
                _PROD = {"MIS": ProductType.MIS, "CNC": ProductType.CNC, "NRML": ProductType.NRML}
                _EX   = {"NSE": NeoEx.NSE, "BSE": NeoEx.BSE, "NFO": NeoEx.NFO,
                         "BFO": NeoEx.BFO, "MCX": NeoEx.MCX, "CDS": NeoEx.CDS}
                _VAL  = {"DAY": NeoVal.DAY, "IOC": NeoVal.IOC}
                order = Order(
                    exchange=_EX[exchange], trading_symbol=symbol,
                    side=_SIDE[side], order_type=_OT[order_type],
                    product=_PROD[product_code], quantity=qty,
                    price=price, trigger_price=trig, validity=_VAL[validity])
                with st.spinner("Sending to exchange…"):
                    resp = client.place_order(order)
                st.success(f"✅ Order placed! ID: **`{resp.order_id}`** · {resp.status}", icon="🎯")
                st.balloons()
                st.session_state.pop("tr_quote", None)
                st.session_state.pop("tr_quote_sym", None)
            except Exception as exc:
                st.error(f"Order failed: {exc}", icon="❌")


# ════════════════════════════════════════════════════════════════════════════
# TAB 4 – GTT
# ════════════════════════════════════════════════════════════════════════════
with TAB_GTT:
    if not _live():
        st.markdown('<div style="color:#ff5252;">🔐 Login required.</div>', unsafe_allow_html=True)
        st.stop()
    client = _client()
    st.markdown('<div class="sec-header">GTT – Good Till Triggered Orders</div>', unsafe_allow_html=True)
    st.caption("Set-and-forget orders that fire when price hits your target. Persist across sessions until filled or cancelled.")

    g1, g2 = st.tabs(["➕ Create GTT", "📋 Active GTTs"])

    with g1:
        gc1, gc2 = st.columns(2)
        with gc1:
            gtt_sym  = st.text_input("Symbol", "RELIANCE-EQ", key="gtt_sym")
            gtt_side = st.selectbox("Side", ["BUY","SELL"], key="gtt_side")
            gtt_qty  = st.number_input("Quantity", min_value=1, value=10, key="gtt_qty")
            gtt_exch = st.selectbox("Exchange", ["NSE","BSE","NFO"], key="gtt_exch")
        with gc2:
            gtt_trig = st.number_input("Trigger Price (₹)", min_value=0.0, value=2300.0, step=0.5, key="gtt_trig")
            gtt_lmt  = st.number_input("Limit Price (₹)", min_value=0.0, value=2295.0, step=0.5, key="gtt_lmt")
            st.markdown(f"""
<div class="order-card" style="margin-top:.5rem;">
  <div class="oc-lbl">When {gtt_sym} hits</div>
  <div class="oc-val">₹{gtt_trig:,.2f}</div>
  <div class="oc-lbl">Execute</div>
  <div class="oc-val">{gtt_side} {gtt_qty} @ ₹{gtt_lmt:,.2f}</div>
</div>""", unsafe_allow_html=True)

        if st.button("⏰ Create GTT Order", type="primary", use_container_width=True):
            try:
                from kotak_neo.models import GTTOrder
                r = client.place_gtt_order(GTTOrder(
                    symbol=gtt_sym, exchange=gtt_exch, side=gtt_side,
                    quantity=gtt_qty, trigger_price=gtt_trig, limit_price=gtt_lmt))
                st.success(f"✅ GTT created: {r}", icon="⏰")
            except Exception as ge:
                st.error(f"GTT failed: {ge}", icon="❌")

    with g2:
        rr, _ = st.columns([1,5])
        with rr:
            if st.button("🔄 Refresh", key="gtt_ref"):
                st.rerun()
        try:
            gtts = client.get_gtt_orders()
            if not gtts:
                st.info("No active GTT orders.", icon="📭")
            else:
                for g in gtts:
                    gid = g.get("id", g.get("gttId","?"))
                    sym = g.get("trdSym","")
                    trp = g.get("triggerPrice","?")
                    with st.expander(f"GTT {gid} · {sym} · Trigger ₹{trp}"):
                        st.json(g)
                        if st.button(f"❌ Cancel GTT {gid}", key=f"cgtt_{gid}"):
                            try:
                                client.cancel_gtt_order(gid)
                                st.success(f"Cancelled {gid}", icon="✅")
                                st.rerun()
                            except Exception as ce:
                                st.error(str(ce), icon="❌")
        except Exception as ge:
            st.error(f"GTT load error: {ge}", icon="⚠️")


# ════════════════════════════════════════════════════════════════════════════
# TAB 5 – OPTION CHAIN
# ════════════════════════════════════════════════════════════════════════════
with TAB_CHAIN:
    if not _live():
        st.markdown('<div style="color:#ff5252;">🔐 Login required.</div>', unsafe_allow_html=True)
        st.stop()
    client = _client()
    st.markdown('<div class="sec-header">Option Chain</div>', unsafe_allow_html=True)

    oc1, oc2, oc3, oc4 = st.columns(4)
    with oc1:
        oc_sym = st.selectbox("Underlying", ["NIFTY","BANKNIFTY","FINNIFTY","MIDCPNIFTY",
                                              "RELIANCE","TCS","INFY","HDFCBANK"])
    with oc2:
        oc_exp = st.text_input("Expiry", value="26-Jun-2025", placeholder="DD-Mon-YYYY")
    with oc3:
        oc_type = st.selectbox("Option Type", ["ALL","CE","PE"])
    with oc4:
        st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)
        fetch_chain = st.button("📡 Fetch Chain", use_container_width=True, type="primary")

    if fetch_chain:
        try:
            with st.spinner(f"Fetching {oc_sym} chain…"):
                chain = client.get_option_chain(oc_sym, oc_exp, oc_type)
            if not chain:
                st.warning("No data returned. Check symbol/expiry.", icon="⚠️")
            else:
                st.success(f"Fetched {len(chain)} strikes.", icon="✅")
                rows = [{"Strike": s.get("strikePrice",s.get("strike","")),
                         "Type":   s.get("optionType", s.get("type","")),
                         "LTP":    s.get("ltp",""),
                         "IV %":   s.get("iv",""),
                         "OI":     s.get("oi",s.get("openInterest","")),
                         "Δ OI":   s.get("oiChange",""),
                         "Vol":    s.get("volume",""),
                         "Bid":    s.get("bid",""),
                         "Ask":    s.get("ask",""),
                         "Symbol": s.get("trdSym",s.get("symbol",""))} for s in chain]
                df = pd.DataFrame(rows)
                st.dataframe(df, hide_index=True, use_container_width=True)

                st.markdown('<div class="sec-header">Quick Buy from Chain</div>', unsafe_allow_html=True)
                syms = [r["Symbol"] for r in rows if r["Symbol"]]
                if syms:
                    sel_sym = st.selectbox("Strike symbol", syms, key="oc_buy_sym")
                    sel_qty = st.number_input("Quantity", min_value=1, value=75, key="oc_buy_qty")
                    if st.button("⚡ Buy MKT · NRML · NFO", type="primary", key="oc_buy_btn"):
                        try:
                            from kotak_neo.models import Order, OrderSide, OrderType as NeoOT, ProductType, Exchange as NeoEx, Validity as NeoVal
                            order = Order(exchange=NeoEx.NFO, trading_symbol=sel_sym,
                                         side=OrderSide.BUY, order_type=NeoOT.MARKET,
                                         product=ProductType.NRML, quantity=sel_qty,
                                         validity=NeoVal.DAY)
                            resp = client.place_order(order)
                            st.success(f"✅ {resp.order_id} · {resp.status}", icon="🎯")
                        except Exception as be:
                            st.error(str(be), icon="❌")
        except Exception as oce:
            st.error(f"Option chain error: {oce}", icon="⚠️")


# ════════════════════════════════════════════════════════════════════════════
# TAB 6 – LIVE QUOTES
# ════════════════════════════════════════════════════════════════════════════
with TAB_QUOTES:
    if not _live():
        st.markdown('<div style="color:#ff5252;">🔐 Login required.</div>', unsafe_allow_html=True)
        st.stop()
    client = _client()
    st.markdown('<div class="sec-header">Live Quotes</div>', unsafe_allow_html=True)

    q1, q2 = st.columns([4, 1])
    with q1:
        quote_input = st.text_area("Symbols — one per line (EXCHANGE:SYMBOL)",
            value="NSE:RELIANCE-EQ\nNSE:TCS-EQ\nNSE:INFY-EQ\nNSE:HDFCBANK-EQ\nNSE:SBIN-EQ",
            height=120, help="e.g. NSE:RELIANCE-EQ · NFO:NIFTY25JUN2424800CE")
    with q2:
        auto_ref     = st.checkbox("Auto-refresh 5s")
        fetch_quotes = st.button("📡 Fetch", use_container_width=True, type="primary")

    if fetch_quotes or auto_ref:
        tokens = [t.strip() for t in quote_input.splitlines() if t.strip()]
        if tokens:
            try:
                with st.spinner("Fetching…"):
                    qs = client.get_quote(tokens)
                if not qs:
                    st.warning("No quotes returned.", icon="⚠️")
                else:
                    rows = []
                    for qr in qs:
                        sign = "▲" if qr.change >= 0 else "▼"
                        rows.append({
                            "Symbol":   qr.trading_symbol,
                            "LTP":     f"₹{qr.ltp:,.2f}",
                            "Change":  f"{sign} {abs(qr.change):.2f} ({qr.change_pct:+.2f}%)",
                            "Open":    f"₹{qr.open:,.2f}",
                            "High":    f"₹{qr.high:,.2f}",
                            "Low":     f"₹{qr.low:,.2f}",
                            "Close":   f"₹{qr.close:,.2f}",
                            "Volume":  f"{qr.volume:,}",
                            "Bid":     f"₹{qr.bid:,.2f}",
                            "Ask":     f"₹{qr.ask:,.2f}",
                        })
                    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
                    st.caption(f"Updated: {datetime.now():%H:%M:%S}")
            except Exception as qe:
                st.error(f"Quote error: {qe}", icon="⚠️")
        if auto_ref:
            time.sleep(5)
            st.rerun()


# ════════════════════════════════════════════════════════════════════════════
# TAB 7 – TRADE HISTORY
# ════════════════════════════════════════════════════════════════════════════
with TAB_HIST:
    if not _live():
        st.markdown('<div style="color:#ff5252;">🔐 Login required.</div>', unsafe_allow_html=True)
        st.stop()
    client = _client()
    st.markdown('<div class="sec-header">Today\'s Trade History</div>', unsafe_allow_html=True)

    rh, _ = st.columns([1, 5])
    with rh:
        if st.button("🔄 Refresh", key="hist_ref"):
            st.rerun()

    try:
        trades = client.get_trade_book()
        if not trades:
            st.info("No trades executed today.", icon="📭")
        else:
            rows = [{"Order ID": t.get("nOrdNo",""), "Symbol": t.get("trdSym",""),
                     "Side": t.get("trnsTp",""), "Qty": t.get("qty",""),
                     "Price": t.get("prc",""), "Product": t.get("prod",""),
                     "Time": t.get("flDt","")} for t in trades]
            st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

            st.markdown('<div class="sec-header">P&L Summary</div>', unsafe_allow_html=True)
            buy_val  = sum(float(t.get("prc",0) or 0) * float(t.get("qty",0) or 0)
                          for t in trades if str(t.get("trnsTp","")).upper()=="B")
            sell_val = sum(float(t.get("prc",0) or 0) * float(t.get("qty",0) or 0)
                          for t in trades if str(t.get("trnsTp","")).upper()=="S")
            realized = sell_val - buy_val
            pa, pb, pc = st.columns(3)
            with pa: st.metric("Buy Value",    f"₹{buy_val:,.2f}")
            with pb: st.metric("Sell Value",   f"₹{sell_val:,.2f}")
            with pc: st.metric("Realized P&L", f"₹{realized:,.2f}",
                               delta_color="normal" if realized>=0 else "inverse")
    except Exception as he:
        st.error(f"Trade history error: {he}", icon="⚠️")
