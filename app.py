"""
Groww AutoTrader Pro - Production-Grade Automated Trading Platform
Multi-indicator screener + Bracket order execution + Risk management + Analytics
"""

import streamlit as st
import time
from datetime import datetime
from config import config

# Page config
st.set_page_config(
    page_title="Groww AutoTrader Pro",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown("""
<style>
    [data-testid="stSidebar"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    .stMetric {
        background: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
    }
    .trade-buy {
        background: #e8f5e9;
        border-left: 4px solid #4caf50;
    }
    .trade-sell {
        background: #ffebee;
        border-left: 4px solid #f44336;
    }
    .signal-strong {
        background: #fff3e0;
        border: 2px solid #ff9800;
    }
</style>
""", unsafe_allow_html=True)


# Sidebar
with st.sidebar:
    st.title("🤖 AutoTrader Pro")
    st.divider()
    
    # Mode indicator
    mode_badge = "🟢 LIVE" if config.is_live_mode else "🔵 PAPER"
    st.markdown(f"### {mode_badge}", help="Paper = simulated, Live = real Groww account")
    
    # Navigation
    st.divider()
    st.caption("NAVIGATION")
    page = st.selectbox(
        "Select page",
        ["⚡ Trade", "📊 Dashboard", "🔍 Screener", "📈 Positions", "🎯 Options Builder", 
         "📊 Backtest", "⏯️ Simulator", "📋 History", "⚙️ Settings"],
        key="page_selector"
    )
    
    # Quick stats
    st.divider()
    st.caption("QUICK STATS")
    
    try:
        from database import get_database
        db = get_database()
        stats = db.get_trade_stats()
        
        col1, col2 = st.columns(2)
        col1.metric("Total Trades", stats["total_trades"])
        col2.metric("Win Rate", f"{stats['win_rate']:.1f}%")
        
        col1.metric("P&L", f"₹{stats['total_pnl']:.0f}")
        col2.metric("Wins/Losses", f"{stats['wins']}/{stats['losses']}")
    except Exception as e:
        st.error(f"Could not load stats: {str(e)}", icon="⚠️")
    
    st.divider()
    st.caption("SETTINGS")
    
    if st.button("🔄 Refresh", use_container_width=True):
        st.rerun()


# Route to pages
if page == "⚡ Trade":
    from pages.trade import show_trade
    show_trade()
elif page == "📊 Dashboard":
    from pages.dashboard import show_dashboard
    show_dashboard()
elif page == "🔍 Screener":
    from pages.screener import show_screener
    show_screener()
elif page == "📈 Positions":
    from pages.positions import show_positions
    show_positions()
elif page == "🎯 Options Builder":
    from pages.options_builder import show_options_builder
    show_options_builder()
elif page == "� Backtest":
    from pages.backtest_results import show_backtest_results
    show_backtest_results()
elif page == "⏯️ Simulator":
    from pages.simulator import show_simulator
    show_simulator()
elif page == "�📋 History":
    from pages.history import show_history
    show_history()
elif page == "⚙️ Settings":
    from pages.settings import show_settings
    show_settings()
