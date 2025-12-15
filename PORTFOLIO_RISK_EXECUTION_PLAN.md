# Portfolio Risk Layer - Execution Plan
**Priority**: 🔴 CRITICAL - Highest Priority  
**Timeline**: 10-14 days  
**Status**: Ready to Start

---

## 🎯 Objective

Build a **portfolio-level risk management layer** that sits **above** all trading decisions (RL, agents, execution).

**Why Critical**: Without this, scaling is unsafe, RL training is misleading, and good strategies can still blow up.

---

## 📋 Phase 1: Portfolio Risk Layer (10-14 days)

### Step 1: Portfolio Greeks Aggregation (3-4 days)

**File**: `core/risk/portfolio_greeks.py`

**What to Build**:
- Aggregate Greeks across ALL open positions
- Compute at every tick:
  - Net Delta (portfolio-wide)
  - Net Gamma (portfolio-wide)
  - Net Theta (per day, portfolio-wide)
  - Net Vega (portfolio-wide)
- Handle multiple tickers, expiries, strikes

**Output Format**:
```json
{
  "delta": +420,
  "gamma": 18.4,
  "theta": -320,
  "vega": +210,
  "timestamp": "2025-12-14T10:30:00Z",
  "positions_count": 5
}
```

**Integration Points**:
- Position tracker
- Options data (Greeks from database/API)
- Real-time updates

---

### Step 2: Portfolio Caps & Circuit Breakers (2-3 days)

**File**: `core/risk/portfolio_risk_manager.py`

**What to Build**:
- Hard limits (configurable):
  - `|Delta| < 500` (example)
  - `Theta/day < $300` (example)
  - `Gamma < X`
  - `Vega < Y`
- Behavior:
  - **Block new trades** if limits violated
  - **Force partial reduction** if extreme
  - **Override RL decisions** (sits above RL)
  - Alert/log violations

**Architecture**:
```
┌─────────────────────────────────┐
│  Portfolio Risk Manager          │  ← Sits ABOVE everything
│  - Check caps before trade      │
│  - Force reductions if needed   │
└─────────────────────────────────┘
           ↓
┌─────────────────────────────────┐
│  RL Agent / Signal Agents       │
│  - Generate signals             │
└─────────────────────────────────┘
           ↓
┌─────────────────────────────────┐
│  Execution Engine               │
│  - Execute trades               │
└─────────────────────────────────┘
```

**Integration Points**:
- Portfolio Greeks Aggregator
- Trading decision pipeline
- Position manager

---

### Step 3: UVaR (Ultra-Short VaR) (3-4 days)

**File**: `core/risk/var_calculator.py`

**What to Build**:
- Historical simulation VaR
- Focus on **1-3 day horizon**
- Use recent option P&L distribution
- Percentile loss (e.g., 99%)
- Include gap risk scenarios

**Method**:
1. Collect historical P&L for portfolio
2. Calculate percentile loss (99th percentile)
3. Compare current exposure to VaR limit
4. Trigger alerts/reductions if exceeded

**Output Format**:
```json
{
  "var_1d": -2500,
  "var_3d": -4200,
  "var_5d": -5800,
  "confidence": 0.99,
  "current_exposure": -1800,
  "status": "within_limits"
}
```

**Integration Points**:
- Historical trade data
- Portfolio Greeks
- Metrics tracker

---

### Step 4: Gap Risk Monitor (2-3 days)

**File**: `core/risk/gap_risk_monitor.py`

**What to Build**:
- Event detection:
  - Earnings dates
  - FOMC meetings
  - CPI releases
  - Fed speakers
  - Known macro days
- Behavior:
  - Reduce position size before events
  - Tighten caps
  - Block new entries
  - Alert/flatten logic

**Data Sources**:
- Earnings calendar API
- Economic calendar API
- Manual event list

**Output Format**:
```json
{
  "upcoming_events": [
    {
      "symbol": "AAPL",
      "event_type": "earnings",
      "date": "2025-12-18",
      "days_until": 4,
      "action": "reduce_size"
    }
  ],
  "risk_level": "elevated",
  "recommended_action": "reduce_delta_by_30pct"
}
```

**Integration Points**:
- Event calendar
- Position manager
- Portfolio risk manager

---

## 🔵 Phase 2: RL Training & Validation (Weeks 3-4)

**Prerequisite**: Portfolio Risk Layer must exist first.

**Why**: Without portfolio constraints:
- RL will learn unsafe behavior
- Training rewards will be distorted
- "Good" models will blow up live

**With portfolio risk**:
- RL learns *within* safety bounds
- Training becomes meaningful

---

## 🟣 Phase 3: Advanced Greeks & Vol Models (Weeks 5-7)

**Prerequisite**: 
- Portfolio risk exists
- RL training baseline works
- Strike/expiry selection works

**Then add**:
- Heston model
- SABR model
- IV surface interpolation
- Term structure

**Note**: These are **alpha multipliers**, not safety nets.

---

## 🚫 What NOT to Do Right Now

- ❌ Training RL before portfolio risk
- ❌ Optimizing execution too early
- ❌ Chasing win-rate improvements
- ❌ Adding more agents
- ❌ Over-fitting Greeks models prematurely

---

## 📊 Success Criteria

### Portfolio Risk Layer is "Complete" when:

1. ✅ Portfolio Greeks aggregation works in real-time
2. ✅ Portfolio caps block unsafe trades
3. ✅ UVaR calculates and alerts on tail risk
4. ✅ Gap risk monitor prevents event-driven blowups
5. ✅ All trading decisions go through risk layer
6. ✅ Integration tested with live positions

---

## 🎯 Next Action

**Start with Step 1: Portfolio Greeks Aggregation**

File: `core/risk/portfolio_greeks.py`

---

**Status**: Ready to implement  
**Priority**: 🔴 CRITICAL  
**Timeline**: 10-14 days for Phase 1

