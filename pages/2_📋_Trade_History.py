"""
Trade History Page
Shows all executed trades
"""
import streamlit as st
import pandas as pd
from pathlib import Path
import json
import sys
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from logs.metrics_tracker import MetricsTracker

st.title("📋 Trade History")

# Load trades
@st.cache_data(ttl=30)
def load_trades():
    tracker = MetricsTracker()
    return tracker.trades

try:
    trades = load_trades()
    
    if trades:
        # Convert to DataFrame
        df = pd.DataFrame(trades)
        
        # Format columns
        if 'entry_time' in df.columns:
            df['entry_time'] = pd.to_datetime(df['entry_time'])
        if 'exit_time' in df.columns:
            df['exit_time'] = pd.to_datetime(df['exit_time'])
        
        # Add P&L color
        df['pnl_color'] = df['pnl'].apply(lambda x: 'green' if x > 0 else 'red')
        
        # Filters
        col1, col2, col3 = st.columns(3)
        with col1:
            symbols = st.multiselect("Filter by Symbol", df['symbol'].unique() if 'symbol' in df.columns else [])
        with col2:
            agents = st.multiselect("Filter by Agent", df['agent_name'].unique() if 'agent_name' in df.columns else [])
        with col3:
            date_range = st.date_input("Date Range", [])
        
        # Apply filters
        filtered_df = df.copy()
        if symbols and 'symbol' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['symbol'].isin(symbols)]
        if agents and 'agent_name' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['agent_name'].isin(agents)]
        
        # Display trades
        st.subheader(f"Total Trades: {len(filtered_df)}")
        
        # Summary metrics
        if len(filtered_df) > 0:
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                total_pnl = filtered_df['pnl'].sum()
                st.metric("Total P&L", f"${total_pnl:,.2f}")
            with col2:
                winning = len(filtered_df[filtered_df['pnl'] > 0])
                st.metric("Winning Trades", winning)
            with col3:
                losing = len(filtered_df[filtered_df['pnl'] < 0])
                st.metric("Losing Trades", losing)
            with col4:
                win_rate = (winning / len(filtered_df) * 100) if len(filtered_df) > 0 else 0
                st.metric("Win Rate", f"{win_rate:.1f}%")
        
        # Display table
        st.dataframe(
            filtered_df,
            use_container_width=True,
            hide_index=True
        )
        
        # Export button
        csv = filtered_df.to_csv(index=False)
        st.download_button(
            label="📥 Download as CSV",
            data=csv,
            file_name=f"trades_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    else:
        st.info("No trades recorded yet. Trades will appear here once executed.")
        
        # Try to load from JSON file
        trades_file = Path("logs/trades.json")
        if trades_file.exists():
            try:
                with open(trades_file, 'r') as f:
                    file_trades = json.load(f)
                if file_trades:
                    st.success(f"Found {len(file_trades)} trades in file")
                    df = pd.DataFrame(file_trades)
                    st.dataframe(df, use_container_width=True)
            except Exception as e:
                st.warning(f"Could not load trades from file: {e}")

except Exception as e:
    st.error(f"Error loading trade history: {e}")
    import traceback
    st.code(traceback.format_exc())

