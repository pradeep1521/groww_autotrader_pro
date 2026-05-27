"""Portfolio Optimization - Markowitz and Risk Parity allocation."""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from portfolio_rebalancing import Markowitz, RiskParity, CovarianceMatrix, PortfolioRebalancer

st.set_page_config(page_title="Portfolio Optimization", layout="wide")

st.title("💼 Portfolio Optimization")
st.markdown("Optimize portfolio allocation using Markowitz and Risk Parity methods")

tab1, tab2, tab3 = st.tabs([
    "📊 Optimization",
    "📈 Efficient Frontier",
    "🎯 Allocation Comparison"
])

# ============ OPTIMIZATION TAB ============
with tab1:
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("⚙️ Optimization Settings")
        
        # Input symbols
        symbols_input = st.text_area(
            "Portfolio Symbols (comma-separated)",
            value="SBIN,RELIANCE,INFY,HDFC,ICICI",
            height=100
        )
        symbols = [s.strip().upper() for s in symbols_input.split(",") if s.strip()]
        
        # Expected returns
        st.write("**Expected Annual Returns (%)**")
        expected_returns_dict = {}
        
        cols_returns = st.columns(len(symbols))
        for idx, symbol in enumerate(symbols):
            with cols_returns[idx]:
                expected_returns_dict[symbol] = st.number_input(
                    symbol,
                    value=15.0,
                    min_value=-50.0,
                    max_value=100.0,
                    step=0.5,
                    label_visibility="collapsed"
                ) / 100.0  # Convert to decimal
        
        # Optimization method
        method = st.radio(
            "Optimization Method",
            options=["Markowitz (Mean-Variance)", "Risk Parity", "Equal Weight"],
            horizontal=True
        )
        
        # Risk-free rate
        risk_free_rate = st.slider(
            "Risk-Free Rate (%)",
            min_value=0.0,
            max_value=10.0,
            value=5.0,
            step=0.1
        ) / 100.0
    
    with col2:
        st.subheader("📊 Volatility & Correlation")
        
        # Generate sample covariance matrix
        n_assets = len(symbols)
        
        # Create a sample covariance matrix with realistic values
        np.random.seed(42)
        
        # Generate correlation matrix
        correlation = np.eye(n_assets)
        for i in range(n_assets):
            for j in range(i+1, n_assets):
                corr_val = np.random.uniform(0.2, 0.8)
                correlation[i, j] = corr_val
                correlation[j, i] = corr_val
        
        # Volatilities (annualized returns standard deviations)
        volatilities = np.array([0.20 + np.random.uniform(-0.05, 0.05) for _ in range(n_assets)])
        
        # Create covariance matrix
        cov_matrix = np.outer(volatilities, volatilities) * correlation
        
        # Display correlation matrix
        st.write("**Correlation Matrix**")
        correlation_df = pd.DataFrame(
            correlation,
            columns=symbols,
            index=symbols
        )
        
        fig_corr = px.imshow(
            correlation_df,
            color_continuous_scale="RdBu",
            zmin=-1,
            zmax=1,
            aspect="auto",
            labels=dict(color="Correlation")
        )
        st.plotly_chart(fig_corr, use_container_width=True)
    
    # Run optimization
    if st.button("🚀 Optimize Portfolio", use_container_width=True, key="optimize_btn"):
        try:
            expected_returns = np.array([expected_returns_dict[s] for s in symbols])
            
            if method == "Markowitz (Mean-Variance)":
                markowitz = Markowitz(risk_free_rate=risk_free_rate)
                weights, sharpe, std = markowitz.optimal_portfolio(expected_returns, cov_matrix)
                method_name = "Markowitz"
            elif method == "Risk Parity":
                risk_parity = RiskParity()
                weights, sharpe, std = risk_parity.allocate(cov_matrix, target_volatility=0.12)
                method_name = "Risk Parity"
            else:  # Equal Weight
                weights = np.array([1.0 / n_assets] * n_assets)
                portfolio_return = np.dot(weights, expected_returns)
                std = np.sqrt(np.dot(weights, np.dot(cov_matrix, weights)))
                sharpe = (portfolio_return - risk_free_rate) / std if std > 0 else 0
                method_name = "Equal Weight"
            
            # Display results
            st.success(f"✅ Optimization completed using {method_name}")
            
            # Results metrics
            col_m1, col_m2, col_m3, col_m4 = st.columns(4)
            
            with col_m1:
                portfolio_return = np.dot(weights, expected_returns)
                st.metric("Expected Return", f"{portfolio_return*100:.2f}%")
            
            with col_m2:
                st.metric("Portfolio Volatility", f"{std*100:.2f}%")
            
            with col_m3:
                st.metric("Sharpe Ratio", f"{sharpe:.2f}")
            
            with col_m4:
                st.metric("# Assets", len(symbols))
            
            # Allocation pie chart
            col_chart, col_table = st.columns([1, 1])
            
            with col_chart:
                fig_pie = go.Figure(data=[go.Pie(
                    labels=symbols,
                    values=weights * 100,
                    marker=dict(line=dict(color='white', width=2))
                )])
                fig_pie.update_layout(
                    title="Portfolio Allocation",
                    height=400,
                    template="plotly_white"
                )
                st.plotly_chart(fig_pie, use_container_width=True)
            
            with col_table:
                allocation_df = pd.DataFrame({
                    'Symbol': symbols,
                    'Weight (%)': weights * 100,
                    'Expected Return (%)': expected_returns * 100,
                    'Volatility (%)': np.sqrt(np.diag(cov_matrix)) * 100
                }).sort_values('Weight (%)', ascending=False)
                
                st.dataframe(allocation_df, use_container_width=True)
            
            # Store in session for other tabs
            st.session_state.opt_weights = weights
            st.session_state.opt_symbols = symbols
            st.session_state.opt_expected_returns = expected_returns
            st.session_state.opt_cov_matrix = cov_matrix
            st.session_state.opt_method = method_name
        
        except Exception as e:
            st.error(f"❌ Optimization error: {e}")

# ============ EFFICIENT FRONTIER TAB ============
with tab2:
    st.subheader("📈 Efficient Frontier")
    
    if 'opt_weights' in st.session_state:
        symbols = st.session_state.opt_symbols
        expected_returns = st.session_state.opt_expected_returns
        cov_matrix = st.session_state.opt_cov_matrix
        weights = st.session_state.opt_weights
        
        # Generate efficient frontier
        n_portfolios = 100
        results = []
        
        for i in range(n_portfolios):
            # Random weights
            rand_weights = np.random.random(len(symbols))
            rand_weights /= np.sum(rand_weights)
            
            # Portfolio metrics
            p_return = np.dot(rand_weights, expected_returns)
            p_std = np.sqrt(np.dot(rand_weights, np.dot(cov_matrix, rand_weights)))
            p_sharpe = (p_return - 0.05) / p_std if p_std > 0 else 0
            
            results.append({
                'Return': p_return * 100,
                'Risk': p_std * 100,
                'Sharpe': p_sharpe,
                'Type': 'Random'
            })
        
        # Add optimal portfolio
        opt_return = np.dot(weights, expected_returns)
        opt_std = np.sqrt(np.dot(weights, np.dot(cov_matrix, weights)))
        opt_sharpe = (opt_return - 0.05) / opt_std if opt_std > 0 else 0
        
        results.append({
            'Return': opt_return * 100,
            'Risk': opt_std * 100,
            'Sharpe': opt_sharpe,
            'Type': 'Optimal'
        })
        
        df_frontier = pd.DataFrame(results)
        
        # Plot
        fig_frontier = px.scatter(
            df_frontier,
            x='Risk',
            y='Return',
            color='Sharpe',
            size='Sharpe',
            hover_data={'Type': True, 'Sharpe': ':.2f'},
            color_continuous_scale='Viridis',
            labels={'Risk': 'Portfolio Volatility (%)', 'Return': 'Expected Return (%)'},
            title='Efficient Frontier - Risk vs Return'
        )
        
        # Highlight optimal portfolio
        fig_frontier.add_scatter(
            x=[opt_std * 100],
            y=[opt_return * 100],
            mode='markers',
            marker=dict(size=15, color='red', symbol='star'),
            name='Optimal Portfolio',
            hovertemplate='<b>Optimal Portfolio</b><br>Risk: %{x:.2f}%<br>Return: %{y:.2f}%<extra></extra>'
        )
        
        fig_frontier.update_layout(height=500, template="plotly_white")
        st.plotly_chart(fig_frontier, use_container_width=True)
    
    else:
        st.info("ℹ️ Run optimization first to view efficient frontier")

# ============ COMPARISON TAB ============
with tab3:
    st.subheader("🎯 Allocation Comparison")
    
    if 'opt_symbols' in st.session_state:
        symbols = st.session_state.opt_symbols
        opt_weights = st.session_state.opt_weights
        expected_returns = st.session_state.opt_expected_returns
        cov_matrix = st.session_state.opt_cov_matrix
        
        # Compare with equal weight
        equal_weights = np.array([1.0 / len(symbols)] * len(symbols))
        
        comparison_data = []
        
        for i, symbol in enumerate(symbols):
            comparison_data.append({
                'Symbol': symbol,
                'Optimal (%)': opt_weights[i] * 100,
                'Equal Weight (%)': equal_weights[i] * 100,
                'Difference (%)': (opt_weights[i] - equal_weights[i]) * 100
            })
        
        df_comparison = pd.DataFrame(comparison_data).sort_values('Optimal (%)', ascending=False)
        st.dataframe(df_comparison, use_container_width=True)
        
        # Bar chart comparison
        fig_comparison = go.Figure(data=[
            go.Bar(name='Optimal', x=df_comparison['Symbol'], y=df_comparison['Optimal (%)']),
            go.Bar(name='Equal Weight', x=df_comparison['Symbol'], y=df_comparison['Equal Weight (%)'])
        ])
        
        fig_comparison.update_layout(
            title='Allocation Comparison',
            barmode='group',
            xaxis_title='Symbol',
            yaxis_title='Weight (%)',
            height=400,
            template="plotly_white"
        )
        
        st.plotly_chart(fig_comparison, use_container_width=True)
        
        # Summary statistics
        col_s1, col_s2, col_s3 = st.columns(3)
        
        opt_return = np.dot(opt_weights, expected_returns)
        opt_std = np.sqrt(np.dot(opt_weights, np.dot(cov_matrix, opt_weights)))
        
        eq_return = np.dot(equal_weights, expected_returns)
        eq_std = np.sqrt(np.dot(equal_weights, np.dot(cov_matrix, equal_weights)))
        
        with col_s1:
            st.metric("Optimal Return", f"{opt_return*100:.2f}%", f"{(opt_return-eq_return)*100:+.2f}%")
        
        with col_s2:
            st.metric("Optimal Risk", f"{opt_std*100:.2f}%", f"{(opt_std-eq_std)*100:+.2f}%")
        
        with col_s3:
            opt_sharpe = (opt_return - 0.05) / opt_std if opt_std > 0 else 0
            eq_sharpe = (eq_return - 0.05) / eq_std if eq_std > 0 else 0
            st.metric("Optimal Sharpe", f"{opt_sharpe:.2f}", f"{opt_sharpe - eq_sharpe:+.2f}")
    
    else:
        st.info("ℹ️ Run optimization first to view comparison")
