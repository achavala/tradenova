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

# Import and render persistent sidebar FIRST (before redirect)
from core.ui.sidebar import render_sidebar
render_sidebar()

# Redirect to Dashboard page
try:
    st.switch_page("pages/1_📊_Dashboard.py")
except Exception:
    # Fallback if pages don't exist yet
    st.title("📊 TradeNova Dashboard")
    st.info("Dashboard pages are being set up. Please check back in a moment.")

