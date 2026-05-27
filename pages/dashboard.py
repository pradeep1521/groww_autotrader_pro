"""Dashboard Page - Market Overview, Live Positions, Recent Signals."""

import streamlit as st
import pandas as pd
from datetime import datetime
from broker import get_broker
from database import get_database
from logger import logger


def show_dashboard():
    """Main dashboard with market snapshot and positions."""
    
    st.title("📊 Dashboard")
    st.caption("Real-time market overview, live positions, and trading activity")
    
    broker = get_broker()
    db = get_database()
    
    # Top KPIs
    col1, col2, col3, col4, col5 = st.columns(5)
    
    try:
        stats = db.get_trade_stats()
        with col1:
            st.metric("Total Trades", stats["total_trades"])
        with col2:
            st.metric("Win Rate", f"{stats['win_rate']:.1f}%", 
                     delta=f"{stats['wins']} wins" if stats["wins"] > 0 else "0 wins")
        with col3:
            color = "normal" if stats['total_pnl'] >= 0 else "inverse"
            st.metric("Total P&L", f"₹{stats['total_pnl']:.0f}", delta_color=color)
        with col4:
            st.metric("Win/Loss", f"{stats['wins']}/{stats['losses']}")
        with col5:
            daily_loss = db.get_daily_loss()
            st.metric("Today's Loss", f"₹{daily_loss:.0f}", 
                     delta=f"-₹{daily_loss:.0f}" if daily_loss > 0 else None)
    except Exception as e:
        st.error(f"Error loading stats: {str(e)}")
    
    st.divider()
    
    # Live Positions
    st.subheader("📈 Open Positions")
    
    open_trades = db.get_open_trades()
    
    if not open_trades:
        st.info("No open positions currently", icon="📭")
    else:
        # Create positions table
        positions_data = []
        for trade in open_trades:
            try:
                # Get current price
                ltp_dict = broker.get_ltp(trade['symbol'])
                ltp = ltp_dict.get(trade['symbol'], trade['entry_price'])
                
                # Calculate P&L
                if trade['side'] == "BUY":
                    pnl = (ltp - trade['entry_price']) * trade['quantity']
                else:
                    pnl = (trade['entry_price'] - ltp) * trade['quantity']
                
                pnl_pct = (pnl / (trade['entry_price'] * trade['quantity'])) * 100 if trade['entry_price'] > 0 else 0
                
                positions_data.append({
                    "ID": trade['id'],
                    "Symbol": trade['symbol'],
                    "Side": trade['side'],
                    "Qty": trade['quantity'],
                    "Entry": f"₹{trade['entry_price']:.2f}",
                    "LTP": f"₹{ltp:.2f}",
                    "P&L": f"₹{pnl:.0f}",
                    "P&L%": f"{pnl_pct:+.2f}%",
                    "Type": trade['order_type'],
                    "Time": trade['entry_time'].split('T')[1][:5] if trade['entry_time'] else "—",
                })
            except Exception as e:
                logger.error(f"Error processing trade {trade['id']}: {str(e)}")
                continue
        
        if positions_data:
            df_positions = pd.DataFrame(positions_data)
            st.dataframe(df_positions, use_container_width=True, hide_index=True)
            
            # Action buttons
            st.caption("**Quick Actions**")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("🔄 Refresh Prices"):
                    st.rerun()
            with col2:
                if st.button("📊 View Charts"):
                    st.info("Navigate to Screener page for detailed charts")
            with col3:
                if st.button("📋 Close Position"):
                    st.warning("Use Positions page to close individual trades")
    
    st.divider()
    
    # Recent Trades
    st.subheader("📋 Recent Closed Trades")
    
    closed_trades = db.get_closed_trades(limit=10)
    
    if not closed_trades:
        st.info("No closed trades yet", icon="📭")
    else:
        trades_data = []
        for trade in closed_trades:
            pnl_pct = trade['pnl_pct'] or 0
            pnl_icon = "✅" if trade['pnl'] > 0 else "❌"
            
            trades_data.append({
                "Time": trade['exit_time'].split('T')[1][:5] if trade['exit_time'] else "—",
                "Symbol": trade['symbol'],
                "Side": trade['side'],
                "Qty": trade['quantity'],
                "Entry": f"₹{trade['entry_price']:.2f}",
                "Exit": f"₹{trade['exit_price']:.2f}" if trade['exit_price'] else "—",
                "P&L": f"{pnl_icon} ₹{trade['pnl']:.0f}",
                "P&L%": f"{pnl_pct:+.2f}%",
                "Duration": "—",
            })
        
        df_trades = pd.DataFrame(trades_data)
        st.dataframe(df_trades, use_container_width=True, hide_index=True)
    
    st.divider()
    
    # System Status
    st.subheader("🔧 System Status")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if broker.is_connected:
            st.success("✅ Broker Connected", icon="📡")
            try:
                margin = broker.get_margin()
                st.metric("Available Margin", f"₹{margin['available']:.0f}")
            except:
                st.caption("Could not fetch margin")
        else:
            st.warning("🔵 Paper Mode", icon="📄")
            st.caption("Not connected to Groww")
    
    with col2:
        st.info("Market Hours: 09:15 - 15:30 IST", icon="🕐")
        st.caption("Pre-close: 15:20 IST")
    
    with col3:
        st.caption(f"Last Updated: {datetime.now().strftime('%H:%M:%S')}")
        if st.button("🔄 Refresh Now"):
            st.rerun()
