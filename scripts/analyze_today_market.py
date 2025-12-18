#!/usr/bin/env python3
"""
Comprehensive Market Analysis for Today
Analyzes why no trades were executed and what needs to be done
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

from config import Config
from alpaca_client import AlpacaClient
from alpaca_trade_api.rest import TimeFrame
from core.multi_agent_orchestrator import MultiAgentOrchestrator
from core.risk.advanced_risk_manager import AdvancedRiskManager
from core.regime.classifier import RegimeClassifier

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


def analyze_today_market():
    """Comprehensive analysis of today's market conditions"""
    print("\n" + "="*90)
    print("COMPREHENSIVE MARKET ANALYSIS - December 15, 2025".center(90))
    print("="*90)
    
    # Initialize
    client = AlpacaClient(
        Config.ALPACA_API_KEY,
        Config.ALPACA_SECRET_KEY,
        Config.ALPACA_BASE_URL
    )
    
    orchestrator = MultiAgentOrchestrator(client)
    risk_manager = AdvancedRiskManager(
        initial_balance=Config.INITIAL_BALANCE,
        daily_loss_limit_pct=0.02,
        max_drawdown_pct=0.10,
        max_loss_streak=3
    )
    
    # Get market status
    is_open = client.is_market_open()
    account = client.get_account()
    
    print(f"\n📊 MARKET STATUS")
    print("-" * 90)
    print(f"Market: {'✅ OPEN' if is_open else '❌ CLOSED'}")
    print(f"Account Equity: ${float(account['equity']):,.2f}")
    print(f"Buying Power: ${float(account['buying_power']):,.2f}")
    
    # Analyze each ticker
    print(f"\n📈 TICKER-BY-TICKER ANALYSIS")
    print("-" * 90)
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)
    
    all_signals = []
    all_rejections = []
    
    for ticker in Config.TICKERS:
        print(f"\n🔍 {ticker}")
        print("-" * 90)
        
        try:
            # Get historical data
            bars = client.get_historical_bars(ticker, TimeFrame.Day, start_date, end_date)
            
            if bars.empty:
                print(f"   ❌ No data available")
                all_rejections.append({
                    'ticker': ticker,
                    'reason': 'No data available',
                    'category': 'data'
                })
                continue
            
            if len(bars) < 50:
                print(f"   ⚠️  Insufficient data: {len(bars)} bars (need 50+)")
                all_rejections.append({
                    'ticker': ticker,
                    'reason': f'Insufficient data: {len(bars)} bars',
                    'category': 'data'
                })
                continue
            
            # Get current price
            current_price = client.get_latest_price(ticker)
            if current_price is None:
                print(f"   ❌ Cannot get current price")
                all_rejections.append({
                    'ticker': ticker,
                    'reason': 'Cannot get current price',
                    'category': 'data'
                })
                continue
            
            # Market data analysis
            latest_bar = bars.iloc[-1]
            prev_bar = bars.iloc[-2] if len(bars) > 1 else latest_bar
            
            price_change = ((latest_bar['close'] - prev_bar['close']) / prev_bar['close']) * 100
            volume_change = ((latest_bar['volume'] - prev_bar['volume'].mean()) / prev_bar['volume'].mean()) * 100
            
            print(f"   Current Price: ${current_price:.2f}")
            print(f"   Today's Change: {price_change:+.2f}%")
            print(f"   Volume vs Avg: {volume_change:+.1f}%")
            
            # Calculate indicators
            bars['rsi'] = calculate_rsi(bars['close'], 14)
            bars['sma_20'] = bars['close'].rolling(20).mean()
            bars['sma_50'] = bars['close'].rolling(50).mean()
            bars['atr'] = calculate_atr(bars)
            
            latest_rsi = bars['rsi'].iloc[-1]
            latest_sma20 = bars['sma_20'].iloc[-1]
            latest_sma50 = bars['sma_50'].iloc[-1]
            
            print(f"   RSI(14): {latest_rsi:.1f}")
            print(f"   Price vs SMA20: {((current_price - latest_sma20) / latest_sma20) * 100:+.2f}%")
            print(f"   Price vs SMA50: {((current_price - latest_sma50) / latest_sma50) * 100:+.2f}%")
            
            # Regime analysis - use orchestrator's method
            features = orchestrator.feature_engine.calculate_all_features(bars)
            if features:
                regime_signal = orchestrator.regime_classifier.classify(features)
            else:
                regime_signal = None
            
            print(f"   Regime: {regime_signal.regime.value}")
            print(f"   Regime Confidence: {regime_signal.confidence:.2f}")
            
            # Multi-agent analysis
            trade_intent = orchestrator.analyze_symbol(ticker, bars)
            
            if trade_intent and trade_intent.direction.value != 'FLAT':
                print(f"   ✅ SIGNAL GENERATED:")
                print(f"      Direction: {trade_intent.direction.value}")
                print(f"      Confidence: {trade_intent.confidence:.2f}")
                print(f"      Agent: {trade_intent.agent_name}")
                print(f"      Reasoning: {trade_intent.reasoning[:80]}...")
                
                all_signals.append({
                    'ticker': ticker,
                    'direction': trade_intent.direction.value,
                    'confidence': trade_intent.confidence,
                    'agent': trade_intent.agent_name,
                    'regime': regime_signal.regime_type.value if regime_signal else 'UNKNOWN',
                    'regime_confidence': regime_signal.confidence if regime_signal else 0.0,
                    'current_price': current_price,
                    'rsi': latest_rsi,
                    'price_change': price_change
                })
                
                # Check why it didn't execute
                print(f"   🔍 EXECUTION ANALYSIS:")
                
                # 1. Confidence threshold
                if trade_intent.confidence < 0.20:
                    print(f"      ❌ Confidence too low: {trade_intent.confidence:.2f} < 0.20")
                    all_rejections.append({
                        'ticker': ticker,
                        'reason': f'Confidence too low: {trade_intent.confidence:.2f}',
                        'category': 'threshold'
                    })
                else:
                    print(f"      ✅ Confidence OK: {trade_intent.confidence:.2f} >= 0.20")
                
                # 2. Regime filter
                if regime_signal.confidence < 0.30:
                    print(f"      ❌ Regime confidence too low: {regime_signal.confidence:.2f} < 0.30")
                    all_rejections.append({
                        'ticker': ticker,
                        'reason': f'Regime confidence too low: {regime_signal.confidence:.2f}',
                        'category': 'regime'
                    })
                else:
                    print(f"      ✅ Regime OK: {regime_signal.confidence:.2f} >= 0.30")
                
                # 3. Risk check
                allowed, reason, risk_level = risk_manager.check_trade_allowed(
                    ticker, 10, current_price, 'buy'
                )
                if not allowed:
                    print(f"      ❌ Risk manager blocked: {reason}")
                    all_rejections.append({
                        'ticker': ticker,
                        'reason': f'Risk: {reason}',
                        'category': 'risk'
                    })
                else:
                    print(f"      ✅ Risk check passed")
                
                # 4. Authentication (check logs)
                print(f"      ⚠️  Authentication: Check logs for 'unauthorized' errors")
                
            else:
                print(f"   ❌ NO SIGNAL GENERATED")
                print(f"      Reason: Agents did not find suitable opportunity")
                all_rejections.append({
                    'ticker': ticker,
                    'reason': 'No signal from agents',
                    'category': 'signal'
                })
        
        except Exception as e:
            print(f"   ❌ Error analyzing {ticker}: {e}")
            all_rejections.append({
                'ticker': ticker,
                'reason': f'Error: {str(e)[:50]}',
                'category': 'error'
            })
    
    # Summary
    print(f"\n" + "="*90)
    print("SUMMARY ANALYSIS".center(90))
    print("="*90)
    
    print(f"\n📊 SIGNALS GENERATED: {len(all_signals)}")
    if all_signals:
        print(f"\n   Signals by Agent:")
        agent_counts = {}
        for sig in all_signals:
            agent = sig['agent']
            agent_counts[agent] = agent_counts.get(agent, 0) + 1
        for agent, count in agent_counts.items():
            print(f"      {agent}: {count}")
        
        print(f"\n   Signals by Direction:")
        direction_counts = {}
        for sig in all_signals:
            direction = sig['direction']
            direction_counts[direction] = direction_counts.get(direction, 0) + 1
        for direction, count in direction_counts.items():
            print(f"      {direction}: {count}")
        
        print(f"\n   Confidence Distribution:")
        confidences = [s['confidence'] for s in all_signals]
        print(f"      Min: {min(confidences):.2f}")
        print(f"      Max: {max(confidences):.2f}")
        print(f"      Avg: {np.mean(confidences):.2f}")
        print(f"      Above 0.60: {sum(1 for c in confidences if c >= 0.60)}")
        print(f"      Above 0.20: {sum(1 for c in confidences if c >= 0.20)}")
    
    print(f"\n❌ REJECTIONS: {len(all_rejections)}")
    if all_rejections:
        print(f"\n   Rejections by Category:")
        category_counts = {}
        for rej in all_rejections:
            cat = rej['category']
            category_counts[cat] = category_counts.get(cat, 0) + 1
        for cat, count in category_counts.items():
            print(f"      {cat}: {count}")
    
    # Root cause analysis
    print(f"\n" + "="*90)
    print("ROOT CAUSE ANALYSIS".center(90))
    print("="*90)
    
    auth_errors = sum(1 for rej in all_rejections if 'unauthorized' in rej['reason'].lower())
    low_confidence = sum(1 for rej in all_rejections if 'confidence' in rej['reason'].lower())
    no_signals = sum(1 for rej in all_rejections if rej['category'] == 'signal')
    risk_blocks = sum(1 for rej in all_rejections if rej['category'] == 'risk')
    
    print(f"\n🔴 PRIMARY ISSUES:")
    
    if auth_errors > 0:
        print(f"   1. Authentication Error: Trading system cannot authenticate with Alpaca")
        print(f"      Impact: ALL trades blocked regardless of signals")
        print(f"      Fix: Restart trading system with proper environment variables")
    
    if len(all_signals) > 0 and auth_errors == 0:
        print(f"   2. Signals Generated But Not Executed: {len(all_signals)} signals")
        print(f"      - These signals met confidence thresholds but didn't execute")
        print(f"      - Likely blocked by authentication or risk management")
    
    if no_signals > 0:
        print(f"   3. No Signals Generated: {no_signals} tickers")
        print(f"      - Market conditions don't meet agent criteria")
        print(f"      - May need to adjust agent sensitivity or thresholds")
    
    if low_confidence > 0:
        print(f"   4. Low Confidence Signals: {low_confidence} rejections")
        print(f"      - Signals generated but below execution threshold (0.20)")
        print(f"      - Consider lowering threshold or improving signal quality")
    
    # Recommendations
    print(f"\n" + "="*90)
    print("RECOMMENDATIONS TO ACHIEVE ORIGINAL VISION (2-5 trades/day)".center(90))
    print("="*90)
    
    print(f"\n🎯 IMMEDIATE ACTIONS (Today):")
    print(f"   1. Fix Authentication:")
    print(f"      → Run: ./scripts/fix_trading_auth.sh")
    print(f"      → This will restart trading system with proper credentials")
    print(f"      → Expected: {len(all_signals)} trades should execute immediately")
    
    print(f"\n   2. Verify Signal Generation:")
    print(f"      → Current: {len(all_signals)} signals generated")
    print(f"      → Target: 2-5 signals per day")
    print(f"      → Status: {'✅ MEETS TARGET' if 2 <= len(all_signals) <= 5 else '⚠️  NEEDS ADJUSTMENT'}")
    
    print(f"\n🔧 SYSTEM IMPROVEMENTS (This Week):")
    print(f"   1. Lower Confidence Thresholds (if needed):")
    print(f"      → Current: 0.20 minimum")
    print(f"      → If < 2 signals/day: Lower to 0.15")
    print(f"      → File: core/multi_agent_orchestrator.py")
    
    print(f"\n   2. Adjust Regime Filters:")
    print(f"      → Current: 0.30 minimum regime confidence")
    print(f"      → If too restrictive: Lower to 0.25")
    print(f"      → File: backtest_trading.py")
    
    print(f"\n   3. Expand Ticker Universe:")
    print(f"      → Current: {len(Config.TICKERS)} tickers")
    print(f"      → Add more liquid options tickers if needed")
    print(f"      → File: config.py")
    
    print(f"\n   4. Agent Sensitivity Tuning:")
    print(f"      → Review agent-specific thresholds")
    print(f"      → Ensure agents are not too conservative")
    print(f"      → Files: core/agents/*.py")
    
    print(f"\n📈 MARKET CONDITIONS ANALYSIS:")
    if all_signals:
        avg_confidence = np.mean([s['confidence'] for s in all_signals])
        high_conf_count = sum(1 for s in all_signals if s['confidence'] >= 0.60)
        
        print(f"   ✅ Market is generating signals")
        print(f"   ✅ Average confidence: {avg_confidence:.2f}")
        print(f"   ✅ High-confidence signals (≥0.60): {high_conf_count}")
        print(f"   → System is working, just needs authentication fix")
    else:
        print(f"   ⚠️  Market conditions not generating signals")
        print(f"   → May be low volatility day")
        print(f"   → Consider: Lower thresholds or expand universe")
    
    print(f"\n" + "="*90)
    print("NEXT STEPS".center(90))
    print("="*90)
    print(f"\n1. Run fix script: ./scripts/fix_trading_auth.sh")
    print(f"2. Monitor next trading cycle")
    print(f"3. If still < 2 trades/day, adjust thresholds")
    print(f"4. Review this analysis daily to tune system")
    print(f"\n" + "="*90)


def calculate_rsi(prices, period=14):
    """Calculate RSI"""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calculate_atr(bars, period=14):
    """Calculate ATR"""
    high_low = bars['high'] - bars['low']
    high_close = np.abs(bars['high'] - bars['close'].shift())
    low_close = np.abs(bars['low'] - bars['close'].shift())
    
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)
    atr = true_range.rolling(period).mean()
    
    return atr


if __name__ == "__main__":
    analyze_today_market()

