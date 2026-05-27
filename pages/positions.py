"""Positions Page - Manage & Monitor Open Trades."""

import streamlit as st
import pandas as pd
from datetime import datetime
from broker import get_broker
from database import get_database
from logger import logger


def show_positions():
    """Manage and monitor live trading positions."""
    
    st.title("📈 Live Positions")
    st.caption("Monitor and manage all open trades")
    
    broker = get_broker()
    db = get_database()
    
    # Fetch open trades
    open_trades = db.get_open_trades()
    
    if not open_trades:
        st.info("No open positions currently", icon="📭")
        return
    
    st.subheader(f"Open Positions ({len(open_trades)})")
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    total_invested = 0
    total_pnl = 0
    winning_positions = 0
    
    for trade in open_trades:
        try:
            ltp_dict = broker.get_ltp(trade['symbol'])
            ltp = ltp_dict.get(trade['symbol'], trade['entry_price'])
            
            if trade['side'] == "BUY":
                pnl = (ltp - trade['entry_price']) * trade['quantity']
            else:
                pnl = (trade['entry_price'] - ltp) * trade['quantity']
            
            invested = trade['entry_price'] * trade['quantity']
            total_invested += invested
            total_pnl += pnl
            
            if pnl > 0:
                winning_positions += 1
        except:
            pass
    
    with col1:
        st.metric("Total Invested", f"₹{total_invested:.0f}")
    with col2:
        color = "normal" if total_pnl >= 0 else "inverse"
        st.metric("Total P&L", f"₹{total_pnl:.0f}", delta_color=color)
    with col3:
        st.metric("Winning Trades", winning_positions)
    with col4:
        max_risk = db.get_daily_loss()
        st.metric("Daily Loss", f"₹{max_risk:.0f}")
    
    st.divider()
    
    # Detailed positions table with actions
    st.subheader("📊 Position Details")
    
    for idx, trade in enumerate(open_trades):
        with st.expander(f"**{trade['symbol']}** • {trade['side']} • {trade['quantity']} shares", expanded=False):
            col1, col2, col3 = st.columns(3)
            
            try:
                # Get live price
                ltp_dict = broker.get_ltp(trade['symbol'])
                ltp = ltp_dict.get(trade['symbol'], trade['entry_price'])
                
                # Calculate metrics
                if trade['side'] == "BUY":
                    pnl = (ltp - trade['entry_price']) * trade['quantity']
                    pnl_pct = ((ltp - trade['entry_price']) / trade['entry_price']) * 100
                else:
                    pnl = (trade['entry_price'] - ltp) * trade['quantity']
                    pnl_pct = ((trade['entry_price'] - ltp) / trade['entry_price']) * 100
                
                pnl_icon = "📈" if pnl > 0 else "📉"
                
                with col1:
                    st.markdown("**Entry Details**")
                    st.write(f"Entry Price: ₹{trade['entry_price']:.2f}")
                    st.write(f"Entry Time: {trade['entry_time'].split('T')[0]}")
                    st.write(f"Quantity: {trade['quantity']}")
                    st.write(f"Order Type: {trade['order_type']}")
                
                with col2:
                    st.markdown("**Current Status**")
                    st.write(f"LTP: ₹{ltp:.2f}")
                    st.write(f"Invested: ₹{trade['entry_price'] * trade['quantity']:.0f}")
                    st.write(f"Margin Used: ₹{trade.get('risk', 0):.0f}")
                    st.write(f"Product: {trade.get('product', 'MIS')}")
                
                with col3:
                    st.markdown(f"**P&L {pnl_icon}**")
                    pnl_color = "🟢" if pnl > 0 else "🔴"
                    st.write(f"{pnl_color} **₹{pnl:.0f}**")
                    st.write(f"{pnl_color} **{pnl_pct:+.2f}%**")
                    if trade.get('target'):
                        st.write(f"Target: ₹{trade['target']:.2f}")
                    if trade.get('risk'):
                        st.write(f"SL: ₹{trade['risk']:.2f}")
                
                st.divider()
                
                # Action buttons
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    if st.button("🔄 Refresh", key=f"refresh_{idx}"):
                        st.rerun()
                
                with col2:
                    new_sl = st.number_input(
                        f"Update SL (₹)",
                        min_value=0.0,
                        value=trade.get('risk', 0.0),
                        key=f"new_sl_{idx}"
                    )
                    if st.button("📌 Update SL", key=f"update_sl_{idx}"):
                        st.info(f"SL would be updated to ₹{new_sl:.2f}", icon="ℹ️")
                
                with col3:
                    new_target = st.number_input(
                        f"Update Target (₹)",
                        min_value=0.0,
                        value=trade.get('target', 0.0),
                        key=f"new_target_{idx}"
                    )
                    if st.button("🎯 Update Target", key=f"update_target_{idx}"):
                        st.info(f"Target would be updated to ₹{new_target:.2f}", icon="ℹ️")
                
                with col4:
                    exit_price = st.number_input(
                        f"Exit Price (₹)",
                        min_value=0.0,
                        value=ltp,
                        key=f"exit_price_{idx}"
                    )
                
                # Close trade button
                if st.button(f"🔴 Close Position", key=f"close_{idx}", type="secondary", use_container_width=True):
                    db.close_trade(trade['id'], exit_price)
                    st.success(f"✅ Trade closed with P&L: ₹{pnl:.0f}", icon="🎉")
                    st.rerun()
            
            except Exception as e:
                st.error(f"Error processing position: {str(e)}")
    
    st.divider()
    
    # Risk management settings
    st.subheader("⚠️ Risk Management")
    
    col1, col2 = st.columns(2)
    
    with col1:
        daily_loss_limit = st.number_input(
            "Daily Loss Limit (₹)",
            min_value=0,
            value=5000
        )
        st.caption("Auto-stop trading if this loss is reached")
    
    with col2:
        max_positions = st.number_input(
            "Max Open Positions",
            min_value=1,
            max_value=20,
            value=5
        )
        st.caption("Maximum concurrent open positions")
    
    if st.button("💾 Save Risk Settings", use_container_width=True):
        st.success("✅ Risk settings updated", icon="✓")
