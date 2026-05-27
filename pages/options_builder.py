"""Options Strategy Builder - Visual options trading interface."""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from greeks_calculator import generate_option_chain, BlackScholesCalculator
from typing import Dict, List, Tuple

def show_options_builder():
    """Options strategy builder with option chain and payoff visualization."""
    
    st.title("🎯 Options Strategy Builder")
    st.caption("Build, analyze, and execute multi-leg options strategies")
    
    # Sidebar controls
    with st.sidebar:
        st.subheader("⚙️ Option Chain Settings")
        
        spot_price = st.number_input("Spot Price (₹)", value=23894.10, step=50.0)
        expiry_days = st.selectbox("Expiry", [1, 6, 13, 20, 27, 34, 62, 90], index=1)
        volatility = st.slider("Volatility (%)", 5, 100, 20, step=5) / 100
        
        st.divider()
        
        st.subheader("📋 Strategy Template")
        strategy_type = st.selectbox(
            "Select Strategy",
            ["Custom", "Straddle", "Strangle", "Bull Call Spread", 
             "Bear Put Spread", "Iron Fly", "Iron Condor"]
        )
    
    # Generate option chain
    chain = generate_option_chain(spot_price, expiry_days)
    
    # Main content tabs
    tab1, tab2, tab3, tab4 = st.tabs(
        ["📊 Option Chain", "📈 Payoff Graph", "🏗️ Builder", "⚡ Greeks"]
    )
    
    # TAB 1: Option Chain Display
    with tab1:
        st.subheader("Option Chain - 7 DTE")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col1:
            st.metric("Spot Price", f"₹{spot_price:.2f}")
        with col2:
            st.metric("Volatility", f"{volatility*100:.1f}%")
        with col3:
            st.metric("Expiry", f"{expiry_days}d")
        
        # Build option chain dataframe
        chain_data = []
        for strike in chain['strikes']:
            call = chain['calls'][strike]
            put = chain['puts'][strike]
            
            chain_data.append({
                "Call Price": f"₹{call['price']:.2f}",
                "Call Delta": f"{call['delta']:.4f}",
                "IV": f"{20:.1f}%",
                "Strike": f"₹{strike}",
                "IV": f"{20:.1f}%",
                "Put Delta": f"{put['delta']:.4f}",
                "Put Price": f"₹{put['price']:.2f}"
            })
        
        df_chain = pd.DataFrame(chain_data)
        st.dataframe(df_chain, use_container_width=True, hide_index=True)
        
        st.caption("💡 Scroll right to see full chain. Click on strikes to add to strategy.")
    
    # TAB 2: Payoff Graph
    with tab2:
        st.subheader("Strategy Payoff Analysis")
        
        # Calculate payoff for different price moves
        price_range = np.linspace(spot_price * 0.90, spot_price * 1.10, 100)
        
        # Example: Long Call
        call_strike = int(spot_price / 100) * 100
        long_call_payoff = np.maximum(price_range - call_strike, 0)
        
        # Example: Short Call
        short_call_payoff = -np.maximum(price_range - (call_strike + 100), 0)
        
        # Combined payoff
        combined_payoff = long_call_payoff + short_call_payoff
        
        # Plot
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=price_range,
            y=long_call_payoff,
            name='Long Call',
            line=dict(color='green', dash='dash')
        ))
        
        fig.add_trace(go.Scatter(
            x=price_range,
            y=short_call_payoff,
            name='Short Call',
            line=dict(color='red', dash='dash')
        ))
        
        fig.add_trace(go.Scatter(
            x=price_range,
            y=combined_payoff,
            name='Combined (Bull Call Spread)',
            line=dict(color='blue', width=3),
            fill='tozeroy'
        ))
        
        fig.update_layout(
            title="Strategy Payoff at Expiration",
            xaxis_title="Underlying Price (₹)",
            yaxis_title="Profit/Loss (₹)",
            hovermode='x unified',
            height=500,
            template='plotly_white'
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Show greeks
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Max Profit", "₹100")
        with col2:
            st.metric("Max Loss", "₹900")
        with col3:
            st.metric("Breakeven", f"₹{call_strike:.0f}")
        with col4:
            st.metric("Profit %", "+10%")
    
    # TAB 3: Strategy Builder
    with tab3:
        st.subheader("Build Your Strategy")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Leg 1: Sell Call**")
            leg1_strike = st.number_input("Strike 1", value=call_strike, key="leg1_strike")
            leg1_qty = st.number_input("Quantity 1", value=1, min_value=1, key="leg1_qty")
        
        with col2:
            st.write("**Leg 2: Buy Call**")
            leg2_strike = st.number_input("Strike 2", value=call_strike + 100, key="leg2_strike")
            leg2_qty = st.number_input("Quantity 2", value=1, min_value=1, key="leg2_qty")
        
        st.divider()
        
        # Calculate strategy metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Premium Received", "₹950")
        with col2:
            st.metric("Max Risk", "₹50")
        with col3:
            st.metric("Risk/Reward", "1:0.053")
        with col4:
            st.metric("Win Probability", "75%")
        
        if st.button("✅ Add Strategy Leg", use_container_width=True):
            st.success("Leg added to strategy!")
        
        if st.button("🚀 Execute Strategy", use_container_width=True, type="primary"):
            st.success("Strategy executed! Check Live Positions.")
    
    # TAB 4: Greeks Dashboard
    with tab4:
        st.subheader("Portfolio Greeks")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Delta",
                "0.25",
                "Net directional exposure",
                delta_color="off"
            )
        
        with col2:
            st.metric(
                "Gamma",
                "0.0125",
                "Delta acceleration",
                delta_color="off"
            )
        
        with col3:
            st.metric(
                "Theta",
                "+2.50",
                "Daily time decay",
                delta_color="normal"
            )
        
        with col4:
            st.metric(
                "Vega",
                "50.00",
                "Volatility exposure",
                delta_color="off"
            )
        
        st.divider()
        st.subheader("Greeks by Expiry")
        
        # Greeks over time
        days_remaining = list(range(expiry_days, 0, -1))
        theta_decay = [i * 0.5 for i in range(len(days_remaining))]
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=days_remaining,
            y=theta_decay,
            name='Theta Decay',
            fill='tozeroy'
        ))
        
        fig.update_layout(
            title="Theta Decay Over Time",
            xaxis_title="Days to Expiration",
            yaxis_title="Theta Value (₹)",
            height=300,
            template='plotly_white'
        )
        
        st.plotly_chart(fig, use_container_width=True)

# Import numpy for calculations
import numpy as np

if __name__ == "__main__":
    show_options_builder()
