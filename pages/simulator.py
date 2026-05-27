"""Strategy Simulator - Timeline scrubber for position analysis."""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np

def show_simulator():
    """Interactive strategy simulator with timeline controls."""
    
    st.title("⏯️ Strategy Simulator")
    st.caption("Play back strategy execution with Greeks evolution and P&L progression")
    
    # Sidebar: Simulation settings
    with st.sidebar:
        st.subheader("⚙️ Simulation Setup")
        
        strategy_name = st.selectbox(
            "Strategy",
            ["Iron Condor - NIFTY50", "Bull Call Spread - TCS", 
             "Long Straddle - INFY", "Calendar Spread - WIPRO"]
        )
        
        backtest_date = st.date_input(
            "Backtest Date",
            value=datetime(2024, 6, 14),
            min_value=datetime(2024, 1, 1)
        )
        
        playback_speed = st.select_slider(
            "Playback Speed",
            options=["0.25x", "0.5x", "1x", "2x", "4x"],
            value="1x"
        )
        
        st.divider()
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("▶️ Play", use_container_width=True):
                st.session_state['simulation_playing'] = True
        with col2:
            if st.button("⏸️ Pause", use_container_width=True):
                st.session_state['simulation_playing'] = False
    
    # Create columns for timeline and Greeks
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.subheader("📍 Position Timeline")
        
        # Timeline slider (time of day: 9:15 AM to 3:30 PM)
        hours = np.arange(9, 15.5, 0.25)  # 15-min intervals
        time_labels = []
        for h in hours:
            hour = int(h)
            minute = int((h - hour) * 60)
            time_labels.append(f"{hour:02d}:{minute:02d}")
        
        selected_time_idx = st.slider(
            "Time (click to scrub timeline)",
            min_value=0,
            max_value=len(time_labels) - 1,
            value=6,
            format=f"Time: %s" if False else None
        )
        
        selected_time = time_labels[selected_time_idx]
        st.caption(f"Simulating at **{selected_time}** | Spot: ₹23894.10")
    
    with col2:
        st.subheader("⏱️ Duration")
        st.metric("Days to Expiry", "6 days", delta_color="off")
    
    # Main charts
    tab1, tab2, tab3, tab4 = st.tabs(
        ["📊 Payoff & P&L", "⚡ Greeks Evolution", "🎯 Position Details", "📈 Greeks Heatmap"]
    )
    
    # TAB 1: Payoff and current P&L
    with tab1:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Current P&L
            st.subheader("Current Position P&L")
            
            price_range = np.linspace(23200, 24600, 100)
            payoff = np.maximum(price_range - 23800, 0) - np.maximum(price_range - 23900, 0)
            
            # Add some time decay
            days_passed = selected_time_idx / 26  # 6.5 trading days total
            days_remaining = 6 - days_passed
            time_decay = days_passed * 50  # Theta decay
            
            current_payoff = payoff + time_decay
            
            fig = go.Figure()
            
            # Payoff line
            fig.add_trace(go.Scatter(
                x=price_range,
                y=payoff,
                name='At Expiration',
                line=dict(color='gray', dash='dash'),
                opacity=0.5
            ))
            
            # Current P&L
            fig.add_trace(go.Scatter(
                x=price_range,
                y=current_payoff,
                name='Current P&L',
                fill='tozeroy',
                line=dict(color='#667eea', width=3)
            ))
            
            # Current spot
            fig.add_vline(
                x=23894.10,
                line_dash="dash",
                line_color="red",
                annotation_text="Current Spot"
            )
            
            fig.update_layout(
                title="Position P&L Across Price Range",
                xaxis_title="Underlying Price (₹)",
                yaxis_title="P&L (₹)",
                height=400,
                template='plotly_white',
                hovermode='x unified'
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.metric("Current P&L", "₹2,450", "+12.3%", delta_color="normal")
            st.metric("Max Profit", "₹550", delta_color="off")
            st.metric("Max Loss", "-₹9,450", delta_color="off")
            st.metric("Breakeven", "₹23850", delta_color="off")
            st.metric("Margin Used", "₹4,200", delta_color="off")
    
    # TAB 2: Greeks over time
    with tab2:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Delta Evolution")
            
            days = np.arange(0, 6.5, 0.25)
            delta_values = 0.25 + (days * 0.02) + np.random.randn(len(days)) * 0.01
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=days,
                y=delta_values,
                mode='lines+markers',
                name='Delta',
                line=dict(color='#667eea', width=2)
            ))
            
            # Mark current time
            fig.add_vline(
                x=days_passed,
                line_dash="dash",
                line_color="red",
                annotation_text="Now"
            )
            
            fig.update_layout(
                title="Delta Over Time",
                xaxis_title="Days Passed",
                yaxis_title="Delta",
                height=300,
                template='plotly_white'
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.subheader("Theta Decay")
            
            theta_values = 2.5 - (days * 0.3)  # Theta increases as expiry approaches
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=days,
                y=theta_values,
                fill='tozeroy',
                name='Theta',
                line=dict(color='#4caf50', width=2)
            ))
            
            fig.add_vline(
                x=days_passed,
                line_dash="dash",
                line_color="red"
            )
            
            fig.update_layout(
                title="Theta Decay Over Time",
                xaxis_title="Days Passed",
                yaxis_title="Theta (₹/day)",
                height=300,
                template='plotly_white'
            )
            
            st.plotly_chart(fig, use_container_width=True)
    
    # TAB 3: Position Details at Current Time
    with tab3:
        st.subheader("Position Breakdown")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Leg 1: SELL 23800 CE**")
            leg1_data = {
                "Metric": ["Price", "Delta", "Gamma", "Theta", "Vega", "Quantity"],
                "Value": ["₹150", "0.65", "0.012", "+0.35", "-25.5", "1 Lot"]
            }
            st.dataframe(pd.DataFrame(leg1_data), hide_index=True, use_container_width=True)
        
        with col2:
            st.write("**Leg 2: BUY 23900 CE**")
            leg2_data = {
                "Metric": ["Price", "Delta", "Gamma", "Theta", "Vega", "Quantity"],
                "Value": ["₹82", "0.42", "0.015", "-0.20", "-18.2", "1 Lot"]
            }
            st.dataframe(pd.DataFrame(leg2_data), hide_index=True, use_container_width=True)
        
        st.divider()
        
        st.write("**Portfolio Greeks**")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Delta", "0.23", delta_color="off")
        with col2:
            st.metric("Gamma", "0.027", delta_color="off")
        with col3:
            st.metric("Theta", "+0.15", delta_color="normal")
        with col4:
            st.metric("Vega", "-43.7", delta_color="inverse")
    
    # TAB 4: Greeks Heatmap
    with tab4:
        st.subheader("Greeks Sensitivity Heatmap")
        
        # Create heatmap of Greeks across different prices and times
        prices = np.linspace(23400, 24400, 20)
        times = np.arange(0, 6.5, 0.5)
        
        # Generate delta surface
        Z_delta = np.zeros((len(times), len(prices)))
        for i, t in enumerate(times):
            for j, p in enumerate(prices):
                Z_delta[i, j] = 0.25 + (t * 0.02) + (p - 23894.10) * 0.0002
        
        fig = go.Figure(data=go.Heatmap(
            z=Z_delta,
            x=prices,
            y=times,
            colorscale='RdBu',
            colorbar=dict(title="Delta")
        ))
        
        fig.update_layout(
            title="Delta Heatmap (Price vs Time)",
            xaxis_title="Underlying Price (₹)",
            yaxis_title="Days to Expiration",
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    show_simulator()
