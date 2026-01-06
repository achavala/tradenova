# Complete TradeNova System Flow - Detailed Architecture

**Date:** December 22, 2025  
**System Version:** IntegratedTrader (Options-Only Trading System)

---

## Table of Contents

1. [System Overview](#system-overview)
2. [RL (Reinforcement Learning) Status](#rl-reinforcement-learning-status)
3. [Complete System Call Flow](#complete-system-call-flow)
4. [Component Details](#component-details)
5. [Data Flow Diagram](#data-flow-diagram)
6. [Decision Making Process](#decision-making-process)

---

## System Overview

TradeNova is a **multi-agent, reinforcement learning-enhanced options trading system** that:
- Trades **OPTIONS ONLY** (0-30 DTE, CALL and PUT)
- Uses **12 tickers**: NVDA, AAPL, TSLA, META, GOOG, MSFT, AMZN, MSTR, AVGO, PLTR, AMD, INTC
- Combines **8 specialized trading agents** + **RL predictions** + **Ensemble logic**
- Implements **4-layer risk management** stack
- Executes trades via **Alpaca API** (Paper Trading)

---

## RL (Reinforcement Learning) Status

### Is RL Working?

**Status:** ✅ **YES** (if model file exists)

**How to Check:**
```bash
ls -la models/grpo_final.zip models/ppo_final.zip
```

**RL Model Loading:**
- System looks for: `./models/grpo_final.zip` (preferred) or `./models/ppo_final.zip`
- If found: RL is **ENABLED** and loaded
- If not found: RL is **DISABLED**, system uses only multi-agent signals

### What Does RL Do?

**RL Predictor Job:**
1. **Input:** Historical price bars (60 days), current price, symbol
2. **Process:** Uses trained GRPO/PPO model to predict:
   - **Direction:** LONG, SHORT, or FLAT
   - **Confidence:** 0.0 to 1.0 (probability)
   - **Reasoning:** Text explanation of prediction
3. **Output:** Trading signal with confidence ≥ 0.6
4. **Integration:** Combined with multi-agent signals via Ensemble Predictor

**RL Model Type:**
- **GRPO (Group Relative Policy Optimization)** - Preferred
- **PPO (Proximal Policy Optimization)** - Fallback
- Trained on historical market data to learn optimal trading patterns

**RL Signal Requirements:**
- Direction must be LONG or SHORT (not FLAT)
- Confidence must be ≥ 0.6 (60%)
- If both conditions met, signal is added to signal pool

**RL Model Degradation Detection:**
- System monitors RL performance
- If model performance degrades, RL is automatically disabled
- Falls back to multi-agent system only

---

## Complete System Call Flow

### Phase 1: System Startup

```
1. User runs: python3 run_daily.py --paper
   │
   ├─> DailyTradingRunner.__init__()
   │   │
   │   ├─> Find RL model (models/grpo_final.zip or ppo_final.zip)
   │   │
   │   └─> IntegratedTrader.__init__()
   │       │
   │       ├─> Initialize AlpacaClient
   │       │   └─> Connect to Alpaca API (Paper Trading)
   │       │
   │       ├─> Initialize MassivePriceFeed (if API key available)
   │       │   └─> For historical price data (1-minute aggregation)
   │       │
   │       ├─> Initialize MultiAgentOrchestrator
   │       │   └─> Load 8 trading agents:
   │       │       - TrendAgent
   │       │       - MeanReversionAgent
   │       │       - FVGAgent (Fair Value Gap)
   │       │       - VolatilityAgent
   │       │       - EMAAgent
   │       │       - OptionsAgent
   │       │       - ThetaHarvesterAgent
   │       │       - GammaScalperAgent
   │       │
   │       ├─> Initialize BrokerExecutor
   │       │   └─> For order execution (stocks & options)
   │       │
   │       ├─> Initialize AdvancedRiskManager
   │       │   ├─> 4-Layer Risk Stack:
   │       │   │   - Gap Risk Monitor (earnings/macro events)
   │       │   │   - IV Regime Filters (volatility conditions)
   │       │   │   - Portfolio Greeks Caps (delta/gamma limits)
   │       │   │   - UVaR Check (portfolio risk limit)
   │       │   └─> Initialize with actual account balance
   │       │
   │       ├─> Initialize ProfitManager
   │       │   └─> Manages profit targets and trailing stops
   │       │
   │       ├─> Initialize MetricsTracker
   │       │   └─> Tracks P&L, win rate, Sharpe ratio
   │       │
   │       ├─> Load RL Predictor (if model exists)
   │       │   ├─> RLPredictor.load_model()
   │       │   └─> Set use_rl = True
   │       │
   │       ├─> Initialize ModelDegradeDetector (if RL enabled)
   │       │   └─> Monitors RL performance
   │       │
   │       ├─> Initialize EnsemblePredictor
   │       │   └─> Combines RL + Multi-Agent signals
   │       │
   │       └─> Initialize NewsFilter
   │           └─> Blocks trading during volatile news events
   │
   └─> TradingScheduler.__init__()
       └─> Setup scheduled tasks:
           - Pre-market warmup (8:00 AM)
           - Market open (9:30 AM)
           - Recurring cycle (every 5 minutes)
           - Market close flatten (3:50 PM)
           - Daily report (4:05 PM)
```

### Phase 2: Trading Cycle (Every 5 Minutes)

```
2. TradingScheduler triggers: trading_cycle()
   │
   └─> DailyTradingRunner.trading_cycle()
       │
       └─> IntegratedTrader.run_trading_cycle()
           │
           ├─> STEP 1: Update Account Balance
           │   ├─> client.get_account()
           │   └─> risk_manager.update_balance(equity)
           │
           ├─> STEP 2: Monitor Existing Positions
           │   └─> _monitor_positions()
           │       │
           │       For each position:
           │       ├─> Get current price
           │       ├─> Check profit manager for exits
           │       │   └─> Profit targets (TP1-TP5)
           │       │   └─> Stop loss
           │       │   └─> Trailing stop
           │       │
           │       └─> If exit needed:
           │           ├─> executor.execute_market_order()
           │           ├─> Calculate P&L
           │           ├─> risk_manager.record_trade()
           │           ├─> metrics_tracker.record_trade()
           │           └─> Remove from positions dict
           │
           ├─> STEP 3: Scan for New Opportunities
           │   └─> _scan_and_trade() [IF positions < MAX_ACTIVE_TRADES]
           │       │
           │       ├─> Check Market Open
           │       │   └─> client.is_market_open()
           │       │
           │       ├─> Check News Filter
           │       │   └─> news_filter.is_blocked()
           │       │
           │       ├─> Check Risk Status
           │       │   └─> risk_manager.get_risk_status()
           │       │       └─> Check: danger/blocked levels
           │       │
           │       ├─> Check RL Model Degradation (if RL enabled)
           │       │   └─> degrade_detector.check_degradation()
           │       │
           │       └─> For each ticker in Config.TICKERS:
           │           │
           │           ├─> Check if already have position
           │           │   └─> Skip if position exists
           │           │
           │           ├─> Get Historical Bars
           │           │   ├─> Try: massive_price_feed.get_daily_bars()
           │           │   │   └─> Aggregates 1-minute bars to daily
           │           │   └─> Fallback: client.get_historical_bars()
           │           │       └─> Need 30+ bars (60 days lookback)
           │           │
           │           ├─> Get Current Price
           │           │   └─> client.get_latest_price(symbol)
           │           │
           │           ├─> SIGNAL GENERATION (3 Sources)
           │           │   │
           │           │   ├─> SOURCE 1: Multi-Agent System
           │           │   │   └─> orchestrator.analyze_symbol(symbol, bars)
           │           │   │       │
           │           │   │       ├─> FeatureEngine.calculate_all_features()
           │           │   │       │   └─> Calculate: RSI, EMA, SMA, ATR, Volume, etc.
           │           │   │       │
           │           │   │       ├─> RegimeClassifier.classify()
           │           │   │       │   └─> Determine market regime (trending/ranging)
           │           │   │       │
           │           │   │       └─> For each of 8 agents:
           │           │   │           ├─> TrendAgent.analyze()
           │           │   │           ├─> MeanReversionAgent.analyze()
           │           │   │           ├─> FVGAgent.analyze()
           │           │   │           ├─> VolatilityAgent.analyze()
           │           │   │           ├─> EMAAgent.analyze()
           │           │   │           ├─> OptionsAgent.analyze()
           │           │   │           ├─> ThetaHarvesterAgent.analyze()
           │           │   │           └─> GammaScalperAgent.analyze()
           │           │   │
           │           │   │       └─> MetaPolicyController.select_best()
           │           │   │           └─> Select best agent signal based on regime
           │           │   │
           │           │   │       Returns: TradeIntent (direction, confidence, agent_name)
           │           │   │
           │           │   ├─> SOURCE 2: RL Predictor (if enabled)
           │           │   │   └─> rl_predictor.predict(symbol, bars, current_price)
           │           │   │       │
           │           │   │       ├─> Prepare observation vector
           │           │   │       │   └─> Extract features from bars
           │           │   │       │
           │           │   │       ├─> Run RL model inference
           │           │   │       │   └─> model.predict(observation)
           │           │   │       │
           │           │   │       └─> Returns: {direction, confidence, reason}
           │           │   │           └─> Only if confidence ≥ 0.6 and direction != FLAT
           │           │   │
           │           │   └─> SOURCE 3: Ensemble Predictor (if multiple signals)
           │           │       └─> ensemble.combine_predictions()
           │           │           ├─> If RL + Multi-Agent signals:
           │           │           │   └─> Weighted combination
           │           │           │   └─> Higher confidence signals weighted more
           │           │           └─> Returns: Combined signal
           │           │
           │           ├─> Select Best Signal
           │           │   ├─> If ensemble signal: Use ensemble
           │           │   └─> Else: Use highest confidence signal
           │           │
           │           ├─> Validate Signal Direction
           │           │   └─> Must be LONG or SHORT (not FLAT)
           │           │
           │           ├─> Determine Option Type
           │           │   ├─> LONG signal → Buy CALL options
           │           │   └─> SHORT signal → Buy PUT options
           │           │
           │           ├─> Risk Check
           │           │   └─> risk_manager.check_trade_allowed()
           │           │       │
           │           │       ├─> Layer 1: Gap Risk Monitor
           │           │       │   └─> Check earnings/macro events (block if within 2 days)
           │           │       │
           │           │       ├─> Layer 2: IV Regime Filters
           │           │       │   └─> Check IV rank (block if IV too low/high)
           │           │       │
           │           │       ├─> Layer 3: Portfolio Greeks Caps
           │           │       │   └─> Check delta/gamma limits (block if exceeded)
           │           │       │
           │           │       └─> Layer 4: UVaR Check
           │           │           └─> Check portfolio risk (block if UVaR > 5%)
           │           │
           │           └─> If Allowed & Confidence ≥ 0.6:
           │               └─> _execute_trade()
           │
           └─> STEP 4: Log Status
               └─> _log_status()
                   ├─> Get account balance
                   ├─> Get risk status
                   └─> Calculate metrics
```

### Phase 3: Trade Execution

```
3. _execute_trade(symbol, signal, current_price, bars)
   │
   ├─> Validate Signal Direction
   │   └─> Must be LONG or SHORT
   │
   ├─> Determine Option Type
   │   ├─> LONG → 'call'
   │   └─> SHORT → 'put'
   │
   ├─> Get Options Chain
   │   └─> options_feed.get_expiration_dates(symbol)
   │
   ├─> Select Expiration (0-30 DTE)
   │   └─> Filter: MIN_DTE <= DTE <= MAX_DTE
   │
   ├─> Get ATM Option
   │   └─> options_feed.get_atm_options(symbol, expiration, option_type)
   │       └─> Finds option closest to current stock price
   │
   ├─> Get Option Symbol
   │   └─> Extract from contract data (DO NOT construct)
   │       └─> Format: NVDA251226C00185000
   │
   ├─> Get Option Price (3-Tier Fallback)
   │   ├─> Method 1: MassiveOptionsFeed (primary)
   │   │   └─> Get from options chain snapshot
   │   ├─> Method 2: Alpaca Quote API (fallback)
   │   │   └─> options_feed.get_option_quote()
   │   └─> Method 3: Contract close_price (last resort)
   │
   ├─> Calculate Position Size
   │   ├─> Get account balance
   │   ├─> Calculate: position_capital = balance * 0.75 / MAX_ACTIVE_TRADES
   │   ├─> Calculate: contract_cost = option_price * 100
   │   └─> Calculate: contracts = position_capital / contract_cost
   │
   ├─> OTM Fallback (if ATM too expensive)
   │   └─> If contracts < 1:
   │       ├─> Calculate OTM strike (5% OTM)
   │       ├─> Find OTM option in chain
   │       └─> Recalculate contracts
   │
   └─> Execute Order
       └─> executor.execute_market_order()
           │
           ├─> Check if is_option=True
           │
           ├─> If option:
           │   └─> options_client.place_option_order()
           │       ├─> option_symbol=NVDA251226C00185000
           │       ├─> qty=contracts
           │       ├─> side='buy'
           │       ├─> order_type='market'
           │       └─> asset_class='option'
           │
           └─> If filled:
               ├─> Add to positions dict
               ├─> Track: option_symbol, qty, entry_price, option_type
               ├─> Add to profit_manager
               └─> Log: "OPTIONS TRADE EXECUTED"
```

---

## Component Details

### 1. Multi-Agent Orchestrator

**8 Specialized Agents:**

1. **TrendAgent**
   - Identifies trending markets
   - Uses moving averages, momentum
   - Best for: Strong directional moves

2. **MeanReversionAgent**
   - Identifies oversold/overbought conditions
   - Uses RSI, Bollinger Bands
   - Best for: Range-bound markets

3. **FVGAgent (Fair Value Gap)**
   - Identifies price gaps
   - Uses order flow imbalance
   - Best for: Breakout trades

4. **VolatilityAgent**
   - Identifies volatility expansion/contraction
   - Uses ATR, IV rank
   - Best for: Options-specific strategies

5. **EMAAgent**
   - Uses EMA crossovers
   - Simple trend following
   - Best for: All market conditions

6. **OptionsAgent**
   - Options-specific analysis
   - Uses Greeks, IV, skew
   - Best for: Options timing

7. **ThetaHarvesterAgent**
   - Identifies high theta opportunities
   - Uses time decay analysis
   - Best for: Short-term options

8. **GammaScalperAgent**
   - Identifies gamma exposure opportunities
   - Uses GEX (Gamma Exposure Index)
   - Best for: High gamma environments

**Agent Selection:**
- RegimeClassifier determines market regime
- MetaPolicyController selects best agent for current regime
- Returns single TradeIntent with highest confidence

### 2. RL Predictor

**Model Architecture:**
- **Type:** GRPO (Group Relative Policy Optimization) or PPO
- **Input:** 60 days of OHLCV data + current price
- **Output:** Direction (LONG/SHORT/FLAT) + Confidence (0-1)

**Training:**
- Trained on historical market data
- Learns optimal entry/exit patterns
- Adapts to different market conditions

**Usage:**
- Runs in parallel with multi-agent system
- Provides independent prediction
- Combined via Ensemble Predictor

### 3. Ensemble Predictor

**Combination Logic:**
- If RL + Multi-Agent signals:
  - Weighted average of confidences
  - Higher confidence signals weighted more
  - Direction must agree (both LONG or both SHORT)
- If only one signal:
  - Use that signal directly

### 4. Risk Manager (4-Layer Stack)

**Layer 1: Gap Risk Monitor**
- Blocks trading 2 days before/after earnings
- Blocks trading during major macro events (Fed meetings, etc.)
- Prevents gap risk exposure

**Layer 2: IV Regime Filters**
- Checks IV rank (0-100)
- Blocks if IV too low (< 20) or too high (> 80)
- Ensures options have reasonable pricing

**Layer 3: Portfolio Greeks Caps**
- Limits total portfolio delta
- Limits total portfolio gamma
- Prevents over-concentration

**Layer 4: UVaR Check**
- Calculates portfolio Value-at-Risk
- Blocks if UVaR > 5% of portfolio
- Prevents excessive risk exposure

**Additional Checks:**
- Daily loss limit (2%)
- Max drawdown (10%)
- Max loss streak (3 consecutive losses)
- Position limit (10 max)

### 5. Options Execution Flow

**Step-by-Step:**

1. **Get Expiration Dates**
   - Fetch from Alpaca options chain
   - Filter for 0-30 DTE

2. **Select Target Expiration**
   - Choose first expiration in range
   - Prefer shorter DTE for higher leverage

3. **Get ATM Option**
   - Calculate current stock price
   - Find option with strike closest to current price
   - Filter by type (CALL for LONG, PUT for SHORT)

4. **Get Option Symbol**
   - Extract from contract data
   - Format: `NVDA251226C00185000`
   - DO NOT construct manually

5. **Get Option Price**
   - Try Massive first (most reliable)
   - Fallback to Alpaca quote
   - Last resort: contract close_price

6. **Calculate Contracts**
   - Position size: 75% of balance / MAX_ACTIVE_TRADES
   - Contract cost: option_price × 100
   - Contracts: position_capital / contract_cost

7. **OTM Fallback**
   - If ATM too expensive (contracts < 1):
   - Find 5% OTM option (cheaper)
   - Recalculate contracts

8. **Execute Order**
   - Place market order via Alpaca
   - Set `asset_class='option'`
   - Track position with option symbol

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    SYSTEM STARTUP                            │
│  run_daily.py → DailyTradingRunner → IntegratedTrader        │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              INITIALIZATION (One-Time)                       │
│  • AlpacaClient (Paper Trading)                             │
│  • MassivePriceFeed (Historical Data)                       │
│  • MultiAgentOrchestrator (8 Agents)                        │
│  • BrokerExecutor (Order Execution)                         │
│  • AdvancedRiskManager (4-Layer Stack)                      │
│  • RLPredictor (if model exists)                            │
│  • EnsemblePredictor (Signal Combination)                    │
│  • NewsFilter (Event Blocking)                              │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│         TRADING CYCLE (Every 5 Minutes)                       │
│  TradingScheduler → trading_cycle()                          │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────┐
        │  1. Update Account Balance        │
        └───────────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────┐
        │  2. Monitor Existing Positions     │
        │     • Check profit targets         │
        │     • Check stop loss              │
        │     • Execute exits if needed      │
        └───────────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────┐
        │  3. Scan for New Opportunities    │
        │     (If positions < 10)            │
        └───────────────────────────────────┘
                            │
                            ▼
    ┌───────────────────────────────────────────┐
    │  For Each Ticker (12 tickers)            │
    └───────────────────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────┐
        │  Get Historical Bars (60 days)    │
        │  • Massive (primary)               │
        │  • Alpaca (fallback)               │
        └───────────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────┐
        │  SIGNAL GENERATION                 │
        │                                    │
        │  ┌──────────────────────────────┐ │
        │  │ Source 1: Multi-Agent        │ │
        │  │ • 8 Agents analyze           │ │
        │  │ • RegimeClassifier selects   │ │
        │  │ • Returns: TradeIntent       │ │
        │  └──────────────────────────────┘ │
        │                                    │
        │  ┌──────────────────────────────┐ │
        │  │ Source 2: RL Predictor       │ │
        │  │ • Model inference            │ │
        │  │ • Returns: {dir, conf, reason}│ │
        │  └──────────────────────────────┘ │
        │                                    │
        │  ┌──────────────────────────────┐ │
        │  │ Source 3: Ensemble           │ │
        │  │ • Combines RL + Multi-Agent  │ │
        │  │ • Weighted average           │ │
        │  └──────────────────────────────┘ │
        └───────────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────┐
        │  Select Best Signal               │
        │  • Highest confidence             │
        │  • Must be LONG or SHORT          │
        └───────────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────┐
        │  RISK CHECK (4 Layers)            │
        │  • Gap Risk Monitor               │
        │  • IV Regime Filters              │
        │  • Portfolio Greeks Caps          │
        │  • UVaR Check                     │
        └───────────────────────────────────┘
                            │
                            ▼
                    ┌───────────────┐
                    │ Allowed?      │
                    └───────────────┘
                            │
                    ┌───────┴───────┐
                    │               │
                   YES              NO
                    │               │
                    ▼               ▼
        ┌───────────────────┐  ┌──────────────┐
        │ Execute Trade      │  │ Block Trade  │
        │                    │  │ Log Reason   │
        └───────────────────┘  └──────────────┘
                    │
                    ▼
        ┌───────────────────────────────────┐
        │  OPTIONS TRADE EXECUTION           │
        │                                    │
        │  1. Get Expiration (0-30 DTE)      │
        │  2. Get ATM Option (CALL/PUT)     │
        │  3. Get Option Symbol             │
        │  4. Get Option Price               │
        │  5. Calculate Contracts            │
        │  6. OTM Fallback (if needed)      │
        │  7. Execute Order                 │
        │  8. Track Position                │
        └───────────────────────────────────┘
```

---

## Decision Making Process

### Signal Selection Logic

```
IF (RL signal exists AND Multi-Agent signal exists):
    → Use Ensemble Predictor
    → Weighted combination
    → Direction must agree
ELSE IF (Only one signal exists):
    → Use that signal directly
ELSE:
    → Skip ticker (no signal)
```

### Risk Check Logic

```
IF (Gap Risk Monitor blocks):
    → REJECT: "Too close to earnings/macro event"
ELSE IF (IV Regime Filter blocks):
    → REJECT: "IV rank outside acceptable range"
ELSE IF (Portfolio Greeks Caps exceeded):
    → REJECT: "Portfolio delta/gamma limit exceeded"
ELSE IF (UVaR > 5%):
    → REJECT: "Portfolio risk too high"
ELSE IF (Daily loss limit exceeded):
    → REJECT: "Daily loss limit reached"
ELSE IF (Max drawdown exceeded):
    → REJECT: "Max drawdown exceeded"
ELSE IF (Max loss streak reached):
    → REJECT: "Max loss streak reached"
ELSE IF (Positions >= 10):
    → REJECT: "Max positions reached"
ELSE:
    → ALLOW: Proceed to execution
```

### Option Selection Logic

```
1. Get all expirations (0-30 DTE)
2. Select first expiration in range
3. Get ATM option:
   - LONG signal → CALL option
   - SHORT signal → PUT option
4. Calculate contracts:
   - If contracts >= 1: Use ATM
   - If contracts < 1: Try OTM (5% away)
5. Get option price (Massive → Alpaca → Contract)
6. Execute if price available
```

---

## Key Files and Their Roles

| File | Role |
|------|------|
| `run_daily.py` | Main entry point, scheduler |
| `core/live/integrated_trader.py` | Core trading system |
| `core/multi_agent_orchestrator.py` | Coordinates 8 agents |
| `core/agents/*.py` | Individual trading agents |
| `rl/predict.py` | RL model inference |
| `core/live/ensemble_predictor.py` | Combines RL + agents |
| `core/risk/advanced_risk_manager.py` | 4-layer risk stack |
| `core/live/broker_executor.py` | Order execution |
| `services/options_data_feed.py` | Options chain data |
| `services/massive_price_feed.py` | Historical price data |

---

## Summary

**System Type:** Multi-Agent + RL-Enhanced Options Trading  
**RL Status:** ✅ Enabled (if model file exists)  
**RL Job:** Predicts LONG/SHORT direction with confidence  
**Trading:** OPTIONS ONLY (0-30 DTE, CALL/PUT)  
**Risk Management:** 4-Layer Stack  
**Execution:** Alpaca Paper Trading  

**Flow:** Startup → Cycle (every 5 min) → Signal Generation → Risk Check → Execution → Position Tracking

---

**Document Generated:** 2025-12-22  
**System Version:** IntegratedTrader v2.0 (Options-Only)




