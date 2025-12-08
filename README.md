# TradeNova - Advanced Options Trading Agent

TradeNova is a sophisticated algorithmic trading agent designed for stock options trading with swing and scalp strategies. The system is built to turn $10K into $400K in one year through disciplined risk management and advanced profit target scaling.

## Features

### Core Capabilities
- **Multi-Ticker Trading**: Monitors and trades 12 high-volatility stocks (NVDA, AAPL, TSLA, META, GOOG, MSFT, AMZN, MSTR, AVGO, PLTR, AMD, INTC)
- **Risk Management**: Maximum 10 active trades at any time
- **Position Sizing**: Uses 50% of previous day's ending balance for new positions
- **Advanced Profit Targets**: 5-tier profit target system with partial exits
- **Trailing Stops**: Activates after TP4, locks in minimum +100% profit
- **Stop Loss**: Always 15% to protect capital

### Profit Target System
1. **TP1 at +40%**: Sell 50% of position
2. **TP2 at +60%**: Sell 20% of remaining position
3. **TP3 at +100%**: Sell 10% of remaining position
4. **TP4 at +150%**: Sell 10% of remaining position
5. **TP5 at +200%**: Full exit
6. **Trailing Stop**: Activates after TP4, locks in +100% minimum profit

### Trading Strategy
- **Swing Trading**: Captures medium-term trends
- **Scalp Trading**: Takes advantage of short-term price movements
- **Technical Indicators**: RSI, Moving Averages, Volume Analysis, Volatility (ATR)
- **Signal Generation**: Multi-factor scoring system with confidence levels

## Installation

1. **Clone or navigate to the project directory**:
```bash
cd TradeNova
```

2. **Set up virtual environment and install dependencies**:

   **Option A: Use the setup script (Recommended)**:
   ```bash
   ./setup.sh
   ```

   **Option B: Manual setup**:
   ```bash
   # Create virtual environment
   python3 -m venv venv
   
   # Activate virtual environment
   source venv/bin/activate  # On macOS/Linux
   # or
   venv\Scripts\activate  # On Windows
   
   # Install dependencies
   pip install -r requirements.txt
   ```

   **Note**: Always activate the virtual environment before running TradeNova:
   ```bash
   source venv/bin/activate
   ```

3. **Set up Alpaca API credentials**:
   - Get your API keys from [Alpaca Paper Trading](https://app.alpaca.markets/paper/dashboard/overview)
   - Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
   - Edit `.env` and add your credentials:
```
ALPACA_API_KEY=your_api_key_here
ALPACA_SECRET_KEY=your_secret_key_here
ALPACA_BASE_URL=https://paper-api.alpaca.markets
```

## Configuration

Edit `.env` file to customize:
- `INITIAL_BALANCE`: Starting capital (default: 10000)
- `MAX_ACTIVE_TRADES`: Maximum concurrent positions (default: 10)
- `POSITION_SIZE_PCT`: Percentage of balance to use (default: 0.50)
- `STOP_LOSS_PCT`: Stop loss percentage (default: 0.15)
- Profit target percentages and exit percentages
- Trailing stop parameters

## Usage

### Run in Continuous Mode (Recommended)
```bash
python main.py
```

This will:
- Monitor positions every 5 minutes
- Scan for new opportunities
- Execute trades based on signals
- Run daily close routine at market close (4:00 PM ET)

### Run Once
```bash
python main.py once
```

This will run a single trading cycle and exit.

## How It Works

### Daily Cycle
1. **Sync Positions**: Updates all positions with current prices from Alpaca
2. **Monitor Positions**: Checks all positions for:
   - Profit target hits (TP1-TP5)
   - Stop loss triggers
   - Trailing stop triggers
3. **Scan for Opportunities**: Analyzes all tickers for buy signals
4. **Execute Trades**: Opens new positions when:
   - Signal confidence > 60%
   - Under max position limit
   - Market is open

### Position Management
- Each position is tracked with entry price, quantity, and current profit target level
- Positions automatically scale out at profit targets
- Stop loss is always active at 15% below entry
- Trailing stop activates after TP4 to protect profits

### Risk Management
- **Never blow up account**: Uses only 50% of previous day balance
- **Position limits**: Maximum 10 active trades
- **Stop loss**: Always 15% to limit downside
- **Profit protection**: Trailing stop locks in minimum +100% after TP4

## File Structure

```
TradeNova/
├── main.py              # Main execution script
├── tradenova.py         # Core TradeNova agent class
├── config.py            # Configuration management
├── alpaca_client.py     # Alpaca API wrapper
├── position.py          # Position tracking and management
├── strategy.py          # Trading strategy implementation
├── requirements.txt     # Python dependencies
├── .env                 # Environment variables (create from .env.example)
├── daily_balance.json   # Previous day balance tracking
└── tradenova.log        # Application logs
```

## Important Notes

⚠️ **Paper Trading**: This system is configured for Alpaca Paper Trading. Always test thoroughly before using with real money.

⚠️ **Options Trading**: While designed for options, the current implementation works with stocks. Options trading requires additional considerations (Greeks, expiration, etc.).

⚠️ **Risk Warning**: Trading involves substantial risk. Past performance does not guarantee future results. The goal of turning $10K into $400K is ambitious and requires favorable market conditions.

## Advanced Features

### Balance Tracking
- System tracks previous day's ending balance
- Uses 50% of this balance for position sizing
- Automatically saves balance at end of trading day

### Position Scaling
- Partial exits at each profit target preserve capital
- Allows winners to run while locking in profits
- Trailing stop protects large gains

### Signal Generation
- Multi-factor analysis with confidence scoring
- Filters for volatility, volume, and momentum
- Only trades high-confidence signals (>60%)

## Monitoring

The system provides:
- Real-time status reports
- Position tracking with P/L
- Account balance monitoring
- Detailed logging to `tradenova.log`

## Troubleshooting

1. **API Connection Issues**: Verify your Alpaca credentials in `.env`
2. **No Trades Executing**: Check market hours and signal confidence thresholds
3. **Position Sync Issues**: Ensure positions in Alpaca match tracked positions

## Future Enhancements

Potential improvements:
- Options-specific trading (Greeks, expiration management)
- Machine learning signal generation
- Portfolio optimization
- Real-time alerts (Telegram, email)
- Advanced backtesting
- Multi-timeframe analysis

## License

This project is for educational and research purposes. Use at your own risk.

## Disclaimer

This software is provided "as is" without warranty of any kind. Trading involves risk of loss. Always test in paper trading before using real money. The authors are not responsible for any financial losses.


# tradenova
