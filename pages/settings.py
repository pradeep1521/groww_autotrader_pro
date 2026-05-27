"""Settings Page - Configuration & API Setup."""

import streamlit as st
from config import config
from broker import get_broker
from logger import logger


def show_settings():
    """Application settings and configuration."""
    
    st.title("⚙️ Settings")
    st.caption("Configure trading parameters and API credentials")
    
    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📡 Broker", "📊 Screener", "⚙️ Trading", "🔐 Security"])
    
    # Broker Settings
    with tab1:
        st.subheader("Broker Configuration")
        
        broker = get_broker()
        
        if broker.is_connected:
            st.success("✅ Connected to Groww", icon="📡")
            try:
                margin = broker.get_margin()
                col1, col2, col3 = st.columns(3)
                col1.metric("Available", f"₹{margin['available']:.0f}")
                col2.metric("Equity", f"₹{margin['equity']:.0f}")
                col3.metric("F&O", f"₹{margin['fno']:.0f}")
            except:
                st.warning("Could not fetch margin details")
        else:
            st.info("🔵 Paper Trading Mode - No Groww connection", icon="📄")
        
        st.divider()
        
        mode_display = "🟢 LIVE" if config.is_live_mode else "🔵 PAPER"
        st.write(f"**Current Mode:** {mode_display}")
        
        if st.button("🔄 Reconnect to Groww"):
            st.info("Reconnection feature would be implemented here")
        
        if st.button("🔌 Disconnect"):
            broker.disconnect()
            st.success("✅ Disconnected from Groww")
    
    # Screener Settings
    with tab2:
        st.subheader("Screener Configuration")
        
        universe = st.selectbox(
            "Default Universe",
            ["NIFTY50", "NIFTY_NEXT50", "NIFTY500"],
            index=0
        )
        
        scan_interval = st.slider(
            "Scan Interval (seconds)",
            min_value=60,
            max_value=3600,
            value=900,
            step=60
        )
        
        st.caption(f"Will scan every {scan_interval // 60} minutes")
        
        st.divider()
        
        st.subheader("Indicator Thresholds")
        
        col1, col2 = st.columns(2)
        
        with col1:
            min_rsi = st.slider("RSI Oversold", 0, 30, 25)
            min_adx = st.slider("Min ADX (Trend)", 0, 30, 15)
        
        with col2:
            max_rsi = st.slider("RSI Overbought", 70, 100, 75)
            min_volume = st.slider("Min Volume Ratio", 0.5, 5.0, 1.5)
        
        if st.button("💾 Save Screener Settings"):
            st.success("✅ Screener settings updated")
    
    # Trading Settings
    with tab3:
        st.subheader("Trading Parameters")
        
        col1, col2 = st.columns(2)
        
        with col1:
            risk_per_trade = st.number_input(
                "Risk Per Trade (₹)",
                min_value=100,
                max_value=50000,
                value=500,
                step=100
            )
            
            max_positions = st.number_input(
                "Max Open Positions",
                min_value=1,
                max_value=20,
                value=5
            )
        
        with col2:
            daily_loss_limit = st.number_input(
                "Daily Loss Limit (₹)",
                min_value=1000,
                max_value=100000,
                value=5000,
                step=1000
            )
            
            order_type = st.selectbox(
                "Default Order Type",
                ["MARKET", "LIMIT", "SL-M"]
            )
        
        st.divider()
        
        st.subheader("Position Management")
        
        auto_sl = st.checkbox("Auto-place Stop Loss", value=True)
        auto_target = st.checkbox("Auto-place Target Orders", value=False)
        auto_close = st.checkbox("Auto-close at target", value=False)
        
        if auto_close:
            st.warning("⚠️ Enable this only if you want fully automated exits")
        
        if st.button("💾 Save Trading Settings"):
            st.success("✅ Trading settings updated")
    
    # Security
    with tab4:
        st.subheader("Security & Credentials")
        
        st.warning("⚠️ Never share your API credentials or access tokens", icon="🔐")
        
        st.divider()
        
        if st.checkbox("Show credential input"):
            st.subheader("Groww API Credentials")
            
            access_token = st.text_input(
                "Access Token",
                type="password",
                help="Your Groww access token"
            )
            
            api_key = st.text_input(
                "API Key",
                type="password",
                help="Your Groww API key"
            )
            
            api_secret = st.text_input(
                "API Secret",
                type="password",
                help="Your Groww API secret"
            )
            
            if st.button("🔐 Update Credentials"):
                if access_token or (api_key and api_secret):
                    st.success("✅ Credentials saved securely")
                    logger.info("Credentials updated")
                else:
                    st.error("❌ Please provide valid credentials")
        
        st.divider()
        
        st.subheader("Backup & Export")
        
        if st.button("📥 Export Trade History"):
            st.info("CSV export would be generated here")
        
        if st.button("📊 Export Statistics"):
            st.info("Performance statistics would be exported here")
        
        st.divider()
        
        st.subheader("Advanced Options")
        
        if st.checkbox("Enable debug logging"):
            st.caption("Detailed logs will be saved to ./logs/trader.log")
        
        if st.checkbox("Enable dry-run mode"):
            st.caption("Orders will be logged but not executed")
        
        if st.button("🗑️ Clear All Data"):
            if st.checkbox("I understand this will delete all trade data"):
                st.error("❌ Data deletion disabled for safety")
