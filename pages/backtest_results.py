"""Backtest Results & Analysis - Historical strategy performance."""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from datetime import datetime, timedelta

def show_backtest_results():
    """Display backtest results and performance analytics."""
    
    st.title("📊 Backtest Results & Analysis")
    st.caption("Historical strategy performance and validation metrics")
    
    # Sidebar: Backtest selection
    with st.sidebar:
        st.subheader("🔍 Backtest Selection")
        
        strategy = st.selectbox(
            "Strategy",
            ["Iron Condor - NIFTY50", "Bull Call Spread - TCS", 
             "Calendar Spread - INFY", "Straddle - WIPRO"]
        )
        
        backtest_period = st.selectbox(
            "Period",
            ["Last 1 Month", "Last 3 Months", "Last 6 Months", "Last 1 Year", "Custom"],
            index=2
        )
        
        if backtest_period == "Custom":
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input("Start Date", datetime(2024, 1, 1))
            with col2:
                end_date = st.date_input("End Date", datetime.now())
        
        st.divider()
        
        if st.button("▶️ Run Backtest", use_container_width=True, type="primary"):
            st.session_state['backtest_running'] = True
    
    # Main content tabs
    tab1, tab2, tab3, tab4 = st.tabs(
        ["📈 Performance", "📊 Metrics", "🔄 Equity Curve", "📋 Trade Log"]
    )
    
    # TAB 1: Performance Summary
    with tab1:
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Total P&L",
                "₹45,280",
                "+22.5%",
                delta_color="normal"
            )
        
        with col2:
            st.metric(
                "Win Rate",
                "68.5%",
                "+5.2%",
                delta_color="normal"
            )
        
        with col3:
            st.metric(
                "Profit Factor",
                "2.85",
                "Good",
                delta_color="off"
            )
        
        with col4:
            st.metric(
                "Max Drawdown",
                "-12.3%",
                "-2.1%",
                delta_color="inverse"
            )
        
        st.divider()
        
        # Risk-Return metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Avg Win", "₹2,150", delta_color="off")
        with col2:
            st.metric("Avg Loss", "-₹1,890", delta_color="off")
        with col3:
            st.metric("Win/Loss Ratio", "1.14x", delta_color="off")
        with col4:
            st.metric("Sharpe Ratio", "1.87", delta_color="off")
        
        st.divider()
        
        # Monthly P&L
        st.subheader("Monthly Performance")
        
        months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun']
        pnl = [2500, 3200, -1200, 4100, 5280, 3400]
        
        fig = go.Figure()
        
        colors = ['green' if x > 0 else 'red' for x in pnl]
        
        fig.add_trace(go.Bar(
            x=months,
            y=pnl,
            marker=dict(color=colors),
            name='Monthly P&L'
        ))
        
        fig.update_layout(
            title="Monthly Profit/Loss",
            xaxis_title="Month",
            yaxis_title="P&L (₹)",
            height=350,
            template='plotly_white',
            showlegend=False
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # TAB 2: Detailed Metrics
    with tab2:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Trade Statistics")
            
            metrics_data = {
                "Metric": [
                    "Total Trades",
                    "Winning Trades",
                    "Losing Trades",
                    "Breakeven Trades",
                    "Consecutive Wins",
                    "Consecutive Losses",
                    "Avg Trade Duration"
                ],
                "Value": [
                    73,
                    50,
                    23,
                    0,
                    5,
                    2,
                    "4.2 hours"
                ]
            }
            
            df_metrics = pd.DataFrame(metrics_data)
            st.dataframe(df_metrics, hide_index=True, use_container_width=True)
        
        with col2:
            st.subheader("Risk Metrics")
            
            risk_data = {
                "Metric": [
                    "Max Consecutive Losses",
                    "Max Single Loss",
                    "Max Single Win",
                    "Risk/Reward Ratio",
                    "Recovery Factor",
                    "Payoff Ratio",
                    "Expectancy"
                ],
                "Value": [
                    "2 trades",
                    "-₹4,200",
                    "+₹8,100",
                    "1:2.3",
                    "3.68x",
                    "1.14",
                    "₹620"
                ]
            }
            
            df_risk = pd.DataFrame(risk_data)
            st.dataframe(df_risk, hide_index=True, use_container_width=True)
    
    # TAB 3: Equity Curve
    with tab3:
        st.subheader("Cumulative Performance")
        
        # Generate equity curve
        dates = pd.date_range('2024-01-01', '2024-06-30', freq='D')
        equity = 100000 + np.cumsum(np.random.randn(len(dates)) * 150)
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=dates,
            y=equity,
            name='Equity Curve',
            fill='tozeroy',
            line=dict(color='#667eea', width=2)
        ))
        
        # Add underwater plot (drawdown)
        running_max = np.maximum.accumulate(equity)
        drawdown = ((equity - running_max) / running_max) * 100
        
        fig.add_trace(go.Scatter(
            x=dates,
            y=drawdown,
            name='Drawdown %',
            yaxis='y2',
            line=dict(color='#f44336', width=1, dash='dash')
        ))
        
        fig.update_layout(
            title="Equity Curve & Drawdown",
            xaxis_title="Date",
            yaxis_title="Equity (₹)",
            yaxis2=dict(title="Drawdown (%)", overlaying='y', side='right'),
            height=500,
            template='plotly_white',
            hovermode='x unified'
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # TAB 4: Trade Log
    with tab4:
        st.subheader("Detailed Trade History")
        
        # Sample trades
        trades_data = {
            "Trade #": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
            "Date": pd.date_range('2024-01-01', periods=10),
            "Strategy": ["Iron Condor", "Bull Spread", "Iron Condor", "Bull Spread", 
                        "Iron Condor", "Straddle", "Bull Spread", "Iron Condor", 
                        "Bull Spread", "Iron Condor"],
            "Entry": ["23800 CE", "2320 CE", "23900 PE", "23700 PE", "24000 CE",
                     "24000 ATM", "2340 CE", "23850 PE", "2330 CE", "23900 CE"],
            "Exit": ["23850 CE", "2330 CE", "23950 PE", "23750 PE", "24050 CE",
                    "24100 ATM", "2345 CE", "23900 PE", "2335 CE", "23950 CE"],
            "Entry Price": [150, 80, 120, 100, 200, 250, 90, 110, 85, 160],
            "Exit Price": [180, 95, 145, 85, 220, 280, 105, 95, 98, 185],
            "P&L": [300, 150, 250, -150, 200, 300, 150, -100, 130, 250],
            "P&L %": [2.0, 1.9, 2.1, -1.5, 1.0, 1.2, 1.7, -0.9, 1.5, 1.6],
            "Duration": ["2h 15m", "3h 45m", "1h 30m", "5h 00m", "4h 20m",
                        "6h 10m", "2h 45m", "3h 15m", "2h 30m", "4h 00m"]
        }
        
        df_trades = pd.DataFrame(trades_data)
        
        # Display with filtering
        col1, col2, col3 = st.columns(3)
        
        with col1:
            filter_strategy = st.multiselect(
                "Filter by Strategy",
                df_trades['Strategy'].unique(),
                default=df_trades['Strategy'].unique()
            )
        
        with col2:
            filter_pnl = st.radio("Filter by Result", ["All", "Profits", "Losses"])
        
        with col3:
            show_count = st.slider("Show trades", 5, 20, 10)
        
        # Apply filters
        df_filtered = df_trades[df_trades['Strategy'].isin(filter_strategy)]
        
        if filter_pnl == "Profits":
            df_filtered = df_filtered[df_filtered['P&L'] > 0]
        elif filter_pnl == "Losses":
            df_filtered = df_filtered[df_filtered['P&L'] < 0]
        
        st.dataframe(
            df_filtered.head(show_count),
            use_container_width=True,
            hide_index=True
        )
        
        # Export button
        csv = df_trades.to_csv(index=False)
        st.download_button(
            label="📥 Download Trade Log (CSV)",
            data=csv,
            file_name="backtest_trades.csv",
            mime="text/csv",
            use_container_width=True
        )

if __name__ == "__main__":
    show_backtest_results()
