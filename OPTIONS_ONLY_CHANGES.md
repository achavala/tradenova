# Options-Only Trading Changes

**Date:** December 19, 2025  
**Change:** Algorithm now ONLY buys options (0-30 DTE), NO stocks

---

## ✅ CHANGES APPLIED

### 1. Signal Filtering
- **Before:** Executed both LONG and SHORT signals (stocks)
- **After:** Only executes LONG signals (options only)
- **Location:** `core/live/integrated_trader.py:409-411`

```python
# Skip if signal is SHORT (we only buy options)
if best_signal['direction'] != 'LONG':
    logger.info(f"⚠️  Skipping {symbol}: Only buying LONG options")
    continue
```

### 2. Trade Execution
- **Before:** Executed stock orders
- **After:** Executes options orders only
- **Location:** `core/live/integrated_trader.py:_execute_trade()`

**Key Changes:**
- Gets options chain for symbol
- Filters for 0-30 DTE expirations
- Selects ATM (at-the-money) call options
- Calculates contracts (not shares)
- Executes BUY orders only

### 3. Position Tracking
- **Before:** Tracked stock positions
- **After:** Tracks option positions with metadata
- **Location:** `core/live/integrated_trader.py:550+`

**New Position Structure:**
```python
{
    'qty': contracts,
    'entry_price': option_price,
    'side': 'long',
    'underlying': symbol,
    'expiration': target_expiration,
    'option_type': 'call',
    'instrument_type': 'option'
}
```

### 4. Position Check
- **Before:** Checked if stock symbol in positions
- **After:** Checks if underlying has option position
- **Location:** `core/live/integrated_trader.py:314-322`

---

## 📊 NEW BEHAVIOR

### What Algorithm Does:
1. ✅ Scans all 12 tickers
2. ✅ Generates signals (LONG/SHORT)
3. ✅ **Only executes LONG signals**
4. ✅ **Buys ATM call options (0-30 DTE)**
5. ✅ Calculates position size in contracts
6. ✅ Tracks option positions

### What Algorithm Does NOT Do:
1. ❌ Execute SHORT signals
2. ❌ Buy or sell stocks
3. ❌ Sell options
4. ❌ Trade options outside 0-30 DTE range

---

## 🎯 OPTIONS SELECTION

### Criteria:
- **DTE Range:** 0-30 days (from Config.MIN_DTE to Config.MAX_DTE)
- **Strike:** ATM (at-the-money) - closest to current stock price
- **Type:** Call options only (for LONG signals)
- **Expiration:** First available expiration in 0-30 DTE range

### Example:
- **Symbol:** TSLA
- **Current Price:** $488.02
- **Selected:** TSLA call option
- **Strike:** ~$488 (ATM)
- **Expiration:** Next expiration in 0-30 DTE range
- **Action:** BUY contracts

---

## 📝 CONFIGURATION

### Current Settings:
```python
MIN_DTE = 0      # Minimum days to expiration
MAX_DTE = 30     # Maximum days to expiration
TARGET_DTE = 15  # Target DTE (preference)
```

### Position Sizing:
- Uses `Config.POSITION_SIZE_PCT` of account equity
- Divides by `Config.MAX_ACTIVE_TRADES`
- Calculates contracts: `position_capital / (option_price * 100)`
- Minimum: 1 contract

---

## ✅ VALIDATION

### Test Results:
- ✅ Imports successful
- ✅ Configuration correct (0-30 DTE)
- ✅ Code changes applied
- ✅ Position tracking updated

### Next Steps:
1. Restart trading system
2. Monitor logs for options execution
3. Verify options orders in Alpaca
4. Check position tracking

---

## 🔄 RESTART REQUIRED

**To apply changes:**
```bash
# Stop current trading system
pkill -f run_daily.py

# Restart with new options-only logic
python run_daily.py --paper
```

---

**The algorithm is now configured to ONLY buy options (0-30 DTE) and will skip all stock trades and SHORT signals.**




