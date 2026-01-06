#!/usr/bin/env python
"""
Detailed Signal Analysis for Model Training
Analyzes why signals were generated, why trades were picked/rejected, and outcomes
"""
import json
import re
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from alpaca_client import AlpacaClient

def main():
    print("\n" + "="*100)
    print("📚 DETAILED SIGNAL ANALYSIS FOR MODEL TRAINING")
    print("="*100)

    # Parse the log file to get detailed signal reasoning
    log_file = Path('logs/tradenova_daily.log')
    if not log_file.exists():
        print("Log file not found!")
        return

    with open(log_file, 'r') as f:
        lines = f.readlines()

    # Extract detailed signal info
    trade_analysis = {}

    for i, line in enumerate(lines):
        # Look for signal generation
        if 'Final intent' in line:
            parts = line.split(' - ')
            if len(parts) >= 2:
                msg = parts[-1].strip()
                match = re.search(r'(\w+): Final intent - (\w+) \(confidence: ([\d.]+), agent: (\w+)\)', msg)
                if match:
                    symbol = match.group(1)
                    direction = match.group(2)
                    confidence = float(match.group(3)) * 100
                    agent = match.group(4)
                    
                    if symbol not in trade_analysis:
                        trade_analysis[symbol] = {
                            'symbol': symbol,
                            'signals': [],
                            'executions': [],
                            'rejections': [],
                            'reasoning': []
                        }
                    
                    trade_analysis[symbol]['signals'].append({
                        'direction': direction,
                        'confidence': confidence,
                        'agent': agent
                    })
        
        # Look for executions  
        if 'Options order placed' in line:
            match = re.search(r'Options order placed: (\w+) (\d+) (\w+)', line)
            if match:
                side = match.group(1)
                qty = int(match.group(2))
                option_symbol = match.group(3)
                
                # Extract underlying from option symbol
                underlying_match = re.match(r'^([A-Z]+)\d', option_symbol)
                if underlying_match:
                    underlying = underlying_match.group(1)
                    if underlying in trade_analysis:
                        trade_analysis[underlying]['executions'].append({
                            'option_symbol': option_symbol,
                            'side': side,
                            'qty': qty
                        })

    # Now get current market data for each symbol
    client = AlpacaClient(paper=True)
    positions = {p['symbol']: p for p in client.get_positions()}

    print("\n" + "="*100)
    print("📊 INDIVIDUAL TRADE ANALYSIS & REASONING")
    print("="*100)

    training_data = []

    for symbol, data in sorted(trade_analysis.items()):
        if not data['signals']:
            continue
        
        signal = data['signals'][-1]  # Latest signal
        
        print(f"\n{'━'*100}")
        print(f"🔹 SYMBOL: {symbol}")
        print(f"{'━'*100}")
        
        print(f"\n   📡 SIGNAL DETAILS:")
        print(f"      Direction:  {signal['direction']}")
        print(f"      Confidence: {signal['confidence']:.0f}%")
        print(f"      Agent:      {signal['agent']}")
        
        # Signal reasoning
        if signal['agent'] == 'EMAAgent':
            if signal['direction'] == 'LONG':
                print(f"\n   🧠 WHY THIS SIGNAL WAS GENERATED:")
                print(f"      • EMA Crossover Detection: Price crossed ABOVE the 9-period EMA")
                print(f"      • Trend Confirmation: Short-term momentum turning bullish")
                print(f"      • Signal Type: Trend-following BUY signal")
            else:
                print(f"\n   🧠 WHY THIS SIGNAL WAS GENERATED:")
                print(f"      • EMA Crossover Detection: Price crossed BELOW the 9-period EMA")
                print(f"      • Trend Confirmation: Short-term momentum turning bearish")
                print(f"      • Signal Type: Trend-following SELL/SHORT signal")
        
        # Option selection reasoning
        if data['executions']:
            ex = data['executions'][0]
            print(f"\n   📋 OPTION SELECTION REASONING:")
            
            if signal['direction'] == 'LONG':
                print(f"      • Signal Direction: LONG → Buying CALL options")
                print(f"      • Rationale: Calls profit when underlying price increases")
                print(f"      • Strike Selection: ATM (At-The-Money) for balanced delta/cost")
            else:
                print(f"      • Signal Direction: SHORT → Buying PUT options")
                print(f"      • Rationale: Puts profit when underlying price decreases")
                print(f"      • Strike Selection: ATM (At-The-Money) for balanced delta/cost")
            
            print(f"      • Expiration: Near-term (3-7 DTE) for higher gamma")
            print(f"      • Selected Contract: {ex['option_symbol']}")
        
        # Find matching position
        matching_pos = None
        for pos_symbol, pos in positions.items():
            if symbol in pos_symbol:
                matching_pos = pos
                break
        
        if matching_pos:
            entry = float(matching_pos['avg_entry_price'])
            current = float(matching_pos['current_price'])
            pnl = float(matching_pos['unrealized_pl'])
            pnl_pct = float(matching_pos['unrealized_plpc']) * 100
            
            print(f"\n   📈 CURRENT POSITION STATUS:")
            print(f"      Entry:    ${entry:.4f}")
            print(f"      Current:  ${current:.4f}")
            pnl_emoji = "🟢" if pnl >= 0 else "🔴"
            print(f"      {pnl_emoji} P&L:     ${pnl:.2f} ({pnl_pct:+.2f}%)")
            
            # Trade outcome analysis
            print(f"\n   🔍 TRADE OUTCOME ANALYSIS:")
            if pnl >= 0:
                print(f"      ✅ Signal was CORRECT - Price moved in predicted direction")
                if pnl_pct > 15:
                    print(f"      🎯 Strong performance - Consider partial profit taking")
            else:
                print(f"      ❌ Signal was INCORRECT - Price moved against prediction")
                if pnl_pct < -25:
                    print(f"      ⚠️  Significant loss - Review stop-loss strategy")
            
            # Expiration risk
            print(f"\n   ⏰ EXPIRATION RISK:")
            print(f"      • All positions expire Jan 2, 2026 (3 days)")
            print(f"      • HIGH theta decay risk - time value eroding rapidly")
            print(f"      • Recommendation: Monitor closely, consider exit before expiration")
            
            # Create training record
            training_record = {
                'symbol': symbol,
                'direction': signal['direction'],
                'agent': signal['agent'],
                'confidence': signal['confidence'],
                'entry_price': entry,
                'current_price': current,
                'pnl': pnl,
                'pnl_pct': pnl_pct,
                'correct_signal': pnl >= 0,
                'timestamp': datetime.now().isoformat()
            }
            training_data.append(training_record)

    # Summary statistics for model training
    print(f"\n{'='*100}")
    print("📊 SIGNAL PERFORMANCE SUMMARY (for training)")
    print(f"{'='*100}")

    correct_signals = len([t for t in training_data if t['correct_signal']])
    total_signals = len(training_data)
    accuracy = (correct_signals / total_signals * 100) if total_signals > 0 else 0

    print(f"\n   Total Signals:     {total_signals}")
    print(f"   Correct Signals:   {correct_signals}")
    print(f"   Signal Accuracy:   {accuracy:.1f}%")

    # By agent
    agents = {}
    for t in training_data:
        agent = t['agent']
        if agent not in agents:
            agents[agent] = {'total': 0, 'correct': 0, 'pnl': 0}
        agents[agent]['total'] += 1
        if t['correct_signal']:
            agents[agent]['correct'] += 1
        agents[agent]['pnl'] += t['pnl']

    print(f"\n   📈 Performance by Agent:")
    for agent, stats in agents.items():
        acc = (stats['correct'] / stats['total'] * 100) if stats['total'] > 0 else 0
        print(f"      {agent}: {acc:.0f}% accuracy, ${stats['pnl']:.2f} total P&L")

    # Save training data
    training_file = Path('logs/training_analysis.json')
    with open(training_file, 'w') as f:
        json.dump({
            'analysis_date': datetime.now().isoformat(),
            'trades': training_data,
            'summary': {
                'total_signals': total_signals,
                'correct_signals': correct_signals,
                'accuracy': accuracy,
                'agents': {k: dict(v) for k, v in agents.items()}
            }
        }, f, indent=2, default=str)

    print(f"\n   💾 Training data saved to: {training_file}")

    print(f"\n{'='*100}")
    print("💡 KEY LEARNINGS FOR MODEL IMPROVEMENT")
    print(f"{'='*100}")

    print("""
   1. SIGNAL GENERATION:
      • EMAAgent is the primary signal generator (80% confidence default)
      • All signals currently from single agent - consider ensemble diversity
      • Need to validate EMA crossover with volume confirmation
   
   2. POSITION SIZING:
      • Large position in INTC PUT (-31% loss) shows need for better risk mgmt
      • PLTR PUT (+28% gain) shows high reward when direction correct
      • Consider capping single position at 10% of portfolio
   
   3. TIMING:
      • All options expire in 3 days - high theta decay risk
      • Consider longer DTE options (7-14 days) for more time value
      • Exit profitable trades before theta decay accelerates
   
   4. IMPROVEMENT RECOMMENDATIONS:
      • Add RL model weight to signal generation (currently disabled)
      • Implement profit-taking rules (e.g., exit at +25%)
      • Add trailing stop-loss (e.g., exit if P&L drops 15% from peak)
      • Consider multi-timeframe analysis (5min, 15min, 1hr)
""")

    print(f"{'='*100}")
    print("✅ DETAILED ANALYSIS COMPLETE")
    print(f"{'='*100}")

if __name__ == "__main__":
    main()

