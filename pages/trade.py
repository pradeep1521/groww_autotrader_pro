"""Trade Page - Simple Order Placement Interface."""

import streamlit as st
import pandas as pd
from datetime import datetime
from broker import get_broker
from database import get_database
from logger import logger


def show_trade():
    """Simple, clear order placement interface."""
    
    st.title("⚡ Place Trade")
    st.caption("Execute BUY or SELL orders on Groww broker")
    
    broker = get_broker()
    db = get_database()
    
    # Top info
    col1, col2, col3 = st.columns(3)
    
    try:
        margin = broker.get_margin()
        with col1:
            st.metric("Available Margin", f"₹{margin['available']:.0f}")
        with col2:
            mode = "🟢 LIVE" if broker.is_connected else "🔵 PAPER"
            st.metric("Mode", mode, help="LIVE = real money, PAPER = simulated")
        with col3:
            stats = db.get_trade_stats()
            st.metric("Win Rate", f"{stats['win_rate']:.1f}%")
    except Exception as e:
        logger.error(f"Error loading margin: {str(e)}")
        st.warning("Could not fetch account details")
    
    st.divider()
    
    # Order Form
    st.subheader("📝 Order Details")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Symbol selection
        popular_symbols = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", 
                          "WIPRO", "LT", "ASIANPAINT", "MARUTI", "SBIN"]
        
        symbol_choice = st.radio("Stock Symbol", ["Pick from list", "Enter custom"], horizontal=True)
        
        if symbol_choice == "Pick from list":
            symbol = st.selectbox(
                "Select Symbol",
                popular_symbols,
                help="Choose from popular NIFTY50 stocks"
            )
        else:
            symbol = st.text_input(
                "Enter Symbol",
                placeholder="e.g., RELIANCE",
                help="Stock symbol (e.g., RELIANCE, TCS, INFY)"
            ).upper()
        
        # Side
        side = st.radio("Order Side", ["BUY", "SELL"], horizontal=True, help="BUY to long, SELL to short")
    
    with col2:
        # Get LTP
        try:
            ltp_dict = broker.get_ltp(symbol) if symbol else {}
            ltp = ltp_dict.get(symbol, 0)
        except:
            ltp = 0
        
        # Quantity
        quantity = st.number_input(
            "Quantity",
            min_value=1,
            value=1,
            step=1,
            help="Number of shares to buy/sell"
        )
        
        # Order Type
        order_type = st.selectbox(
            "Order Type",
            ["MARKET", "LIMIT"],
            help="MARKET = instant execution, LIMIT = at specific price"
        )
    
    st.divider()
    
    # Price input based on order type
    st.subheader("💰 Price Details")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if ltp > 0:
            st.metric("Current LTP", f"₹{ltp:.2f}")
        else:
            st.warning("Could not fetch current price. Please check symbol.")
    
    with col2:
        if order_type == "LIMIT":
            price = st.number_input(
                "Limit Price (₹)",
                value=ltp if ltp > 0 else 1000.0,
                step=0.05,
                help="Price at which to execute the order"
            )
        else:
            price = ltp if ltp > 0 else 0
            st.metric("Market Price", f"₹{price:.2f}")
    
    with col3:
        if price > 0 and quantity > 0:
            total_amount = price * quantity
            st.metric("Total Amount", f"₹{total_amount:,.0f}")
        else:
            st.metric("Total Amount", "₹0")
    
    st.divider()
    
    # Order Summary
    st.subheader("📋 Order Summary")
    
    if symbol and price > 0 and quantity > 0:
        summary_data = {
            "Symbol": symbol,
            "Side": f"🟢 {side}" if side == "BUY" else f"🔴 {side}",
            "Quantity": quantity,
            "Order Type": order_type,
            "Price": f"₹{price:.2f}",
            "Total": f"₹{price * quantity:,.0f}"
        }
        
        df = pd.DataFrame([summary_data])
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        # Show margin impact
        if margin['available'] >= price * quantity:
            st.success(f"✅ Sufficient margin available (₹{margin['available'] - price * quantity:,.0f} remaining)", 
                      icon="💰")
        else:
            st.error(f"❌ Insufficient margin! Need ₹{price * quantity:,.0f}, have ₹{margin['available']:.0f}", 
                    icon="⚠️")
    else:
        st.info("Enter symbol, quantity, and price to see order summary", icon="ℹ️")
    
    st.divider()
    
    # Action Buttons
    st.subheader("⚙️ Actions")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("✅ PLACE ORDER", use_container_width=True, type="primary"):
            if not symbol or symbol.strip() == "":
                st.error("❌ Please select a symbol")
            elif quantity <= 0:
                st.error("❌ Quantity must be greater than 0")
            elif price <= 0:
                st.error("❌ Invalid price")
            elif margin['available'] < price * quantity:
                st.error("❌ Insufficient margin")
            else:
                # Place order
                try:
                    with st.spinner(f"Placing {side} order for {symbol}..."):
                        order_id = broker.place_order(
                            symbol=symbol,
                            side=side,
                            quantity=int(quantity),
                            price=float(price),
                            order_type=order_type
                        )
                        
                        # Save to database
                        db.add_trade({
                            'symbol': symbol,
                            'side': side,
                            'quantity': int(quantity),
                            'entry_price': float(price),
                            'order_type': order_type,
                            'status': 'OPEN',
                            'entry_time': datetime.now().isoformat()
                        })
                        
                        st.success(f"✅ Order placed! Order ID: {order_id}", icon="🎉")
                        logger.info(f"Order placed: {symbol} {side} {quantity} @ ₹{price}")
                        
                        # Show in table
                        st.subheader("✅ Order Confirmation")
                        confirmation = pd.DataFrame([{
                            "Order ID": order_id,
                            "Symbol": symbol,
                            "Side": side,
                            "Quantity": quantity,
                            "Price": f"₹{price:.2f}",
                            "Total": f"₹{price * quantity:,.0f}",
                            "Status": "PLACED",
                            "Time": datetime.now().strftime("%H:%M:%S")
                        }])
                        st.dataframe(confirmation, use_container_width=True, hide_index=True)
                        
                except Exception as e:
                    st.error(f"❌ Failed to place order: {str(e)}", icon="⚠️")
                    logger.error(f"Order placement failed: {str(e)}")
    
    with col2:
        if st.button("🔄 Clear Form", use_container_width=True):
            st.rerun()
    
    with col3:
        if st.button("📊 View Positions", use_container_width=True):
            st.info("Navigate to the Positions page to see all open trades", icon="ℹ️")
    
    st.divider()
    
    # Quick tips
    st.subheader("💡 Quick Tips")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        **Order Types:**
        - **MARKET**: Buy/Sell immediately at current price
        - **LIMIT**: Wait for price to reach your target
        """)
    
    with col2:
        st.markdown("""
        **Trading Tips:**
        - Start with small quantities (1-5 shares)
        - Always check available margin before ordering
        - Monitor positions on Dashboard
        - Paper mode (🔵) = simulated, no real money
        """)
    
    st.divider()
    
    # Recent orders
    st.subheader("📋 Your Recent Orders")
    
    try:
        recent_orders = db.get_open_trades(limit=5)
        
        if recent_orders:
            orders_data = []
            for trade in recent_orders:
                try:
                    ltp_dict = broker.get_ltp(trade['symbol'])
                    ltp = ltp_dict.get(trade['symbol'], trade['entry_price'])
                    pnl = (ltp - trade['entry_price']) * trade['quantity'] if trade['side'] == "BUY" else (trade['entry_price'] - ltp) * trade['quantity']
                    pnl_pct = (pnl / (trade['entry_price'] * trade['quantity']) * 100) if trade['entry_price'] > 0 else 0
                    
                    orders_data.append({
                        "ID": trade['id'][:8] + "...",
                        "Symbol": trade['symbol'],
                        "Side": "🟢 BUY" if trade['side'] == "BUY" else "🔴 SELL",
                        "Qty": trade['quantity'],
                        "Entry": f"₹{trade['entry_price']:.2f}",
                        "LTP": f"₹{ltp:.2f}",
                        "P&L": f"₹{pnl:.0f}",
                        "P&L%": f"{pnl_pct:+.2f}%",
                        "Status": trade['status']
                    })
                except Exception as e:
                    logger.error(f"Error processing trade: {str(e)}")
            
            if orders_data:
                df_orders = pd.DataFrame(orders_data)
                st.dataframe(df_orders, use_container_width=True, hide_index=True)
        else:
            st.info("No open orders yet. Place your first trade above! 👆", icon="📭")
    
    except Exception as e:
        st.warning(f"Could not load recent orders: {str(e)}")
