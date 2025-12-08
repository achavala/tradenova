# TradeNova Quick Start Guide

## 1. Installation

**Option A: Use setup script (Recommended)**
```bash
./setup.sh
```

**Option B: Manual setup**
```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

**Important**: Always activate the virtual environment before running TradeNova:
```bash
source venv/bin/activate
```

## 2. Configure Alpaca API

1. Sign up for [Alpaca Paper Trading](https://app.alpaca.markets/paper/dashboard/overview)
2. Get your API Key and Secret Key
3. Create `.env` file:
```bash
cp .env.example .env
```
4. Edit `.env` and add your credentials:
```
ALPACA_API_KEY=your_actual_api_key
ALPACA_SECRET_KEY=your_actual_secret_key
ALPACA_BASE_URL=https://paper-api.alpaca.markets
```

## 3. Verify Setup

```bash
python setup_check.py
```

This will verify:
- All dependencies are installed
- Environment variables are set
- Configuration loads correctly
- Alpaca API connection works

## 4. Activate Virtual Environment

**Before running TradeNova, make sure the virtual environment is activated:**
```bash
source venv/bin/activate
```

You should see `(venv)` in your terminal prompt.

## 5. Run TradeNova

### Continuous Mode (Recommended)
```bash
python main.py
```

This runs continuously, monitoring positions every 5 minutes and scanning for new opportunities.

### Single Run
```bash
python main.py once
```

This runs one trading cycle and exits.

## 6. Monitor Performance

- Check console output for real-time status
- View detailed logs in `tradenova.log`
- Status reports show:
  - Account balance
  - Active positions
  - Unrealized P/L
  - Profit target levels
  - Stop loss prices

## Key Features in Action

### Position Sizing
- System uses 50% of previous day's ending balance
- Automatically saved at end of trading day
- First run uses `INITIAL_BALANCE` from config

### Profit Targets
When a position reaches:
- **+40%**: Sells 50% of position (TP1)
- **+60%**: Sells 20% of remaining (TP2)
- **+100%**: Sells 10% of remaining (TP3)
- **+150%**: Sells 10% of remaining (TP4)
- **+200%**: Full exit (TP5)

### Risk Management
- **Stop Loss**: Always 15% below entry
- **Trailing Stop**: Activates after TP4, locks in +100% minimum
- **Max Positions**: Never more than 10 active trades

## Troubleshooting

### "API credentials not set"
- Check `.env` file exists and has correct values
- Run `python setup_check.py` to verify

### "Market is closed"
- Normal message outside trading hours
- System will resume when market opens

### "Max positions reached"
- System is at capacity (10 positions)
- Will open new positions as old ones close

### No trades executing
- Check signal confidence threshold (default: 60%)
- Verify market is open
- Check that tickers have sufficient data

## Next Steps

1. **Monitor First Day**: Watch how the system behaves
2. **Review Logs**: Check `tradenova.log` for detailed information
3. **Adjust Config**: Modify `.env` to fine-tune parameters
4. **Scale Up**: Once comfortable, consider increasing position size

## Important Notes

⚠️ **Paper Trading Only**: This is configured for paper trading. Always test thoroughly.

⚠️ **Market Hours**: System works best during regular market hours (9:30 AM - 4:00 PM ET).

⚠️ **Starting Balance**: Default is $10,000. Adjust `INITIAL_BALANCE` in `.env` if needed.

## Support

- Check `README.md` for detailed documentation
- Review logs in `tradenova.log` for error details
- Verify setup with `python setup_check.py`

Happy Trading! 🚀


