"""
Options Chain Page
Shows options chain data for selected symbols
"""
import streamlit as st
import pandas as pd
from pathlib import Path
import sys
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import Config
from services.options_data_feed import OptionsDataFeed
from alpaca_client import AlpacaClient

st.title("⚙️ Options Chain")

# Initialize clients
try:
    client = AlpacaClient(
        Config.ALPACA_API_KEY,
        Config.ALPACA_SECRET_KEY,
        Config.ALPACA_BASE_URL
    )
    options_feed = OptionsDataFeed(client)
except Exception as e:
    st.error(f"Error initializing clients: {e}")
    st.stop()

# Symbol selection
symbol = st.selectbox("Select Symbol", Config.TICKERS, index=0)

# Expiration date filter
expiration_days = st.slider("Days to Expiration", 0, 60, (0, 30))

# Strike range
col1, col2 = st.columns(2)
with col1:
    min_strike = st.number_input("Min Strike", value=0.0, step=10.0)
with col2:
    max_strike = st.number_input("Max Strike", value=1000.0, step=10.0)

# Load options chain
if st.button("🔍 Load Options Chain"):
    with st.spinner("Loading options chain..."):
        try:
            # Get options chain
            chain = options_feed.get_options_chain(symbol)
            
            if chain and len(chain) > 0:
                df = pd.DataFrame(chain)
                
                # Filter by expiration
                if 'expiration_date' in df.columns:
                    df['expiration_date'] = pd.to_datetime(df['expiration_date'])
                    today = datetime.now().date()
                    days_to_exp = (df['expiration_date'].dt.date - today).dt.days
                    df = df[(days_to_exp >= expiration_days[0]) & (days_to_exp <= expiration_days[1])]
                
                # Filter by strike
                if 'strike' in df.columns:
                    df = df[(df['strike'] >= min_strike) & (df['strike'] <= max_strike)]
                
                st.success(f"Loaded {len(df)} option contracts")
                
                # Display options chain
                st.subheader(f"Options Chain for {symbol}")
                st.dataframe(df, use_container_width=True, height=400)
                
                # Summary statistics
                if len(df) > 0:
                    st.markdown("---")
                    st.subheader("Summary Statistics")
                    
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        if 'bid' in df.columns:
                            avg_bid = df['bid'].mean()
                            st.metric("Avg Bid", f"${avg_bid:.2f}")
                    
                    with col2:
                        if 'ask' in df.columns:
                            avg_ask = df['ask'].mean()
                            st.metric("Avg Ask", f"${avg_ask:.2f}")
                    
                    with col3:
                        if 'volume' in df.columns:
                            total_volume = df['volume'].sum()
                            st.metric("Total Volume", f"{total_volume:,.0f}")
                    
                    with col4:
                        if 'open_interest' in df.columns:
                            total_oi = df['open_interest'].sum()
                            st.metric("Total OI", f"{total_oi:,.0f}")
                    
                    # Download button
                    csv = df.to_csv(index=False)
                    st.download_button(
                        label="📥 Download Options Chain",
                        data=csv,
                        file_name=f"{symbol}_options_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv"
                    )
            else:
                st.warning(f"No options chain data available for {symbol}")
                
        except Exception as e:
            st.error(f"Error loading options chain: {e}")
            import traceback
            st.code(traceback.format_exc())

# Options Greeks Calculator
st.markdown("---")
st.subheader("📊 Options Greeks Calculator")

col1, col2, col3, col4 = st.columns(4)
with col1:
    calc_symbol = st.selectbox("Symbol", Config.TICKERS, key="calc_symbol")
with col2:
    calc_strike = st.number_input("Strike", value=100.0, step=1.0)
with col3:
    calc_expiry = st.date_input("Expiration", datetime.now() + timedelta(days=30))
with col4:
    option_type = st.selectbox("Type", ["Call", "Put"])

if st.button("Calculate Greeks"):
    try:
        from services.iv_calculator import IVCalculator
        iv_calc = IVCalculator(client)
        
        # Get current price
        current_price = client.get_latest_price(calc_symbol)
        if current_price:
            st.info(f"Current {calc_symbol} Price: ${current_price:.2f}")
            
            # Calculate IV and Greeks (simplified)
            st.info("Greeks calculation requires market data. This is a placeholder.")
            st.json({
                "Delta": "N/A",
                "Gamma": "N/A",
                "Theta": "N/A",
                "Vega": "N/A",
                "IV": "N/A"
            })
        else:
            st.error("Could not get current price")
    except Exception as e:
        st.error(f"Error calculating Greeks: {e}")

