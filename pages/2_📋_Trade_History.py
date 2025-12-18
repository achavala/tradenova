"""
Trade History Page
Displays all trades from backtests and live trading
"""
import streamlit as st
import pandas as pd
import json
from pathlib import Path
from datetime import datetime
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

st.set_page_config(
    page_title="Trade History - TradeNova",
    page_icon="📋",
    layout="wide"
)

# Import and render persistent sidebar
from core.ui.sidebar import render_sidebar
render_sidebar()

st.title("📋 Trade History")

# Load trades from both backtest and live trading
@st.cache_data(ttl=60)
def load_all_trades():
    """Load trades from both backtest results and live Alpaca orders"""
    from core.ui.trade_loader import load_all_trades as loader
    
    return loader()

# Load trades
trades = load_all_trades()

if not trades:
    st.info("No trades found.")
    st.markdown("""
    ### How to see trades:
    1. **Backtest trades**: Run a backtest: `python scripts/backtest_last_week.py`
       - Trades will be saved to `logs/backtest_results_*.json`
    2. **Live trades**: The system will automatically load trades from your Alpaca account
       - Make sure your Alpaca API credentials are configured in `.env`
    3. Refresh this page to see the results
    """)
else:
    # Convert to DataFrame
    df = pd.DataFrame(trades)
    
    # Parse dates
    if 'entry_time' in df.columns:
        df['entry_time'] = pd.to_datetime(df['entry_time'])
    if 'exit_time' in df.columns:
        df['exit_time'] = pd.to_datetime(df['exit_time'], errors='coerce')
    
    # Sort by entry time (newest first)
    if 'entry_time' in df.columns:
        df = df.sort_values('entry_time', ascending=False)
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_trades = len(df)
        st.metric("Total Trades", total_trades)
    
    with col2:
        winning_trades = len(df[df['pnl'] > 0]) if 'pnl' in df.columns else 0
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        st.metric("Win Rate", f"{win_rate:.1f}%")
    
    with col3:
        total_pnl = df['pnl'].sum() if 'pnl' in df.columns else 0
        st.metric("Total P&L", f"${total_pnl:,.2f}")
    
    with col4:
        avg_pnl = df['pnl'].mean() if 'pnl' in df.columns else 0
        st.metric("Avg P&L", f"${avg_pnl:,.2f}")
    
    st.markdown("---")
    
    # Filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        symbols = ['All'] + sorted(df['symbol'].unique().tolist()) if 'symbol' in df.columns else ['All']
        selected_symbol = st.selectbox("Filter by Symbol", symbols)
    
    with col2:
        if 'agent' in df.columns:
            agents = ['All'] + sorted(df['agent'].dropna().unique().tolist())
            selected_agent = st.selectbox("Filter by Agent", agents)
        else:
            selected_agent = 'All'
    
    with col3:
        if 'pnl' in df.columns:
            pnl_filter = st.selectbox("Filter by P&L", ['All', 'Winners', 'Losers'])
        else:
            pnl_filter = 'All'
    
    # Apply filters
    filtered_df = df.copy()
    
    if selected_symbol != 'All' and 'symbol' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['symbol'] == selected_symbol]
    
    if selected_agent != 'All' and 'agent' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['agent'] == selected_agent]
    
    if pnl_filter == 'Winners' and 'pnl' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['pnl'] > 0]
    elif pnl_filter == 'Losers' and 'pnl' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['pnl'] <= 0]
    
    st.markdown(f"**Showing {len(filtered_df)} of {len(df)} trades**")
    
    # Prepare display columns
    display_columns = []
    if 'entry_time' in filtered_df.columns:
        display_columns.append('entry_time')
    if 'symbol' in filtered_df.columns:
        display_columns.append('symbol')
    if 'agent' in filtered_df.columns:
        display_columns.append('agent')
    if 'entry_price' in filtered_df.columns:
        display_columns.append('entry_price')
    if 'exit_price' in filtered_df.columns:
        display_columns.append('exit_price')
    if 'exit_time' in filtered_df.columns:
        display_columns.append('exit_time')
    if 'pnl' in filtered_df.columns:
        display_columns.append('pnl')
    if 'pnl_pct' in filtered_df.columns:
        display_columns.append('pnl_pct')
    
    if display_columns:
        display_df = filtered_df[display_columns].copy()
        
        # Format columns for display
        if 'entry_time' in display_df.columns:
            display_df['entry_time'] = display_df['entry_time'].dt.strftime('%Y-%m-%d %H:%M')
        if 'exit_time' in display_df.columns:
            display_df['exit_time'] = display_df['exit_time'].dt.strftime('%Y-%m-%d %H:%M')
        if 'entry_price' in display_df.columns:
            display_df['entry_price'] = display_df['entry_price'].apply(lambda x: f"${x:.2f}" if pd.notna(x) else "N/A")
        if 'exit_price' in display_df.columns:
            display_df['exit_price'] = display_df['exit_price'].apply(lambda x: f"${x:.2f}" if pd.notna(x) else "N/A")
        if 'pnl' in display_df.columns:
            display_df['pnl'] = display_df['pnl'].apply(lambda x: f"${x:,.2f}" if pd.notna(x) else "$0.00")
        if 'pnl_pct' in display_df.columns:
            display_df['pnl_pct'] = display_df['pnl_pct'].apply(lambda x: f"{x:.2f}%" if pd.notna(x) else "0.00%")
        
        # Rename columns for display
        column_names = {
            'entry_time': 'Entry Time',
            'symbol': 'Symbol',
            'agent': 'Agent',
            'entry_price': 'Entry Price',
            'exit_price': 'Exit Price',
            'exit_time': 'Exit Time',
            'pnl': 'P&L',
            'pnl_pct': 'P&L %'
        }
        display_df = display_df.rename(columns=column_names)
        
        # Color code P&L
        def color_pnl(val):
            try:
                pnl_val = float(val.replace('$', '').replace(',', ''))
                if pnl_val > 0:
                    return 'background-color: #d4edda; color: #155724;'
                elif pnl_val < 0:
                    return 'background-color: #f8d7da; color: #721c24;'
                else:
                    return ''
            except:
                return ''
        
        # Apply styling
        styled_df = display_df.style.applymap(color_pnl, subset=['P&L'])
        
        st.dataframe(styled_df, use_container_width=True, hide_index=True)
        
        # Download button
        csv = filtered_df.to_csv(index=False)
        st.download_button(
            label="📥 Download Trade History (CSV)",
            data=csv,
            file_name=f"trade_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
    else:
        st.warning("No displayable columns found in trade data.")
    
    # Performance by symbol
    if 'symbol' in filtered_df.columns and 'pnl' in filtered_df.columns:
        st.markdown("---")
        st.subheader("📊 Performance by Symbol")
        
        symbol_stats = filtered_df.groupby('symbol').agg({
            'pnl': ['sum', 'count', 'mean']
        }).round(2)
        symbol_stats.columns = ['Total P&L', 'Trades', 'Avg P&L']
        symbol_stats = symbol_stats.sort_values('Total P&L', ascending=False)
        
        st.dataframe(symbol_stats, use_container_width=True)
    
    # Performance by agent
    if 'agent' in filtered_df.columns and 'pnl' in filtered_df.columns:
        st.markdown("---")
        st.subheader("🤖 Performance by Agent")
        
        agent_stats = filtered_df.groupby('agent').agg({
            'pnl': ['sum', 'count', 'mean']
        }).round(2)
        agent_stats.columns = ['Total P&L', 'Trades', 'Avg P&L']
        agent_stats = agent_stats.sort_values('Total P&L', ascending=False)
        
        st.dataframe(agent_stats, use_container_width=True)

