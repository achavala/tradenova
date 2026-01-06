# Comprehensive System Analysis - TradeNova Options Trading

**Date:** December 19, 2025  
**Purpose:** Identify why no trades are executing and validate all systems

---

## 📊 SYSTEM OVERVIEW

### **Goal:**
Buy LONG options (0-30 DTE expiration) on 12 tickers:
- NVDA, AAPL, TSLA, META, GOOG, MSFT, AMZN, MSTR, AVGO, PLTR, AMD, INTC

---

## 🔍 DATA SOURCES & SYSTEMS

### **1. DATA PROVIDERS**

#### **A. Massive (Polygon.io) - PRIMARY DATA SOURCE**
- **Purpose:** Historical price data & Options quotes
- **Endpoints Used:**
  - `/v2/aggs/ticker/{symbol}/range/1/minute/{start}/{end}` - 1-minute bars
  - `/v3/snapshot/options/{symbol}` - Options chain with prices
- **Data Used:**
  - Historical daily bars (aggregated from 1-minute)
  - Options chain data
  - Option prices (day.close, prev_day.close, day.open)
- **File:** `services/massive_price_feed.py`, `services/polygon_options_feed.py`
- **Status:** ✅ Configured (if API key set)

#### **B. Alpaca - TRADING PLATFORM & EXECUTION**
- **Purpose:** Trade execution & Account management
- **Endpoints Used:**
  - `/v2/account` - Account info
  - `/v2/options/contracts` - Options chain
  - `/v2/orders` - Order execution
  - `/v2/positions` - Position tracking
- **Data Used:**
  - Account balance
  - Options contracts (symbols, strikes, expirations)
  - Order placement
- **File:** `alpaca_client.py`, `core/live/broker_executor.py`
- **Status:** ✅ Paper Trading configured

#### **C. Alpha Vantage (Optional)**
- **Purpose:** Earnings calendar
- **Status:** Optional

---

## 🎯 TRADING FLOW - COMPLETE PROCESS

### **STEP 1: Trading Cycle Trigger**
```
run_daily.py → TradingScheduler → run_trading_cycle()
```
- Runs every 5 minutes during market hours
- Checks if market is open
- Proceeds to scan

**File:** `run_daily.py`, `core/live/trading_scheduler.py`

---

### **STEP 2: Position Limit Check**
```python
if len(self.positions) >= Config.MAX_ACTIVE_TRADES:
    logger.info("Max positions reached - skipping scan")
    return
```
- **Check:** Current positions < 10
- **Action:** If >= 10, skip scan

**File:** `core/live/integrated_trader.py:240`

---

### **STEP 3: Market Hours Check**
```python
if not self.client.is_market_open():
    logger.info("Market is closed - Exiting scan")
    return
```
- **Check:** Market is open (9:30 AM - 4:00 PM ET)
- **Action:** If closed, exit

**File:** `core/live/integrated_trader.py:252`

---

### **STEP 4: News Filter Check**
```python
if self.news_filter.is_blocked():
    logger.warning("Trading blocked due to news event")
    return
```
- **Check:** No volatile news events
- **Action:** If blocked, skip trading

**File:** `core/live/integrated_trader.py:256`

---

### **STEP 5: Scan Each Ticker**

For each of 12 tickers:

#### **5A. Get Historical Bars (Data Source Check)**
```python
# Try Massive first
if self.massive_price_feed and self.massive_price_feed.is_available():
    bars = self.massive_price_feed.get_daily_bars(...)
else:
    bars = self.client.get_historical_bars(...)  # Alpaca fallback
```

**Requirements:**
- Minimum 30 bars needed
- If < 30 bars → Skip symbol

**File:** `core/live/integrated_trader.py:330`

---

#### **5B. Signal Generation**

**Multi-Agent System:**
- TrendAgent
- MeanReversionAgent
- FVGAgent
- VolatilityAgent
- EMAAgent
- OptionsAgent
- ThetaHarvesterAgent
- GammaScalperAgent

**RL Predictor (Optional):**
- PPO/GRPO model predictions

**Ensemble:**
- Combines multiple signals if available

**Output:** Trade direction (LONG/SHORT/FLAT) + confidence (0-1)

**File:** `core/multi_agent_orchestrator.py`

**Requirements:**
- Direction must be LONG (options-only)
- Confidence >= 60%

---

#### **5C. Current Price Check**
```python
current_price = self.client.get_latest_price(symbol)
if current_price is None:
    continue  # Skip symbol
```

**File:** `core/live/integrated_trader.py:353`

---

#### **5D. IV Rank Check (Optional)**
```python
iv_rank = iv_rank_service.get_iv_rank(symbol)
# Warning if insufficient IV history, but doesn't block
```

**File:** `core/live/integrated_trader.py:423`

---

#### **5E. Risk Manager Check**
```python
allowed, reason, risk_level = self.risk_manager.check_trade_allowed(
    symbol=symbol,
    qty=qty,
    price=current_price,
    side='buy',
    iv_rank=iv_rank,
    current_positions=current_positions
)
```

**Risk Checks (4-Layer Stack):**

1. **Gap Risk Monitor:**
   - Checks for earnings/macro events
   - Blocks if high gap risk

2. **IV Regime Filters:**
   - Checks IV rank vs IV regime
   - Blocks if unfavorable IV conditions

3. **Portfolio Greeks Caps:**
   - Checks total portfolio Greeks
   - Blocks if limits exceeded

4. **UVaR Check:**
   - Checks portfolio risk (UVaR)
   - Blocks if risk too high

**File:** `core/risk/advanced_risk_manager.py`

---

#### **5F. Signal Filter (Options-Only)**
```python
if best_signal['direction'] != 'LONG':
    logger.info("⚠️ Skipping {symbol}: Only buying LONG options")
    continue
```

**Requirement:** Must be LONG signal (SHORT signals skipped)

**File:** `core/live/integrated_trader.py:417`

---

### **STEP 6: Options Execution (If All Checks Pass)**

#### **6A. Get Expiration Dates**
```python
expirations = options_feed.get_expiration_dates(symbol)
# From Alpaca: /v2/options/contracts
```

**Requirement:** Must have expirations available

---

#### **6B. Select Expiration (0-30 DTE)**
```python
for exp_date in sorted(expirations):
    dte = (exp_date - today).days
    if Config.MIN_DTE <= dte <= Config.MAX_DTE:  # 0 <= dte <= 30
        target_expiration = exp_date
        break
```

**Requirement:** Must find expiration in 0-30 DTE range

---

#### **6C. Get ATM Call Option**
```python
option_contract = options_feed.get_atm_options(
    symbol,
    target_expiration,
    'call'
)
```

**Process:**
1. Get options chain from Alpaca
2. Filter for calls
3. Find strike closest to current stock price
4. Return contract

**Requirement:** Must find ATM call option

---

#### **6D. Get Option Symbol**
```python
option_symbol = (
    option_contract.get('symbol') or 
    option_contract.get('contract_symbol') or
    ...
)
```

**Format:** `TSLA251219C00005000` (from Alpaca)

---

#### **6E. Get Option Price**

**Priority:**
1. **Massive (Primary):**
   - Get options chain from Massive
   - Match by strike
   - Extract: `day.close`, `prev_day.close`, `day.open`

2. **Alpaca Quote API (Fallback):**
   - `get_latest_trade()`, `get_latest_quote()`
   - Extract: `last_price`, `mid_price`, `bid/ask`

3. **Contract Data (Last Resort):**
   - Use `close_price` from contract

**Requirement:** Must get valid price > 0

---

#### **6F. Calculate Position Size**
```python
# Options position: 75% per trade
options_position_pct = min(position_size_pct * 1.5, 0.75)
position_capital = balance * options_position_pct / Config.MAX_ACTIVE_TRADES

contract_cost = option_price * 100
contracts = int(position_capital / contract_cost)
```

**Requirements:**
- `contracts >= 1` (must afford at least 1 contract)
- If < 1, try OTM option (5% OTM)

---

#### **6G. Execute Order**
```python
if self.dry_run:
    # Simulate
else:
    order = self.executor.execute_market_order(
        symbol=option_symbol,
        qty=contracts,
        side='buy',
        is_option=True
    )
```

**Process:**
- Call `OptionsBrokerClient.place_option_order()`
- Submit to Alpaca API
- Wait for fill

---

## 🔄 COMPLETE FLOWCHART

```
START: Trading Cycle (Every 5 min)
│
├─→ Check Position Limit
│   ├─→ >= 10 positions? → EXIT (Skip)
│   └─→ < 10 positions? → CONTINUE
│
├─→ Check Market Hours
│   ├─→ Closed? → EXIT
│   └─→ Open? → CONTINUE
│
├─→ Check News Filter
│   ├─→ Blocked? → EXIT
│   └─→ Allowed? → CONTINUE
│
├─→ FOR EACH TICKER (12 tickers):
│   │
│   ├─→ Get Historical Bars
│   │   ├─→ Try Massive (Primary)
│   │   ├─→ Fallback to Alpaca
│   │   └─→ < 30 bars? → SKIP TICKER
│   │
│   ├─→ Generate Signal
│   │   ├─→ Multi-Agent System
│   │   ├─→ RL Predictor (Optional)
│   │   ├─→ Ensemble
│   │   └─→ Not LONG? → SKIP TICKER
│   │
│   ├─→ Get Current Price
│   │   └─→ None? → SKIP TICKER
│   │
│   ├─→ Risk Manager Check
│   │   ├─→ Gap Risk Monitor
│   │   ├─→ IV Regime Filters
│   │   ├─→ Portfolio Greeks Caps
│   │   ├─→ UVaR Check
│   │   └─→ Blocked? → SKIP TICKER
│   │
│   ├─→ Get Options Expirations
│   │   └─→ None? → SKIP TICKER
│   │
│   ├─→ Select Expiration (0-30 DTE)
│   │   └─→ None found? → SKIP TICKER
│   │
│   ├─→ Get ATM Call Option
│   │   └─→ None found? → SKIP TICKER
│   │
│   ├─→ Get Option Symbol
│   │   └─→ None? → SKIP TICKER
│   │
│   ├─→ Get Option Price
│   │   ├─→ Try Massive
│   │   ├─→ Try Alpaca Quote
│   │   ├─→ Try Contract Data
│   │   └─→ None? → SKIP TICKER
│   │
│   ├─→ Calculate Position Size
│   │   ├─→ Can afford 1+ contracts? → CONTINUE
│   │   └─→ Too expensive? → Try OTM → SKIP if still too expensive
│   │
│   └─→ Execute Order
│       ├─→ Dry Run? → Log only
│       └─→ Live? → Submit to Alpaca
│
└─→ END: Cycle Complete
```

---

## ⚠️ POTENTIAL BLOCKING POINTS

### **1. Signal Generation Issues**
- **Problem:** No LONG signals generated
- **Check:** Are signals being generated? (Check logs for "Signal found")
- **Action:** Verify multi-agent system is working

### **2. Risk Manager Blocking**
- **Problem:** Trades blocked by risk manager
- **Check:** Look for "Trade BLOCKED" in logs
- **Action:** Review risk check reasons

### **3. Data Insufficiency**
- **Problem:** Not enough historical bars (< 30)
- **Check:** Look for "Insufficient data" warnings
- **Action:** Verify Massive data feed is working

### **4. Options Availability**
- **Problem:** No options in 0-30 DTE range
- **Check:** Look for "No expiration found" warnings
- **Action:** Verify Alpaca options chain retrieval

### **5. Price Availability**
- **Problem:** No option price available
- **Check:** Look for "No quote available" warnings
- **Action:** Verify Massive/Alpaca quote feeds

### **6. Position Size Too Small**
- **Problem:** Can't afford even 1 contract
- **Check:** Look for "Position size too small" warnings
- **Action:** Verify account balance and option prices

### **7. Market Closed**
- **Problem:** Trading during market closed hours
- **Check:** Verify market hours
- **Action:** Wait for market open (9:30 AM - 4:00 PM ET)

---

## 📋 VALIDATION CHECKLIST

### **Data Sources:**
- [ ] Massive API key configured?
- [ ] Massive returning data?
- [ ] Alpaca API keys configured?
- [ ] Alpaca connection working?

### **Signal Generation:**
- [ ] Signals being generated?
- [ ] LONG signals found?
- [ ] Confidence >= 60%?

### **Risk Management:**
- [ ] Risk manager initialized?
- [ ] Trades passing risk checks?
- [ ] IV Rank available?

### **Options Data:**
- [ ] Expirations available?
- [ ] 0-30 DTE options found?
- [ ] ATM options selected?
- [ ] Option symbols correct?

### **Execution:**
- [ ] Option prices available?
- [ ] Position size calculated?
- [ ] Orders being submitted?
- [ ] Dry run mode off?

---

## 🎯 NEXT STEPS

1. **Check Logs:** Review recent logs for blocking points
2. **Test Each Component:** Validate each system independently
3. **Manual Test:** Try executing a single trade manually
4. **Debug Mode:** Add more detailed logging

---

**This analysis shows all systems, data sources, and potential blocking points.**




