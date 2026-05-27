"""History Page - Trade Journal & Performance Analytics."""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from database import get_database
from logger import logger


def show_history():
    """Trade history and performance analytics dashboard."""
    
    st.title("📋 Trade History")
    st.caption("Complete trade journal and performance analytics")
    
    db = get_database()
    
    # Tabs
    tab1, tab2, tab3 = st.tabs(["📊 Analytics", "📈 Charts", "📋 Trade Log"])
    
    # Get trade statistics
    stats = db.get_trade_stats()
    closed_trades = db.get_closed_trades(limit=500)
    
    # Analytics Tab
    with tab1:
        st.subheader("📊 Performance Summary")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Trades", stats['total_trades'])
        with col2:
            st.metric("Win Rate", f"{stats['win_rate']:.1f}%")
        with col3:
            color = "normal" if stats['total_pnl'] >= 0 else "inverse"
            st.metric("Total P&L", f"₹{stats['total_pnl']:.0f}", delta_color=color)
        with col4:
            if stats['total_trades'] > 0:
                avg_pnl = stats['total_pnl'] / stats['total_trades']
                st.metric("Avg P&L per trade", f"₹{avg_pnl:.0f}")
        
        st.divider()
        
        # Detailed metrics
        col1, col2, col3 = st.columns(3)
        
        if closed_trades:
            pnl_values = [t['pnl'] for t in closed_trades if t['pnl']]
            
            with col1:
                st.metric("Wins", stats['wins'])
                st.metric("Losses", stats['losses'])
            
            with col2:
                if pnl_values:
                    max_profit = max(pnl_values)
                    st.metric("Best Trade", f"₹{max_profit:.0f}")
                    
                    worst_loss = min(pnl_values)
                    st.metric("Worst Trade", f"₹{worst_loss:.0f}")
            
            with col3:
                if stats['wins'] > 0:
                    avg_win = sum([p for p in pnl_values if p > 0]) / stats['wins']
                    st.metric("Avg Win", f"₹{avg_win:.0f}")
                
                if stats['losses'] > 0:
                    avg_loss = sum([p for p in pnl_values if p < 0]) / stats['losses']
                    st.metric("Avg Loss", f"₹{avg_loss:.0f}")
        
        st.divider()
        
        # Risk metrics
        st.subheader("⚠️ Risk Metrics")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if stats['total_trades'] > 0:
                avg_trades_per_day = stats['total_trades'] / 20  # 20 trading days assumption
                st.metric("Avg Trades/Day", f"{avg_trades_per_day:.1f}")
        
        with col2:
            if stats['wins'] > 0 and stats['losses'] > 0:
                profit_factor = sum([p for p in pnl_values if p > 0]) / abs(sum([p for p in pnl_values if p < 0]))
                st.metric("Profit Factor", f"{profit_factor:.2f}")
        
        with col3:
            if stats['total_trades'] > 0:
                avg_duration_minutes = 30  # Mock value
                st.metric("Avg Trade Duration", f"{avg_duration_minutes} min")
    
    # Charts Tab
    with tab2:
        st.subheader("📈 Performance Charts")
        
        if closed_trades:
            # Extract P&L values
            pnl_values = [t['pnl'] for t in closed_trades if t['pnl']]
            
            # P&L Distribution
            col1, col2 = st.columns(2)
            
            with col1:
                fig = go.Figure()
                fig.add_trace(go.Histogram(
                    x=pnl_values,
                    nbinsx=20,
                    name="P&L",
                    marker_color='#667eea'
                ))
                fig.update_layout(
                    title="P&L Distribution",
                    xaxis_title="Profit/Loss (₹)",
                    yaxis_title="Frequency",
                    height=400,
                    template="plotly_white"
                )
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                # Cumulative P&L
                cumulative_pnl = []
                running_total = 0
                for pnl in pnl_values:
                    running_total += pnl
                    cumulative_pnl.append(running_total)
                
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    y=cumulative_pnl,
                    mode='lines',
                    name='Cumulative P&L',
                    line=dict(color='#764ba2', width=2)
                ))
                fig.update_layout(
                    title="Cumulative P&L",
                    xaxis_title="Trade #",
                    yaxis_title="Cumulative P&L (₹)",
                    height=400,
                    template="plotly_white",
                    hovermode='x unified'
                )
                st.plotly_chart(fig, use_container_width=True)
            
            # Win/Loss breakdown
            col1, col2 = st.columns(2)
            
            with col1:
                win_values = [p for p in pnl_values if p > 0]
                loss_values = [p for p in pnl_values if p < 0]
                
                fig = go.Figure(data=[
                    go.Bar(name='Wins', x=['Total'], y=[sum(win_values) if win_values else 0], marker_color='#4caf50'),
                    go.Bar(name='Losses', x=['Total'], y=[sum(loss_values) if loss_values else 0], marker_color='#f44336')
                ])
                fig.update_layout(
                    title="Wins vs Losses",
                    height=400,
                    template="plotly_white"
                )
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                fig = go.Figure(data=[go.Pie(
                    labels=['Wins', 'Losses'],
                    values=[stats['wins'], stats['losses']],
                    marker=dict(colors=['#4caf50', '#f44336'])
                )])
                fig.update_layout(title="Win/Loss Ratio", height=400)
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No closed trades yet to display charts", icon="📭")
    
    # Trade Log Tab
    with tab3:
        st.subheader("📋 Complete Trade Log")
        
        if closed_trades:
            # Create dataframe
            trade_log_data = []
            for trade in closed_trades:
                entry_time = trade['entry_time'].split('T')[0] if trade['entry_time'] else "—"
                exit_time = trade['exit_time'].split('T')[0] if trade['exit_time'] else "—"
                pnl_icon = "✅" if trade['pnl'] > 0 else "❌"
                
                trade_log_data.append({
                    "ID": trade['id'],
                    "Symbol": trade['symbol'],
                    "Side": trade['side'],
                    "Qty": trade['quantity'],
                    "Entry": f"₹{trade['entry_price']:.2f}",
                    "Exit": f"₹{trade['exit_price']:.2f}" if trade['exit_price'] else "—",
                    "Entry Date": entry_time,
                    "Exit Date": exit_time,
                    "P&L": f"{pnl_icon} ₹{trade['pnl']:.0f}",
                    "P&L%": f"{trade['pnl_pct']:+.2f}%" if trade['pnl_pct'] else "—",
                    "Type": trade['order_type']
                })
            
            df_log = pd.DataFrame(trade_log_data)
            
            # Display with filtering
            col1, col2 = st.columns(2)
            
            with col1:
                symbol_filter = st.multiselect(
                    "Filter by Symbol",
                    options=df_log['Symbol'].unique().tolist(),
                    default=None
                )
            
            with col2:
                side_filter = st.multiselect(
                    "Filter by Side",
                    options=['BUY', 'SELL'],
                    default=None
                )
            
            # Apply filters
            filtered_df = df_log
            if symbol_filter:
                filtered_df = filtered_df[filtered_df['Symbol'].isin(symbol_filter)]
            if side_filter:
                filtered_df = filtered_df[filtered_df['Side'].isin(side_filter)]
            
            st.dataframe(filtered_df, use_container_width=True, hide_index=True)
            
            # Download option
            csv = filtered_df.to_csv(index=False)
            st.download_button(
                label="📥 Download as CSV",
                data=csv,
                file_name="trade_history.csv",
                mime="text/csv"
            )
        else:
            st.info("No trades recorded yet", icon="📭")
