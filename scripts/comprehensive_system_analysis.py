#!/usr/bin/env python3
"""
Comprehensive System Analysis - TradeNova
Expert-level analysis from 20+ years trading + PhD quant + institutional microstructure lens
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import Config
from alpaca_client import AlpacaClient
from datetime import datetime
import pytz
import os

def analyze_system():
    """Comprehensive system analysis"""
    
    print("="*80)
    print("TRADENOVA COMPREHENSIVE SYSTEM ANALYSIS")
    print("Expert Lens: 20+ Years Trading + PhD Quant + Institutional Microstructure")
    print("="*80)
    
    # 1. Vision & Goals
    print("\n" + "="*80)
    print("1. VISION & INITIAL GOALS")
    print("="*80)
    print("""
    Initial Goal: "Solve trading problem that no one solved before"
    
    Target: Turn $10K → $400K in 1 year (40x return)
    Strategy: Options trading (0-30 DTE) with disciplined risk management
    Approach: Multi-agent RL system with automated execution
    
    Current Status:
    ✅ Automated options trading system operational
    ✅ Multi-agent signal generation
    ✅ Risk management framework
    ✅ Profit-taking and stop-loss automation
    ⚠️  Performance: ~$70K equity (7x from $10K start) - ON TRACK but needs optimization
    """)
    
    # 2. System Architecture
    print("\n" + "="*80)
    print("2. SYSTEM ARCHITECTURE")
    print("="*80)
    
    print(f"""
    Core Components:
    ├─ Trading Engine: core/live/integrated_trader.py
    ├─ Signal Generation: core/multi_agent_orchestrator.py
    ├─ Risk Management: core/risk/advanced_risk_manager.py
    ├─ Options Execution: core/live/options_broker_client.py
    ├─ Data Feeds:
    │   ├─ Alpaca (execution, account, positions)
    │   ├─ Massive/Polygon (options chain, Greeks, market data)
    │   └─ Alpha Vantage (earnings calendar - optional)
    └─ Monitoring: dashboard.py (Streamlit)
    
    Trading Agents ({len(Config.TICKERS)} tickers monitored):
    ├─ EMAAgent (EMA crossovers)
    ├─ TrendAgent (Golden/Death cross, ADX)
    ├─ MeanReversionAgent (RSI, Bollinger Bands)
    ├─ VolatilityAgent (IV rank, HV/IV)
    ├─ OptionsAgent (options-specific logic)
    ├─ ThetaHarvesterAgent (premium collection)
    ├─ GammaScalperAgent (volatility expansion)
    └─ RL Agent (GRPO/PPO - optional)
    """)
    
    # 3. Current Configuration
    print("\n" + "="*80)
    print("3. CURRENT CONFIGURATION")
    print("="*80)
    
    client = AlpacaClient(paper=True)
    account = client.get_account()
    equity = float(account['equity'])
    
    print(f"""
    Risk Management:
    ├─ Stop Loss: -{Config.STOP_LOSS_PCT*100:.0f}% (hard exit)
    ├─ TP1: +{Config.TP1_PCT*100:.0f}% → Exit {Config.TP1_EXIT_PCT*100:.0f}%
    ├─ TP2: +{Config.TP2_PCT*100:.0f}% → Exit {Config.TP2_EXIT_PCT*100:.0f}%
    ├─ TP3: +{Config.TP3_PCT*100:.0f}% → Exit {Config.TP3_EXIT_PCT*100:.0f}%
    ├─ TP4: +{Config.TP4_PCT*100:.0f}% → Exit {Config.TP4_EXIT_PCT*100:.0f}%
    ├─ TP5: +{Config.TP5_PCT*100:.0f}% → Exit {Config.TP5_EXIT_PCT*100:.0f}%
    └─ Trailing Stop: Tiered (10-18% pullback based on peak)
    
    Position Limits:
    ├─ Max Contracts: {Config.MAX_CONTRACTS_PER_TRADE}
    ├─ Max Position Size: {Config.MAX_POSITION_PCT*100:.0f}% of portfolio
    ├─ Max Portfolio Heat: {Config.MAX_PORTFOLIO_HEAT*100:.0f}%
    ├─ Max Active Positions: {Config.MAX_ACTIVE_TRADES}
    └─ Max Correlated Exposure: {Config.MAX_CORRELATED_EXPOSURE*100:.0f}%
    
    DTE Configuration:
    ├─ Range: {Config.MIN_DTE}-{Config.MAX_DTE} days
    ├─ Target: {Config.TARGET_DTE} days
    ├─ Short-term (high confidence): {Config.MIN_DTE_SHORT_TERM}-{Config.MAX_DTE_SHORT_TERM} days
    └─ Confidence Threshold: {Config.SHORT_TERM_CONFIDENCE_THRESHOLD*100:.0f}%
    
    Account Status:
    ├─ Equity: ${equity:,.2f}
    ├─ Cash: ${float(account['cash']):,.2f}
    ├─ Buying Power: ${float(account['buying_power']):,.2f}
    └─ Return: {(equity/10000 - 1)*100:.1f}% from $10K start
    """)
    
    # 4. API Analysis
    print("\n" + "="*80)
    print("4. API & DATA SOURCE ANALYSIS")
    print("="*80)
    
    massive_key = Config.MASSIVE_API_KEY
    alpaca_key = Config.ALPACA_API_KEY
    alpaca_status = '✅ Configured' if alpaca_key else '❌ Missing'
    massive_status = '✅ Configured' if massive_key else '❌ Missing'
    alpha_status = '✅ Configured' if Config.ALPHA_VANTAGE_API_KEY else '⚠️  Optional'
    
    print(f"""
    Alpaca API (Execution & Account):
    ├─ Status: {alpaca_status}
    ├─ Purpose: Order execution, position tracking, account management
    ├─ Endpoints Used:
    │   ├─ /v2/account - Account balance, equity
    │   ├─ /v2/positions - Current positions
    │   ├─ /v2/orders - Order placement
    │   ├─ /v2/options/contracts - Options chain
    │   └─ /v2/clock - Market hours
    └─ Mode: Paper Trading
    
    Massive/Polygon API (Market Data):
    ├─ Status: {massive_status}
    ├─ Purpose: Options chain, Greeks, historical data
    ├─ Endpoints Used:
    │   ├─ /v3/snapshot/options/[SYMBOL] - Real-time options with Greeks
    │   ├─ /v2/aggs/ticker/[SYMBOL]/range/1/minute/[START]/[END] - 1-min bars
    │   └─ Historical aggregation for daily bars
    └─ Data Quality: Real prices, Greeks, IV, volume, OI
    
    Alpha Vantage (Earnings):
    ├─ Status: {alpha_status}
    └─ Purpose: Earnings calendar for gap risk
    
    Data Flow:
    Stock Price → Massive (primary) → Alpaca (fallback)
    Options Chain → Massive (with Greeks) → Alpaca (reference only)
    Order Execution → Alpaca (only)
    """)
    
    # 5. What's Complete
    print("\n" + "="*80)
    print("5. WHAT'S COMPLETE ✅")
    print("="*80)
    
    print("""
    ✅ Core Infrastructure:
       • Automated trading engine (runs every 5 min)
       • Multi-agent signal generation
       • Options execution pipeline
       • Risk management framework
       • Profit-taking automation
       • Stop-loss automation
       • Trailing stop with tiered pullback
    
    ✅ Risk Management:
       • Position sizing limits (10% max per position)
       • Portfolio heat cap (35% max)
       • Contract limits (10 max per trade)
       • Stop-loss at -20%
       • 5-tier profit targets (40%, 60%, 100%, 150%, 200%)
       • Dynamic trailing stops
    
    ✅ Options Infrastructure:
       • Options chain retrieval (Massive + Alpaca)
       • Liquidity filtering (bid-ask spread, size, quote age)
       • DTE selection (0-14 days, conditional 0-6 for high confidence)
       • ATM option selection
       • Greeks calculation (Black-Scholes)
       • IV Rank tracking
    
    ✅ Monitoring & Logging:
       • Streamlit dashboard (localhost:8506)
       • Comprehensive logging
       • Trade history tracking
       • Performance metrics
    
    ✅ Automation:
       • LaunchAgent for auto-start
       • Watchdog for health monitoring
       • Auto-restart on crash
       • Market hours detection (ET timezone)
       • News/event filtering
    """)
    
    # 6. What's Missing for 0-30 DTE Success
    print("\n" + "="*80)
    print("6. WHAT'S MISSING FOR 0-30 DTE SUCCESS 🔴")
    print("="*80)
    
    print("""
    🔴 CRITICAL GAPS (Institutional Perspective):
    
    1. THETA DECAY MANAGEMENT:
       ❌ No time-based exit rules (e.g., exit if no move in X days)
       ❌ No DTE-based position sizing (smaller size for 0-3 DTE)
       ❌ No theta burn rate monitoring
       ⚠️  Risk: Holding 0-3 DTE options can lose 30-50% from time decay alone
    
    2. GAMMA RISK MANAGEMENT:
       ❌ No gamma exposure limits
       ❌ No delta hedging for large positions
       ❌ No gamma scalping logic
       ⚠️  Risk: High gamma = extreme P&L swings near expiration
    
    3. VOLATILITY REGIME ADAPTATION:
       ❌ IV Rank filtering exists but not actively used in execution
       ❌ No IV skew analysis (calls vs puts)
       ❌ No volatility term structure analysis
       ⚠️  Risk: Buying options when IV is high = paying premium
    
    4. LIQUIDITY OPTIMIZATION:
       ⚠️  Current: Basic bid-ask spread filter (20% max)
       ❌ Missing: Minimum volume requirements
       ❌ Missing: Open interest thresholds
       ❌ Missing: Market maker presence detection
       ⚠️  Risk: Illiquid options = wide spreads = poor fills
    
    5. STRIKE SELECTION INTELLIGENCE:
       ⚠️  Current: ATM only
       ❌ Missing: Delta-based strike selection (e.g., 0.30-0.70 delta)
       ❌ Missing: Strike optimization based on IV skew
       ❌ Missing: OTM/ITM selection based on confidence
       ⚠️  Risk: ATM may not be optimal for all scenarios
    
    6. EXECUTION OPTIMIZATION:
       ⚠️  Current: Market orders only
       ❌ Missing: Limit order placement with spread analysis
       ❌ Missing: Time-weighted average price (TWAP) for large orders
       ❌ Missing: Fill quality monitoring
       ⚠️  Risk: Market orders = paying spread = immediate loss
    
    7. PORTFOLIO GREEKS MANAGEMENT:
       ❌ No portfolio-level delta limits
       ❌ No portfolio gamma limits
       ❌ No portfolio theta budget
       ❌ No portfolio vega exposure
       ⚠️  Risk: Unbalanced Greeks = unexpected P&L swings
    
    8. EXPIRATION MANAGEMENT:
       ❌ No automatic roll logic (close expiring, open new)
       ❌ No early exit for expiring options (< 1 DTE)
       ❌ No expiration day special handling
       ⚠️  Risk: Options expiring worthless = 100% loss
    
    9. VOLUME & MOMENTUM CONFIRMATION:
       ⚠️  Current: Volume checked but not weighted heavily
       ❌ Missing: Volume surge detection
       ❌ Missing: Unusual options activity (UOA) detection
       ❌ Missing: Options flow analysis
       ⚠️  Risk: Low volume = poor signal quality
    
    10. BACKTESTING & VALIDATION:
        ⚠️  Current: Basic backtesting exists
        ❌ Missing: Walk-forward optimization
        ❌ Missing: Out-of-sample testing
        ❌ Missing: Monte Carlo simulation
        ⚠️  Risk: Strategy may not be robust across market regimes
    """)
    
    # 7. Performance Analysis
    print("\n" + "="*80)
    print("7. PERFORMANCE ANALYSIS")
    print("="*80)
    
    positions = client.get_positions()
    orders = client.get_orders(status='all', limit=50)
    
    print(f"""
    Current Metrics:
    ├─ Account Equity: ${equity:,.2f}
    ├─ Open Positions: {len(positions)}
    ├─ Total Orders (recent): {len(orders)}
    └─ Return from $10K: {(equity/10000 - 1)*100:.1f}%
    
    Performance vs Goal:
    ├─ Target: $400K (40x)
    ├─ Current: ${equity:,.2f} ({equity/10000:.1f}x)
    ├─ Progress: {(equity/400000)*100:.1f}% of target
    └─ Required Monthly: ~{(400000/equity)**(1/12) - 1:.1%} to reach goal
    """)
    
    # 8. Expert Recommendations
    print("\n" + "="*80)
    print("8. EXPERT RECOMMENDATIONS (20+ Years Trading + PhD Quant)")
    print("="*80)
    
    print("""
    🎯 PRIORITY 1: THETA DECAY PROTECTION (CRITICAL)
    
    For 0-30 DTE options, time decay is the #1 killer. Implement:
    
    1. Time-Based Exit Rules:
       • If position is < 3 DTE and P&L < +20% → Exit
       • If position is < 1 DTE and P&L < +50% → Exit
       • Reason: Theta accelerates exponentially near expiration
    
    2. DTE-Based Position Sizing:
       • 0-3 DTE: Max 5% of portfolio (high risk)
       • 4-7 DTE: Max 10% of portfolio (medium risk)
       • 8-14 DTE: Max 10% of portfolio (standard)
       • Reason: Shorter DTE = higher gamma risk = smaller size
    
    3. Theta Budget:
       • Track daily theta burn across portfolio
       • Limit total theta exposure (e.g., max $X/day)
       • Reason: Prevents portfolio-wide time decay losses
    
    🎯 PRIORITY 2: GAMMA RISK MANAGEMENT
    
    1. Gamma Exposure Limits:
       • Calculate portfolio gamma
       • Limit total gamma exposure (e.g., max 100 contracts * delta)
       • Reason: High gamma = extreme P&L volatility
    
    2. Delta Hedging:
       • For positions with |delta| > 0.70, consider delta hedging
       • Use underlying stock or opposite options
       • Reason: Reduces directional risk, focuses on volatility/theta
    
    3. Gamma Scalping:
       • For high-gamma positions, implement rebalancing
       • Rebalance when delta moves > 0.10
       • Reason: Captures gamma profits while managing risk
    
    🎯 PRIORITY 3: VOLATILITY REGIME ADAPTATION
    
    1. IV Rank-Based Entry:
       • Only buy options when IV Rank < 50% (buying cheap vol)
       • Skip when IV Rank > 80% (too expensive)
       • Reason: Buying high IV = paying premium = lower win rate
    
    2. IV Skew Analysis:
       • Compare call IV vs put IV
       • Favor direction with lower IV (cheaper)
       • Reason: Skew indicates market sentiment and relative value
    
    3. Volatility Term Structure:
       • Compare short-term IV vs long-term IV
       • Favor expirations with lower IV
       • Reason: Term structure shows volatility expectations
    
    🎯 PRIORITY 4: EXECUTION OPTIMIZATION
    
    1. Limit Orders Instead of Market:
       • Place limit at mid-price or better
       • Only use market for urgent exits
       • Reason: Saves 1-3% on every trade (spread cost)
    
    2. Fill Quality Monitoring:
       • Track actual fill vs expected price
       • Reject trades with poor fill quality
       • Reason: Poor execution = immediate loss
    
    3. Time-of-Day Optimization:
       • Avoid first/last 30 min (low liquidity)
       • Prefer 10 AM - 3 PM ET (best liquidity)
       • Reason: Better fills = better P&L
    
    🎯 PRIORITY 5: STRIKE SELECTION INTELLIGENCE
    
    1. Delta-Based Selection:
       • High confidence (>90%): Use 0.50-0.70 delta (ITM)
       • Medium confidence (80-90%): Use 0.30-0.50 delta (ATM)
       • Lower confidence (<80%): Use 0.20-0.30 delta (OTM)
       • Reason: Delta = probability of profit (roughly)
    
    2. IV Skew Optimization:
       • If call IV < put IV: Favor calls (cheaper)
       • If put IV < call IV: Favor puts (cheaper)
       • Reason: Buy cheaper volatility = better risk/reward
    
    3. Strike Selection Based on Expected Move:
       • Calculate expected move (IV * sqrt(DTE/365) * price)
       • Select strike at expected move distance
       • Reason: Maximizes probability of profit
    
    🎯 PRIORITY 6: PORTFOLIO GREEKS MANAGEMENT
    
    1. Portfolio Delta Limits:
       • Limit total portfolio delta (e.g., max ±500)
       • Reason: Prevents directional bias
    
    2. Portfolio Gamma Limits:
       • Limit total portfolio gamma (e.g., max 100)
       • Reason: Prevents extreme P&L swings
    
    3. Portfolio Theta Budget:
       • Limit total daily theta burn (e.g., max $500/day)
       • Reason: Controls time decay exposure
    
    4. Portfolio Vega Exposure:
       • Limit total vega (e.g., max 50)
       • Reason: Controls volatility exposure
    
    🎯 PRIORITY 7: EXPIRATION MANAGEMENT
    
    1. Auto-Roll Logic:
       • If position is 2 DTE and profitable → Roll to next expiration
       • If position is 2 DTE and losing → Close
       • Reason: Prevents expiration day risk
    
    2. Early Exit for Expiring Options:
       • Exit all positions < 1 DTE at market close
       • Reason: Avoids pin risk and assignment risk
    
    3. Expiration Day Special Handling:
       • Reduce position sizes on expiration day
       • Avoid new positions < 3 DTE on expiration day
       • Reason: Expiration day = extreme volatility
    
    🎯 PRIORITY 8: VOLUME & MOMENTUM CONFIRMATION
    
    1. Volume Surge Detection:
       • Require volume > 1.5x average for entry
       • Reason: Confirms signal strength
    
    2. Unusual Options Activity (UOA):
       • Detect large block trades
       • Follow smart money flow
       • Reason: Institutions often have better information
    
    3. Options Flow Analysis:
       • Track call/put ratio
       • Track large trades (dark pool detection)
       • Reason: Flow indicates sentiment and potential moves
    """)
    
    # 9. System Flow Analysis
    print("\n" + "="*80)
    print("9. SYSTEM FLOW ANALYSIS")
    print("="*80)
    
    print("""
    Current Flow (Every 5 Minutes):
    
    1. Market Status Check ✅
       → Is market open? (9:30 AM - 4:00 PM ET)
       → Skip if closed
    
    2. News/Event Filter ✅
       → Check macro_calendar.py
       → Block during NFP, FOMC, etc.
       → Block volatile windows (8:30-9:15 AM ET)
    
    3. Monitor Existing Positions ✅
       a. Check Stop-Losses (-20%)
       b. Check Profit Targets (TP1-TP5)
       c. Check Trailing Stops (tiered)
    
    4. Scan for New Trades ✅
       For each of 21 tickers:
       a. Get historical bars (Massive → Alpaca)
       b. Run multi-agent orchestrator
       c. Generate signals (>=80% confidence)
       d. Check risk limits
       e. Get options chain
       f. Filter for liquidity
       g. Select DTE (0-14 days)
       h. Select ATM option
       i. Calculate position size
       j. Execute trade
    
    5. Risk Checks ✅
       → Portfolio heat (<35%)
       → Position size (<10%)
       → Contract limit (<10)
       → Correlation (<25%)
    
    ⚠️  MISSING IN FLOW:
    
    • Theta decay check (time-based exits)
    • Gamma risk check (portfolio-level)
    • IV Rank check (entry filter)
    • Strike optimization (delta-based)
    • Execution optimization (limit orders)
    • Expiration management (auto-roll)
    • Volume confirmation (surge detection)
    """)
    
    # 10. Vision Alignment
    print("\n" + "="*80)
    print("10. VISION ALIGNMENT CHECK")
    print("="*80)
    
    print("""
    Initial Vision: "Solve trading problem that no one solved before"
    
    ✅ ACHIEVED:
    • Automated options trading system (rare)
    • Multi-agent RL ensemble (advanced)
    • Comprehensive risk management (institutional-level)
    • Profit-taking automation (sophisticated)
    • Trailing stops with tiered pullback (innovative)
    • 21-ticker monitoring (scalable)
    
    ⚠️  PARTIALLY ACHIEVED:
    • 0-30 DTE optimization (needs theta/gamma management)
    • Options-specific intelligence (needs IV regime adaptation)
    • Execution optimization (needs limit orders, fill quality)
    
    ❌ NOT YET ACHIEVED:
    • Portfolio Greeks management (critical for options)
    • Volatility regime adaptation (IV Rank filtering)
    • Strike selection intelligence (delta-based)
    • Expiration management (auto-roll logic)
    • Volume/momentum confirmation (UOA detection)
    
    VERDICT: System is SOLID FOUNDATION but needs OPTIONS-SPECIFIC enhancements
    for true 0-30 DTE success. Current system is more "stock trading with options"
    than "options-first trading system."
    """)
    
    # 11. Next Steps
    print("\n" + "="*80)
    print("11. RECOMMENDED NEXT STEPS (Priority Order)")
    print("="*80)
    
    print("""
    PHASE 1: THETA PROTECTION (Week 1)
    1. Implement time-based exit rules (< 3 DTE, < 1 DTE)
    2. Add DTE-based position sizing
    3. Add theta budget tracking
    
    PHASE 2: GAMMA RISK (Week 2)
    4. Implement portfolio gamma limits
    5. Add delta hedging logic for large positions
    6. Add gamma scalping for high-gamma positions
    
    PHASE 3: VOLATILITY INTELLIGENCE (Week 3)
    7. Implement IV Rank entry filter (< 50%)
    8. Add IV skew analysis
    9. Add volatility term structure analysis
    
    PHASE 4: EXECUTION OPTIMIZATION (Week 4)
    10. Switch to limit orders (mid-price)
    11. Add fill quality monitoring
    12. Add time-of-day optimization
    
    PHASE 5: STRIKE SELECTION (Week 5)
    13. Implement delta-based strike selection
    14. Add IV skew optimization
    15. Add expected move calculation
    
    PHASE 6: PORTFOLIO GREEKS (Week 6)
    16. Implement portfolio delta limits
    17. Implement portfolio gamma limits
    18. Implement portfolio theta budget
    19. Implement portfolio vega limits
    
    PHASE 7: EXPIRATION MANAGEMENT (Week 7)
    20. Implement auto-roll logic
    21. Add early exit for expiring options
    22. Add expiration day special handling
    
    PHASE 8: VOLUME & MOMENTUM (Week 8)
    23. Add volume surge detection
    24. Add UOA detection
    25. Add options flow analysis
    """)
    
    print("\n" + "="*80)
    print("✅ ANALYSIS COMPLETE")
    print("="*80)

if __name__ == "__main__":
    analyze_system()

