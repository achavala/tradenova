"""
Dashboard Page - Main Overview
Shows system status, metrics, and charts
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

st.set_page_config(
    page_title="Dashboard - TradeNova",
    page_icon="📊",
    layout="wide"
)

# Import and render persistent sidebar
from core.ui.sidebar import render_sidebar
render_sidebar()

st.title("📊 Dashboard Overview")

# Load recent trades for summary
@st.cache_data(ttl=30)
def load_recent_trades():
    """Load recent trades from backtest results"""
    trades = []
    logs_dir = Path('logs')
    backtest_files = list(logs_dir.glob('backtest_results_*.json'))
    backtest_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    
    for file_path in backtest_files[:1]:  # Just latest
        try:
            import json
            with open(file_path, 'r') as f:
                data = json.load(f)
                if 'trades' in data:
                    trades.extend(data['trades'])
        except:
            pass
    
    return trades

trades = load_recent_trades()

# Key Metrics
col1, col2, col3, col4 = st.columns(4)

with col1:
    total_trades = len(trades)
    st.metric("Total Trades", total_trades)

with col2:
    if trades:
        winning = len([t for t in trades if t.get('pnl', 0) > 0])
        win_rate = (winning / total_trades * 100) if total_trades > 0 else 0
        st.metric("Win Rate", f"{win_rate:.1f}%")
    else:
        st.metric("Win Rate", "0%")

with col3:
    if trades:
        total_pnl = sum(t.get('pnl', 0) for t in trades)
        st.metric("Total P&L", f"${total_pnl:,.2f}")
    else:
        st.metric("Total P&L", "$0.00")

with col4:
    st.metric("System Status", "🟢 Operational")

st.markdown("---")

# Recent Trades Table
st.subheader("📋 Recent Trades")
if trades:
    df = pd.DataFrame(trades)
    if 'entry_time' in df.columns:
        df['entry_time'] = pd.to_datetime(df['entry_time'])
        df = df.sort_values('entry_time', ascending=False).head(10)
    
    display_cols = ['symbol', 'entry_time', 'agent', 'pnl', 'pnl_pct'] if all(c in df.columns for c in ['symbol', 'entry_time', 'agent', 'pnl', 'pnl_pct']) else df.columns[:5]
    st.dataframe(df[display_cols], use_container_width=True, hide_index=True)
else:
    st.info("No trades found. Run a backtest to see results.")

st.markdown("---")
st.info("💡 **Tip**: Visit the Trade History page to see all trades with detailed filters and analysis.")

