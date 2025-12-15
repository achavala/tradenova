#!/usr/bin/env python3
"""
7-Day Backtest - Detailed Analysis
Shows exactly why signals aren't being generated
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
from datetime import datetime, timedelta
import pandas as pd

from config import Config
from alpaca_client import AlpacaClient
from alpaca_trade_api.rest import TimeFrame
from core.multi_agent_orchestrator import MultiAgentOrchestrator
from core.features.indicators import FeatureEngine
from core.regime.classifier import RegimeClassifier

# Setup logging - reduce noise
logging.basicConfig(
    level=logging.WARNING,  # Only show warnings/errors
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Detailed 7-day analysis"""
    print("\n" + "="*70)
    print("7-DAY DETAILED ANALYSIS - Why No Trades?")
    print("="*70)
    
    end_date = datetime.now()
    backtest_start = end_date - timedelta(days=7)
    data_start = backtest_start - timedelta(days=60)
    
    client = AlpacaClient(
        Config.ALPACA_API_KEY,
        Config.ALPACA_SECRET_KEY,
        Config.ALPACA_BASE_URL
    )
    
    orchestrator = MultiAgentOrchestrator(client)
    feature_engine = FeatureEngine()
    regime_classifier = RegimeClassifier()
    
    test_tickers = ['AAPL', 'NVDA', 'TSLA', 'GOOG']
    
    print(f"\n📅 Period: {backtest_start.date()} to {end_date.date()}")
    print(f"📊 Testing: {', '.join(test_tickers)}")
    print("\n" + "="*70)
    
    # Analyze each ticker
    for ticker in test_tickers:
        print(f"\n🔍 Analyzing {ticker}...")
        
        try:
            bars = client.get_historical_bars(
                ticker,
                TimeFrame.Day,
                data_start,
                end_date
            )
            
            if bars.empty or len(bars) < 30:
                print(f"  ❌ Insufficient data: {len(bars)} bars (need at least 30)")
                continue
            
            if len(bars) < 50:
                print(f"  ⚠️  Limited data: {len(bars)} bars (prefer 50+, but will try)")
            
            print(f"  ✅ Data: {len(bars)} bars")
            
            # Get latest bars (last 7 days)
            latest_bars = bars.tail(10)  # Last 10 bars
            current_date = latest_bars.index[-1]
            
            print(f"  📅 Latest date: {current_date.date()}")
            
            # Calculate features
            features = feature_engine.calculate_all_features(bars)
            if not features:
                print(f"  ❌ Could not calculate features")
                continue
            
            print(f"  ✅ Features calculated")
            
            # Classify regime
            regime_signal = regime_classifier.classify(features)
            print(f"  📊 Regime: {regime_signal.regime_type.value}")
            print(f"  📊 Regime Confidence: {regime_signal.confidence:.2f}")
            
            if regime_signal.confidence < 0.4:
                print(f"  ⚠️  LOW REGIME CONFIDENCE ({regime_signal.confidence:.2f} < 0.40) - BLOCKING SIGNALS")
                continue
            
            # Get intents from agents
            print(f"  🤖 Checking agents...")
            intents = []
            for agent in orchestrator.agents:
                try:
                    intent = agent.evaluate(ticker, regime_signal, features)
                    if intent:
                        intents.append(intent)
                        status = "✅" if intent.confidence >= 0.30 else "⚠️ "
                        print(f"     {status} {agent.name:20s}: {intent.direction.value:5s} @ {intent.confidence:.2f} confidence")
                except Exception as e:
                    print(f"     ❌ {agent.name}: Error - {str(e)[:50]}")
            
            if not intents:
                print(f"  ❌ No agents generated intents")
                continue
            
            # Meta-policy arbitration
            final_intent = orchestrator.meta_policy.arbitrate(
                intents,
                regime_signal.regime_type.value,
                regime_signal.volatility_level.value
            )
            
            if final_intent:
                status = "✅ WOULD TRADE" if final_intent.confidence >= 0.30 else "⚠️  BELOW THRESHOLD"
                print(f"  {status}: {final_intent.direction.value} @ {final_intent.confidence:.2f} confidence ({final_intent.agent_name})")
            else:
                print(f"  ❌ Meta-policy did not select any intent")
        
        except Exception as e:
            print(f"  ❌ Error: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*70)
    print("ANALYSIS COMPLETE")
    print("="*70)


if __name__ == "__main__":
    main()

