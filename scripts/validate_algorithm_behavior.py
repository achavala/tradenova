#!/usr/bin/env python3
"""
Validate Algorithm Behavior
Checks what setups are being validated and if algorithm is acting as intended
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
from datetime import datetime, timedelta
from alpaca_client import AlpacaClient
from services.massive_price_feed import MassivePriceFeed
from core.multi_agent_orchestrator import MultiAgentOrchestrator
from core.live.integrated_trader import IntegratedTrader
from config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def validate_algorithm_behavior():
    """Validate what the algorithm is checking and how it's behaving"""
    
    print("="*80)
    print("ALGORITHM BEHAVIOR VALIDATION")
    print("="*80)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Initialize components
    massive_feed = MassivePriceFeed()
    alpaca_client = AlpacaClient(
        Config.ALPACA_API_KEY,
        Config.ALPACA_SECRET_KEY,
        Config.ALPACA_BASE_URL
    )
    
    orchestrator = MultiAgentOrchestrator(alpaca_client)
    
    print("1. TICKERS BEING ANALYZED:")
    print("-" * 80)
    print(f"Total Tickers: {len(Config.TICKERS)}")
    print(f"Tickers: {', '.join(Config.TICKERS)}")
    print()
    
    print("2. AGENTS AVAILABLE:")
    print("-" * 80)
    print(f"Total Agents: {len(orchestrator.agents)}")
    for i, agent in enumerate(orchestrator.agents, 1):
        print(f"  {i}. {agent.__class__.__name__}")
    print()
    
    print("3. SETUPS BEING VALIDATED (Testing Each Ticker):")
    print("-" * 80)
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=60)
    
    results = []
    
    for symbol in Config.TICKERS:
        print(f"\nAnalyzing {symbol}...")
        print("-" * 40)
        
        try:
            # Get data
            bars = None
            if massive_feed.is_available():
                bars = massive_feed.get_daily_bars(symbol, start_date, end_date, use_1min_aggregation=True)
            else:
                from alpaca_trade_api.rest import TimeFrame
                bars = alpaca_client.get_historical_bars(symbol, TimeFrame.Day, start_date, end_date)
            
            if bars.empty or len(bars) < 30:
                print(f"  ❌ Insufficient data: {len(bars)} bars")
                results.append({
                    'symbol': symbol,
                    'status': 'insufficient_data',
                    'bars': len(bars)
                })
                continue
            
            # Set timestamp as index if needed
            if 'timestamp' in bars.columns:
                bars = bars.set_index('timestamp')
            
            latest_price = bars['close'].iloc[-1]
            print(f"  ✅ Data: {len(bars)} bars, Latest: ${latest_price:.2f}")
            
            # Generate signal
            intent = orchestrator.analyze_symbol(symbol, bars)
            
            if intent and intent.direction.value != 'FLAT':
                print(f"  ✅ Signal Generated:")
                print(f"     Direction: {intent.direction.value}")
                print(f"     Confidence: {intent.confidence:.2%}")
                print(f"     Agent: {intent.agent_name}")
                print(f"     Reasoning: {intent.reasoning}")
                
                results.append({
                    'symbol': symbol,
                    'status': 'signal_generated',
                    'direction': intent.direction.value,
                    'confidence': intent.confidence,
                    'agent': intent.agent_name,
                    'reasoning': intent.reasoning,
                    'price': latest_price
                })
            else:
                print(f"  ⚠️  No signal (FLAT or None)")
                if intent:
                    print(f"     Direction: {intent.direction.value}")
                    print(f"     Confidence: {intent.confidence:.2%}")
                
                results.append({
                    'symbol': symbol,
                    'status': 'no_signal',
                    'direction': intent.direction.value if intent else 'N/A',
                    'confidence': intent.confidence if intent else 0
                })
                
        except Exception as e:
            print(f"  ❌ Error: {e}")
            results.append({
                'symbol': symbol,
                'status': 'error',
                'error': str(e)
            })
    
    # Summary
    print()
    print("="*80)
    print("VALIDATION SUMMARY")
    print("="*80)
    print()
    
    signals_generated = sum(1 for r in results if r.get('status') == 'signal_generated')
    no_signals = sum(1 for r in results if r.get('status') == 'no_signal')
    insufficient_data = sum(1 for r in results if r.get('status') == 'insufficient_data')
    errors = sum(1 for r in results if r.get('status') == 'error')
    
    print(f"Total Tickers: {len(results)}")
    print(f"✅ Signals Generated: {signals_generated}")
    print(f"⚠️  No Signals: {no_signals}")
    print(f"❌ Insufficient Data: {insufficient_data}")
    print(f"❌ Errors: {errors}")
    print()
    
    if signals_generated > 0:
        print("SIGNALS GENERATED:")
        print("-" * 80)
        for r in results:
            if r.get('status') == 'signal_generated':
                print(f"  {r['symbol']}: {r['direction']} @ {r['confidence']:.2%} ({r['agent']})")
                print(f"    Reasoning: {r['reasoning']}")
        print()
    
    # Check what agents are being used
    agents_used = {}
    for r in results:
        if r.get('status') == 'signal_generated':
            agent = r.get('agent', 'Unknown')
            agents_used[agent] = agents_used.get(agent, 0) + 1
    
    if agents_used:
        print("AGENTS BEING USED:")
        print("-" * 80)
        for agent, count in sorted(agents_used.items(), key=lambda x: x[1], reverse=True):
            print(f"  {agent}: {count} signals")
        print()
    
    # Check directions
    directions = {}
    for r in results:
        if r.get('status') == 'signal_generated':
            direction = r.get('direction', 'Unknown')
            directions[direction] = directions.get(direction, 0) + 1
    
    if directions:
        print("SIGNAL DIRECTIONS:")
        print("-" * 80)
        for direction, count in sorted(directions.items(), key=lambda x: x[1], reverse=True):
            print(f"  {direction}: {count} signals")
        print()
    
    # Validate against expected behavior
    print("="*80)
    print("ALGORITHM BEHAVIOR VALIDATION")
    print("="*80)
    print()
    
    print("✅ EXPECTED BEHAVIOR:")
    print("  1. Scan all 12 tickers")
    print("  2. Generate signals using multiple agents")
    print("  3. Use Massive for price data")
    print("  4. Apply risk checks before execution")
    print("  5. Execute trades that pass all checks")
    print()
    
    print("ACTUAL BEHAVIOR:")
    print(f"  ✅ Scanning {len(Config.TICKERS)} tickers")
    print(f"  ✅ Using {len(orchestrator.agents)} agents")
    print(f"  {'✅' if massive_feed.is_available() else '❌'} Massive feed: {'Available' if massive_feed.is_available() else 'Not Available'}")
    print(f"  ✅ Signals generated: {signals_generated}/{len(results)}")
    print()
    
    if signals_generated > 0:
        print("✅ ALGORITHM IS WORKING AS INTENDED")
        print("   - Scanning all tickers")
        print("   - Generating signals")
        print("   - Using multiple agents")
    else:
        print("⚠️  NO SIGNALS GENERATED")
        print("   - Check if market conditions meet criteria")
        print("   - Verify agent thresholds")
        print("   - Check risk filters")
    
    return results

if __name__ == "__main__":
    results = validate_algorithm_behavior()
    sys.exit(0)

