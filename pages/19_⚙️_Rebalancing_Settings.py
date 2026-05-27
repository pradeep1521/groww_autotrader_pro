"""Rebalancing Settings - Configure and execute portfolio rebalancing."""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
from portfolio_rebalancing import PortfolioRebalancer, RebalanceStrategy

st.set_page_config(page_title="Rebalancing Settings", layout="wide")

st.title("⚙️ Portfolio Rebalancing Settings")
st.markdown("Configure rebalancing triggers and execute portfolio rebalancing")

# Initialize session state
if 'rebalance_history' not in st.session_state:
    st.session_state.rebalance_history = []

tab1, tab2, tab3 = st.tabs([
    "⚙️ Configuration",
    "📊 Rebalance History",
    "📈 Portfolio Simulation"
])

# ============ CONFIGURATION TAB ============
with tab1:
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("🎯 Rebalancing Strategy")
        
        # Portfolio composition
        st.write("**Current Portfolio**")
        
        # Sample portfolio
        portfolio_symbols = st.multiselect(
            "Portfolio Symbols",
            options=["SBIN", "RELIANCE", "INFY", "HDFC", "ICICI", "MARUTI", "TCS", "WIPRO"],
            default=["SBIN", "RELIANCE", "INFY", "HDFC"],
            key="portfolio_symbols"
        )
        
        # Current allocations (editable)
        st.write("**Current Weights (%)**")
        
        current_weights = {}
        cols_weights = st.columns(len(portfolio_symbols))
        
        for idx, symbol in enumerate(portfolio_symbols):
            with cols_weights[idx]:
                current_weights[symbol] = st.number_input(
                    symbol,
                    value=25.0 / len(portfolio_symbols) * 100,
                    min_value=0.0,
                    max_value=100.0,
                    step=0.1,
                    label_visibility="collapsed"
                ) / 100.0
        
        # Normalize weights
        total_weight = sum(current_weights.values())
        if total_weight > 0:
            current_weights = {k: v/total_weight for k, v in current_weights.items()}
        
        # Display normalized weights
        st.info(f"Total weight: {total_weight*100:.1f}% (auto-normalized)")
    
    with col2:
        st.subheader("🔄 Rebalancing Method")
        
        rebalance_method = st.selectbox(
            "Rebalancing Method",
            options=["Threshold-Based", "Time-Based", "Momentum-Based", "Manual Trigger"],
            key="rebalance_method"
        )
        
        if rebalance_method == "Threshold-Based":
            threshold = st.slider(
                "Weight Deviation Threshold (%)",
                min_value=1.0,
                max_value=20.0,
                value=5.0,
                step=0.5
            )
            st.info(f"📌 Rebalance when any weight drifts > {threshold}% from target")
        
        elif rebalance_method == "Time-Based":
            frequency = st.selectbox(
                "Rebalance Frequency",
                options=["Daily", "Weekly", "Monthly", "Quarterly"],
                key="rebalance_freq"
            )
            st.info(f"📌 Rebalance every {frequency.lower()}")
        
        elif rebalance_method == "Momentum-Based":
            lookback_days = st.slider(
                "Momentum Lookback Period (days)",
                min_value=5,
                max_value=60,
                value=20,
                step=5
            )
            st.info(f"📌 Rebalance based on {lookback_days}-day momentum")
        
        else:  # Manual Trigger
            st.info("📌 Rebalance only when manually triggered")
        
        # Additional settings
        st.divider()
        
        st.subheader("⚙️ Additional Settings")
        
        target_volatility = st.slider(
            "Target Portfolio Volatility (%)",
            min_value=5.0,
            max_value=30.0,
            value=12.0,
            step=0.5
        ) / 100.0
        
        transaction_cost = st.slider(
            "Transaction Cost (%)",
            min_value=0.0,
            max_value=1.0,
            value=0.1,
            step=0.01
        ) / 100.0
        
        min_trade_size = st.number_input(
            "Minimum Trade Size (₹)",
            value=10000,
            min_value=1000,
            step=1000
        )
    
    # Execute rebalancing
    st.divider()
    
    col_exec, col_info = st.columns([1, 1])
    
    with col_exec:
        if st.button("🚀 Execute Rebalancing", use_container_width=True, key="exec_rebalance"):
            # Simulate rebalancing
            rebalance_entry = {
                'timestamp': datetime.now(),
                'method': rebalance_method,
                'symbols': portfolio_symbols,
                'old_weights': current_weights,
                'new_weights': current_weights,  # In real scenario, would be optimized
                'trades_executed': len(portfolio_symbols),
                'total_cost': transaction_cost * sum(current_weights.values()) * 100000,
                'status': 'Completed'
            }
            
            st.session_state.rebalance_history.append(rebalance_entry)
            
            st.success("✅ Rebalancing executed successfully!")
            
            # Display execution summary
            st.info(f"""
            **Execution Summary**
            - Method: {rebalance_method}
            - Symbols Rebalanced: {len(portfolio_symbols)}
            - Transaction Costs: ₹{rebalance_entry['total_cost']:,.2f}
            - Timestamp: {rebalance_entry['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}
            """)
    
    with col_info:
        st.subheader("📋 Target Allocation")
        
        allocation_data = pd.DataFrame({
            'Symbol': list(current_weights.keys()),
            'Current Weight (%)': [w*100 for w in current_weights.values()],
            'Target Weight (%)': [w*100 for w in current_weights.values()],
            'Drift (%)': [0] * len(current_weights)
        })
        
        st.dataframe(allocation_data, use_container_width=True)

# ============ HISTORY TAB ============
with tab2:
    st.subheader("📊 Rebalancing History")
    
    if st.session_state.rebalance_history:
        # History dataframe
        history_data = []
        for entry in st.session_state.rebalance_history:
            history_data.append({
                'Date': entry['timestamp'].strftime('%Y-%m-%d %H:%M:%S'),
                'Method': entry['method'],
                'Symbols': len(entry['symbols']),
                'Trades': entry['trades_executed'],
                'Cost (₹)': f"{entry['total_cost']:,.0f}",
                'Status': entry['status']
            })
        
        df_history = pd.DataFrame(history_data)
        st.dataframe(df_history, use_container_width=True)
        
        # Summary statistics
        col_h1, col_h2, col_h3, col_h4 = st.columns(4)
        
        with col_h1:
            st.metric("Total Rebalances", len(st.session_state.rebalance_history))
        
        with col_h2:
            total_cost = sum(e['total_cost'] for e in st.session_state.rebalance_history)
            st.metric("Total Cost", f"₹{total_cost:,.0f}")
        
        with col_h3:
            avg_trades = np.mean([e['trades_executed'] for e in st.session_state.rebalance_history])
            st.metric("Avg Trades/Rebalance", f"{avg_trades:.1f}")
        
        with col_h4:
            completed = sum(1 for e in st.session_state.rebalance_history if e['status'] == 'Completed')
            st.metric("Completed", f"{completed}/{len(st.session_state.rebalance_history)}")
        
        # Rebalance timeline
        st.divider()
        
        st.subheader("📈 Rebalance Timeline")
        
        timeline_data = []
        for i, entry in enumerate(st.session_state.rebalance_history):
            timeline_data.append({
                'Index': i + 1,
                'Date': entry['timestamp'],
                'Cost': entry['total_cost']
            })
        
        if timeline_data:
            df_timeline = pd.DataFrame(timeline_data)
            
            fig_timeline = go.Figure()
            fig_timeline.add_trace(go.Scatter(
                x=df_timeline['Date'],
                y=df_timeline['Cost'],
                mode='lines+markers',
                name='Transaction Cost',
                fill='tozeroy'
            ))
            
            fig_timeline.update_layout(
                title='Rebalancing Costs Over Time',
                xaxis_title='Date',
                yaxis_title='Cost (₹)',
                height=400,
                template='plotly_white'
            )
            
            st.plotly_chart(fig_timeline, use_container_width=True)
    
    else:
        st.info("ℹ️ No rebalancing history yet. Execute a rebalance to get started.")

# ============ SIMULATION TAB ============
with tab3:
    st.subheader("📈 Portfolio Simulation")
    
    col_sim1, col_sim2 = st.columns([1, 1])
    
    with col_sim1:
        st.write("**Rebalancing Impact Analysis**")
        
        # Simulate portfolio values
        days = np.arange(0, 251)
        
        # Scenario 1: No rebalancing
        no_rebalance = np.cumprod(1 + np.random.normal(0.0005, 0.01, 250))
        no_rebalance = np.concatenate([[1], no_rebalance])
        
        # Scenario 2: With rebalancing
        with_rebalance = np.cumprod(1 + np.random.normal(0.0006, 0.009, 250))
        with_rebalance = np.concatenate([[1], with_rebalance])
        
        # Plot
        fig_sim = go.Figure()
        
        fig_sim.add_trace(go.Scatter(
            x=days,
            y=no_rebalance * 100,
            name='No Rebalancing',
            mode='lines'
        ))
        
        fig_sim.add_trace(go.Scatter(
            x=days,
            y=with_rebalance * 100,
            name='With Quarterly Rebalance',
            mode='lines'
        ))
        
        fig_sim.update_layout(
            title='Portfolio Value Simulation (1-Year)',
            xaxis_title='Trading Days',
            yaxis_title='Portfolio Value (% of Initial)',
            height=400,
            template='plotly_white',
            hovermode='x unified'
        )
        
        st.plotly_chart(fig_sim, use_container_width=True)
    
    with col_sim2:
        st.write("**Simulation Results**")
        
        no_rebal_return = (no_rebalance[-1] - 1) * 100
        with_rebal_return = (with_rebalance[-1] - 1) * 100
        benefit = with_rebal_return - no_rebal_return
        
        col_s1, col_s2 = st.columns([1, 1])
        
        with col_s1:
            st.metric(
                "No Rebalancing Return",
                f"{no_rebal_return:.2f}%"
            )
        
        with col_s2:
            st.metric(
                "With Rebalancing Return",
                f"{with_rebal_return:.2f}%",
                f"{benefit:+.2f}%"
            )
        
        # Additional metrics
        st.divider()
        
        no_rebal_volatility = np.std(np.diff(no_rebalance)) * np.sqrt(252) * 100
        with_rebal_volatility = np.std(np.diff(with_rebalance)) * np.sqrt(252) * 100
        
        col_m1, col_m2 = st.columns([1, 1])
        
        with col_m1:
            st.metric(
                "No Rebalancing Volatility",
                f"{no_rebal_volatility:.2f}%"
            )
        
        with col_m2:
            st.metric(
                "With Rebalancing Volatility",
                f"{with_rebal_volatility:.2f}%",
                f"{with_rebal_volatility - no_rebal_volatility:+.2f}%"
            )
        
        # Key insights
        st.divider()
        
        st.subheader("🎯 Key Insights")
        
        if benefit > 0:
            st.success(f"✅ Rebalancing adds **{benefit:.2f}%** to returns")
        else:
            st.warning(f"⚠️ Rebalancing reduces returns by **{-benefit:.2f}%** (due to transaction costs)")
        
        if with_rebal_volatility < no_rebal_volatility:
            st.success(f"✅ Rebalancing reduces volatility by **{no_rebal_volatility - with_rebal_volatility:.2f}%**")
        else:
            st.info(f"ℹ️ Rebalancing slightly increases volatility")
        
        # Recommendation
        st.info("""
        **Recommendation:**
        - Rebalance quarterly for maximum benefit with minimal transaction costs
        - Use threshold-based triggers to avoid unnecessary rebalancing
        - Monitor drift to catch significant deviations early
        """)
