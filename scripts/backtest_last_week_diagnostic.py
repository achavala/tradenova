#!/usr/bin/env python3
"""
Last Week Backtest - Diagnostic Version
Shows what signals are being filtered and why
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
from datetime import datetime, timedelta
import pandas as pd
from collections import defaultdict

from config import Config
from alpaca_client import AlpacaClient
from alpaca_trade_api.rest import TimeFrame
from core.multi_agent_orchestrator import MultiAgentOrchestrator

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


def main():
    """Diagnostic backtest to see filtered signals"""
    print("\n" + "="*70)
    print("LAST WEEK BACKTEST - DIAGNOSTIC MODE")
    print("="*70)
    
    # Calculate date ranges
    end_date = datetime.now()
    trading_start = end_date - timedelta(days=7)
    data_start = trading_start - timedelta(days=90)
    
    tickers = Config.TICKERS
    
    print(f"\n📅 Analysis Window: {data_start.date()} to {end_date.date()}")
    print(f"📅 Trading Window: {trading_start.date()} to {end_date.date()}")
    print(f"📈 Tickers: {len(tickers)} symbols")
    print("="*70)
    
    # Initialize
    client = AlpacaClient(
        Config.ALPACA_API_KEY,
        Config.ALPACA_SECRET_KEY,
        Config.ALPACA_BASE_URL
    )
    orchestrator = MultiAgentOrchestrator(client)
    
    # Track signals
    all_signals = []
    filtered_signals = []
    
    # Fetch data for each ticker
    for ticker in tickers:
        try:
            bars = client.get_historical_bars(ticker, TimeFrame.Day, data_start, end_date)
            if bars.empty or len(bars) < 50:
                continue
            
            # Analyze each day in trading window
            for date in pd.date_range(trading_start, end_date, freq='D'):
                bars_up_to_date = bars[bars.index <= pd.Timestamp(date, tz='UTC')]
                if len(bars_up_to_date) < 50:
                    continue
                
                # Get trade intent
                intent = orchestrator.analyze_symbol(ticker, bars_up_to_date)
                
                if intent:
                    signal_info = {
                        'date': date.date(),
                        'symbol': ticker,
                        'direction': intent.direction.value,
                        'confidence': intent.confidence,
                        'agent': intent.agent_name,
                        'reasoning': intent.reasoning
                    }
                    all_signals.append(signal_info)
                    
                    # Check if it would pass current thresholds
                    if intent.confidence >= 0.30:
                        filtered_signals.append(signal_info)
                    else:
                        logger.info(f"FILTERED: {ticker} on {date.date()} - "
                                  f"Confidence {intent.confidence:.2f} < 0.30")
                else:
                    logger.debug(f"No signal: {ticker} on {date.date()}")
        
        except Exception as e:
            logger.error(f"Error processing {ticker}: {e}")
            continue
    
    # Results
    print("\n" + "="*70)
    print("DIAGNOSTIC RESULTS")
    print("="*70)
    
    print(f"\n📊 Total Signals Generated: {len(all_signals)}")
    print(f"📊 Signals Passing Threshold (>=0.30): {len(filtered_signals)}")
    
    if all_signals:
        # Group by date
        signals_by_date = defaultdict(list)
        for sig in all_signals:
            signals_by_date[sig['date']].append(sig)
        
        print(f"\n📈 Signals Per Day:")
        print(f"{'='*70}")
        for date in sorted(signals_by_date.keys()):
            day_signals = signals_by_date[date]
            passing = [s for s in day_signals if s['confidence'] >= 0.30]
            print(f"{date}: {len(day_signals)} total, {len(passing)} passing")
            
            # Show confidence distribution
            confidences = [s['confidence'] for s in day_signals]
            if confidences:
                print(f"  Confidence range: {min(confidences):.2f} - {max(confidences):.2f}")
                print(f"  Average: {sum(confidences)/len(confidences):.2f}")
        
        # Confidence analysis
        confidences = [s['confidence'] for s in all_signals]
        print(f"\n📊 Confidence Statistics:")
        print(f"{'='*70}")
        print(f"Min: {min(confidences):.2f}")
        print(f"Max: {max(confidences):.2f}")
        print(f"Average: {sum(confidences)/len(confidences):.2f}")
        print(f"Median: {sorted(confidences)[len(confidences)//2]:.2f}")
        
        # Count by threshold
        print(f"\n📊 Signals by Threshold:")
        print(f"{'='*70}")
        for threshold in [0.20, 0.25, 0.30, 0.35, 0.40]:
            count = sum(1 for s in all_signals if s['confidence'] >= threshold)
            print(f">= {threshold:.2f}: {count} signals")
        
        # Agent breakdown
        agent_counts = defaultdict(int)
        for sig in all_signals:
            agent_counts[sig['agent']] += 1
        
        print(f"\n🤖 Signals by Agent:")
        print(f"{'='*70}")
        for agent, count in sorted(agent_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"{agent:20s}: {count:3d} signals")
        
        # Recommendation
        print(f"\n💡 RECOMMENDATIONS:")
        print(f"{'='*70}")
        if len(filtered_signals) < 14:  # Less than 2 per day
            print(f"Current threshold (0.30) too high - only {len(filtered_signals)} signals pass")
            print(f"To get 2-5 trades/day (14-35 total), consider:")
            print(f"  - Lower confidence threshold to 0.20-0.25")
            print(f"  - Lower regime confidence from 0.40 to 0.30")
            print(f"  - Check if agents are being too conservative")
        else:
            print(f"Threshold seems reasonable - {len(filtered_signals)} signals pass")
    
    print("="*70)


if __name__ == "__main__":
    main()





