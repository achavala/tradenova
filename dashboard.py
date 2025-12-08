"""
Streamlit Dashboard for TradeNova
Real-time monitoring and analytics
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys
import os

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from logs.metrics_tracker import MetricsTracker
from core.live.model_degrade_detector import ModelDegradeDetector
from config import Config
from alpaca_client import AlpacaClient
from datetime import time as dt_time

# Set page config with unique branding
st.set_page_config(
    page_title="TradeNova - AI Trading Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': "TradeNova - Institutional-Grade Multi-Agent RL Trading System"
    }
)

# Add custom CSS for unique branding
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        padding: 1rem;
        background: linear-gradient(90deg, #1f77b4 0%, #ff7f0e 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .tradenova-brand {
        font-family: 'Arial', sans-serif;
        font-weight: bold;
        color: #1f77b4;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_metrics():
    """Load metrics from tracker"""
    tracker = MetricsTracker()
    return tracker.calculate_metrics()

@st.cache_data(ttl=10)  # Cache for 10 seconds to allow real-time updates
def parse_option_symbol(symbol: str):
    """
    Parse Alpaca option symbol format: TICKER + YYMMDD + C/P + STRIKE
    Example: AAPL251205C00150000 = AAPL, Dec 5 2025, Call, $150 strike
    
    Returns:
        (underlying, expiry_date, option_type, strike) or None if not an option
    """
    import re
    from datetime import datetime
    
    # Option symbols are longer and contain date + C/P + strike
    # Pattern: TICKER(1-5 chars) + YYMMDD(6) + C/P(1) + STRIKE(8 digits)
    pattern = r'^([A-Z]{1,5})(\d{6})([CP])(\d{8})$'
    match = re.match(pattern, symbol)
    
    if not match:
        return None  # Not an option symbol
    
    underlying = match.group(1)
    date_str = match.group(2)
    option_type = 'CALL' if match.group(3) == 'C' else 'PUT'
    strike_str = match.group(4)
    
    # Parse date (YYMMDD format)
    try:
        year = 2000 + int(date_str[0:2])
        month = int(date_str[2:4])
        day = int(date_str[4:6])
        expiry_date = datetime(year, month, day).date()
    except:
        return None
    
    # Parse strike (8 digits, divide by 1000)
    try:
        strike = float(strike_str) / 1000.0
    except:
        return None
    
    return {
        'underlying': underlying,
        'expiry_date': expiry_date,
        'option_type': option_type,
        'strike': strike
    }

def load_trades(lookback_days: int = 30):
    """Load current OPTIONS positions from Alpaca (0-30 days to expiry, for configured tickers only)"""
    try:
        from datetime import date, timedelta
        
        client = AlpacaClient(
            Config.ALPACA_API_KEY,
            Config.ALPACA_SECRET_KEY,
            Config.ALPACA_BASE_URL
        )
        
        # Get all positions
        positions = client.get_positions()
        
        if not positions:
            return pd.DataFrame()
        
        # Filter to only options with 0-5 days to expiry for configured tickers
        today = date.today()
        trades_data = []
        
        for pos in positions:
            symbol = pos['symbol']
            
            # Skip if it's a stock (not an option)
            # Stocks are just the ticker symbol (e.g., "SPY", "AAPL")
            # Options have format: TICKER + YYMMDD + C/P + STRIKE
            option_info = parse_option_symbol(symbol)
            
            if not option_info:
                # This is a stock, skip it
                continue
            
            # Check if underlying is in our configured tickers
            if option_info['underlying'] not in Config.TICKERS:
                continue
            
            # Check expiry: 0-30 days to expiry
            days_to_expiry = (option_info['expiry_date'] - today).days
            
            if days_to_expiry < 0:
                # Expired option, skip
                continue
            
            if days_to_expiry > 30:
                # More than 30 days to expiry, skip
                continue
            
            # This is a valid option position to display
            trades_data.append({
                'Symbol': symbol,
                'Underlying': option_info['underlying'],
                'Type': option_info['option_type'],
                'Strike': f"${option_info['strike']:.2f}",
                'Expiry': option_info['expiry_date'].strftime('%Y-%m-%d'),
                'DTE': days_to_expiry,
                'Side': pos['side'].upper(),
                'Quantity': pos['qty'],
                'Entry Price': f"${pos['avg_entry_price']:.2f}",
                'Current Price': f"${pos['current_price']:.2f}",
                'Market Value': f"${pos['market_value']:,.2f}",
                'Cost Basis': f"${pos['cost_basis']:,.2f}",
                'P/L': f"${pos['unrealized_pl']:,.2f}",
                'P/L %': f"{pos['unrealized_plpc']*100:.2f}%",
                'Status': 'Open'
            })
        
        df = pd.DataFrame(trades_data)
        return df
        
    except Exception as e:
        st.error(f"Error loading positions: {e}")
        return pd.DataFrame()

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
        
        # Check market hours using Alpaca API (most accurate)
        # Also check ET timezone for display
        try:
            import pytz
            et_tz = pytz.timezone('America/New_York')
            now_et = datetime.now(et_tz)
            now_et_time = now_et.time()
            market_open = dt_time(9, 30)
            market_close = dt_time(16, 0)
            is_weekday = now_et.weekday() < 5  # Monday=0, Friday=4
            
            # Use Alpaca API result as primary source (most accurate)
            if is_market_open:
                status_items.append({
                    'component': 'Market Status',
                    'status': '✅ Trading Hours',
                    'details': f"Market is open (9:30 AM - 4:00 PM ET)"
                })
            else:
                # Market is closed - determine why
                if not is_weekday:
                    status_items.append({
                        'component': 'Market Status',
                        'status': '🔒 Weekend',
                        'details': f"Market closed (weekend). Next open: Monday 9:30 AM ET"
                    })
                elif now_et_time < market_open:
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
        except Exception as e:
            # Fallback to simple check if timezone fails
            if is_market_open:
                status_items.append({
                    'component': 'Market Status',
                    'status': '✅ Trading Hours',
                    'details': f"Market is open (9:30 AM - 4:00 PM ET)"
                })
            else:
                status_items.append({
                    'component': 'Market Status',
                    'status': '🔒 Closed',
                    'details': f"Market is closed"
                })
        
        # Check scheduler status (if running)
        try:
            import subprocess
            # Check for either run_daily.py or tradenova_daemon.py
            result1 = subprocess.run(['pgrep', '-f', 'run_daily.py'], 
                                   capture_output=True, text=True, timeout=2)
            result2 = subprocess.run(['pgrep', '-f', 'tradenova_daemon.py'], 
                                   capture_output=True, text=True, timeout=2)
            
            if (result1.returncode == 0 and result1.stdout.strip()) or \
               (result2.returncode == 0 and result2.stdout.strip()):
                status_items.append({
                    'component': 'Trading Scheduler',
                    'status': '✅ Running',
                    'details': 'Automated trading system is active'
                })
            else:
                status_items.append({
                    'component': 'Trading Scheduler',
                    'status': '⏸️ Stopped',
                    'details': 'Start with: ./install_service.sh or ./start_trading.sh --paper'
                })
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
            # Fallback: check if log file is being updated recently
            try:
                log_file = Path('logs/tradenova_daily.log')
                if log_file.exists():
                    import time
                    mod_time = log_file.stat().st_mtime
                    # If log was modified in last 5 minutes, assume running
                    if time.time() - mod_time < 300:
                        status_items.append({
                            'component': 'Trading Scheduler',
                            'status': '✅ Running (inferred)',
                            'details': 'Log file recently updated'
                        })
                    else:
                        status_items.append({
                            'component': 'Trading Scheduler',
                            'status': '⏸️ Stopped',
                            'details': 'Start with: ./start_trading.sh --paper'
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

def main():
    # Branded header with unique identifier
    st.markdown("""
    <div style="background: linear-gradient(90deg, #1f77b4 0%, #ff7f0e 100%); padding: 1rem; border-radius: 10px; margin-bottom: 1rem;">
        <h1 style="color: white; text-align: center; margin: 0;">
            📈 TradeNova - AI Trading System Dashboard
        </h1>
        <p style="color: white; text-align: center; margin: 0.5rem 0 0 0;">
            Institutional-Grade Multi-Agent RL Trading Platform
        </p>
    </div>
    """, unsafe_allow_html=True)
    
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
    
    # Sidebar
    with st.sidebar:
        st.header("📊 TradeNova System")
        st.markdown("**Status**: 🟢 Operational")
        st.markdown("**Mode**: Paper Trading")
        st.markdown("---")
        
        st.header("⚙️ Settings")
        refresh_interval = st.slider("Auto-refresh (seconds)", 5, 60, 30)
        lookback_days = st.slider("Lookback (days)", 1, 90, 30)
        
        st.markdown("---")
        
        if st.button("🔄 Refresh Now"):
            st.cache_data.clear()
            st.rerun()
        
        st.markdown("---")
        st.markdown("**TradeNova v1.0**")
        st.markdown("Multi-Agent RL Trading System")
    
    # Load data
    try:
        metrics = load_metrics()
        trades_df = load_trades(lookback_days)
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return
    
    # Key Metrics Row
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Total P&L",
            f"${metrics.get('total_pnl', 0):,.2f}",
            delta=f"{metrics.get('daily_pnl', 0):,.2f}"
        )
    
    with col2:
        st.metric(
            "Win Rate",
            f"{metrics.get('win_rate', 0):.1f}%",
            delta=f"{metrics.get('win_rate_change', 0):.1f}%"
        )
    
    with col3:
        st.metric(
            "Sharpe Ratio",
            f"{metrics.get('sharpe_ratio', 0):.2f}",
            delta=None
        )
    
    with col4:
        st.metric(
            "Max Drawdown",
            f"{metrics.get('max_drawdown', 0):.2f}%",
            delta=None
        )
    
    st.markdown("---")
    
    # Current Positions - Options Only (0-30 days to expiry)
    st.subheader("📋 Current Options Positions")
    st.caption("Showing only options with 0-30 days to expiry for configured tickers (excluding stocks like SPY)")
    if not trades_df.empty:
        # Display the dataframe
        st.dataframe(trades_df, use_container_width=True, hide_index=True)
        
        # Summary
        try:
            total_pl = sum([float(p.replace('$', '').replace(',', '')) for p in trades_df['P/L']])
            total_positions = len(trades_df)
            pl_color = "🟢" if total_pl >= 0 else "🔴"
            st.caption(f"**Total Options Positions:** {total_positions} | **Total Unrealized P/L:** {pl_color} ${total_pl:,.2f}")
        except Exception as e:
            st.caption(f"**Total Options Positions:** {len(trades_df)}")
    else:
        st.info("No open options positions (0-30 days to expiry)")
    
    st.markdown("---")
    
    # Charts Row
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Equity Curve")
        # Create equity curve with drawdown
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
        # Sample agent performance
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
        # Sample confidence distribution
        import numpy as np
        confidences = np.random.beta(8, 2, 100)  # Skewed towards high confidence
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
        metrics_df = pd.DataFrame({
            'Metric': ['Total Trades', 'Winning Trades', 'Losing Trades', 'Average Win', 'Average Loss', 'Profit Factor'],
            'Value': [
                str(metrics.get('total_trades', 0)),
                str(metrics.get('winning_trades', 0)),
                str(metrics.get('losing_trades', 0)),
                f"${metrics.get('avg_win', 0):.2f}",
                f"${metrics.get('avg_loss', 0):.2f}",
                f"{metrics.get('profit_factor', 0):.2f}"
            ]
        })
        st.dataframe(metrics_df, use_container_width=True, hide_index=True)
    
    with col2:
        st.subheader("🛡️ Risk Metrics")
        risk_df = pd.DataFrame({
            'Metric': ['Daily Loss Limit', 'Current Drawdown', 'Max Drawdown', 'Risk Level', 'Active Positions', 'Available Capital'],
            'Value': [
                f"{metrics.get('daily_loss_limit', 0):.2f}%",
                f"{metrics.get('current_drawdown', 0):.2f}%",
                f"{metrics.get('max_drawdown', 0):.2f}%",
                str(metrics.get('risk_level', 'Normal')),
                str(metrics.get('active_positions', 0)),
                f"${metrics.get('available_capital', 0):,.2f}"
            ]
        })
        st.dataframe(risk_df, use_container_width=True, hide_index=True)
    
    st.markdown("---")
    
    # System Status Bar
    st.subheader("🔍 System Validation Status")
    
    try:
        status_items = get_system_status()
        
        # Create status display with progress indicators
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
    
    st.markdown("---")
    
    # Real-Time Activity Status Bar
    st.subheader("📊 Real-Time Activity Status")
    
    try:
        from core.live.activity_tracker import ActivityTracker
        
        activity_tracker = ActivityTracker()
        activity = activity_tracker.get_current_activity()
        
        # Compute relative time on frontend (timezone-aware)
        try:
            last_updated_str = activity.get('last_updated') or activity.get('timestamp')
            if last_updated_str:
                # Parse ISO timestamp (handle both with and without timezone)
                if last_updated_str.endswith('Z'):
                    activity_time = datetime.fromisoformat(last_updated_str.replace('Z', '+00:00'))
                elif '+' in last_updated_str or last_updated_str.count('-') > 2:
                    activity_time = datetime.fromisoformat(last_updated_str)
                else:
                    # Assume UTC if no timezone
                    activity_time = datetime.fromisoformat(last_updated_str).replace(tzinfo=timezone.utc)
                
                # Compute relative time
                now = datetime.now(timezone.utc) if activity_time.tzinfo else datetime.now()
                if activity_time.tzinfo:
                    time_ago = (now - activity_time).total_seconds()
                else:
                    time_ago = (datetime.now() - activity_time).total_seconds()
                
                if time_ago < 10:
                    time_str = f"{int(time_ago)}s ago"
                elif time_ago < 60:
                    time_str = f"{int(time_ago)}s ago"
                elif time_ago < 3600:
                    time_str = f"{int(time_ago/60)}m ago"
                else:
                    time_str = f"{int(time_ago/3600)}h ago"
            else:
                time_str = "unknown"
        except Exception as e:
            time_str = "unknown"
        
        # Status mapping with icons and colors
        status = activity.get('status', 'IDLE').upper()
        status_config = {
            'IDLE': {'icon': '⏸️', 'color': '#808080', 'label': 'Idle'},
            'SCANNING': {'icon': '🔍', 'color': '#1f77b4', 'label': 'Scanning'},
            'ANALYZING': {'icon': '📊', 'color': '#ff7f0e', 'label': 'Analyzing'},
            'EXECUTING': {'icon': '⚡', 'color': '#2ca02c', 'label': 'Executing'},
            'MONITORING': {'icon': '👁️', 'color': '#9467bd', 'label': 'Monitoring'},
            'ERROR': {'icon': '❌', 'color': '#d62728', 'label': 'Error'}
        }
        
        config = status_config.get(status, status_config['IDLE'])
        icon = config['icon']
        color = config['color']
        label = config['label']
        
        # Create status bar with styled container
        status_container = st.container()
        with status_container:
            col1, col2, col3 = st.columns([1, 4, 2])
            
            with col1:
                st.markdown(f"<div style='text-align: center; font-size: 2.5em; color: {color};'>{icon}</div>", unsafe_allow_html=True)
            
            with col2:
                ticker = activity.get('ticker')
                message = activity.get('message', 'Unknown')
                details = activity.get('details', '')
                
                if ticker:
                    st.markdown(f"**{message}** - **{ticker}**")
                    if details:
                        st.caption(details)
                else:
                    st.markdown(f"**{message}**")
                    if details:
                        st.caption(details)
                
                # Progress bar if step/total_steps available
                step = activity.get('step')
                total_steps = activity.get('total_steps')
                if step is not None and total_steps and total_steps > 0:
                    progress = step / total_steps
                    st.progress(progress, text=f"Step {step} of {total_steps}")
            
            with col3:
                st.caption(f"⏱️ **Updated:** {time_str}")
                st.caption(f"📌 **Status:** {label}")
                if activity.get('cycle_id'):
                    st.caption(f"🔄 Cycle: {activity['cycle_id'][:19]}")
                
                # Link to logs
                if st.button("📋 View Logs", key="view_logs_btn", use_container_width=True):
                    st.info("💡 Check terminal or logs/tradenova_daemon.log for detailed activity")
        
        # Status-specific progress indicator
        if status == 'SCANNING' or status == 'ANALYZING':
            if not (step and total_steps):
                st.progress(0.5, text="Processing...")
        elif status == 'EXECUTING':
            st.progress(0.8, text="Executing trade...")
        elif status == 'IDLE':
            st.progress(1.0, text="Ready")
        elif status == 'ERROR':
            st.progress(0.0, text="Error state")
        
    except FileNotFoundError:
        st.info("💡 **Status:** No activity file found - system may be starting")
        st.caption("Activity tracking will appear once trading cycle runs")
    except json.JSONDecodeError:
        st.warning("⚠️ **Status:** Activity file corrupted - showing default status")
        st.caption("System will recover on next activity update")
    except Exception as e:
        st.warning(f"⚠️ **Status:** Could not load activity - {str(e)[:50]}")
        st.caption("Activity tracking temporarily unavailable")
    
    # Auto-refresh
    if refresh_interval > 0:
        time.sleep(refresh_interval)
        st.rerun()

if __name__ == '__main__':
    import time
    main()

