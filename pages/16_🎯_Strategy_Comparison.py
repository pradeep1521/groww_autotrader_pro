"""Strategy Comparison - Compare backtested strategies side-by-side."""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from strategy_comparison import StrategyComparison

st.set_page_config(page_title="Strategy Comparison", layout="wide")

st.title("🎯 Strategy Comparison Dashboard")
st.markdown("Compare multiple backtested strategies side-by-side")

# Initialize comparison
@st.cache_resource
def init_comparison():
    return StrategyComparison()

comparison = init_comparison()

# Sample data (in production, load from database)
@st.cache_data
def load_sample_strategies():
    """Load sample strategy backtests."""
    
    # Strategy 1: Iron Condor
    trades_iron_condor = [
        {'pnl': 2000, 'open_date': datetime(2025, 1, 1), 'close_date': datetime(2025, 1, 5)},
        {'pnl': -500, 'open_date': datetime(2025, 1, 6), 'close_date': datetime(2025, 1, 8)},
        {'pnl': 3000, 'open_date': datetime(2025, 1, 9), 'close_date': datetime(2025, 1, 15)},
        {'pnl': 1500, 'open_date': datetime(2025, 1, 16), 'close_date': datetime(2025, 1, 20)},
        {'pnl': -200, 'open_date': datetime(2025, 1, 21), 'close_date': datetime(2025, 1, 25)},
        {'pnl': 2500, 'open_date': datetime(2025, 1, 26), 'close_date': datetime(2025, 1, 31)},
    ]
    
    # Strategy 2: Bull Call Spread
    trades_bull_call = [
        {'pnl': 1000, 'open_date': datetime(2025, 1, 1), 'close_date': datetime(2025, 1, 4)},
        {'pnl': 800, 'open_date': datetime(2025, 1, 5), 'close_date': datetime(2025, 1, 8)},
        {'pnl': -300, 'open_date': datetime(2025, 1, 9), 'close_date': datetime(2025, 1, 12)},
        {'pnl': 1200, 'open_date': datetime(2025, 1, 13), 'close_date': datetime(2025, 1, 16)},
        {'pnl': 950, 'open_date': datetime(2025, 1, 17), 'close_date': datetime(2025, 1, 20)},
        {'pnl': 1100, 'open_date': datetime(2025, 1, 21), 'close_date': datetime(2025, 1, 25)},
        {'pnl': 600, 'open_date': datetime(2025, 1, 26), 'close_date': datetime(2025, 1, 31)},
    ]
    
    # Strategy 3: Bull Put Spread
    trades_bull_put = [
        {'pnl': 1500, 'open_date': datetime(2025, 1, 1), 'close_date': datetime(2025, 1, 6)},
        {'pnl': 1200, 'open_date': datetime(2025, 1, 7), 'close_date': datetime(2025, 1, 12)},
        {'pnl': -800, 'open_date': datetime(2025, 1, 13), 'close_date': datetime(2025, 1, 18)},
        {'pnl': 1000, 'open_date': datetime(2025, 1, 19), 'close_date': datetime(2025, 1, 25)},
        {'pnl': 900, 'open_date': datetime(2025, 1, 26), 'close_date': datetime(2025, 1, 31)},
    ]
    
    # Load into comparison
    comparison.add_strategy("Iron Condor", trades_iron_condor, capital=100000)
    comparison.add_strategy("Bull Call Spread", trades_bull_call, capital=100000)
    comparison.add_strategy("Bull Put Spread", trades_bull_put, capital=100000)

load_sample_strategies()

# Tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Metrics Comparison",
    "🏆 Rankings",
    "📈 Equity Curves",
    "📉 Drawdown Analysis",
    "📅 Monthly Returns"
])

# Tab 1: Metrics Comparison
with tab1:
    st.subheader("Performance Metrics Comparison")
    
    metrics_df = comparison.comparison_table()
    
    col1, col2 = st.columns([1, 3])
    
    with col1:
        # Metric selector
        metric_options = [
            'Total Return',
            'Annual Return',
            'Sharpe',
            'Sortino',
            'Max DD',
            'Win Rate',
            'Profit Factor',
            'Total Trades',
            'Avg Trade'
        ]
        
        selected_metric = st.selectbox(
            "Select metric to highlight",
            metric_options,
            index=0
        )
    
    with col2:
        # Display full table
        st.dataframe(
            metrics_df.style.highlight_max(
                axis=0,
                color='lightgreen'
            ).highlight_min(
                axis=0,
                color='lightcoral'
            ),
            use_container_width=True,
            height=400
        )
    
    # Horizontal bar charts for key metrics
    st.subheader("Key Metrics Visualization")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Total Return
        return_data = []
        for name, strat in comparison.strategies.items():
            return_data.append({
                'Strategy': name,
                'Return': strat['metrics'].total_return * 100
            })
        return_df = pd.DataFrame(return_data)
        
        fig_return = go.Figure(data=[
            go.Bar(x=return_df['Return'], y=return_df['Strategy'], orientation='h')
        ])
        fig_return.update_layout(
            title="Total Return %",
            xaxis_title="Return (%)",
            height=300,
            showlegend=False
        )
        st.plotly_chart(fig_return, use_container_width=True)
    
    with col2:
        # Sharpe Ratio
        sharpe_data = []
        for name, strat in comparison.strategies.items():
            sharpe_data.append({
                'Strategy': name,
                'Sharpe': strat['metrics'].sharpe_ratio
            })
        sharpe_df = pd.DataFrame(sharpe_data)
        
        fig_sharpe = go.Figure(data=[
            go.Bar(x=sharpe_df['Sharpe'], y=sharpe_df['Strategy'], orientation='h')
        ])
        fig_sharpe.update_layout(
            title="Sharpe Ratio",
            xaxis_title="Sharpe",
            height=300,
            showlegend=False
        )
        st.plotly_chart(fig_sharpe, use_container_width=True)
    
    with col3:
        # Win Rate
        winrate_data = []
        for name, strat in comparison.strategies.items():
            winrate_data.append({
                'Strategy': name,
                'Win Rate': strat['metrics'].win_rate * 100
            })
        winrate_df = pd.DataFrame(winrate_data)
        
        fig_winrate = go.Figure(data=[
            go.Bar(x=winrate_df['Win Rate'], y=winrate_df['Strategy'], orientation='h')
        ])
        fig_winrate.update_layout(
            title="Win Rate %",
            xaxis_title="Win Rate (%)",
            height=300,
            showlegend=False
        )
        st.plotly_chart(fig_winrate, use_container_width=True)

# Tab 2: Rankings
with tab2:
    st.subheader("Strategy Rankings")
    
    ranking_df = comparison.ranking()
    
    st.dataframe(
        ranking_df.style.highlight_min(
            subset=['Rank'],
            color='lightgreen'
        ),
        use_container_width=True,
        height=300
    )
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("Top Strategy by Return", ranking_df.iloc[0]['Strategy'])
    
    with col2:
        st.metric("Highest Sharpe Ratio", ranking_df.loc[ranking_df['By Sharpe'] == 1, 'Strategy'].values[0] if len(ranking_df[ranking_df['By Sharpe'] == 1]) > 0 else "N/A")

# Tab 3: Equity Curves
with tab3:
    st.subheader("Equity Curve Comparison")
    
    curves = comparison.equity_curve_comparison()
    
    fig_equity = go.Figure()
    
    for strategy_name, equity_values in curves.items():
        fig_equity.add_trace(go.Scatter(
            y=equity_values,
            mode='lines',
            name=strategy_name,
            hovertemplate='Trade: %{x}<br>Equity: ₹%{y:,.0f}<extra></extra>'
        ))
    
    fig_equity.update_layout(
        title="Equity Curve Comparison",
        xaxis_title="Trade Number",
        yaxis_title="Portfolio Value (₹)",
        hovermode='x unified',
        height=500
    )
    
    st.plotly_chart(fig_equity, use_container_width=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.info("📈 Equity curves show cumulative account value over trades. Steeper slope indicates faster growth.")
    
    with col2:
        st.success("✅ Use this to visualize strategy performance over time and identify drawdown periods.")

# Tab 4: Drawdown Analysis
with tab4:
    st.subheader("Drawdown Comparison")
    
    drawdowns = comparison.drawdown_comparison()
    
    fig_dd = go.Figure()
    
    for strategy_name, dd_values in drawdowns.items():
        fig_dd.add_trace(go.Scatter(
            y=dd_values,
            mode='lines',
            name=strategy_name,
            fill='tozeroy',
            hovertemplate='Trade: %{x}<br>Drawdown: %{y:.2f}%<extra></extra>'
        ))
    
    fig_dd.update_layout(
        title="Drawdown Analysis",
        xaxis_title="Trade Number",
        yaxis_title="Drawdown (%)",
        hovermode='x unified',
        height=500
    )
    
    st.plotly_chart(fig_dd, use_container_width=True)
    
    # Max drawdown comparison
    col1, col2, col3 = st.columns(3)
    
    for i, (name, strat) in enumerate(comparison.strategies.items()):
        if i % 3 == 0:
            col = col1
        elif i % 3 == 1:
            col = col2
        else:
            col = col3
        
        with col:
            st.metric(
                f"{name} Max DD",
                f"{strat['metrics'].max_drawdown * 100:.2f}%"
            )

# Tab 5: Monthly Returns
with tab5:
    st.subheader("Monthly Returns Breakdown")
    
    monthly = comparison.monthly_returns()
    
    cols = st.columns(len(monthly))
    
    for i, (strategy_name, monthly_df) in enumerate(monthly.items()):
        with cols[i]:
            st.write(f"### {strategy_name}")
            
            fig_monthly = go.Figure(data=[
                go.Bar(
                    x=monthly_df['Month'],
                    y=monthly_df['Return%'],
                    name='Monthly Return',
                    hovertemplate='Month: %{x}<br>Return: %{y:.2f}%<extra></extra>'
                )
            ])
            
            fig_monthly.update_layout(
                height=400,
                showlegend=False,
                xaxis_title="Month",
                yaxis_title="Return (%)"
            )
            
            st.plotly_chart(fig_monthly, use_container_width=True)
            
            # Summary stats
            st.dataframe(
                monthly_df.style.format({
                    'PnL': '₹{:.0f}',
                    'Return%': '{:.2f}%'
                }),
                use_container_width=True
            )

# Footer
st.divider()

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("📥 Export Comparison", key="export_comp"):
        # Generate CSV
        csv = comparison.comparison_table().to_csv(index=False)
        st.download_button(
            label="Download as CSV",
            data=csv,
            file_name=f"strategy_comparison_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )

with col2:
    if st.button("🔄 Refresh Data", key="refresh_comp"):
        st.rerun()

with col3:
    st.info("💡 Tip: Use rankings to identify the best strategy for your risk tolerance. Compare Sharpe for risk-adjusted returns.")
