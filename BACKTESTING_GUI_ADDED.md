# Backtesting Feature Added to GUI

## ✅ New Feature: Backtesting Page

A comprehensive backtesting interface has been added to the TradeNova dashboard, allowing you to test the trading system on any historical date range.

## 📍 Location

**Dashboard Page**: `7_🔬_Backtesting.py`  
**Access**: Navigate to "🔬 Backtesting" in the sidebar menu

## 🎯 Features

### 1. **Run Backtest Tab**
- **Ticker Selection**: Choose multiple tickers from the available list
- **Date Range Picker**: Select any start and end date
- **Initial Balance**: Set starting capital for the backtest
- **Quick Presets**: One-click date ranges (30 days, 90 days, 6 months, 1 year)
- **Real-time Progress**: Progress bar and status updates during backtest execution

### 2. **View Results Tab**
- **Performance Summary**: 
  - Initial/Final Balance
  - Total Return %
  - Total P&L
  - Max Drawdown %
  
- **Trade Statistics**:
  - Total Trades
  - Winning/Losing Trades
  - Win Rate
  
- **Visualizations**:
  - Equity Curve Chart (interactive)
  - Drawdown Chart
  - Performance by Symbol (bar chart)
  
- **Trade History Table**:
  - All executed trades
  - Filter by symbol
  - Filter by P&L (winners/losers)
  - Export to CSV

### 3. **Previous Backtests Tab**
- View all previously run backtests
- Load and analyze historical backtest results
- Compare different backtest runs

## 🚀 How to Use

### Step 1: Configure Backtest
1. Open the dashboard: `streamlit run dashboard.py --server.port 8502`
2. Navigate to "🔬 Backtesting" in the sidebar
3. Select tickers to backtest
4. Choose date range (or use quick presets)
5. Set initial balance

### Step 2: Run Backtest
1. Click "🚀 Run Backtest" button
2. Watch progress bar and status updates
3. Wait for completion (may take a few minutes depending on date range)

### Step 3: View Results
1. Switch to "View Results" tab
2. Review performance metrics
3. Analyze equity curve and drawdown charts
4. Examine individual trades
5. Export data if needed

### Step 4: Compare Previous Runs
1. Go to "Previous Backtests" tab
2. Select a previous backtest from the dropdown
3. Click "Load Backtest" to view details

## 📊 What Gets Tested

The backtest engine simulates:
- ✅ Multi-agent signal generation
- ✅ Trade execution logic
- ✅ Profit target system (TP1-TP5)
- ✅ Stop loss management
- ✅ Position sizing
- ✅ Risk management rules
- ✅ Real historical market data from Alpaca

## 📈 Metrics Calculated

- **Total Return**: Percentage gain/loss
- **Total P&L**: Dollar amount profit/loss
- **Win Rate**: Percentage of winning trades
- **Max Drawdown**: Largest peak-to-trough decline
- **Average Win/Loss**: Average profit per winning/losing trade
- **Profit Factor**: Ratio of gross profit to gross loss
- **Performance by Symbol**: Individual ticker performance

## 🔧 Technical Details

### Backend Engine
- Uses `BacktestEngine` from `backtest_trading.py`
- Fetches real historical data from Alpaca API
- Simulates trading with actual market conditions
- Tracks all positions, trades, and equity curve

### Data Storage
- Results saved to `logs/backtest_results_*.json`
- Includes all trades, equity curve, and metrics
- Can be reloaded later for comparison

### Performance
- Processes historical data day-by-day
- Simulates 5-minute trading cycles
- Handles multiple tickers simultaneously
- Efficient data caching

## 💡 Use Cases

1. **Strategy Validation**: Test trading strategies on historical data
2. **Parameter Tuning**: Compare different parameter settings
3. **Market Analysis**: See how system performs in different market conditions
4. **Risk Assessment**: Understand drawdown patterns and risk metrics
5. **Symbol Selection**: Identify which tickers perform best

## ⚠️ Important Notes

- **API Limits**: Backtests use Alpaca API - be mindful of rate limits
- **Data Availability**: Historical data depends on Alpaca's data coverage
- **Simulation vs Reality**: Backtests are simulations - actual results may vary
- **Processing Time**: Longer date ranges take more time to process

## 🎨 UI Features

- **Interactive Charts**: Zoom, pan, and hover for details
- **Real-time Updates**: Progress tracking during execution
- **Filtering**: Easy filtering of trades and results
- **Export**: Download results as CSV
- **Responsive Design**: Works on different screen sizes

## 📝 Example Workflow

1. **Test Recent Performance**:
   - Select: NVDA, AAPL, TSLA
   - Date Range: Last 90 days
   - Initial Balance: $100,000
   - Run backtest and review results

2. **Compare Different Periods**:
   - Run backtest for Q1 2024
   - Run backtest for Q2 2024
   - Compare results in "Previous Backtests" tab

3. **Optimize Symbol Selection**:
   - Run backtest with different ticker combinations
   - Review "Performance by Symbol" chart
   - Identify best-performing symbols

## ✅ Status

**Backtesting feature is fully integrated and ready to use!**

The page is accessible from the dashboard sidebar and provides a complete backtesting interface with visualization and analysis tools.

---

**Enjoy testing your trading strategies on historical data!** 📈

