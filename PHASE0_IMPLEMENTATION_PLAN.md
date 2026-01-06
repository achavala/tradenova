# Phase-0 Implementation Plan

**Based on:** Forensic Review (Rating: 6.8/10)  
**Timeline:** 1-2 weeks  
**Goal:** Do no harm - System correctly refusing to trade is good

---

## Priority 1: Option Universe Filter BEFORE Signals ✅

**Status:** Code created, needs integration

**File:** `core/live/option_universe_filter.py`

**Integration Points:**
1. In `_execute_trade()`: Filter options chain BEFORE selecting ATM option
2. Only pass liquid options to signal generation
3. Log filtered options with reasons

**Liquidity Rules:**
- Bid > $0.01
- Spread ≤ 20%
- Bid size ≥ 1 contract
- Quote age < 5 seconds

---

## Priority 2: Add Liquidity Gatekeeper to Risk Stack

**Current Risk Stack:**
1. Gap Risk Monitor
2. IV Regime Filters
3. Portfolio Greeks Caps
4. UVaR Check

**New Risk Stack:**
1. Gap Risk Monitor
2. **Liquidity Gatekeeper** ← NEW
3. IV Regime Filters
4. Portfolio Greeks Caps
5. UVaR Check

**Implementation:**
- Add to `AdvancedRiskManager.check_trade_allowed()`
- Check liquidity metrics before IV checks
- Block if spread > 20% or bid missing

---

## Priority 3: Restrict RL Scope

**RL CAN Choose:**
- Direction (LONG/SHORT/HOLD)
- Size scalar (0-1)

**RL CANNOT Choose:**
- Strike (rule-based, liquidity-aware)
- Expiry (rule-based, 0-30 DTE filter)

**Current Status:** ✅ Already correct - RL only predicts direction

**Action:** Verify RL never selects strike/expiry in code

---

## Priority 4: Prune Multi-Agent Ensemble

**Current:** 8 agents
**Target:** 5 agents

**Keep:**
1. TrendAgent
2. VolatilityAgent
3. OptionsAgent
4. EMAAgent
5. MeanReversionAgent

**Remove/Consolidate:**
- FVGAgent → Merge into TrendAgent
- ThetaHarvesterAgent → Merge into OptionsAgent
- GammaScalperAgent → Merge into OptionsAgent

**Implementation:**
- Update `MultiAgentOrchestrator.__init__()`
- Remove 3 agents from list
- Test that remaining 5 work correctly

---

## Priority 5: Raise Confidence Threshold

**Current:** ≥ 0.6 (60%)
**Target:** ≥ 0.7 (70%)

**Implementation:**
- Update `_scan_and_trade()` line 469: `if allowed and best_signal['confidence'] >= 0.7:`
- Update RL threshold: `if rl_pred['direction'] != 'FLAT' and rl_pred['confidence'] >= 0.7:`

---

## Priority 6: Add Daily Trade Budget

**Requirement:** Max 3-5 new trades per day

**Implementation:**
- Add `daily_trade_count` to `IntegratedTrader`
- Reset at market open
- Check before executing trade
- Block if limit reached

---

## Implementation Checklist

- [ ] Integrate OptionUniverseFilter into _execute_trade()
- [ ] Add Liquidity Gatekeeper to risk stack
- [ ] Verify RL scope restriction (already correct)
- [ ] Prune agents from 8 to 5
- [ ] Raise confidence threshold to 0.7
- [ ] Add daily trade budget (max 3-5/day)
- [ ] Backtest with real spreads + slippage
- [ ] Test with live paper trading

---

## Success Criteria

1. ✅ No execution bugs (DONE)
2. ⏳ Option Universe Filter enforced BEFORE signals
3. ⏳ Liquidity rules enforced
4. ⏳ RL restricted to direction + size only (verify)
5. ⏳ Confidence threshold ≥ 70%
6. ⏳ Daily trade budget enforced
7. ⏳ Backtest with real spreads + slippage

**Target:** Few trades, no blow-ups, flat or slightly negative PnL is acceptable.




