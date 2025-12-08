"""
User Dashboard - Streamlit Web Interface
Professional dashboard for users to monitor their accounts
"""
import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

# Page config
st.set_page_config(
    page_title="TradeNova - Your Trading Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API base URL
API_BASE_URL = "http://localhost:8000"

# Initialize session state
if 'token' not in st.session_state:
    st.session_state.token = None
if 'user_id' not in st.session_state:
    st.session_state.user_id = None

def get_headers():
    """Get API headers with auth token"""
    if st.session_state.token:
        return {"Authorization": f"Bearer {st.session_state.token}"}
    return {}

def login_page():
    """Login page"""
    st.title("🔐 TradeNova Platform")
    st.subheader("Login to Your Account")
    
    # Show test credentials if no users exist
    st.info("**Test Credentials:**\n- Email: admin@tradenova.com\n- Password: admin123")
    
    with st.form("login_form"):
        email = st.text_input("Email", value="admin@tradenova.com")
        password = st.text_input("Password", type="password", value="admin123")
        submit = st.form_submit_button("Login")
        
        if submit:
            try:
                response = requests.post(
                    f"{API_BASE_URL}/api/auth/login",
                    json={"email": email, "password": password}
                )
                if response.status_code == 200:
                    data = response.json()
                    st.session_state.token = data['token']
                    st.session_state.user_id = data['id']
                    st.success("Login successful!")
                    st.rerun()
                else:
                    st.error(f"Login failed: {response.text}")
                    st.info("If this is your first time, the test user may need to be created. Check the terminal.")
            except Exception as e:
                st.error(f"Error connecting to API: {e}")
                st.info(f"Make sure the API server is running on {API_BASE_URL}")

def dashboard():
    """Main dashboard"""
    st.title("📈 TradeNova Trading Dashboard")
    
    # Sidebar
    with st.sidebar:
        st.header("Account")
        if st.button("Logout"):
            st.session_state.token = None
            st.session_state.user_id = None
            st.rerun()
        
        st.header("Navigation")
        page = st.radio(
            "Select Page",
            ["Portfolio", "Trades", "Backtesting", "Settings"]
        )
    
    # Get portfolio data
    try:
        portfolio_response = requests.get(
            f"{API_BASE_URL}/api/portfolio",
            headers=get_headers()
        )
        
        if portfolio_response.status_code == 200:
            portfolio = portfolio_response.json()
            
            # Portfolio Overview
            st.header("Portfolio Overview")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Equity", f"${portfolio['equity']:,.2f}")
            with col2:
                st.metric("Cash", f"${portfolio['cash']:,.2f}")
            with col3:
                return_color = "green" if portfolio['total_return_pct'] >= 0 else "red"
                st.metric("Total Return", f"{portfolio['total_return_pct']:.2f}%", delta=f"{portfolio['total_pnl']:,.2f}")
            with col4:
                st.metric("Win Rate", f"{portfolio['win_rate']:.2f}%")
            
            # Performance Metrics
            st.header("Performance Metrics")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Trades", portfolio.get('total_trades', 0))
            with col2:
                st.metric("Winning Trades", portfolio.get('winning_trades', 0))
            with col3:
                st.metric("Losing Trades", portfolio.get('losing_trades', 0))
            with col4:
                st.metric("Max Drawdown", f"{portfolio['max_drawdown_pct']:.2f}%")
            
            # Open Positions
            st.header("Open Positions")
            positions_response = requests.get(
                f"{API_BASE_URL}/api/portfolio/positions",
                headers=get_headers()
            )
            
            if positions_response.status_code == 200:
                positions = positions_response.json().get('positions', [])
                if positions:
                    df = pd.DataFrame(positions)
                    st.dataframe(df, use_container_width=True)
                else:
                    st.info("No open positions")
            
            # Trading Controls
            st.header("Trading Controls")
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("Start Trading", type="primary"):
                    response = requests.post(
                        f"{API_BASE_URL}/api/trading/start",
                        headers=get_headers()
                    )
                    if response.status_code == 200:
                        st.success("Trading started!")
                    else:
                        st.error("Error starting trading")
            
            with col2:
                if st.button("Stop Trading"):
                    response = requests.post(
                        f"{API_BASE_URL}/api/trading/stop",
                        headers=get_headers()
                    )
                    if response.status_code == 200:
                        st.success("Trading stopped!")
                    else:
                        st.error("Error stopping trading")
            
            # Trade History
            if page == "Trades":
                st.header("Trade History")
                trades_response = requests.get(
                    f"{API_BASE_URL}/api/portfolio/trades",
                    headers=get_headers()
                )
                
                if trades_response.status_code == 200:
                    trades = trades_response.json().get('trades', [])
                    if trades:
                        df = pd.DataFrame(trades)
                        st.dataframe(df, use_container_width=True)
                    else:
                        st.info("No trades yet")
            
            # Backtesting
            if page == "Backtesting":
                st.header("Run Backtest")
                
                with st.form("backtest_form"):
                    col1, col2 = st.columns(2)
                    with col1:
                        tickers = st.multiselect(
                            "Select Tickers",
                            ["NVDA", "AAPL", "TSLA", "META", "GOOG", "MSFT", "AMZN", "MSTR", "AVGO", "PLTR", "AMD", "INTC"],
                            default=["NVDA", "AAPL", "TSLA"]
                        )
                        start_date = st.date_input("Start Date", datetime.now() - timedelta(days=90))
                    with col2:
                        end_date = st.date_input("End Date", datetime.now())
                        initial_balance = st.number_input("Initial Balance", value=100000.0, step=10000.0)
                    
                    submit = st.form_submit_button("Run Backtest")
                    
                    if submit and tickers:
                        with st.spinner("Running backtest..."):
                            response = requests.post(
                                f"{API_BASE_URL}/api/backtest/run",
                                headers=get_headers(),
                                json={
                                    "tickers": tickers,
                                    "start_date": start_date.strftime("%Y-%m-%d"),
                                    "end_date": end_date.strftime("%Y-%m-%d"),
                                    "initial_balance": initial_balance
                                }
                            )
                            
                            if response.status_code == 200:
                                result = response.json()
                                st.success("Backtest completed!")
                                st.json(result)
                            else:
                                st.error("Error running backtest")
        
        else:
            st.error("Error loading portfolio")
    
    except Exception as e:
        st.error(f"Error: {e}")

# Main app
if st.session_state.token:
    dashboard()
else:
    login_page()

