"""
System Logs Page
Shows real-time trading system activity, validations, and decisions
"""
import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
import sys
import re
import time
import logging

sys.path.insert(0, str(Path(__file__).parent.parent))

logger = logging.getLogger(__name__)

# Import and render persistent sidebar
from core.ui.sidebar import render_sidebar
render_sidebar()

st.set_page_config(
    page_title="System Logs - TradeNova",
    page_icon="📝",
    layout="wide"
)

st.title("📝 System Logs")
st.markdown("Real-time trading system activity, validations, and decisions")

# Auto-refresh settings
col1, col2, col3 = st.columns([1, 1, 2])
with col1:
    auto_refresh = st.checkbox("Auto-refresh", value=True)
with col2:
    refresh_interval = st.selectbox("Interval (seconds)", [5, 10, 30, 60], index=2)
with col3:
    if st.button("🔄 Refresh Now"):
        st.rerun()

# Real-time System Status
st.markdown("### 🔍 Real-Time System Status")

col1, col2, col3, col4 = st.columns(4)

system_status = {}
try:
    from config import Config
    from alpaca_client import AlpacaClient
    from alpaca_trade_api.rest import TimeFrame
    
    client = AlpacaClient(
        Config.ALPACA_API_KEY,
        Config.ALPACA_SECRET_KEY,
        Config.ALPACA_BASE_URL
    )
    
    # Check market status
    is_open = client.is_market_open()
    account = client.get_account()
    positions = client.get_positions()
    orders = client.api.list_orders(status='all', limit=20, nested=True)
    
    system_status = {
        'market_open': is_open,
        'equity': float(account['equity']),
        'buying_power': float(account['buying_power']),
        'positions': len(positions),
        'recent_orders': len(orders)
    }
    
    with col1:
        status_icon = "🟢" if is_open else "🔴"
        st.metric("Market Status", "OPEN" if is_open else "CLOSED")
        st.caption(f"{status_icon} Market is {'open' if is_open else 'closed'}")
    
    with col2:
        st.metric("Account Equity", f"${float(account['equity']):,.2f}")
        st.caption(f"Buying Power: ${float(account['buying_power']):,.2f}")
    
    with col3:
        st.metric("Open Positions", len(positions))
        if positions:
            pos_symbols = [p['symbol'] for p in positions[:3]]
            st.caption(f"Active: {', '.join(pos_symbols)}")
        else:
            st.caption("No open positions")
    
    with col4:
        st.metric("Recent Orders", len(orders))
        if orders:
            today_orders = [o for o in orders if hasattr(o, 'submitted_at') and 
                          pd.to_datetime(o.submitted_at).date() == datetime.now().date()]
            st.caption(f"Today: {len(today_orders)}")
        else:
            st.caption("No orders found")
    
except Exception as e:
    st.error(f"Error checking system status: {e}")
    system_status = {'error': str(e)}

st.markdown("---")

# Check what system is doing RIGHT NOW
st.markdown("### ⚡ Current System Activity")

try:
    from core.multi_agent_orchestrator import MultiAgentOrchestrator
    
    orchestrator = MultiAgentOrchestrator(client)
    
    # Check recent signals
    st.markdown("#### 🔍 Signal Generation Check (Last 5 Minutes)")
    
    signals_found = []
    for ticker in Config.TICKERS[:5]:  # Check first 5 tickers
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=90)
            
            bars = client.get_historical_bars(ticker, TimeFrame.Day, start_date, end_date)
            if bars.empty or len(bars) < 50:
                continue
            
            trade_intent = orchestrator.analyze_symbol(ticker, bars)
            
            if trade_intent and trade_intent.direction.value != 'FLAT':
                signals_found.append({
                    'ticker': ticker,
                    'direction': trade_intent.direction.value,
                    'confidence': trade_intent.confidence,
                    'agent': trade_intent.agent_name,
                    'reasoning': trade_intent.reasoning[:100]
                })
        except Exception as e:
            continue
    
    if signals_found:
        st.success(f"✅ Found {len(signals_found)} signal(s) in recent check:")
        for sig in signals_found:
            st.markdown(f"""
            **{sig['ticker']}** - {sig['direction']} (Confidence: {sig['confidence']:.2f})
            - Agent: {sig['agent']}
            - Reasoning: {sig['reasoning']}
            """)
    else:
        st.info("ℹ️ No signals generated in recent check. System may be waiting for market conditions.")
    
except Exception as e:
    st.warning(f"Could not check signal generation: {e}")

st.markdown("---")

# Log file paths (check multiple locations for Fly.io)
log_files = [
    Path("logs/tradenova_daily.log"),
    Path("logs/trading_today.log"),
    Path("logs/trading.log"),
    Path("tradenova.log"),
    Path("/app/logs/tradenova_daily.log"),  # Fly.io absolute path
    Path("/app/logs/trading_today.log"),
    Path("/app/tradenova.log"),
    Path("logs/backtest.log"),  # Backtest logs
]

# Ensure logs directory exists
logs_dir = Path("logs")
if not logs_dir.exists():
    try:
        logs_dir.mkdir(parents=True, exist_ok=True)
    except:
        pass

def parse_log_line(line):
    """Parse a log line into structured data"""
    # Pattern: 2025-12-17 09:30:15,123 - module - LEVEL - message
    pattern = r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}(?:,\d+)?)\s+-\s+([\w.]+)\s+-\s+(\w+)\s+-\s+(.+)'
    match = re.match(pattern, line.strip())
    
    if match:
        timestamp_str, module, level, message = match.groups()
        try:
            # Parse timestamp (handle both with and without microseconds)
            if ',' in timestamp_str:
                timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S,%f')
            else:
                timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
        except:
            timestamp = datetime.now()
        
        return {
            'timestamp': timestamp,
            'module': module,
            'level': level,
            'message': message
        }
    return None

def load_logs(max_lines=500):
    """Load and parse log files"""
    all_logs = []
    found_files = []
    
    for log_file in log_files:
        if log_file.exists():
            found_files.append(str(log_file))
            try:
                with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                    # Get last N lines
                    for line in lines[-max_lines:]:
                        parsed = parse_log_line(line)
                        if parsed:
                            parsed['source_file'] = log_file.name
                            all_logs.append(parsed)
            except Exception as e:
                logger.debug(f"Could not read {log_file}: {e}")
                pass  # Silently skip files we can't read
    
    # Store found files in session state for display
    if found_files:
        st.session_state['log_files_found'] = found_files
    else:
        st.session_state['log_files_found'] = []
    
    # Sort by timestamp
    all_logs.sort(key=lambda x: x['timestamp'], reverse=True)
    return all_logs

def categorize_log(log):
    """Categorize log entry by activity type"""
    message = log['message'].lower()
    
    # Signal Generation
    if any(word in message for word in ['signal', 'trade intent', 'analyze', 'agent', 'confidence', 'generated']):
        return 'Signal Generation'
    # Trade Execution
    elif any(word in message for word in ['execute', 'executing trade', 'order', 'filled', 'trade executed']):
        return 'Trade Execution'
    # Trade Rejection
    elif any(word in message for word in ['blocked', 'reject', 'not allowed', 'risk', 'confidence too low', 'trade blocked']):
        return 'Trade Rejection'
    # Validation
    elif any(word in message for word in ['validate', 'check', 'setup', 'config', 'initialized', 'warmup']):
        return 'Validation'
    # Market Status
    elif any(word in message for word in ['market open', 'market close', 'warmup', 'pre-market', 'after hours']):
        return 'Market Status'
    # Account Status
    elif any(word in message for word in ['account', 'balance', 'equity', 'buying power', 'positions']):
        return 'Account Status'
    # Errors
    elif any(word in message for word in ['error', 'exception', 'failed', 'unauthorized']):
        return 'Error'
    # Trading Cycle
    elif any(word in message for word in ['trading cycle', 'scan', 'monitor', 'cycle']):
        return 'Trading Cycle'
    else:
        return 'Other'

# Load logs
logs = load_logs()

if not logs:
    st.warning("⚠️ No log files found. Showing real-time system status instead.")
    
    # Show what we CAN see
    st.markdown("### 📊 Available Information")
    
    if 'error' not in system_status:
        st.success("✅ System Status: Connected to Alpaca")
        st.info(f"💰 Account Equity: ${system_status.get('equity', 0):,.2f}")
        st.info(f"📊 Open Positions: {system_status.get('positions', 0)}")
        st.info(f"📋 Recent Orders: {system_status.get('recent_orders', 0)}")
        
        # Check recent orders
        try:
            from alpaca_client import AlpacaClient
            from config import Config
            
            client = AlpacaClient(
                Config.ALPACA_API_KEY,
                Config.ALPACA_SECRET_KEY,
                Config.ALPACA_BASE_URL
            )
            orders = client.get_orders(status='all', limit=10)
            if orders:
                st.markdown("#### 📋 Recent Orders from Alpaca")
                orders_df = pd.DataFrame(orders)
                if 'symbol' in orders_df.columns:
                    st.dataframe(orders_df[['symbol', 'side', 'qty', 'status', 'filled_qty', 'filled_avg_price']], use_container_width=True, hide_index=True)
        except Exception as e:
            st.debug(f"Could not fetch orders: {e}")
    else:
        st.error(f"❌ Cannot connect to system: {system_status['error']}")
    
    st.markdown("---")
    st.markdown("### 💡 Why No Logs?")
    
    # Show which log files we checked
    checked_files = [str(f) for f in log_files]
    st.markdown(f"**Checked locations:** {len(checked_files)} paths")
    with st.expander("See checked paths"):
        for path in checked_files:
            exists = "✅" if Path(path).exists() else "❌"
            st.text(f"{exists} {path}")
    
    st.markdown("""
    **Possible reasons:**
    1. Trading system not running on Fly.io (only dashboard is deployed)
    2. Logs are in a different location
    3. Trading system hasn't generated any activity yet
    
    **To see logs:**
    - Ensure trading system is running: `run_daily.py --paper`
    - Check Fly.io logs: `fly logs --app tradenova`
    - Logs should appear in `logs/tradenova_daily.log`
    """)
else:
    # Create DataFrame
    df = pd.DataFrame(logs)
    df['category'] = df.apply(categorize_log, axis=1)
    
    # Filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        levels = st.multiselect(
            "Filter by Level",
            options=['INFO', 'WARNING', 'ERROR', 'DEBUG'],
            default=['INFO', 'WARNING', 'ERROR']
        )
    
    with col2:
        categories = st.multiselect(
            "Filter by Category",
            options=df['category'].unique().tolist(),
            default=df['category'].unique().tolist()
        )
    
    with col3:
        search_term = st.text_input("Search logs", "")
    
    # Apply filters
    filtered_df = df[df['level'].isin(levels)]
    filtered_df = filtered_df[filtered_df['category'].isin(categories)]
    
    if search_term:
        filtered_df = filtered_df[filtered_df['message'].str.contains(search_term, case=False, na=False)]
    
    # Statistics
    st.markdown("### 📊 Activity Summary")
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Total Logs", len(filtered_df))
    with col2:
        signals = len(filtered_df[filtered_df['category'] == 'Signal Generation'])
        st.metric("Signals Generated", signals)
    with col3:
        executions = len(filtered_df[filtered_df['category'] == 'Trade Execution'])
        st.metric("Trades Executed", executions)
    with col4:
        rejections = len(filtered_df[filtered_df['category'] == 'Trade Rejection'])
        st.metric("Trades Rejected", rejections)
    with col5:
        errors = len(filtered_df[filtered_df['category'] == 'Error'])
        st.metric("Errors", errors, delta=None if errors == 0 else f"-{errors}")
    
    # System Activity Overview
    st.markdown("### 🔍 System Activity Overview")
    
    # Show key activities in tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Signals & Trades", "✅ Validations", "🔄 Trading Cycles", "⚠️ Rejections", "❌ Errors"])
    
    with tab1:
        st.markdown("#### Signal Generation & Trade Execution")
        signal_logs = filtered_df[filtered_df['category'].isin(['Signal Generation', 'Trade Execution'])].head(20)
        if len(signal_logs) > 0:
            for _, log in signal_logs.iterrows():
                icon = "✅" if log['category'] == 'Trade Execution' else "📊"
                st.markdown(f"**{icon} {log['timestamp'].strftime('%H:%M:%S')}** | {log['message']}")
        else:
            st.info("No signal or trade activity yet. The system may be waiting for market conditions.")
    
    with tab2:
        st.markdown("#### Setup Validations")
        validation_logs = filtered_df[filtered_df['category'] == 'Validation'].head(20)
        if len(validation_logs) > 0:
            for _, log in validation_logs.iterrows():
                st.markdown(f"**✅ {log['timestamp'].strftime('%H:%M:%S')}** | {log['message']}")
        else:
            st.info("No validation logs found.")
    
    with tab3:
        st.markdown("#### Trading Cycle Activity")
        cycle_logs = filtered_df[filtered_df['category'] == 'Trading Cycle'].head(20)
        if len(cycle_logs) > 0:
            for _, log in cycle_logs.iterrows():
                st.markdown(f"**🔄 {log['timestamp'].strftime('%H:%M:%S')}** | {log['message']}")
        else:
            st.info("No trading cycle activity yet.")
    
    with tab4:
        st.markdown("#### Trade Rejections & Reasons")
        rejection_logs = filtered_df[filtered_df['category'] == 'Trade Rejection'].head(20)
        if len(rejection_logs) > 0:
            for _, log in rejection_logs.iterrows():
                st.warning(f"**⚠️ {log['timestamp'].strftime('%H:%M:%S')}** | {log['message']}")
        else:
            st.success("No trade rejections - all signals are passing validation!")
    
    with tab5:
        st.markdown("#### Errors & Issues")
        error_logs = filtered_df[filtered_df['category'] == 'Error'].head(20)
        if len(error_logs) > 0:
            for _, log in error_logs.iterrows():
                st.error(f"**❌ {log['timestamp'].strftime('%H:%M:%S')}** | `{log['module']}` | {log['message']}")
        else:
            st.success("No errors - system running smoothly!")
    
    # Recent activity timeline
    st.markdown("### ⏱️ Recent Activity Timeline (All Categories)")
    
    # Group by category and show recent entries
    for category in ['Signal Generation', 'Trade Execution', 'Trade Rejection', 'Validation', 'Trading Cycle', 'Market Status', 'Account Status', 'Error']:
        category_logs = filtered_df[filtered_df['category'] == category].head(10)
        
        if len(category_logs) > 0:
            with st.expander(f"{category} ({len(category_logs)} entries)", expanded=(category in ['Signal Generation', 'Trade Execution', 'Trade Rejection'])):
                for _, log in category_logs.iterrows():
                    # Color code by level
                    if log['level'] == 'ERROR':
                        icon = "🔴"
                        color = "red"
                    elif log['level'] == 'WARNING':
                        icon = "🟡"
                        color = "orange"
                    elif log['level'] == 'INFO':
                        icon = "🔵"
                        color = "blue"
                    else:
                        icon = "⚪"
                        color = "gray"
                    
                    timestamp = log['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
                    st.markdown(
                        f"""
                        <div style="padding: 8px; margin: 4px 0; border-left: 3px solid {color}; background-color: #f0f0f0;">
                            <strong>{icon} {timestamp}</strong> | <code>{log['module']}</code> | <strong>{log['level']}</strong><br>
                            {log['message']}
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
    
    # Full log viewer
    st.markdown("### 📋 Full Log Viewer")
    
    # Show logs in reverse chronological order
    log_display = filtered_df.head(100).copy()
    log_display = log_display.sort_values('timestamp', ascending=False)
    
    for _, log in log_display.iterrows():
        # Determine color based on level
        if log['level'] == 'ERROR':
            st.error(f"**{log['timestamp'].strftime('%H:%M:%S')}** | `{log['module']}` | {log['message']}")
        elif log['level'] == 'WARNING':
            st.warning(f"**{log['timestamp'].strftime('%H:%M:%S')}** | `{log['module']}` | {log['message']}")
        elif log['level'] == 'INFO':
            st.info(f"**{log['timestamp'].strftime('%H:%M:%S')}** | `{log['module']}` | {log['message']}")
        else:
            st.text(f"**{log['timestamp'].strftime('%H:%M:%S')}** | `{log['module']}` | {log['message']}")

# Auto-refresh
if auto_refresh:
    time.sleep(refresh_interval)
    st.rerun()
4