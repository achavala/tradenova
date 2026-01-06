#!/usr/bin/env python3
"""
Validate December 17, 2025 Trade Opportunities
Checks if the algorithm would have picked up HOOD and PLTR trades
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
from datetime import datetime, timedelta
import pandas as pd

from services.massive_price_feed import MassivePriceFeed
from alpaca_client import AlpacaClient
from config import Config
from core.multi_agent_orchestrator import MultiAgentOrchestrator
from core.live.integrated_trader import IntegratedTrader

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def validate_dec17_opportunities():
    """Validate opportunities from December 17, 2025"""
    
    print("="*80)
    print("DECEMBER 17, 2025 TRADE OPPORTUNITY VALIDATION")
    print("="*80)
    print()
    
    # Target date: December 17, 2025
    target_date = datetime(2025, 12, 17)
    start_date = target_date - timedelta(days=60)
    end_date = target_date
    
    print(f"Target Date: {target_date.strftime('%Y-%m-%d')}")
    print(f"Data Range: {start_date.date()} to {end_date.date()}")
    print()
    
    # Initialize data sources
    massive_feed = MassivePriceFeed()
    alpaca_client = AlpacaClient(
        Config.ALPACA_API_KEY,
        Config.ALPACA_SECRET_KEY,
        Config.ALPACA_BASE_URL
    )
    
    # Initialize orchestrator
    orchestrator = MultiAgentOrchestrator(alpaca_client)
    
    opportunities = [
        {
            'symbol': 'HOOD',
            'pattern': 'Inverse head and shoulders',
            'entry': 122.0,
            'target': 125.0,
            'recommended': '$127C EOW',
            'in_tickers': 'HOOD' in Config.TICKERS
        },
        {
            'symbol': 'PLTR',
            'pattern': 'Cup and handle',
            'entry': 190.4,
            'target': 192.5,
            'recommended': '$195C EOW',
            'in_tickers': 'PLTR' in Config.TICKERS
        }
    ]
    
    results = []
    
    for opp in opportunities:
        symbol = opp['symbol']
        print("="*80)
        print(f"ANALYZING: {symbol}")
        print("="*80)
        print(f"Pattern: {opp['pattern']}")
        print(f"Entry: Above ${opp['entry']:.2f}")
        print(f"Target: ${opp['target']:.2f}")
        print(f"Recommended: {opp['recommended']}")
        print(f"In Ticker List: {'✅ YES' if opp['in_tickers'] else '❌ NO'}")
        print()
        
        # Get historical data
        print("FETCHING DATA:")
        print("-" * 80)
        
        bars = None
        data_source = None
        
        if massive_feed.is_available():
            print("Fetching from Massive API...")
            bars = massive_feed.get_daily_bars(symbol, start_date, end_date, use_1min_aggregation=True)
            if not bars.empty:
                bars['date'] = pd.to_datetime(bars['timestamp']).dt.date
                bars = bars[bars['date'] <= target_date.date()]
                data_source = "Massive"
                print(f"✅ Got {len(bars)} bars from Massive")
        else:
            print("Massive not available, trying Alpaca...")
            try:
                from alpaca_trade_api.rest import TimeFrame
                bars = alpaca_client.get_historical_bars(symbol, TimeFrame.Day, start_date, end_date)
                if not bars.empty:
                    data_source = "Alpaca"
                    print(f"✅ Got {len(bars)} bars from Alpaca")
            except Exception as e:
                print(f"❌ Error from Alpaca: {e}")
        
        if bars is None or bars.empty:
            print(f"❌ No data available for {symbol}")
            results.append({
                'symbol': symbol,
                'data_available': False,
                'signal_generated': False,
                'reason': 'No data available'
            })
            continue
        
        # Show latest data
        if len(bars) > 0:
            latest = bars.iloc[-1]
            latest_date = pd.to_datetime(latest['timestamp']).date() if 'timestamp' in latest else None
            latest_close = latest['close']
            print(f"Latest Close: ${latest_close:.2f}")
            if latest_date:
                print(f"Latest Date: {latest_date}")
            print()
        
        # Check if enough data
        if len(bars) < 30:
            print(f"❌ Insufficient data: {len(bars)} bars (need 30+)")
            results.append({
                'symbol': symbol,
                'data_available': True,
                'bars_count': len(bars),
                'signal_generated': False,
                'reason': f'Insufficient data ({len(bars)} < 30)'
            })
            continue
        
        # Generate signal
        print("SIGNAL GENERATION:")
        print("-" * 80)
        
        try:
            intent = orchestrator.analyze_symbol(symbol, bars)
            
            if intent and intent.direction.value != 'FLAT':
                print(f"✅ Signal Generated:")
                print(f"   Direction: {intent.direction.value}")
                print(f"   Confidence: {intent.confidence:.2%}")
                print(f"   Agent: {intent.agent_name}")
                print(f"   Reasoning: {intent.reasoning}")
                print()
                
                # Check if signal matches opportunity
                matches = False
                if opp['pattern'].lower() in ['inverse head and shoulders', 'head and shoulders']:
                    # Should be LONG for inverse H&S
                    matches = intent.direction.value == 'LONG'
                elif opp['pattern'].lower() in ['cup and handle']:
                    # Should be LONG for cup and handle
                    matches = intent.direction.value == 'LONG'
                
                print(f"Signal Match: {'✅ YES' if matches else '❌ NO'}")
                print(f"   Opportunity: LONG (calls)")
                print(f"   Signal: {intent.direction.value}")
                print()
                
                results.append({
                    'symbol': symbol,
                    'data_available': True,
                    'bars_count': len(bars),
                    'data_source': data_source,
                    'signal_generated': True,
                    'direction': intent.direction.value,
                    'confidence': intent.confidence,
                    'agent': intent.agent_name,
                    'matches_opportunity': matches,
                    'latest_price': latest_close
                })
            else:
                print("❌ No signal generated")
                print(f"   Reason: {intent.reasoning if intent else 'No intent returned'}")
                print()
                
                results.append({
                    'symbol': symbol,
                    'data_available': True,
                    'bars_count': len(bars),
                    'data_source': data_source,
                    'signal_generated': False,
                    'reason': 'No signal generated',
                    'latest_price': latest_close
                })
        except Exception as e:
            print(f"❌ Error generating signal: {e}")
            import traceback
            traceback.print_exc()
            results.append({
                'symbol': symbol,
                'data_available': True,
                'bars_count': len(bars),
                'signal_generated': False,
                'reason': f'Error: {e}'
            })
        
        print()
    
    # Summary
    print("="*80)
    print("VALIDATION SUMMARY")
    print("="*80)
    print()
    
    for result in results:
        symbol = result['symbol']
        print(f"{symbol}:")
        print(f"  Data Available: {'✅' if result.get('data_available') else '❌'}")
        if result.get('data_available'):
            print(f"  Bars: {result.get('bars_count', 'N/A')} ({result.get('data_source', 'Unknown')})")
            print(f"  Latest Price: ${result.get('latest_price', 'N/A'):.2f}" if result.get('latest_price') else "")
        print(f"  Signal Generated: {'✅' if result.get('signal_generated') else '❌'}")
        if result.get('signal_generated'):
            print(f"    Direction: {result.get('direction')}")
            print(f"    Confidence: {result.get('confidence', 0):.2%}")
            print(f"    Agent: {result.get('agent')}")
            print(f"    Matches Opportunity: {'✅ YES' if result.get('matches_opportunity') else '❌ NO'}")
        else:
            print(f"    Reason: {result.get('reason', 'Unknown')}")
        print()
    
    print("="*80)
    print("CONCLUSION")
    print("="*80)
    
    signals_found = sum(1 for r in results if r.get('signal_generated'))
    matches_found = sum(1 for r in results if r.get('matches_opportunity'))
    
    print(f"Signals Generated: {signals_found}/{len(results)}")
    print(f"Matches Opportunity: {matches_found}/{len(results)}")
    print()
    
    if signals_found == 0:
        print("❌ Algorithm did NOT pick up these opportunities")
        print("   Reasons:")
        for r in results:
            if not r.get('signal_generated'):
                print(f"   - {r['symbol']}: {r.get('reason', 'Unknown')}")
    elif matches_found == len(results):
        print("✅ Algorithm WOULD HAVE picked up these opportunities!")
    else:
        print("⚠️  Algorithm generated signals but may not match opportunities")
    
    return results

if __name__ == "__main__":
    results = validate_dec17_opportunities()
    sys.exit(0)




