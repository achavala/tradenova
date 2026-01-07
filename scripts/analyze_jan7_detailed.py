#!/usr/bin/env python3
"""
Comprehensive Trading Analysis for January 7, 2026
Analyzes all signals, trades, rejections, and system decisions
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from alpaca_client import AlpacaClient
from config import Config
from datetime import datetime
import pytz
import re
from collections import defaultdict

def parse_logs(log_file_path):
    """Parse trading logs for today"""
    today = "2026-01-07"
    signals = []
    executions = []
    rejections = []
    stop_losses = []
    profit_takes = []
    
    try:
        with open(log_file_path, 'r') as f:
            for line in f:
                if today not in line:
                    continue
                
                # Signals
                if "Signal found for" in line:
                    match = re.search(r"Signal found for (\w+): (\w+) @ ([\d.]+)% \(([\w]+)\)", line)
                    if match:
                        signals.append({
                            'time': line[:19],
                            'symbol': match.group(1),
                            'direction': match.group(2),
                            'confidence': float(match.group(3)),
                            'agent': match.group(4)
                        })
                
                # Executions
                if "✅ EXECUTING TRADE:" in line:
                    match = re.search(r"EXECUTING TRADE: (\w+) (\w+) \(confidence: ([\d.]+)%, agent: ([\w]+)\)", line)
                    if match:
                        executions.append({
                            'time': line[:19],
                            'symbol': match.group(1),
                            'direction': match.group(2),
                            'confidence': float(match.group(3)),
                            'agent': match.group(4)
                        })
                
                # Order placed
                if "Options order placed:" in line:
                    match = re.search(r"Options order placed: (\w+) (\d+) (\w+) @ (\w+)", line)
                    if match and executions:
                        executions[-1].update({
                            'order_action': match.group(1),
                            'order_qty': int(match.group(2)),
                            'order_symbol': match.group(3),
                            'order_type': match.group(4)
                        })
                
                # Rejections
                if "rejected" in line.lower() or "blocked" in line.lower() or "skipped" in line.lower():
                    rejections.append({
                        'time': line[:19],
                        'message': line.strip()
                    })
                
                # Stop losses
                if "STOP-LOSS TRIGGERED" in line or "STOP-LOSS EXECUTED" in line:
                    match = re.search(r"for (\w+)", line)
                    if match:
                        stop_losses.append({
                            'time': line[:19],
                            'symbol': match.group(1),
                            'executed': "EXECUTED" in line
                        })
                
                # Profit taking
                if "PROFIT TARGET HIT" in line or "PROFIT TAKEN" in line:
                    match = re.search(r"for (\w+)", line)
                    if match:
                        profit_takes.append({
                            'time': line[:19],
                            'symbol': match.group(1),
                            'executed': "TAKEN" in line or "EXECUTED" in line
                        })
    
    except FileNotFoundError:
        print(f"⚠️  Log file not found: {log_file_path}")
    
    return signals, executions, rejections, stop_losses, profit_takes

def analyze_positions(client):
    """Analyze current positions"""
    positions = client.get_positions()
    
    position_details = []
    total_unrealized = 0
    total_cost = 0
    
    for pos in positions:
        symbol = pos['symbol']
        qty = int(float(pos['qty']))
        entry = float(pos['avg_entry_price'])
        current = float(pos['current_price'])
        pnl = float(pos['unrealized_pl'])
        pnl_pct = float(pos['unrealized_plpc']) * 100
        cost = float(pos['cost_basis'])
        market_value = float(pos['market_value'])
        
        total_unrealized += pnl
        total_cost += cost
        
        # Determine status
        if pnl_pct >= 100:
            status = "TP3 (100%+)"
            action = "Should exit 10%"
        elif pnl_pct >= 60:
            status = "TP2 (60%+)"
            action = "Should exit 20%"
        elif pnl_pct >= 40:
            status = "TP1 (40%+)"
            action = "Should exit 50%"
        elif pnl_pct >= 20:
            status = "Good profit"
            action = "Hold"
        elif pnl_pct <= -20:
            status = "STOP LOSS!"
            action = "Should close ALL"
        elif pnl_pct <= -15:
            status = "Warning"
            action = "Monitor closely"
        else:
            status = "Normal"
            action = "Hold"
        
        position_details.append({
            'symbol': symbol,
            'qty': qty,
            'entry': entry,
            'current': current,
            'pnl': pnl,
            'pnl_pct': pnl_pct,
            'cost': cost,
            'market_value': market_value,
            'status': status,
            'action': action
        })
    
    return position_details, total_unrealized, total_cost

def main():
    print("="*80)
    print("COMPREHENSIVE TRADING ANALYSIS - JANUARY 7, 2026")
    print("="*80)
    
    # Initialize
    client = AlpacaClient(paper=True)
    et = pytz.timezone('America/New_York')
    
    # Parse logs
    log_path = Path(__file__).parent.parent / "logs" / "tradenova_daily.log"
    signals, executions, rejections, stop_losses, profit_takes = parse_logs(log_path)
    
    # Get account info
    account = client.get_account()
    equity = float(account['equity'])
    
    # Analyze positions
    positions, total_unrealized, total_cost = analyze_positions(client)
    
    # Print summary
    print("\n" + "="*80)
    print("📊 EXECUTIVE SUMMARY")
    print("="*80)
    print(f"  Total Signals Generated: {len(signals)}")
    print(f"  Trades Executed: {len(executions)}")
    print(f"  Rejections/Blocks: {len(rejections)}")
    print(f"  Stop-Losses Triggered: {len(stop_losses)}")
    print(f"  Profit Targets Hit: {len(profit_takes)}")
    print(f"  Current Open Positions: {len(positions)}")
    print(f"  Total Unrealized P&L: ${total_unrealized:,.2f}")
    print(f"  Account Equity: ${equity:,.2f}")
    
    # Configuration
    print("\n" + "="*80)
    print("⚙️  SYSTEM CONFIGURATION")
    print("="*80)
    print(f"""
    Risk Management:
      - Stop Loss: -{Config.STOP_LOSS_PCT*100:.0f}%
      - TP1: +{Config.TP1_PCT*100:.0f}% (exit {Config.TP1_EXIT_PCT*100:.0f}%)
      - TP2: +{Config.TP2_PCT*100:.0f}% (exit {Config.TP2_EXIT_PCT*100:.0f}%)
      - TP3: +{Config.TP3_PCT*100:.0f}% (exit {Config.TP3_EXIT_PCT*100:.0f}%)
    
    Position Limits:
      - Max contracts per trade: {Config.MAX_CONTRACTS_PER_TRADE}
      - Max position size: {Config.MAX_POSITION_PCT*100:.0f}% of portfolio
      - Max portfolio heat: {Config.MAX_PORTFOLIO_HEAT*100:.0f}%
      - Max active positions: {Config.MAX_ACTIVE_TRADES}
      - DTE range: {Config.MIN_DTE}-{Config.MAX_DTE} days
    
    Tickers Being Monitored: {len(Config.TICKERS)}
    """)
    
    # Signal analysis
    print("\n" + "="*80)
    print("📡 SIGNAL GENERATION ANALYSIS")
    print("="*80)
    
    signal_by_agent = defaultdict(list)
    signal_by_symbol = defaultdict(list)
    
    for sig in signals:
        signal_by_agent[sig['agent']].append(sig)
        signal_by_symbol[sig['symbol']].append(sig)
    
    print(f"\nSignals by Agent:")
    for agent, sigs in sorted(signal_by_agent.items()):
        avg_conf = sum(s['confidence'] for s in sigs) / len(sigs)
        print(f"  {agent}: {len(sigs)} signals (avg confidence: {avg_conf:.1f}%)")
    
    print(f"\nSignals by Symbol:")
    for symbol, sigs in sorted(signal_by_symbol.items(), key=lambda x: len(x[1]), reverse=True):
        print(f"  {symbol}: {len(sigs)} signals")
    
    # Trade execution analysis
    print("\n" + "="*80)
    print("✅ TRADE EXECUTION DETAILS")
    print("="*80)
    
    for i, exec in enumerate(executions, 1):
        print(f"\nTrade #{i}:")
        print(f"  Time: {exec['time']}")
        print(f"  Symbol: {exec['symbol']}")
        print(f"  Direction: {exec['direction']}")
        print(f"  Agent: {exec['agent']}")
        print(f"  Confidence: {exec['confidence']:.1f}%")
        if 'order_qty' in exec:
            print(f"  Order: {exec['order_action'].upper()} {exec['order_qty']} {exec['order_symbol']} @ {exec['order_type']}")
    
    # Rejection analysis
    if rejections:
        print("\n" + "="*80)
        print("❌ REJECTIONS & BLOCKS")
        print("="*80)
        
        rejection_reasons = defaultdict(int)
        for rej in rejections:
            msg = rej['message'].lower()
            if "portfolio heat" in msg or "heat" in msg:
                rejection_reasons["Portfolio Heat Limit"] += 1
            elif "position" in msg and "limit" in msg:
                rejection_reasons["Position Limit"] += 1
            elif "risk" in msg or "danger" in msg:
                rejection_reasons["Risk Level"] += 1
            elif "news" in msg or "blocked" in msg:
                rejection_reasons["News/Event Block"] += 1
            elif "market" in msg and "closed" in msg:
                rejection_reasons["Market Closed"] += 1
            else:
                rejection_reasons["Other"] += 1
        
        for reason, count in sorted(rejection_reasons.items(), key=lambda x: x[1], reverse=True):
            print(f"  {reason}: {count}")
        
        print(f"\nSample Rejections:")
        for rej in rejections[:10]:
            print(f"  {rej['time']}: {rej['message'][:100]}")
    
    # Position analysis
    print("\n" + "="*80)
    print("📈 CURRENT POSITIONS ANALYSIS")
    print("="*80)
    
    for pos in sorted(positions, key=lambda x: x['pnl'], reverse=True):
        print(f"\n{'='*60}")
        print(f"Position: {pos['symbol']}")
        print(f"{'='*60}")
        print(f"  Quantity: {pos['qty']} contracts")
        print(f"  Entry Price: ${pos['entry']:.2f}")
        print(f"  Current Price: ${pos['current']:.2f}")
        print(f"  Cost Basis: ${pos['cost']:,.2f}")
        print(f"  Market Value: ${pos['market_value']:,.2f}")
        print(f"  P&L: ${pos['pnl']:,.2f} ({pos['pnl_pct']:+.1f}%)")
        print(f"  Status: {pos['status']}")
        print(f"  Action: {pos['action']}")
        
        # Why it should/shouldn't be closed
        if pos['pnl_pct'] >= 100:
            print(f"\n  🎯 DECISION LOGIC:")
            print(f"     → TP3 (+100%) hit: System should exit 10% of position")
            print(f"     → Remaining: Let winners run, trailing stop at +150%")
        elif pos['pnl_pct'] >= 60:
            print(f"\n  🎯 DECISION LOGIC:")
            print(f"     → TP2 (+60%) hit: System should exit 20% of remaining")
            print(f"     → Reason: Lock in gains, reduce exposure")
        elif pos['pnl_pct'] >= 40:
            print(f"\n  🎯 DECISION LOGIC:")
            print(f"     → TP1 (+40%) hit: System should exit 50% of position")
            print(f"     → Reason: Take profits, let rest run")
        elif pos['pnl_pct'] <= -20:
            print(f"\n  🔴 DECISION LOGIC:")
            print(f"     → STOP LOSS triggered: System should exit 100%")
            print(f"     → Reason: Risk management - limit losses")
        elif pos['pnl_pct'] >= 20:
            print(f"\n  ✅ DECISION LOGIC:")
            print(f"     → Hold: Approaching TP1 (+40%)")
            print(f"     → Next exit: TP1 at +40%")
        else:
            print(f"\n  ✅ DECISION LOGIC:")
            print(f"     → Hold: Normal range")
            print(f"     → Stop loss: -20% (currently {pos['pnl_pct']:.1f}%)")
    
    print(f"\n{'='*80}")
    print(f"TOTAL UNREALIZED P&L: ${total_unrealized:,.2f}")
    print(f"TOTAL COST BASIS: ${total_cost:,.2f}")
    print(f"RETURN ON CAPITAL: {(total_unrealized/total_cost*100):.1f}%")
    print(f"{'='*80}")
    
    # System flow explanation
    print("\n" + "="*80)
    print("🔄 SYSTEM DECISION FLOW")
    print("="*80)
    print("""
    ┌─────────────────────────────────────────────────────────────────────┐
    │                    TRADING CYCLE (Every 5 min)                       │
    └─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
    ┌─────────────────────────────────────────────────────────────────────┐
    │  1. MARKET STATUS CHECK                                              │
    │     ┌───────────────────────────────────────────────────────────┐   │
    │     │ • Is market open? (9:30 AM - 4:00 PM ET)                 │   │
    │     │ • Check current time in Eastern Timezone                 │   │
    │     │ • Skip if closed                                         │   │
    │     └───────────────────────────────────────────────────────────┘   │
    └─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
    ┌─────────────────────────────────────────────────────────────────────┐
    │  2. NEWS/EVENT FILTER                                                │
    │     ┌───────────────────────────────────────────────────────────┐   │
    │     │ • Check macro_calendar.py for high-impact events         │   │
    │     │ • Block during NFP, FOMC, etc.                            │   │
    │     │ • Block volatile time windows (8:30-9:15 AM ET)          │   │
    │     └───────────────────────────────────────────────────────────┘   │
    └─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
    ┌─────────────────────────────────────────────────────────────────────┐
    │  3. MONITOR EXISTING POSITIONS                                      │
    │     ┌───────────────────────────────────────────────────────────┐   │
    │     │ a. _check_stop_losses()                                   │   │
    │     │    • Query Alpaca for all positions                       │   │
    │     │    • IF P&L% <= -20%:                                     │   │
    │     │      → SELL ALL (market order)                            │   │
    │     │                                                           │   │
    │     │ b. _check_profit_targets()                                │   │
    │     │    • Query Alpaca for all positions                       │   │
    │     │    • IF P&L% >= 100%: SELL 10% (TP3)                     │   │
    │     │    • ELIF P&L% >= 60%: SELL 20% (TP2)                    │   │
    │     │    • ELIF P&L% >= 40%: SELL 50% (TP1)                    │   │
    │     └───────────────────────────────────────────────────────────┘   │
    └─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
    ┌─────────────────────────────────────────────────────────────────────┐
    │  4. SCAN FOR NEW TRADES (if positions < MAX_ACTIVE_TRADES)          │
    │     ┌───────────────────────────────────────────────────────────┐   │
    │     │ For each ticker in Config.TICKERS (21 symbols):           │   │
    │     │                                                           │   │
    │     │   a. Run Multi-Agent Orchestrator:                       │   │
    │     │      • EMAAgent: EMA crossover signals                   │   │
    │     │      • TrendAgent: Golden/Death cross, ADX               │   │
    │     │      • MeanReversionAgent: RSI, Bollinger Bands          │   │
    │     │      • VolatilityAgent: IV rank, HV/IV                   │   │
    │     │      • (Optional) RL Agent: ML predictions               │   │
    │     │                                                           │   │
    │     │   b. Aggregate signals with confidence scores            │   │
    │     │                                                           │   │
    │     │   c. If high-confidence signal (>= 80%):                 │   │
    │     │      • Check portfolio heat (< 35%)                      │   │
    │     │      • Check position count (< 10)                       │   │
    │     │      • Check position size (< 10% of portfolio)          │   │
    │     │      • Check correlated exposure (< 25%)                 │   │
    │     │      • Find liquid option (DTE 0-14)                     │   │
    │     │      • Calculate contract qty (max 10)                   │   │
    │     │      • Place BUY order                                   │   │
    │     └───────────────────────────────────────────────────────────┘   │
    └─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
    ┌─────────────────────────────────────────────────────────────────────┐
    │  5. RISK CHECKS (Advanced Risk Manager)                              │
    │     ┌───────────────────────────────────────────────────────────┐   │
    │     │ • Portfolio heat calculation                               │   │
    │     │ • Correlation checks                                       │   │
    │     │ • Daily loss limits                                        │   │
    │     │ • Position concentration                                   │   │
    │     └───────────────────────────────────────────────────────────┘   │
    └─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
    ┌─────────────────────────────────────────────────────────────────────┐
    │  6. LOG STATUS & WAIT                                                │
    │     • Log: Balance, Positions, Risk Level, Daily P&L                │
    │     • Wait 5 minutes                                                │
    │     • Repeat cycle                                                  │
    └─────────────────────────────────────────────────────────────────────┘
    """)
    
    # Key decision factors
    print("\n" + "="*80)
    print("🎯 KEY DECISION FACTORS")
    print("="*80)
    print("""
    1. SIGNAL GENERATION:
       • Multiple agents analyze each ticker
       • Signals must have >= 80% confidence
       • Agents consider: Price action, volume, volatility, mean reversion
    
    2. RISK MANAGEMENT:
       • Portfolio heat cap: 35% max
       • Position size: 10% max per trade
       • Contract limit: 10 contracts max
       • Correlated exposure: 25% max
    
    3. PROFIT TAKING:
       • TP1 (+40%): Exit 50% → Lock in gains
       • TP2 (+60%): Exit 20% of remaining → Let winners run
       • TP3 (+100%): Exit 10% of remaining → Trail with stop
       • Trailing stop activates at +150%, locks in +100%
    
    4. STOP LOSS:
       • -20% threshold: Exit 100% immediately
       • Warning at -15% for monitoring
    
    5. DTE SELECTION:
       • Range: 0-14 days (0 DTE now allowed)
       • Prefer 7-10 DTE for optimal theta/gamma
       • 0-6 DTE only for very high confidence
    """)
    
    print("\n" + "="*80)
    print("✅ ANALYSIS COMPLETE")
    print("="*80)

if __name__ == "__main__":
    main()

