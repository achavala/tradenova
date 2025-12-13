"""
Backtesting Page
Run backtests on historical data and view results
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path
import sys
import json
from datetime import datetime, timedelta
import os

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import Config
from backtest_trading import BacktestEngine

st.title("🔬 Backtesting")

# Initialize session state for backtest results
if 'backtest_results' not in st.session_state:
    st.session_state.backtest_results = None
if 'backtest_running' not in st.session_state:
    st.session_state.backtest_running = False

# Sidebar for configuration
with st.sidebar:
    st.header("⚙️ Backtest Configuration")
    
    # Ticker selection
    selected_tickers = st.multiselect(
        "Select Tickers",
        Config.TICKERS,
        default=['NVDA', 'AAPL', 'TSLA']
    )
    
    # Date range
    st.subheader("Date Range")
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input(
            "Start Date",
            value=datetime.now() - timedelta(days=90),
            max_value=datetime.now()
        )
    with col2:
        end_date = st.date_input(
            "End Date",
            value=datetime.now(),
            max_value=datetime.now(),
            min_value=start_date
        )
    
    # Initial balance
    initial_balance = st.number_input(
        "Initial Balance ($)",
        value=100000.0,
        min_value=1000.0,
        step=10000.0
    )
    
    # Quick date presets
    st.subheader("Quick Presets")
    if st.button("Last 30 Days"):
        start_date = datetime.now() - timedelta(days=30)
        st.rerun()
    if st.button("Last 90 Days"):
        start_date = datetime.now() - timedelta(days=90)
        st.rerun()
    if st.button("Last 6 Months"):
        start_date = datetime.now() - timedelta(days=180)
        st.rerun()
    if st.button("Last Year"):
        start_date = datetime.now() - timedelta(days=365)
        st.rerun()

# Main content area
tab1, tab2, tab3 = st.tabs(["Run Backtest", "View Results", "Previous Backtests"])

with tab1:
    st.subheader("Run New Backtest")
    
    if not selected_tickers:
        st.warning("⚠️ Please select at least one ticker to backtest")
    else:
        st.info(f"**Selected Tickers**: {', '.join(selected_tickers)}")
        st.info(f"**Date Range**: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        st.info(f"**Initial Balance**: ${initial_balance:,.2f}")
        
        if st.button("🚀 Run Backtest", type="primary", disabled=st.session_state.backtest_running):
            if not selected_tickers:
                st.error("Please select at least one ticker")
            elif end_date <= start_date:
                st.error("End date must be after start date")
            else:
                st.session_state.backtest_running = True
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                try:
                    status_text.text("Initializing backtest engine...")
                    progress_bar.progress(10)
                    
                    # Create backtest engine
                    engine = BacktestEngine(
                        tickers=selected_tickers,
                        start_date=datetime.combine(start_date, datetime.min.time()),
                        end_date=datetime.combine(end_date, datetime.max.time()),
                        initial_balance=initial_balance
                    )
                    
                    status_text.text("Fetching historical data...")
                    progress_bar.progress(30)
                    
                    # Fetch data
                    if not engine.fetch_historical_data():
                        st.error("Failed to fetch historical data. Please check your Alpaca API credentials.")
                        st.session_state.backtest_running = False
                    else:
                        status_text.text("Running backtest simulation...")
                        progress_bar.progress(50)
                        
                        # Run backtest
                        engine.run_backtest()
                        
                        progress_bar.progress(90)
                        status_text.text("Generating results...")
                        
                        # Prepare results
                        total_trades = len(engine.trades)
                        winning_trades = [t for t in engine.trades if t['pnl'] > 0]
                        losing_trades = [t for t in engine.trades if t['pnl'] <= 0]
                        
                        win_rate = len(winning_trades) / total_trades * 100 if total_trades > 0 else 0
                        total_pnl = sum(t['pnl'] for t in engine.trades)
                        total_return = ((engine.current_balance - initial_balance) / initial_balance) * 100
                        
                        # Calculate drawdown
                        peak = initial_balance
                        max_drawdown = 0
                        for point in engine.equity_curve:
                            if point['equity'] > peak:
                                peak = point['equity']
                            drawdown = ((peak - point['equity']) / peak) * 100
                            if drawdown > max_drawdown:
                                max_drawdown = drawdown
                        
                        # Store results
                        st.session_state.backtest_results = {
                            'start_date': start_date.isoformat(),
                            'end_date': end_date.isoformat(),
                            'tickers': selected_tickers,
                            'initial_balance': initial_balance,
                            'final_balance': engine.current_balance,
                            'total_return_pct': total_return,
                            'total_pnl': total_pnl,
                            'max_drawdown_pct': max_drawdown,
                            'total_trades': total_trades,
                            'winning_trades': len(winning_trades),
                            'losing_trades': len(losing_trades),
                            'win_rate_pct': win_rate,
                            'trades': engine.trades,
                            'equity_curve': engine.equity_curve,
                            'timestamp': datetime.now().isoformat()
                        }
                        
                        progress_bar.progress(100)
                        status_text.text("✅ Backtest complete!")
                        st.success("Backtest completed successfully! View results in the 'View Results' tab.")
                        st.session_state.backtest_running = False
                        
                except Exception as e:
                    st.error(f"Error running backtest: {e}")
                    import traceback
                    st.code(traceback.format_exc())
                    st.session_state.backtest_running = False

with tab2:
    st.subheader("Backtest Results")
    
    if st.session_state.backtest_results is None:
        st.info("No backtest results available. Run a backtest in the 'Run Backtest' tab.")
    else:
        results = st.session_state.backtest_results
        
        # Summary metrics
        st.markdown("### 📊 Performance Summary")
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric("Initial Balance", f"${results['initial_balance']:,.2f}")
        with col2:
            st.metric("Final Balance", f"${results['final_balance']:,.2f}")
        with col3:
            st.metric("Total Return", f"{results['total_return_pct']:.2f}%")
        with col4:
            st.metric("Total P&L", f"${results['total_pnl']:,.2f}")
        with col5:
            st.metric("Max Drawdown", f"{results['max_drawdown_pct']:.2f}%")
        
        st.markdown("---")
        
        # Trade statistics
        st.markdown("### 📈 Trade Statistics")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Trades", results['total_trades'])
        with col2:
            st.metric("Winning Trades", results['winning_trades'])
        with col3:
            st.metric("Losing Trades", results['losing_trades'])
        with col4:
            st.metric("Win Rate", f"{results['win_rate_pct']:.2f}%")
        
        st.markdown("---")
        
        # Equity curve chart
        st.markdown("### 📊 Equity Curve")
        if results['equity_curve']:
            equity_df = pd.DataFrame(results['equity_curve'])
            equity_df['timestamp'] = pd.to_datetime(equity_df['timestamp'])
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=equity_df['timestamp'],
                y=equity_df['equity'],
                mode='lines',
                name='Equity',
                line=dict(color='green', width=2)
            ))
            fig.add_hline(
                y=results['initial_balance'],
                line_dash="dash",
                line_color="gray",
                annotation_text="Initial Balance"
            )
            fig.update_layout(
                title="Equity Curve Over Time",
                xaxis_title="Date",
                yaxis_title="Equity ($)",
                height=400
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Drawdown chart
            equity_df['peak'] = equity_df['equity'].cummax()
            equity_df['drawdown'] = ((equity_df['peak'] - equity_df['equity']) / equity_df['peak']) * 100
            
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(
                x=equity_df['timestamp'],
                y=equity_df['drawdown'],
                mode='lines',
                name='Drawdown',
                fill='tozeroy',
                line=dict(color='red'),
                fillcolor='rgba(255,0,0,0.3)'
            ))
            fig2.update_layout(
                title="Drawdown Over Time",
                xaxis_title="Date",
                yaxis_title="Drawdown (%)",
                height=300
            )
            st.plotly_chart(fig2, use_container_width=True)
        
        # Trades table
        st.markdown("### 📋 Trade History")
        if results['trades']:
            trades_df = pd.DataFrame(results['trades'])
            
            # Format columns
            if 'entry_time' in trades_df.columns:
                trades_df['entry_time'] = pd.to_datetime(trades_df['entry_time'])
            if 'exit_time' in trades_df.columns:
                trades_df['exit_time'] = pd.to_datetime(trades_df['exit_time'])
            
            # Filters
            col1, col2 = st.columns(2)
            with col1:
                symbol_filter = st.multiselect(
                    "Filter by Symbol",
                    trades_df['symbol'].unique() if 'symbol' in trades_df.columns else []
                )
            with col2:
                pnl_filter = st.selectbox(
                    "Filter by P&L",
                    ["All", "Winners Only", "Losers Only"]
                )
            
            # Apply filters
            filtered_trades = trades_df.copy()
            if symbol_filter and 'symbol' in filtered_trades.columns:
                filtered_trades = filtered_trades[filtered_trades['symbol'].isin(symbol_filter)]
            if pnl_filter == "Winners Only":
                filtered_trades = filtered_trades[filtered_trades['pnl'] > 0]
            elif pnl_filter == "Losers Only":
                filtered_trades = filtered_trades[filtered_trades['pnl'] <= 0]
            
            st.dataframe(filtered_trades, use_container_width=True, height=400)
            
            # Download button
            csv = filtered_trades.to_csv(index=False)
            st.download_button(
                label="📥 Download Trades as CSV",
                data=csv,
                file_name=f"backtest_trades_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
        else:
            st.info("No trades executed during this backtest period.")
        
        # Performance by symbol
        if results['trades']:
            st.markdown("### 📊 Performance by Symbol")
            trades_df = pd.DataFrame(results['trades'])
            symbol_perf = trades_df.groupby('symbol')['pnl'].agg(['sum', 'count', 'mean']).reset_index()
            symbol_perf.columns = ['Symbol', 'Total P&L', 'Trades', 'Avg P&L']
            symbol_perf = symbol_perf.sort_values('Total P&L', ascending=False)
            
            fig = px.bar(
                symbol_perf,
                x='Symbol',
                y='Total P&L',
                title="P&L by Symbol",
                color='Total P&L',
                color_continuous_scale='RdYlGn'
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
            
            st.dataframe(symbol_perf, use_container_width=True)

with tab3:
    st.subheader("Previous Backtest Results")
    
    # Load previous backtest results from logs directory
    logs_dir = Path("logs")
    backtest_files = list(logs_dir.glob("backtest_results_*.json"))
    
    if not backtest_files:
        st.info("No previous backtest results found.")
    else:
        # Sort by modification time (newest first)
        backtest_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        st.info(f"Found {len(backtest_files)} previous backtest(s)")
        
        # Select a backtest to view
        backtest_options = {}
        for bf in backtest_files:
            try:
                with open(bf, 'r') as f:
                    data = json.load(f)
                    timestamp = datetime.fromtimestamp(bf.stat().st_mtime)
                    label = f"{timestamp.strftime('%Y-%m-%d %H:%M')} - {', '.join(data.get('tickers', []))}"
                    backtest_options[label] = bf
            except:
                backtest_options[bf.name] = bf
        
        selected_backtest = st.selectbox("Select Backtest to View", list(backtest_options.keys()))
        
        if selected_backtest and st.button("Load Backtest"):
            backtest_file = backtest_options[selected_backtest]
            try:
                with open(backtest_file, 'r') as f:
                    loaded_results = json.load(f)
                
                # Display summary
                st.markdown("### 📊 Summary")
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Initial Balance", f"${loaded_results.get('initial_balance', 0):,.2f}")
                with col2:
                    st.metric("Final Balance", f"${loaded_results.get('final_balance', 0):,.2f}")
                with col3:
                    st.metric("Total Return", f"{loaded_results.get('total_return_pct', 0):.2f}%")
                with col4:
                    st.metric("Win Rate", f"{loaded_results.get('win_rate_pct', 0):.2f}%")
                
                # Equity curve
                if 'equity_curve' in loaded_results:
                    st.markdown("### 📊 Equity Curve")
                    equity_df = pd.DataFrame(loaded_results['equity_curve'])
                    equity_df['timestamp'] = pd.to_datetime(equity_df['timestamp'])
                    
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=equity_df['timestamp'],
                        y=equity_df['equity'],
                        mode='lines',
                        name='Equity',
                        line=dict(color='green', width=2)
                    ))
                    fig.update_layout(
                        title="Equity Curve",
                        xaxis_title="Date",
                        yaxis_title="Equity ($)",
                        height=400
                    )
                    st.plotly_chart(fig, use_container_width=True)
                
                # Trades
                if 'trades' in loaded_results and loaded_results['trades']:
                    st.markdown("### 📋 Trades")
                    trades_df = pd.DataFrame(loaded_results['trades'])
                    st.dataframe(trades_df, use_container_width=True, height=400)
                
            except Exception as e:
                st.error(f"Error loading backtest: {e}")

