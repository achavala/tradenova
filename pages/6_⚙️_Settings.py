"""
Settings Page
Configuration and system settings
"""
import streamlit as st
import pandas as pd
from pathlib import Path
import sys
import os

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import Config

st.title("⚙️ Settings")

# System Configuration
st.subheader("System Configuration")

col1, col2 = st.columns(2)

with col1:
    st.metric("Initial Balance", f"${Config.INITIAL_BALANCE:,.2f}")
    st.metric("Max Active Trades", Config.MAX_ACTIVE_TRADES)
    st.metric("Position Size", f"{Config.POSITION_SIZE_PCT*100:.0f}%")
    st.metric("Stop Loss", f"{Config.STOP_LOSS_PCT*100:.0f}%")

with col2:
    st.metric("TP1 Target", f"{Config.TP1_PCT*100:.0f}%")
    st.metric("TP2 Target", f"{Config.TP2_PCT*100:.0f}%")
    st.metric("TP3 Target", f"{Config.TP3_PCT*100:.0f}%")
    st.metric("TP4 Target", f"{Config.TP4_PCT*100:.0f}%")
    st.metric("TP5 Target", f"{Config.TP5_PCT*100:.0f}%")

st.markdown("---")

# Trading Symbols
st.subheader("Trading Symbols")
st.write(f"**Total Symbols**: {len(Config.TICKERS)}")
symbols_df = pd.DataFrame({
    'Symbol': Config.TICKERS
})
st.dataframe(symbols_df, use_container_width=True, hide_index=True)

st.markdown("---")

# Alpaca Configuration
st.subheader("Alpaca Configuration")
col1, col2 = st.columns(2)

with col1:
    api_key_display = Config.ALPACA_API_KEY[:10] + "..." if Config.ALPACA_API_KEY else "Not Set"
    st.text_input("API Key", api_key_display, disabled=True)
    
with col2:
    base_url = Config.ALPACA_BASE_URL
    st.text_input("Base URL", base_url, disabled=True)

st.info("⚠️ To change configuration, edit the `.env` file and restart the system.")

st.markdown("---")

# System Information
st.subheader("System Information")
st.write(f"**Trading Mode**: Paper Trading")
st.write(f"**Log Level**: {Config.LOG_LEVEL}")

# Environment Variables
if st.checkbox("Show Environment Variables"):
    env_vars = {
        "ALPACA_API_KEY": "Set" if Config.ALPACA_API_KEY else "Not Set",
        "ALPACA_SECRET_KEY": "Set" if Config.ALPACA_SECRET_KEY else "Not Set",
        "ALPACA_BASE_URL": Config.ALPACA_BASE_URL,
        "INITIAL_BALANCE": Config.INITIAL_BALANCE,
        "MAX_ACTIVE_TRADES": Config.MAX_ACTIVE_TRADES,
        "POSITION_SIZE_PCT": Config.POSITION_SIZE_PCT,
        "STOP_LOSS_PCT": Config.STOP_LOSS_PCT,
    }
    env_df = pd.DataFrame(list(env_vars.items()), columns=['Variable', 'Value'])
    st.dataframe(env_df, use_container_width=True, hide_index=True)

