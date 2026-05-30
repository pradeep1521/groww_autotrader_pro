"""Broker Setup Page - Configure and test brokers."""

import streamlit as st
import json
from pathlib import Path
from brokers import (
    get_broker, get_broker_type, switch_broker, BrokerFactory
)
from logger import logger


def show_broker_setup():
    """Broker setup and configuration page."""
    
    st.title("⚙️ Broker Setup")
    st.caption("Configure your trading broker - Paper, Groww, or Zerodha")
    
    # Tabs
    tab1, tab2, tab3 = st.tabs(["🔌 Connect Broker", "📋 Credentials", "📊 Account Status"])
    
    # TAB 1: Connect Broker
    with tab1:
        st.subheader("Select Your Broker")
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            current_broker = get_broker_type()
            
            broker_options = BrokerFactory.get_available_brokers()
            
            selected_broker = st.selectbox(
                "Broker",
                list(broker_options.keys()),
                index=list(broker_options.keys()).index(current_broker),
                format_func=lambda x: f"{x.upper()}: {broker_options[x]}"
            )
        
        with col2:
            broker_info = broker_options[selected_broker]
            st.info(f"**{selected_broker.upper()}**: {broker_info}")
        
        st.divider()
        
        # Broker-specific setup
        if selected_broker == 'paper':
            st.subheader("📚 Paper Trading (Learning Mode)")
            st.write("""
            **Perfect for:**
            - Learning trading without risk
            - Testing strategies before live trading
            - Paper trading competitions
            
            **Features:**
            - Starting balance: ₹100,000
            - Real-time mock quotes
            - Simulated order execution
            - No real money at risk
            - No broker account needed
            """)
            
            if st.button("✅ Use Paper Trading", use_container_width=True, type="primary"):
                success, message = switch_broker('paper')
                if success:
                    st.success(message, icon="✅")
                    st.rerun()
                else:
                    st.error(f"Error: {message}", icon="❌")
        
        elif selected_broker == 'zerodha':
            st.subheader("🔗 Zerodha Kite API Setup")
            
            st.write("""
            **Steps to connect Zerodha:**
            
            1. Go to https://kite.zerodha.com/connect/login
            2. Login with your Zerodha account
            3. Copy the **access_token** from browser console:
               - F12 → Network → Look for request with "accessToken"
               - Or check Local Storage for "access_token"
            4. Paste it below
            """)
            
            access_token = st.text_input(
                "Zerodha Access Token",
                type="password",
                placeholder="eyJ0eXAiOiJKV1QiLC...",
                help="Your Zerodha access token (keep it secret!)"
            )
            
            if st.button("🔐 Connect Zerodha", use_container_width=True, type="primary"):
                if access_token:
                    success, message = switch_broker('zerodha', {'access_token': access_token})
                    if success:
                        st.success(f"✅ {message}", icon="✅")
                        st.balloons()
                    else:
                        st.error(f"❌ {message}", icon="❌")
                else:
                    st.warning("Please enter access token", icon="⚠️")
        
        elif selected_broker == 'groww':
            st.subheader("🚀 Groww Broker Setup")
            
            st.write("""
            **Two options to connect Groww:**
            
            ### Option A: Pre-generated Access Token (Easier)
            - Groww provides access tokens for registered APIs
            - Paste your token directly
            
            ### Option B: Credentials (Full Access)
            - Client ID & Secret from Groww Developer
            - Your Groww username & password
            """)
            
            st.divider()
            
            option = st.radio("Authentication Method", ["Access Token", "Credentials"])
            
            if option == "Access Token":
                access_token = st.text_input(
                    "Groww Access Token",
                    type="password",
                    placeholder="token_...",
                    help="Pre-generated access token from Groww"
                )
                
                if st.button("🔐 Connect with Token", use_container_width=True, type="primary"):
                    if access_token:
                        success, message = switch_broker('groww', {'access_token': access_token})
                        if success:
                            st.success(f"✅ {message}", icon="✅")
                            st.balloons()
                        else:
                            st.error(f"❌ {message}", icon="❌")
                    else:
                        st.warning("Please enter access token", icon="⚠️")
            
            else:  # Credentials
                col1, col2 = st.columns(2)
                
                with col1:
                    client_id = st.text_input("Client ID", type="password")
                    username = st.text_input("Groww Username", type="password")
                
                with col2:
                    client_secret = st.text_input("Client Secret", type="password")
                    password = st.text_input("Groww Password", type="password")
                
                if st.button("🔐 Connect with Credentials", use_container_width=True, type="primary"):
                    if all([client_id, client_secret, username, password]):
                        credentials = {
                            'client_id': client_id,
                            'client_secret': client_secret,
                            'username': username,
                            'password': password
                        }
                        success, message = switch_broker('groww', credentials)
                        if success:
                            st.success(f"✅ {message}", icon="✅")
                            st.balloons()
                        else:
                            st.error(f"❌ {message}", icon="❌")
                    else:
                        st.warning("Please fill all fields", icon="⚠️")
    
    # TAB 2: Saved Credentials
    with tab2:
        st.subheader("📋 Saved Credentials")
        
        st.warning("""
        **SECURITY NOTE:** 
        - Never share your credentials
        - Store credentials in .env file, not in code
        - Use environment variables for production
        """, icon="🔒")
        
        credentials_file = Path(".broker_config.json")
        
        if st.checkbox("💾 Save credentials locally (not recommended)"):
            st.info("This saves credentials unencrypted in .broker_config.json")
            
            if st.button("Save Current Broker Config"):
                current_broker = get_broker()
                broker_name = get_broker_type()
                
                # For demo only - don't save actual credentials
                st.write("Demo: Would save credentials here (disabled for safety)")
        
        if credentials_file.exists():
            st.success("✅ Found saved credentials")
            
            if st.button("🗑️ Delete Saved Credentials"):
                credentials_file.unlink()
                st.success("Deleted!")
                st.rerun()
        else:
            st.info("No saved credentials found")
    
    # TAB 3: Account Status
    with tab3:
        st.subheader("📊 Connected Broker Status")
        
        broker = get_broker()
        broker_name = get_broker_type()
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            status = "🟢 Connected" if broker.is_connected else "🔴 Disconnected"
            st.metric("Status", status)
        
        with col2:
            st.metric("Broker", broker_name.upper())
        
        with col3:
            st.metric("Market Open", "Yes" if broker.is_market_open() else "No")
        
        st.divider()
        
        st.subheader("🏦 Account Details")
        
        try:
            balance = broker.get_balance()
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Available Margin", f"₹{balance.available_margin:,.0f}")
            
            with col2:
                st.metric("Used Margin", f"₹{balance.used_margin:,.0f}")
            
            with col3:
                st.metric("Total Equity", f"₹{balance.total_equity:,.0f}")
            
            with col4:
                cash_pct = (balance.available_cash / balance.total_equity * 100) if balance.total_equity > 0 else 0
                st.metric("Cash %", f"{cash_pct:.1f}%")
            
            st.divider()
            
            st.subheader("📍 Product Balances")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**MIS (Intraday)**")
                st.metric("Balance", f"₹{balance.product_balance.get('MIS', 0):,.0f}")
            
            with col2:
                st.write("**CNC (Delivery)**")
                st.metric("Balance", f"₹{balance.product_balance.get('CNC', 0):,.0f}")
        
        except Exception as e:
            st.error(f"Could not fetch account details: {str(e)}", icon="❌")
        
        st.divider()
        
        st.subheader("✅ Quick Test")
        
        if st.button("Test Market Data"):
            with st.spinner("Fetching market data..."):
                try:
                    test_symbols = ['RELIANCE', 'TCS', 'INFY']
                    quotes = broker.get_quotes(test_symbols)
                    
                    st.success("✅ Market data working!")
                    
                    for symbol, quote in quotes.items():
                        col1, col2, col3 = st.columns(3)
                        col1.metric(symbol, f"₹{quote['ltp']:.2f}")
                        col2.write(f"Bid: ₹{quote['bid']:.2f}")
                        col3.write(f"Ask: ₹{quote['ask']:.2f}")
                
                except Exception as e:
                    st.error(f"Market data error: {str(e)}", icon="❌")
        
        st.divider()
        
        st.subheader("📚 Broker Documentation")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.write("**Zerodha**")
            st.write("[API Docs](https://kite.trade/docs)")
            st.write("[Console](https://kite.zerodha.com)")
        
        with col2:
            st.write("**Groww**")
            st.write("[API Docs](https://groww.in/docs)")
            st.write("[Account](https://app.groww.in)")
        
        with col3:
            st.write("**Paper Trading**")
            st.write("[Docs](https://localhost:8504)")
            st.write("[No setup needed]")
