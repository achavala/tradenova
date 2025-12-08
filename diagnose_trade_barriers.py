#!/usr/bin/env python3
"""
Diagnose Trade Barriers
Comprehensive analysis of why no trades are executing
"""
import logging
import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent))

from alpaca_client import AlpacaClient
from config import Config
from core.multi_agent_orchestrator import MultiAgentOrchestrator
from core.risk.advanced_risk_manager import AdvancedRiskManager
from alpaca_trade_api.rest import TimeFrame

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def diagnose_trade_barriers():
    """Comprehensive diagnosis of trade barriers"""
    print("="*80)
    print("🔍 TRADE BARRIER DIAGNOSIS")
    print("="*80)
    print()
    
    # Initialize clients
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
    
    # Test a single ticker in detail
    test_symbol = "SPY"  # Use SPY as it should have data
    
    print("="*80)
    print("1️⃣  MARKET STATUS CHECK")
    print("="*80)
    try:
        is_open = client.is_market_open()
        print(f"✅ Market Status: {'OPEN' if is_open else 'CLOSED'}")
        if not is_open:
            print("⚠️  BARRIER: Market is closed - no trades will execute")
    except Exception as e:
        print(f"❌ Error checking market: {e}")
    print()
    
    print("="*80)
    print("2️⃣  DATA AVAILABILITY CHECK")
    print("="*80)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=60)
    
    data_available_count = 0
    for symbol in Config.TICKERS[:3]:  # Test first 3
        try:
            bars = client.get_historical_bars(symbol, TimeFrame.Day, start_date, end_date)
            if bars.empty or len(bars) < 50:
                print(f"❌ {symbol}: Insufficient data ({len(bars)} bars)")
            else:
                print(f"✅ {symbol}: Data available ({len(bars)} bars)")
                data_available_count += 1
        except Exception as e:
            error_msg = str(e)
            if "subscription" in error_msg.lower() or "sip" in error_msg.lower():
                print(f"❌ {symbol}: Subscription limitation - {error_msg[:60]}")
            else:
                print(f"❌ {symbol}: Error - {error_msg[:60]}")
    
    if data_available_count == 0:
        print()
        print("⚠️  BARRIER: No data available for any ticker!")
        print("   → This prevents signal generation")
        print("   → Check Alpaca subscription level")
    print()
    
    print("="*80)
    print("3️⃣  SIGNAL GENERATION TEST")
    print("="*80)
    # Test with SPY first (should have data)
    try:
        bars = client.get_historical_bars(test_symbol, TimeFrame.Day, start_date, end_date)
        if not bars.empty and len(bars) >= 50:
            current_price = client.get_latest_price(test_symbol)
            if current_price:
                print(f"✅ {test_symbol}: Data loaded ({len(bars)} bars), Price: ${current_price:.2f}")
                
                # Test orchestrator
                try:
                    intents = orchestrator.analyze_symbol(test_symbol, bars, current_price)
                    print(f"✅ Orchestrator: Generated {len(intents)} trade intents")
                    
                    if intents:
                        for intent in intents[:3]:  # Show first 3
                            print(f"   • {intent.agent_name}: {intent.direction.value} @ {intent.confidence:.2%}")
                    else:
                        print("⚠️  BARRIER: Orchestrator generated NO signals")
                        print("   → Agents may be too conservative")
                        print("   → Market conditions may not meet criteria")
                except Exception as e:
                    print(f"❌ Orchestrator error: {e}")
            else:
                print(f"❌ {test_symbol}: Could not get current price")
        else:
            print(f"❌ {test_symbol}: Insufficient data for signal generation")
    except Exception as e:
        print(f"❌ Error testing signal generation: {e}")
    print()
    
    print("="*80)
    print("4️⃣  CONFIDENCE THRESHOLD CHECK")
    print("="*80)
    confidence_threshold = 0.5  # 50% from integrated_trader.py
    print(f"📊 Confidence Threshold: {confidence_threshold:.0%}")
    print(f"   → Signals must have confidence >= {confidence_threshold:.0%} to execute")
    print(f"   → This is a CONSERVATIVE threshold (professional level)")
    print()
    
    print("="*80)
    print("5️⃣  RISK MANAGEMENT CHECK")
    print("="*80)
    try:
        account = client.get_account()
        equity = float(account['equity'])
        risk_manager.update_balance(equity)
        
        print(f"✅ Account Equity: ${equity:,.2f}")
        
        # Test risk check for a trade
        test_price = 100.0
        test_qty = 10
        allowed, reason, risk_level = risk_manager.check_trade_allowed(
            test_symbol, test_qty, test_price, 'buy'
        )
        
        print(f"✅ Risk Check: {'ALLOWED' if allowed else 'BLOCKED'}")
        if not allowed:
            print(f"⚠️  BARRIER: Risk manager blocking trades - {reason}")
            print(f"   Risk Level: {risk_level}")
        else:
            print(f"   Risk Level: {risk_level}")
    except Exception as e:
        print(f"❌ Error checking risk: {e}")
    print()
    
    print("="*80)
    print("6️⃣  POSITION LIMIT CHECK")
    print("="*80)
    try:
        positions = client.get_positions()
        current_positions = len(positions)
        max_positions = Config.MAX_ACTIVE_TRADES
        
        print(f"✅ Current Positions: {current_positions}/{max_positions}")
        if current_positions >= max_positions:
            print(f"⚠️  BARRIER: At position limit - no new trades allowed")
        else:
            print(f"   → Can open {max_positions - current_positions} more positions")
    except Exception as e:
        print(f"❌ Error checking positions: {e}")
    print()
    
    print("="*80)
    print("7️⃣  SUMMARY - IDENTIFIED BARRIERS")
    print("="*80)
    barriers = []
    
    # Check each barrier
    try:
        if not client.is_market_open():
            barriers.append("❌ Market is CLOSED")
    except:
        barriers.append("❌ Cannot check market status")
    
    # Check data
    try:
        bars = client.get_historical_bars(Config.TICKERS[0], TimeFrame.Day, start_date, end_date)
        if bars.empty or len(bars) < 50:
            barriers.append("❌ No historical data available (subscription limitation)")
    except Exception as e:
        if "subscription" in str(e).lower():
            barriers.append("❌ Data subscription limitation")
        else:
            barriers.append(f"❌ Data fetch error: {str(e)[:50]}")
    
    # Check signals
    try:
        bars = client.get_historical_bars(test_symbol, TimeFrame.Day, start_date, end_date)
        if not bars.empty:
            current_price = client.get_latest_price(test_symbol)
            if current_price:
                intents = orchestrator.analyze_symbol(test_symbol, bars, current_price)
                if not intents:
                    barriers.append("⚠️  No signals generated (agents too conservative)")
                elif all(i.confidence < 0.5 for i in intents):
                    barriers.append(f"⚠️  Signals too weak (max confidence: {max(i.confidence for i in intents):.1%} < 50%)")
    except:
        pass
    
    if barriers:
        print("🚫 BARRIERS PREVENTING TRADES:")
        for barrier in barriers:
            print(f"   {barrier}")
    else:
        print("✅ No obvious barriers detected")
        print("   → System should be able to trade")
        print("   → Check logs for specific ticker failures")
    
    print()
    print("="*80)
    print("💡 RECOMMENDATIONS")
    print("="*80)
    
    if "subscription" in str(barriers).lower() or "data" in str(barriers).lower():
        print("1. ⚠️  DATA ISSUE:")
        print("   → Upgrade Alpaca subscription for historical data access")
        print("   → Or use alternative data source")
        print()
    
    if "No signals" in str(barriers) or "too weak" in str(barriers):
        print("2. ⚠️  SIGNAL GENERATION:")
        print("   → Consider lowering confidence threshold (currently 50%)")
        print("   → Review agent parameters for less conservative signals")
        print("   → Check if market conditions are suitable for trading")
        print()
    
    if "Market is CLOSED" in str(barriers):
        print("3. ⚠️  MARKET HOURS:")
        print("   → Wait for market to open (9:30 AM - 4:00 PM ET)")
        print("   → Or use weekend testing mode for historical replay")
        print()
    
    print("="*80)

if __name__ == '__main__':
    diagnose_trade_barriers()

