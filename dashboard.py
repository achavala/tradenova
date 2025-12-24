"""
Streamlit Dashboard for TradeNova
Main entry point - redirects to Dashboard page
"""
import streamlit as st
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

# Set page config
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

# Import and render persistent sidebar FIRST
from core.ui.sidebar import render_sidebar
render_sidebar()

# Show dashboard content directly (Streamlit will handle page routing automatically)
# Users can navigate via sidebar
st.title("📊 TradeNova Dashboard")
st.markdown("Welcome to TradeNova - Institutional-Grade Multi-Agent RL Trading System")

st.info("💡 **Navigation**: Use the sidebar to navigate to different pages:")
st.markdown("""
- **📊 Dashboard**: Overview of trades and system status
- **📋 Trade History**: Detailed trade history with filters
- **📝 System Logs**: Real-time system activity and logs
""")

# Try to load and show recent trades summary (LIVE TRADES ONLY - no backtest)
try:
    from core.ui.trade_loader import load_all_trades
    trades = load_all_trades(include_backtest=False)  # Only show live trades, not backtest results
    
    if trades:
        st.success(f"✅ Found {len(trades)} total trades")
        st.markdown("Visit the **Trade History** page to see detailed trade information.")
    else:
        st.info("No trades found yet. Run a backtest or wait for live trades to appear.")
except Exception as e:
    st.debug(f"Could not load trades: {e}")

