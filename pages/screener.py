"""Screener Page - Multi-Indicator Analysis & Signal Generation."""

import streamlit as st
import pandas as pd
import yfinance as yf
import asyncio
import logging
from datetime import datetime
from indicators import TechnicalAnalyzer
from broker import get_broker
from database import get_database
from logger import logger

logging.getLogger("yfinance").setLevel(logging.CRITICAL)


def show_screener():
    """Stock screener with technical analysis and signal generation."""
    
    st.title("🔍 Screener")
    st.caption("Multi-indicator stock analysis with signal generation")
    
    broker = get_broker()
    db = get_database()
    
    # Sidebar controls
    with st.sidebar:
        st.caption("**SCREENER SETTINGS**")
        universe = st.selectbox(
            "Select Universe",
            ["NIFTY50", "NIFTY_NEXT50", "CUSTOM"],
            key="universe"
        )
        
        if universe == "CUSTOM":
            symbols_input = st.text_area(
                "Enter symbols (comma-separated)",
                value="RELIANCE,TCS,INFY,HDFCBANK,ICICIBANK",
                height=3
            )
            symbols = [s.strip().upper() for s in symbols_input.split(",")]
        else:
            # Predefined universes
            universes_map = {
                "NIFTY50": [
                    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK",
                    "HINDUNILVR", "ITC", "SBIN", "BHARTIARTL", "KOTAKBANK",
                    "LT", "AXISBANK", "BAJFINANCE", "ASIANPAINT", "MARUTI",
                    "HCLTECH", "WIPRO", "ULTRACEMCO", "NESTLEIND", "POWERGRID",
                    "NTPC", "TATAMOTORS", "SUNPHARMA", "TITAN", "ONGC"
                ],
                "NIFTY_NEXT50": [
                    "ADANIENT", "ADANIGREEN", "AMBUJACEM", "AUROPHARMA", "BANDHANBNK",
                    "BERGEPAINT", "BIOCON", "BOSCHLTD", "CANBK", "CHOLAFIN",
                    "COLPAL", "DABUR", "DLF", "GAIL", "GODREJCP",
                    "HAVELLS", "ICICIPRULI", "ICICIGI", "IDEA", "INDUSTOWER"
                ]
            }
            symbols = universes_map.get(universe, [])
        
        period = st.selectbox("Period", ["1d", "5d", "3mo"], key="period")
        min_rsi = st.slider("Min RSI (Oversold)", 0, 30, 25, key="min_rsi")
        max_rsi = st.slider("Max RSI (Overbought)", 70, 100, 75, key="max_rsi")
        min_momentum = st.slider("Min Momentum Score", 0, 100, 50, key="min_momentum")
        
        scan_button = st.button("🔍 Scan Universe", use_container_width=True, type="primary")
    
    # Main area
    if scan_button or "scan_results" not in st.session_state:
        with st.spinner("📊 Scanning stocks... This may take 30-60 seconds"):
            st.session_state.scan_results = []
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for idx, symbol in enumerate(symbols):
                try:
                    status_text.text(f"Scanning {symbol}... ({idx+1}/{len(symbols)})")
                    
                    # Download data
                    data = yf.download(
                        f"{symbol}.NS",
                        period=period,
                        interval="1d",
                        auto_adjust=True,
                        progress=False,
                        quiet=True
                    )
                    
                    if data.empty or len(data) < 20:
                        continue
                    
                    # Analyze
                    analysis = TechnicalAnalyzer.analyze_stock(data, symbol)
                    
                    if analysis and len(analysis) > 0:
                        # Check signal criteria
                        rsi = analysis.get('rsi', 50)
                        momentum = analysis.get('momentum_score', 0)
                        
                        signal = None
                        if rsi < min_rsi and momentum > min_momentum:
                            signal = "🟢 BUY - Oversold"
                        elif rsi > max_rsi:
                            signal = "🔴 SELL - Overbought"
                        
                        st.session_state.scan_results.append({
                            **analysis,
                            "signal": signal or "NEUTRAL"
                        })
                    
                    progress_bar.progress((idx + 1) / len(symbols))
                
                except Exception as e:
                    logger.error(f"Error scanning {symbol}: {str(e)}")
                    continue
            
            progress_bar.empty()
            status_text.empty()
    
    # Display results
    if st.session_state.scan_results:
        st.success(f"✅ Scan complete: {len(st.session_state.scan_results)} stocks analyzed")
        
        # Sort by momentum score
        sorted_results = sorted(
            st.session_state.scan_results,
            key=lambda x: x.get('momentum_score', 0),
            reverse=True
        )
        
        # Create DataFrame
        results_data = []
        for r in sorted_results:
            results_data.append({
                "Symbol": r['symbol'],
                "Price": f"₹{r['price']:.2f}",
                "RSI": f"{r['rsi']:.1f}",
                "MACD": f"{r['macd_hist']:+.4f}",
                "BB Pos": f"{r['bb_position']:.2f}",
                "ADX": f"{r['adx']:.1f}",
                "Vol Ratio": f"{r['volume_ratio']:.2f}",
                "Trend": r['trend'],
                "Score": f"{r['momentum_score']:.1f}",
                "Signal": r['signal']
            })
        
        df_results = pd.DataFrame(results_data)
        
        # Display with styling
        st.dataframe(df_results, use_container_width=True, hide_index=True)
        
        st.divider()
        
        # Top signals
        st.subheader("🚀 Top Trading Signals")
        
        buy_signals = [r for r in sorted_results if "BUY" in r['signal']]
        
        if buy_signals:
            for signal_result in buy_signals[:5]:
                col1, col2, col3 = st.columns([2, 1, 1])
                
                with col1:
                    st.markdown(f"### 🟢 {signal_result['symbol']}")
                    st.write(f"Price: ₹{signal_result['price']:.2f} | RSI: {signal_result['rsi']:.1f} | Score: {signal_result['momentum_score']:.0f}")
                
                with col2:
                    if st.button("📊 Chart", key=f"chart_{signal_result['symbol']}"):
                        st.info(f"Loading chart for {signal_result['symbol']}...")
                
                with col3:
                    if st.button("🛒 Trade", key=f"trade_{signal_result['symbol']}"):
                        st.session_state.selected_symbol = signal_result['symbol']
                        st.session_state.selected_price = signal_result['price']
                        st.session_state.show_trade_panel = True
        else:
            st.info("No buy signals found matching criteria", icon="📭")
        
        # Trade execution panel
        if st.session_state.get("show_trade_panel"):
            st.divider()
            st.subheader("🛒 Place Trade")
            
            symbol = st.session_state.selected_symbol
            entry_price = st.session_state.selected_price
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                side = st.radio("Side", ["BUY", "SELL"], horizontal=True)
            
            with col2:
                qty = st.number_input("Quantity", min_value=1, value=1)
            
            with col3:
                order_type = st.selectbox("Order Type", ["MARKET", "LIMIT"])
            
            col1, col2 = st.columns(2)
            with col1:
                risk = st.number_input("Risk (₹)", min_value=100, value=500)
            with col2:
                sl_price = st.number_input("Stop Loss (₹)", min_value=0.0, value=entry_price * 0.95)
            
            if st.button("✅ Place Order", type="primary", use_container_width=True):
                success, response = broker.place_market_order(
                    symbol, side, qty
                )
                
                if success:
                    # Log trade
                    trade_id = db.add_trade(
                        symbol=symbol,
                        entry_price=entry_price,
                        quantity=qty,
                        side=side,
                        order_type=order_type,
                        risk=risk,
                        target=entry_price * 1.05 if side == "BUY" else entry_price * 0.95
                    )
                    
                    st.success(f"✅ Order placed! Trade ID: {trade_id}", icon="🎉")
                    st.session_state.show_trade_panel = False
                else:
                    st.error(f"❌ Order failed: {response.get('error', 'Unknown error')}", icon="⚠️")
    else:
        st.info("Click 'Scan Universe' to start analysis", icon="👈")
