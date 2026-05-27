"""Greeks Sensitivity Dashboard - Interactive options Greeks analysis."""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from greeks_sensitivity import GreeksSensitivityCalculator, PortfolioGreeksSensitivity
from greeks_calculator import GreeksCalculator

st.set_page_config(page_title="Greeks Sensitivity", layout="wide")

st.title("📊 Greeks Sensitivity Dashboard")
st.markdown("Analyze option Greeks sensitivity to price, IV, and time changes")

# Sidebar parameters
st.sidebar.header("⚙️ Analysis Parameters")

tab1, tab2, tab3, tab4 = st.tabs([
    "📈 Price Sensitivity",
    "🔄 IV Sensitivity",
    "⏰ Time Sensitivity",
    "🔥 2D Heatmap"
])

with st.sidebar:
    # Option selection
    option_type = st.radio("Option Type", ["CALL", "PUT"], horizontal=True)
    
    current_price = st.number_input(
        "Current Price (₹)",
        value=23894,
        step=100,
        min_value=0
    )
    
    strike = st.number_input(
        "Strike Price (₹)",
        value=23900,
        step=100,
        min_value=0
    )
    
    expiry_days = st.slider(
        "Days to Expiry",
        min_value=1,
        max_value=180,
        value=30
    )
    
    iv = st.slider(
        "Implied Volatility",
        min_value=0.05,
        max_value=1.0,
        value=0.20,
        step=0.01
    )

# Initialize calculator
calculator = GreeksSensitivityCalculator()

# Tab 1: Price Sensitivity
with tab1:
    st.subheader("Price Sensitivity Analysis")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # Generate price sensitivity data
        price_sens = calculator.generate_price_sensitivity(
            current_price=current_price,
            strike=strike,
            expiry_days=expiry_days,
            option_type=option_type,
            iv=iv
        )
        
        # Plot 1: Delta across prices
        fig_delta = go.Figure()
        fig_delta.add_trace(go.Scatter(
            x=price_sens['price'],
            y=price_sens['delta'],
            mode='lines+markers',
            name='Delta',
            line=dict(color='blue', width=3),
            hovertemplate='Price: ₹%{x:.2f}<br>Delta: %{y:.3f}<extra></extra>'
        ))
        fig_delta.update_xaxes(title="Stock Price (₹)")
        fig_delta.update_yaxes(title="Delta")
        fig_delta.update_layout(
            title="Delta vs Stock Price",
            hovermode='x unified',
            height=400
        )
        st.plotly_chart(fig_delta, use_container_width=True)
        
        # Plot 2: Greeks across prices
        fig_greeks = go.Figure()
        
        fig_greeks.add_trace(go.Scatter(
            x=price_sens['price'],
            y=price_sens['gamma'],
            name='Gamma',
            yaxis='y2'
        ))
        fig_greeks.add_trace(go.Scatter(
            x=price_sens['price'],
            y=price_sens['theta'],
            name='Theta',
            yaxis='y3'
        ))
        fig_greeks.add_trace(go.Scatter(
            x=price_sens['price'],
            y=price_sens['vega'],
            name='Vega',
            yaxis='y4'
        ))
        
        fig_greeks.update_layout(
            title="Greeks vs Stock Price",
            xaxis=dict(title="Stock Price (₹)"),
            yaxis2=dict(title="Gamma", overlaying="y", side="left"),
            yaxis3=dict(title="Theta", overlaying="y", side="right"),
            yaxis4=dict(title="Vega", overlaying="y", side="right", position=0.85),
            hovermode='x unified',
            height=400
        )
        st.plotly_chart(fig_greeks, use_container_width=True)
    
    with col2:
        # Summary table
        st.metric("Current Delta", f"{price_sens.iloc[10]['delta']:.3f}")
        st.metric("Current Gamma", f"{price_sens.iloc[10]['gamma']:.4f}")
        st.metric("Current Theta", f"{price_sens.iloc[10]['theta']:.3f}")
        st.metric("Current Vega", f"{price_sens.iloc[10]['vega']:.3f}")
    
    # Detailed table
    st.subheader("Price Sensitivity Table")
    display_cols = ['price', 'price_change_%', 'option_value', 'delta', 'gamma', 'theta', 'vega']
    st.dataframe(
        price_sens[display_cols].style.format({
            'price': '₹{:.2f}',
            'price_change_%': '{:.2f}%',
            'option_value': '₹{:.2f}',
            'delta': '{:.3f}',
            'gamma': '{:.4f}',
            'theta': '{:.3f}',
            'vega': '{:.3f}'
        }),
        use_container_width=True,
        height=300
    )

# Tab 2: IV Sensitivity
with tab2:
    st.subheader("Implied Volatility Sensitivity")
    
    iv_sens = calculator.generate_iv_sensitivity(
        current_price=current_price,
        strike=strike,
        expiry_days=expiry_days,
        option_type=option_type
    )
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # Plot: Option value vs IV
        fig_iv = go.Figure()
        fig_iv.add_trace(go.Scatter(
            x=iv_sens['iv_%'],
            y=iv_sens['option_value'],
            mode='lines+markers',
            name='Option Value',
            line=dict(color='green', width=3),
            hovertemplate='IV: %{x:.1f}%<br>Value: ₹%{y:.2f}<extra></extra>'
        ))
        fig_iv.update_xaxes(title="Implied Volatility (%)")
        fig_iv.update_yaxes(title="Option Value (₹)")
        fig_iv.update_layout(
            title="Option Value vs IV",
            hovermode='x unified',
            height=400
        )
        st.plotly_chart(fig_iv, use_container_width=True)
        
        # Greeks vs IV
        fig_iv_greeks = px.scatter_matrix(
            iv_sens[['iv_%', 'delta', 'gamma', 'vega']],
            labels={'iv_%': 'IV (%)', 'delta': 'Delta', 'gamma': 'Gamma', 'vega': 'Vega'},
            title="Greeks vs IV Correlation"
        )
        st.plotly_chart(fig_iv_greeks, use_container_width=True)
    
    with col1:
        st.dataframe(
            iv_sens[['iv_%', 'option_value', 'delta', 'gamma', 'theta', 'vega']].style.format({
                'iv_%': '{:.1f}%',
                'option_value': '₹{:.2f}',
                'delta': '{:.3f}',
                'gamma': '{:.4f}',
                'theta': '{:.3f}',
                'vega': '{:.3f}'
            }),
            use_container_width=True,
            height=300
        )

# Tab 3: Time Sensitivity
with tab3:
    st.subheader("Time Decay (Theta) Analysis")
    
    time_sens = calculator.generate_time_sensitivity(
        current_price=current_price,
        strike=strike,
        max_days=min(expiry_days, 90),
        option_type=option_type,
        iv=iv
    )
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # Plot: Option value vs time
        fig_time = go.Figure()
        fig_time.add_trace(go.Scatter(
            x=time_sens['days_to_expiry'],
            y=time_sens['option_value'],
            mode='lines+markers',
            name='Option Value',
            line=dict(color='red', width=3),
            fill='tozeroy',
            hovertemplate='Days: %{x}<br>Value: ₹%{y:.2f}<extra></extra>'
        ))
        fig_time.update_xaxes(title="Days to Expiry")
        fig_time.update_yaxes(title="Option Value (₹)")
        fig_time.update_layout(
            title="Theta Decay (Time Decay)",
            hovermode='x unified',
            height=400
        )
        st.plotly_chart(fig_time, use_container_width=True)
        
        # Greeks vs time
        fig_time_greeks = go.Figure()
        fig_time_greeks.add_trace(go.Scatter(
            x=time_sens['days_to_expiry'],
            y=time_sens['theta'],
            mode='lines+markers',
            name='Theta',
            line=dict(color='orange')
        ))
        fig_time_greeks.update_xaxes(title="Days to Expiry")
        fig_time_greeks.update_yaxes(title="Theta (Daily Decay)")
        fig_time_greeks.update_layout(
            title="Daily Theta Decay Over Time",
            height=400
        )
        st.plotly_chart(fig_time_greeks, use_container_width=True)
    
    with col2:
        st.dataframe(
            time_sens[['days_to_expiry', 'option_value', 'delta', 'gamma', 'theta', 'vega']].style.format({
                'days_to_expiry': '{:.0f}',
                'option_value': '₹{:.2f}',
                'delta': '{:.3f}',
                'gamma': '{:.4f}',
                'theta': '{:.3f}',
                'vega': '{:.3f}'
            }),
            use_container_width=True,
            height=300
        )

# Tab 4: 2D Heatmap
with tab4:
    st.subheader("2D Greeks Heatmap - Price vs IV")
    
    greek_to_plot = st.selectbox(
        "Select Greek to visualize",
        ["delta", "gamma", "theta", "vega"]
    )
    
    # Generate 2D heatmap
    heatmap_data = calculator.generate_2d_greeks_heatmap(
        current_price=current_price,
        strike=strike,
        expiry_days=expiry_days,
        greek=greek_to_plot,
        option_type=option_type
    )
    
    # Plot heatmap
    fig_heatmap = go.Figure(data=go.Heatmap(
        z=heatmap_data.values,
        x=np.round(heatmap_data.columns, 2),
        y=np.round(heatmap_data.index * 100, 1),
        colorscale='RdBu',
        hovertemplate='Price: ₹%{x:.2f}<br>IV: %{y:.1f}%<br>' + greek_to_plot.capitalize() + ': %{z:.3f}<extra></extra>'
    ))
    
    fig_heatmap.update_xaxes(title="Stock Price (₹)")
    fig_heatmap.update_yaxes(title="Implied Volatility (%)")
    fig_heatmap.update_layout(
        title=f"{greek_to_plot.upper()} Heatmap (Price vs IV)",
        height=500
    )
    
    st.plotly_chart(fig_heatmap, use_container_width=True)

# Summary section
st.divider()
st.subheader("📋 Summary")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Option Type",
        option_type,
        f"Strike: ₹{strike:.0f}"
    )

with col2:
    st.metric(
        "Time to Expiry",
        f"{expiry_days} days",
        f"Current Price: ₹{current_price:.0f}"
    )

with col3:
    st.metric(
        "IV",
        f"{iv*100:.1f}%",
        f"Moneyness: {current_price/strike:.3f}"
    )

with col4:
    st.metric(
        "Option Value",
        f"₹{price_sens.iloc[10]['option_value']:.2f}",
        f"Intrinsic: ₹{max(current_price - strike, 0):.2f}"
    )

st.info(
    "💡 **Tips for Using Greeks Sensitivity:**\n"
    "- **Delta**: Risk per ₹1 move in underlying. Higher near ATM.\n"
    "- **Gamma**: Delta change per ₹1 move. Peaks at ATM.\n"
    "- **Theta**: Daily P&L decay. Increases near expiry.\n"
    "- **Vega**: Risk per 1% IV change. Highest near ATM.\n"
    "- Use heatmaps to find risk concentrations in price/IV space."
)
