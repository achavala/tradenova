# 📅 Weekend Testing Guide - Real Historical Data Replay

## Overview

The Weekend Testing system allows you to test your trading strategies using **REAL historical market data** from Alpaca, simulating live market conditions on weekends when markets are closed.

### ✅ **Key Features:**
- **100% Real Data**: Uses authentic historical data from Alpaca API
- **No Fake Entries**: All prices, volumes, and market data are real
- **Live Simulation**: Replays historical data as if it's happening in real-time
- **Intraday Support**: Uses 5-minute bars for realistic intraday trading
- **Speed Control**: Run at real-time or accelerated speeds (1x, 10x, 100x)
- **Full Integration**: Works with your existing trading system

---

## 🚀 Quick Start

### Basic Usage

Test with yesterday's data at 10x speed:

```bash
python weekend_test_runner.py --date 2025-12-04 --speed 10.0
```

### Test Specific Date

```bash
python weekend_test_runner.py --date 2025-12-03 --speed 5.0
```

### Real-Time Speed (for detailed analysis)

```bash
python weekend_test_runner.py --date 2025-12-04 --speed 1.0
```

### Daily Bars Mode (faster, less detailed)

```bash
python weekend_test_runner.py --date 2025-12-04 --speed 10.0 --daily
```

---

## 📊 How It Works

### 1. **Data Loading**
- Fetches **real historical data** from Alpaca API
- Loads 5-minute bars for intraday replay (or daily bars if `--daily`)
- Caches data for efficient replay

### 2. **Time Simulation**
- Simulates market hours: 9:30 AM - 4:00 PM ET
- Advances time based on speed multiplier
- System thinks market is "open" during simulation

### 3. **Price Replay**
- Returns historical prices at the correct simulation time
- `get_latest_price()` returns the price at current simulation time
- `get_historical_bars()` returns data up to current simulation time

### 4. **Order Simulation**
- Orders are simulated (not actually placed)
- Uses historical prices at execution time
- Tracks positions and P&L

---

## 🔧 Configuration

### Speed Multipliers

- **1.0x**: Real-time (6.5 hours = 6.5 hours)
- **10.0x**: 10x speed (6.5 hours = 39 minutes)
- **100.0x**: 100x speed (6.5 hours = 3.9 minutes)

### Data Modes

- **Intraday (default)**: Uses 5-minute bars for realistic intraday trading
- **Daily (`--daily`)**: Uses daily bars only (faster, less detailed)

---

## 📈 Example Output

```
================================================================================
WEEKEND TEST RUNNER - HISTORICAL DATA REPLAY
================================================================================
📅 Test Date: 2025-12-04
⏱️  Speed: 10.0x
📊 Mode: Intraday (5min)
================================================================================
📥 Loading REAL historical data for NVDA on 2025-12-04
✅ Loaded 78 bars for NVDA
📥 Loading REAL historical data for AAPL on 2025-12-04
✅ Loaded 78 bars for AAPL
...
================================================================================
STARTING FULL DAY SIMULATION
================================================================================
🌅 PRE-MARKET WARMUP (8:00 AM)
💰 Account Equity: $100,000.00
💵 Buying Power: $200,000.00
🛡️  Risk Level: Normal
🔔 MARKET OPEN (9:30 AM)
================================================================================
TRADING CYCLE #1 - 09:30:00
================================================================================
🔍 SCAN START: Analyzing 10 tickers
📊 Analyzing - NVDA
   Evaluating NVDA for trading signals
...
```

---

## ✅ Validation - Real Data Only

### How to Verify Data is Real:

1. **Check Logs**: Look for "Loading REAL historical data" messages
2. **Compare Prices**: Compare simulated prices with known historical prices
3. **Data Source**: All data comes from `AlpacaClient.get_historical_bars()` - no synthetic data

### What Gets Simulated:

- ✅ **Prices**: Real historical prices from Alpaca
- ✅ **Volumes**: Real historical volumes
- ✅ **Market Hours**: Simulated (9:30 AM - 4:00 PM)
- ✅ **Time Progression**: Simulated (based on speed multiplier)

### What Does NOT Get Simulated:

- ❌ **Price Data**: All prices are real
- ❌ **Volume Data**: All volumes are real
- ❌ **Market Events**: Real historical events are reflected in data

---

## 🎯 Use Cases

### 1. **Strategy Validation**
Test your strategy on historical dates to see how it would have performed.

### 2. **Weekend Testing**
Test and debug your system when markets are closed.

### 3. **Parameter Tuning**
Try different parameters and see results quickly with accelerated replay.

### 4. **Risk Testing**
Test risk management rules with historical volatile periods.

---

## 📝 Notes

### Data Availability

- Historical data availability depends on your Alpaca subscription
- Some tickers may have limited historical data
- Intraday data (5-minute bars) may not be available for all dates

### Performance

- First run loads all data (may take a few minutes)
- Subsequent cycles use cached data (fast)
- Daily mode is faster than intraday mode

### Limitations

- Options data: Historical options chains may be limited
- Real-time features: Some real-time features won't work (e.g., live news)
- Order execution: Orders are simulated, not actually placed

---

## 🔍 Troubleshooting

### "No historical data found"

**Solution**: Check if the date is a valid trading day and if your Alpaca subscription includes historical data for that date.

### "Market is closed"

**Solution**: The system simulates market hours. If you see this during simulation, it means the simulation time has reached market close (4:00 PM).

### "Insufficient data"

**Solution**: Some tickers may not have data for the selected date. Check your Alpaca subscription and data availability.

---

## 🚀 Next Steps

1. **Run a test**: `python weekend_test_runner.py --date 2025-12-04`
2. **Review logs**: Check `logs/weekend_test.log` for detailed output
3. **Analyze results**: Review the generated report in `logs/weekend_test_YYYY-MM-DD.txt`
4. **Iterate**: Adjust parameters and test again

---

## ✅ Summary

The Weekend Testing system provides a **production-grade** way to test your trading strategies using **100% real historical data** from Alpaca. No fake entries, no synthetic data - just authentic market data replayed in a controlled environment.

**Perfect for weekend testing when markets are closed!** 🎉

