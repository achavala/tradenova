"""
Performance Analytics Page
Detailed performance metrics and analysis
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path
import sys
from datetime import datetime, timedelta
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from logs.metrics_tracker import MetricsTracker

st.title("📈 Performance Analytics")

# Load data
@st.cache_data(ttl=30)
def load_performance_data():
    tracker = MetricsTracker()
    metrics = tracker.calculate_metrics()
    agent_perf = tracker.get_agent_performance()
    return metrics, agent_perf, tracker.trades

try:
    metrics, agent_perf, trades = load_performance_data()
    
    # Overall Performance
    st.subheader("Overall Performance")
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Total Trades", metrics.get('total_trades', 0))
    with col2:
        st.metric("Win Rate", f"{metrics.get('win_rate', 0):.1f}%")
    with col3:
        st.metric("Total P&L", f"${metrics.get('total_pnl', 0):,.2f}")
    with col4:
        st.metric("Sharpe Ratio", f"{metrics.get('sharpe_ratio', 0):.2f}")
    with col5:
        st.metric("Max Drawdown", f"${metrics.get('max_drawdown', 0):,.2f}")
    
    st.markdown("---")
    
    # Agent Performance
    if agent_perf:
        st.subheader("Agent Performance")
        agent_df = pd.DataFrame(agent_perf).T
        agent_df = agent_df.sort_values('total_pnl', ascending=False)
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Bar chart
            fig = px.bar(
                agent_df,
                x=agent_df.index,
                y='total_pnl',
                title="P&L by Agent",
                color='total_pnl',
                color_continuous_scale='RdYlGn'
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Win rate chart
            fig = px.bar(
                agent_df,
                x=agent_df.index,
                y='win_rate',
                title="Win Rate by Agent",
                color='win_rate',
                color_continuous_scale='RdYlGn'
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        
        # Agent table
        st.dataframe(agent_df, use_container_width=True)
    
    # Trade Analysis
    if trades and len(trades) > 0:
        st.markdown("---")
        st.subheader("Trade Analysis")
        
        df = pd.DataFrame(trades)
        
        # P&L Distribution
        col1, col2 = st.columns(2)
        
        with col1:
            fig = go.Figure()
            fig.add_trace(go.Histogram(
                x=df['pnl'],
                nbinsx=30,
                name='P&L Distribution',
                marker_color='blue'
            ))
            fig.update_layout(
                title="P&L Distribution",
                xaxis_title="P&L ($)",
                yaxis_title="Frequency",
                height=300
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Cumulative P&L
            df_sorted = df.sort_values('entry_time' if 'entry_time' in df.columns else 'symbol')
            df_sorted['cumulative_pnl'] = df_sorted['pnl'].cumsum()
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=range(len(df_sorted)),
                y=df_sorted['cumulative_pnl'],
                mode='lines',
                name='Cumulative P&L',
                line=dict(color='green', width=2)
            ))
            fig.update_layout(
                title="Cumulative P&L Over Time",
                xaxis_title="Trade Number",
                yaxis_title="Cumulative P&L ($)",
                height=300
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # Performance by Symbol
        if 'symbol' in df.columns:
            st.subheader("Performance by Symbol")
            symbol_perf = df.groupby('symbol')['pnl'].agg(['sum', 'count', 'mean']).reset_index()
            symbol_perf.columns = ['Symbol', 'Total P&L', 'Trades', 'Avg P&L']
            symbol_perf = symbol_perf.sort_values('Total P&L', ascending=False)
            
            fig = px.bar(
                symbol_perf,
                x='Symbol',
                y='Total P&L',
                title="P&L by Symbol",
                color='Total P&L',
                color_continuous_scale='RdYlGn'
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
            
            st.dataframe(symbol_perf, use_container_width=True)
    
    else:
        st.info("No trade data available for analysis")

except Exception as e:
    st.error(f"Error loading performance data: {e}")
    import traceback
    st.code(traceback.format_exc())

