"""
Persistent Sidebar Component
This sidebar will appear on all dashboard pages
"""
import streamlit as st
from datetime import datetime
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

def render_sidebar():
    """
    Render the persistent sidebar that appears on all pages.
    This function should be called at the top of every page to ensure
    the sidebar menu is always visible regardless of code changes.
    """
    
    # TradeNova System Section
    st.sidebar.markdown("### 📊 TradeNova System")
    
    # System Status - Check actual status
    try:
        from config import Config
        # Only check if API keys are set (don't make actual API calls in sidebar)
        if Config.ALPACA_API_KEY and Config.ALPACA_SECRET_KEY:
            status_color = "🟢"
            status_text = "Operational"
        else:
            status_color = "🟡"
            status_text = "Config Missing"
    except Exception:
        status_color = "🟡"
        status_text = "Initializing"
    
    st.sidebar.markdown(f"**Status:** {status_color} {status_text}")
    st.sidebar.markdown(f"**Mode:** Paper Trading")
    
    st.sidebar.markdown("---")
    
    # Settings Section
    st.sidebar.markdown("### ⚙️ Settings")
    
    # Auto-refresh setting (persist in session state)
    if 'auto_refresh' not in st.session_state:
        st.session_state['auto_refresh'] = 30
    
    auto_refresh = st.sidebar.slider(
        "Auto-refresh (seconds)",
        min_value=10,
        max_value=300,
        value=st.session_state['auto_refresh'],
        step=10,
        key="auto_refresh_global"
    )
    st.session_state['auto_refresh'] = auto_refresh
    
    # Lookback days (persist in session state)
    if 'lookback_days' not in st.session_state:
        st.session_state['lookback_days'] = 30
    
    lookback_days = st.sidebar.slider(
        "Lookback (days)",
        min_value=7,
        max_value=365,
        value=st.session_state['lookback_days'],
        step=7,
        key="lookback_days_global"
    )
    st.session_state['lookback_days'] = lookback_days
    
    # Refresh button
    if st.sidebar.button("🔄 Refresh Now", use_container_width=True):
        st.rerun()
    
    st.sidebar.markdown("---")
    
    # Version Info
    st.sidebar.markdown("**TradeNova v1.0**")
    st.sidebar.caption("Multi-Agent RL Trading System")
    
    return {
        'auto_refresh': auto_refresh,
        'lookback_days': lookback_days
    }

