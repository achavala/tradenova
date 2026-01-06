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
@st.cache_data(ttl=30)  # Refresh every 30 seconds
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
        df['entry_time'] = pd.to_datetime(df['entry_time'], errors='coerce')
    if 'exit_time' in df.columns:
        df['exit_time'] = pd.to_datetime(df['exit_time'], errors='coerce')
    
    # Sort by entry time (newest first)
    if 'entry_time' in df.columns:
        df = df.sort_values('entry_time', ascending=False)
    
    # Separate open and closed positions
    open_positions = df[df['status'] == 'OPEN'] if 'status' in df.columns else pd.DataFrame()
    closed_trades = df[df['status'] == 'CLOSED'] if 'status' in df.columns else df
    
    # Summary metrics
    st.subheader("📈 Portfolio Summary")
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        total_positions = len(open_positions)
        st.metric("Open Positions", total_positions)
    
    with col2:
        open_pnl = open_positions['pnl'].sum() if 'pnl' in open_positions.columns and len(open_positions) > 0 else 0
        st.metric("Unrealized P&L", f"${open_pnl:,.2f}", 
                 delta=f"{open_pnl/1000:.1f}K" if abs(open_pnl) > 0 else None,
                 delta_color="normal" if open_pnl >= 0 else "inverse")
    
    with col3:
        closed_pnl = closed_trades['pnl'].sum() if 'pnl' in closed_trades.columns and len(closed_trades) > 0 else 0
        st.metric("Realized P&L", f"${closed_pnl:,.2f}")
    
    with col4:
        total_pnl = (open_pnl if pd.notna(open_pnl) else 0) + (closed_pnl if pd.notna(closed_pnl) else 0)
        st.metric("Total P&L", f"${total_pnl:,.2f}",
                 delta_color="normal" if total_pnl >= 0 else "inverse")
    
    with col5:
        total_trades = len(df)
        winning = len(df[df['pnl'] > 0]) if 'pnl' in df.columns else 0
        win_rate = (winning / total_trades * 100) if total_trades > 0 else 0
        st.metric("Win Rate", f"{win_rate:.1f}%")
    
    st.markdown("---")
    
    # Show open positions
    if len(open_positions) > 0:
        st.subheader("🔓 Open Positions")
        
        # Prepare display
        open_display = open_positions[['symbol', 'qty', 'entry_price', 'exit_price', 'pnl', 'pnl_pct']].copy()
        open_display.columns = ['Symbol', 'Qty', 'Entry', 'Current', 'P&L ($)', 'P&L (%)']
        
        # Format columns
        open_display['Entry'] = open_display['Entry'].apply(lambda x: f"${x:.2f}" if pd.notna(x) else "N/A")
        open_display['Current'] = open_display['Current'].apply(lambda x: f"${x:.2f}" if pd.notna(x) else "N/A")
        open_display['P&L ($)'] = open_display['P&L ($)'].apply(lambda x: f"${x:,.2f}" if pd.notna(x) else "$0.00")
        open_display['P&L (%)'] = open_display['P&L (%)'].apply(lambda x: f"{x:.2f}%" if pd.notna(x) else "0.00%")
        open_display['Qty'] = open_display['Qty'].apply(lambda x: f"{int(x)}" if pd.notna(x) else "0")
        
        # Color code P&L
        def style_pnl(val):
            try:
                if isinstance(val, str):
                    # Remove $ and % and commas
                    clean = val.replace('$', '').replace('%', '').replace(',', '')
                    num = float(clean)
                else:
                    num = float(val)
                if num > 0:
                    return 'background-color: #d4edda; color: #155724; font-weight: bold;'
                elif num < 0:
                    return 'background-color: #f8d7da; color: #721c24; font-weight: bold;'
            except:
                pass
            return ''
        
        styled_open = open_display.style.applymap(style_pnl, subset=['P&L ($)', 'P&L (%)'])
        st.dataframe(styled_open, use_container_width=True, hide_index=True)
    
    st.markdown("---")
    
    # Show closed trades
    st.subheader("✅ Closed Trades")
    
    if len(closed_trades) > 0:
        # Filters
        col1, col2, col3 = st.columns(3)
        
        with col1:
            symbols = ['All'] + sorted(closed_trades['symbol'].unique().tolist()) if 'symbol' in closed_trades.columns else ['All']
            selected_symbol = st.selectbox("Filter by Symbol", symbols)
        
        with col2:
            if 'agent' in closed_trades.columns:
                agents = ['All'] + sorted(closed_trades['agent'].dropna().unique().tolist())
                selected_agent = st.selectbox("Filter by Agent", agents)
            else:
                selected_agent = 'All'
        
        with col3:
            if 'pnl' in closed_trades.columns:
                pnl_filter = st.selectbox("Filter by P&L", ['All', 'Winners', 'Losers'])
            else:
                pnl_filter = 'All'
        
        # Apply filters
        filtered_df = closed_trades.copy()
        
        if selected_symbol != 'All' and 'symbol' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['symbol'] == selected_symbol]
        
        if selected_agent != 'All' and 'agent' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['agent'] == selected_agent]
        
        if pnl_filter == 'Winners' and 'pnl' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['pnl'] > 0]
        elif pnl_filter == 'Losers' and 'pnl' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['pnl'] <= 0]
        
        st.markdown(f"**Showing {len(filtered_df)} closed trades**")
        
        if len(filtered_df) > 0:
            # Prepare display columns
            display_columns = []
            if 'entry_time' in filtered_df.columns:
                display_columns.append('entry_time')
            if 'symbol' in filtered_df.columns:
                display_columns.append('symbol')
            if 'qty' in filtered_df.columns:
                display_columns.append('qty')
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
                    display_df['exit_time'] = pd.to_datetime(display_df['exit_time'], errors='coerce').dt.strftime('%Y-%m-%d %H:%M')
                if 'entry_price' in display_df.columns:
                    display_df['entry_price'] = display_df['entry_price'].apply(lambda x: f"${x:.2f}" if pd.notna(x) else "N/A")
                if 'exit_price' in display_df.columns:
                    display_df['exit_price'] = display_df['exit_price'].apply(lambda x: f"${x:.2f}" if pd.notna(x) else "N/A")
                if 'pnl' in display_df.columns:
                    display_df['pnl'] = display_df['pnl'].apply(lambda x: f"${x:,.2f}" if pd.notna(x) else "$0.00")
                if 'pnl_pct' in display_df.columns:
                    display_df['pnl_pct'] = display_df['pnl_pct'].apply(lambda x: f"{x:.2f}%" if pd.notna(x) else "0.00%")
                if 'qty' in display_df.columns:
                    display_df['qty'] = display_df['qty'].apply(lambda x: f"{int(x)}" if pd.notna(x) else "0")
                
                # Rename columns for display
                column_names = {
                    'entry_time': 'Entry Time',
                    'symbol': 'Symbol',
                    'qty': 'Qty',
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
                        pnl_val = float(val.replace('$', '').replace(',', '').replace('%', ''))
                        if pnl_val > 0:
                            return 'background-color: #d4edda; color: #155724;'
                        elif pnl_val < 0:
                            return 'background-color: #f8d7da; color: #721c24;'
                        else:
                            return ''
                    except:
                        return ''
                
                # Apply styling
                if 'P&L' in display_df.columns:
                    styled_df = display_df.style.applymap(color_pnl, subset=['P&L'])
                    if 'P&L %' in display_df.columns:
                        styled_df = styled_df.applymap(color_pnl, subset=['P&L %'])
                    st.dataframe(styled_df, use_container_width=True, hide_index=True)
                else:
                    st.dataframe(display_df, use_container_width=True, hide_index=True)
        else:
            st.info("No closed trades matching filters.")
    else:
        st.info("No closed trades yet. All positions are currently open.")
    
    # Download button
    csv = df.to_csv(index=False)
    st.download_button(
        label="📥 Download All Trade History (CSV)",
        data=csv,
        file_name=f"trade_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv"
    )
    
    # Performance by symbol
    if 'symbol' in df.columns and 'pnl' in df.columns:
        st.markdown("---")
        st.subheader("📊 Performance by Symbol")
        
        symbol_stats = df.groupby('symbol').agg({
            'pnl': ['sum', 'count', 'mean']
        }).round(2)
        symbol_stats.columns = ['Total P&L', 'Trades', 'Avg P&L']
        symbol_stats['Total P&L'] = symbol_stats['Total P&L'].apply(lambda x: f"${x:,.2f}")
        symbol_stats['Avg P&L'] = symbol_stats['Avg P&L'].apply(lambda x: f"${x:,.2f}")
        symbol_stats = symbol_stats.sort_values('Trades', ascending=False)
        
        st.dataframe(symbol_stats, use_container_width=True)
