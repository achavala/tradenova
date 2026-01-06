#!/usr/bin/env python3
"""
Analyze signals generated and rejections today
Parses Fly.io logs to find all signals and rejection reasons
"""
import re
import sys
from pathlib import Path
from datetime import datetime, date
from collections import defaultdict

def parse_logs_for_signals(log_file_path=None):
    """Parse logs to extract signals and rejections"""
    
    signals = []
    rejections = []
    executions = []
    
    # Patterns to match
    signal_pattern = re.compile(r'Signal found for (\w+): (\w+) @ ([\d.]+)%')
    rejection_pattern = re.compile(r'(?:Trade BLOCKED|Skipping|⚠️|❌).*?for (\w+):\s*(.+?)(?:\n|$)')
    execution_pattern = re.compile(r'EXECUTING TRADE: (\w+) (\w+)')
    confidence_pattern = re.compile(r'confidence.*?([\d.]+)%')
    risk_pattern = re.compile(r'risk_level:\s*(\w+)')
    
    if log_file_path and Path(log_file_path).exists():
        with open(log_file_path, 'r') as f:
            content = f.read()
    else:
        # Try to get from Fly.io logs
        print("Note: Reading from Fly.io logs...")
        import subprocess
        try:
            result = subprocess.run(
                ['flyctl', 'logs', '--app', 'tradenova', '--region', 'dfw'],
                capture_output=True,
                text=True,
                timeout=30
            )
            content = result.stdout
        except:
            print("Could not fetch Fly.io logs. Please provide log file path.")
            return signals, rejections, executions
    
    lines = content.split('\n')
    
    for i, line in enumerate(lines):
        # Match signals
        signal_match = signal_pattern.search(line)
        if signal_match:
            symbol, direction, confidence = signal_match.groups()
            signals.append({
                'symbol': symbol,
                'direction': direction,
                'confidence': float(confidence),
                'line': i,
                'raw': line
            })
        
        # Match rejections
        rejection_match = rejection_pattern.search(line)
        if rejection_match:
            symbol = rejection_match.group(1)
            reason = rejection_match.group(2).strip()
            
            # Try to get more context from surrounding lines
            context = []
            for j in range(max(0, i-2), min(len(lines), i+3)):
                if j != i:
                    context.append(lines[j])
            
            rejections.append({
                'symbol': symbol,
                'reason': reason,
                'line': i,
                'raw': line,
                'context': '\n'.join(context)
            })
        
        # Match executions
        exec_match = execution_pattern.search(line)
        if exec_match:
            symbol, direction = exec_match.groups()
            executions.append({
                'symbol': symbol,
                'direction': direction,
                'line': i,
                'raw': line
            })
    
    return signals, rejections, executions

def analyze_today():
    """Main analysis function"""
    print("="*80)
    print("TRADENOVA - SIGNAL & REJECTION ANALYSIS")
    print("="*80)
    print(f"Date: {date.today()}")
    print(f"Time: {datetime.now().strftime('%H:%M:%S')}")
    print("="*80)
    
    # Parse logs
    signals, rejections, executions = parse_logs_for_signals()
    
    # Group by symbol
    signals_by_symbol = defaultdict(list)
    rejections_by_symbol = defaultdict(list)
    
    for sig in signals:
        signals_by_symbol[sig['symbol']].append(sig)
    
    for rej in rejections:
        rejections_by_symbol[rej['symbol']].append(rej)
    
    # Summary
    print(f"\n📊 SUMMARY")
    print(f"  Total signals generated: {len(signals)}")
    print(f"  Total rejections: {len(rejections)}")
    print(f"  Total executions: {len(executions)}")
    print(f"  Unique symbols with signals: {len(signals_by_symbol)}")
    print(f"  Unique symbols rejected: {len(rejections_by_symbol)}")
    
    # Signals breakdown
    print(f"\n📈 SIGNALS GENERATED")
    if signals:
        for symbol, sigs in sorted(signals_by_symbol.items()):
            for sig in sigs:
                print(f"  {symbol}: {sig['direction']} @ {sig['confidence']:.2f}%")
    else:
        print("  No signals generated today")
    
    # Rejections breakdown
    print(f"\n❌ REJECTIONS")
    if rejections:
        rejection_reasons = defaultdict(list)
        for rej in rejections:
            rejection_reasons[rej['reason']].append(rej['symbol'])
        
        for reason, symbols in sorted(rejection_reasons.items()):
            print(f"  {reason}:")
            for symbol in set(symbols):
                print(f"    - {symbol}")
    else:
        print("  No rejections found in logs")
    
    # Executions
    print(f"\n✅ EXECUTIONS")
    if executions:
        for exec in executions:
            print(f"  {exec['symbol']}: {exec['direction']}")
    else:
        print("  No trades executed today")
    
    # Detailed analysis per symbol
    print(f"\n🔍 DETAILED ANALYSIS BY SYMBOL")
    all_symbols = set(list(signals_by_symbol.keys()) + list(rejections_by_symbol.keys()))
    
    if all_symbols:
        for symbol in sorted(all_symbols):
            print(f"\n  {symbol}:")
            
            # Signals
            if symbol in signals_by_symbol:
                print(f"    Signals: {len(signals_by_symbol[symbol])}")
                for sig in signals_by_symbol[symbol]:
                    print(f"      - {sig['direction']} @ {sig['confidence']:.2f}%")
            
            # Rejections
            if symbol in rejections_by_symbol:
                print(f"    Rejections: {len(rejections_by_symbol[symbol])}")
                for rej in rejections_by_symbol[symbol]:
                    print(f"      - {rej['reason']}")
            
            # Executions
            execs = [e for e in executions if e['symbol'] == symbol]
            if execs:
                print(f"    Executions: {len(execs)}")
                for exec in execs:
                    print(f"      - {exec['direction']}")
    else:
        print("  No activity found for any symbols")
    
    print("\n" + "="*80)
    print("ANALYSIS COMPLETE")
    print("="*80)
    
    # Recommendations
    print(f"\n💡 RECOMMENDATIONS")
    if len(signals) > 0 and len(executions) == 0:
        print("  ⚠️  Signals were generated but no trades executed.")
        print("  → Check rejection reasons above")
        print("  → Verify risk management settings")
        print("  → Check liquidity filters")
    elif len(signals) == 0:
        print("  ⚠️  No signals generated today.")
        print("  → Check if market was open")
        print("  → Verify data feeds are working")
        print("  → Check confidence thresholds")
    else:
        print("  ✅ System appears to be working correctly")

if __name__ == '__main__':
    analyze_today()




