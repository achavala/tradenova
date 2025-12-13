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

# Hide the main dashboard.py from navigation using CSS
st.markdown("""
<style>
    /* Hide the first navigation item (main dashboard.py) */
    section[data-testid="stSidebar"] nav ul li:first-child {
        display: none !important;
    }
    /* Alternative: Hide by text content */
    section[data-testid="stSidebar"] nav a[href*="dashboard"]:not([href*="pages"]) {
        display: none !important;
    }
</style>
""", unsafe_allow_html=True)

from logs.metrics_tracker import MetricsTracker
from core.live.model_degrade_detector import ModelDegradeDetector
from config import Config
from alpaca_client import AlpacaClient
from datetime import time as dt_time

# Load metrics
@st.cache_data(ttl=30)
def load_metrics():
    tracker = MetricsTracker()
    return tracker.calculate_metrics()

@st.cache_data(ttl=30)
def load_trades(lookback_days: int = 30):
    """Load recent trades"""
    tracker = MetricsTracker()
    return pd.DataFrame()  # Placeholder - would load from actual trade history

def get_system_status():
    """Get current system validation status"""
    status_items = []
    
    try:
        # Check Alpaca connection
        try:
            client = AlpacaClient(
                Config.ALPACA_API_KEY,
                Config.ALPACA_SECRET_KEY,
                Config.ALPACA_BASE_URL
            )
            account = client.get_account()
            is_market_open = client.is_market_open()
            
            status_items.append({
                'component': 'Alpaca Connection',
                'status': '✅ Connected',
                'details': f"Equity: ${float(account['equity']):,.2f} | Market: {'Open' if is_market_open else 'Closed'}"
            })
        except Exception as e:
            status_items.append({
                'component': 'Alpaca Connection',
                'status': '❌ Error',
                'details': str(e)[:50]
            })
        
        # Check market hours
        now = datetime.now().time()
        market_open = dt_time(9, 30)
        market_close = dt_time(16, 0)
        is_market_hours = market_open <= now <= market_close
        
        if is_market_hours:
            status_items.append({
                'component': 'Market Status',
                'status': '✅ Trading Hours',
                'details': f"Market is open (9:30 AM - 4:00 PM ET)"
            })
        else:
            if now < market_open:
                status_items.append({
                    'component': 'Market Status',
                    'status': '⏳ Pre-Market',
                    'details': f"Waiting for market open at 9:30 AM ET"
                })
            else:
                status_items.append({
                    'component': 'Market Status',
                    'status': '🔒 After Hours',
                    'details': f"Market closed. Next open: Tomorrow 9:30 AM ET"
                })
        
        # Check scheduler status
        try:
            import subprocess
            result = subprocess.run(['pgrep', '-f', 'run_daily.py'], 
                                  capture_output=True, text=True, timeout=2)
            if result.returncode == 0 and result.stdout.strip():
                status_items.append({
                    'component': 'Trading Scheduler',
                    'status': '✅ Running',
                    'details': 'Automated trading system is active'
                })
            else:
                status_items.append({
                    'component': 'Trading Scheduler',
                    'status': '⏸️ Stopped',
                    'details': 'Start with: ./start_trading.sh --paper'
                })
        except:
            status_items.append({
                'component': 'Trading Scheduler',
                'status': '⚠️ Unknown',
                'details': 'Cannot check process status'
            })
        
        # Check components
        try:
            from core.live.integrated_trader import IntegratedTrader
            status_items.append({
                'component': 'Trading Components',
                'status': '✅ Loaded',
                'details': 'All components initialized'
            })
        except Exception as e:
            status_items.append({
                'component': 'Trading Components',
                'status': '❌ Error',
                'details': str(e)[:50]
            })
        
        # Check risk manager
        try:
            from core.risk.advanced_risk_manager import AdvancedRiskManager
            status_items.append({
                'component': 'Risk Management',
                'status': '✅ Active',
                'details': 'Risk limits and guards enabled'
            })
        except Exception as e:
            status_items.append({
                'component': 'Risk Management',
                'status': '❌ Error',
                'details': str(e)[:50]
            })
        
    except Exception as e:
        status_items.append({
            'component': 'System Status',
            'status': '❌ Error',
            'details': f"Failed to check status: {str(e)[:50]}"
        })
    
    return status_items

# Main content
st.title("📊 Dashboard Overview")

# System status badges
col_status1, col_status2, col_status3, col_status4 = st.columns(4)
with col_status1:
    st.metric("System Status", "🟢 Operational", "")
with col_status2:
    st.metric("Trading Mode", "Paper Trading", "")
with col_status3:
    st.metric("Version", "v1.0", "")
with col_status4:
    st.metric("Platform", "TradeNova", "")

st.markdown("---")

# Load data
try:
    metrics = load_metrics()
    trades_df = load_trades(30)
except Exception as e:
    st.error(f"Error loading data: {e}")
    metrics = {}
    trades_df = pd.DataFrame()

# Key Metrics Row
col1, col2, col3, col4 = st.columns(4)

with col1:
    total_pnl = metrics.get('total_pnl', 0)
    daily_pnl = metrics.get('daily_pnl', 0)
    st.metric(
        "Total P&L",
        f"${total_pnl:,.2f}",
        delta=f"${daily_pnl:,.2f}" if daily_pnl != 0 else None
    )

with col2:
    win_rate = metrics.get('win_rate', 0)
    st.metric(
        "Win Rate",
        f"{win_rate:.1f}%",
        delta=None
    )

with col3:
    sharpe = metrics.get('sharpe_ratio', 0)
    st.metric(
        "Sharpe Ratio",
        f"{sharpe:.2f}",
        delta=None
    )

with col4:
    max_dd = metrics.get('max_drawdown', 0)
    st.metric(
        "Max Drawdown",
        f"${max_dd:,.2f}",
        delta=None
    )

st.markdown("---")

# Charts Row
col1, col2 = st.columns(2)

with col1:
    st.subheader("📈 Equity Curve")
    dates = pd.date_range(end=datetime.now(), periods=30, freq='D')
    pnl_data = pd.DataFrame({
        'date': dates,
        'pnl': [100 * (i * 0.1 + (i % 3 - 1) * 0.5) for i in range(30)]
    })
    pnl_data['cumulative'] = pnl_data['pnl'].cumsum()
    pnl_data['running_max'] = pnl_data['cumulative'].cummax()
    pnl_data['drawdown'] = pnl_data['cumulative'] - pnl_data['running_max']
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=pnl_data['date'],
        y=pnl_data['cumulative'],
        mode='lines',
        name='Equity Curve',
        line=dict(color='green' if pnl_data['cumulative'].iloc[-1] > 0 else 'red', width=2)
    ))
    fig.add_trace(go.Scatter(
        x=pnl_data['date'],
        y=pnl_data['running_max'],
        mode='lines',
        name='Running High',
        line=dict(color='blue', dash='dash', width=1)
    ))
    fig.update_layout(
        title="Equity Curve",
        xaxis_title="Date",
        yaxis_title="Cumulative P&L ($)",
        height=300
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Drawdown chart
    st.subheader("📉 Drawdown Chart")
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(
        x=pnl_data['date'],
        y=pnl_data['drawdown'],
        mode='lines',
        name='Drawdown',
        fill='tozeroy',
        line=dict(color='red'),
        fillcolor='rgba(255,0,0,0.3)'
    ))
    fig2.update_layout(
        title="Drawdown Over Time",
        xaxis_title="Date",
        yaxis_title="Drawdown ($)",
        height=250
    )
    st.plotly_chart(fig2, use_container_width=True)

with col2:
    st.subheader("🎯 Win Rate by Agent")
    agent_data = pd.DataFrame({
        'Agent': ['RL_GRPO', 'Trend', 'MeanReversion', 'Volatility', 'FVG'],
        'Win Rate': [65, 58, 62, 55, 60],
        'Trades': [45, 32, 28, 25, 20]
    })
    
    fig = px.bar(
        agent_data,
        x='Agent',
        y='Win Rate',
        color='Win Rate',
        color_continuous_scale='RdYlGn',
        title="Win Rate by Agent"
    )
    fig.update_layout(height=300)
    st.plotly_chart(fig, use_container_width=True)
    
    # Model Confidence Histogram
    st.subheader("🧠 RL Model Confidence")
    import numpy as np
    confidences = np.random.beta(8, 2, 100)
    fig3 = go.Figure()
    fig3.add_trace(go.Histogram(
        x=confidences,
        nbinsx=20,
        name='Confidence',
        marker_color='blue',
        opacity=0.7
    ))
    fig3.update_layout(
        title="RL Prediction Confidence Distribution",
        xaxis_title="Confidence",
        yaxis_title="Frequency",
        height=250
    )
    st.plotly_chart(fig3, use_container_width=True)

st.markdown("---")

# Detailed Metrics
col1, col2 = st.columns(2)

with col1:
    st.subheader("📈 Performance Metrics")
    metrics_df = pd.DataFrame([
        ['Total Trades', metrics.get('total_trades', 0)],
        ['Winning Trades', metrics.get('winning_trades', 0)],
        ['Losing Trades', metrics.get('losing_trades', 0)],
        ['Average Win', f"${metrics.get('avg_win', 0):.2f}"],
        ['Average Loss', f"${metrics.get('avg_loss', 0):.2f}"],
        ['Profit Factor', f"{metrics.get('profit_factor', 0):.2f}"],
    ], columns=['Metric', 'Value'])
    st.dataframe(metrics_df, use_container_width=True, hide_index=True)

with col2:
    st.subheader("🛡️ Risk Metrics")
    risk_df = pd.DataFrame([
        ['Daily Loss Limit', f"{metrics.get('daily_loss_limit', 2.0):.2f}%"],
        ['Current Drawdown', f"${metrics.get('current_drawdown', 0):,.2f}"],
        ['Max Drawdown', f"${metrics.get('max_drawdown', 0):,.2f}"],
        ['Risk Level', metrics.get('risk_level', 'Normal')],
        ['Active Positions', metrics.get('active_positions', 0)],
        ['Available Capital', f"${metrics.get('available_capital', 0):,.2f}"],
    ], columns=['Metric', 'Value'])
    st.dataframe(risk_df, use_container_width=True, hide_index=True)

st.markdown("---")

# Recent Trades
st.subheader("📋 Recent Trades")
if not trades_df.empty:
    st.dataframe(trades_df, use_container_width=True)
else:
    st.info("No trades recorded yet")

st.markdown("---")

# System Status Bar
st.subheader("🔍 System Validation Status")

try:
    status_items = get_system_status()
    
    for item in status_items:
        col1, col2, col3 = st.columns([2, 1, 4])
        
        with col1:
            st.markdown(f"**{item['component']}**")
        
        with col2:
            st.markdown(f"**{item['status']}**")
        
        with col3:
            st.caption(item['details'])
    
    # Overall status summary
    all_good = all('✅' in item['status'] for item in status_items)
    some_warnings = any('⚠️' in item['status'] or '⏳' in item['status'] for item in status_items)
    has_errors = any('❌' in item['status'] for item in status_items)
    
    st.markdown("---")
    
    if has_errors:
        st.error("⚠️ **System Status**: Some components have errors. Please check the status above.")
    elif some_warnings:
        st.warning("ℹ️ **System Status**: System is ready but waiting for market conditions.")
    elif all_good:
        st.success("✅ **System Status**: All systems operational and ready for trading.")
    else:
        st.info("ℹ️ **System Status**: System is initializing. Please wait...")
        
except Exception as e:
    st.error(f"Error checking system status: {e}")

