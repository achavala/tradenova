#!/usr/bin/env python3
"""
Diagnostic Script for TradeNova Options Trading System
Validates all components and identifies why trades aren't executing
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from datetime import datetime
import logging
from config import Config
from alpaca_client import AlpacaClient
import os
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def print_section(title):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)

def check_config():
    print_section("1. CONFIGURATION CHECK")
    print(f"✅ Tickers: {Config.TICKERS}")
    print(f"✅ MIN_DTE: {Config.MIN_DTE}")
    print(f"✅ MAX_DTE: {Config.MAX_DTE}")
    print(f"✅ MAX_ACTIVE_TRADES: {Config.MAX_ACTIVE_TRADES}")
    print(f"✅ POSITION_SIZE_PCT: {Config.POSITION_SIZE_PCT * 100}%")
    print(f"✅ ALPACA_BASE_URL: {Config.ALPACA_BASE_URL}")
    return True

def check_alpaca():
    print_section("2. ALPACA CONNECTION CHECK")
    try:
        client = AlpacaClient(
            Config.ALPACA_API_KEY,
            Config.ALPACA_SECRET_KEY,
            Config.ALPACA_BASE_URL
        )
        
        account = client.get_account()
        print(f"✅ Alpaca Connected")
        print(f"   Account Equity: ${float(account['equity']):,.2f}")
        print(f"   Buying Power: ${float(account['buying_power']):,.2f}")
        
        is_open = client.is_market_open()
        print(f"   Market Open: {'✅ YES' if is_open else '❌ NO (Outside trading hours)'}")
        
        return client, is_open
    except Exception as e:
        print(f"❌ Alpaca Connection Failed: {e}")
        return None, False

def check_massive():
    print_section("3. MASSIVE (POLYGON.IO) CHECK")
    try:
        from services.massive_price_feed import MassivePriceFeed
        feed = MassivePriceFeed()
        
        if feed.is_available():
            print("✅ Massive API Available")
            print(f"   API Key: {'Set' if feed.api_key else 'Not Set'}")
            
            # Test data retrieval
            test_symbol = "AAPL"
            today = datetime.now()
            start = datetime(today.year, today.month, 1)
            
            bars = feed.get_daily_bars(test_symbol, start, today)
            print(f"   Test Data Retrieval: {'✅ Working' if not bars.empty else '❌ Failed'}")
            if not bars.empty:
                print(f"   Retrieved {len(bars)} bars for {test_symbol}")
            
            return True
        else:
            print("❌ Massive API Not Available (API key not configured)")
            return False
    except Exception as e:
        print(f"❌ Massive Check Failed: {e}")
        return False

def check_options_data(client):
    print_section("4. OPTIONS DATA CHECK")
    try:
        from services.options_data_feed import OptionsDataFeed
        options_feed = OptionsDataFeed(client)
        
        test_symbol = "AAPL"
        print(f"Testing options data for {test_symbol}...")
        
        # Get expirations
        expirations = options_feed.get_expiration_dates(test_symbol)
        print(f"   Expirations Available: {'✅ YES' if expirations else '❌ NO'}")
        if expirations:
            print(f"   Found {len(expirations)} expiration dates")
            
            # Check for 0-30 DTE
            today = datetime.now().date()
            valid_expirations = []
            for exp in expirations[:5]:  # Check first 5
                if isinstance(exp, str):
                    exp_date = datetime.strptime(exp, '%Y-%m-%d').date()
                else:
                    exp_date = exp
                dte = (exp_date - today).days
                if Config.MIN_DTE <= dte <= Config.MAX_DTE:
                    valid_expirations.append((exp, dte))
            
            print(f"   Valid Expirations (0-30 DTE): {len(valid_expirations)}")
            if valid_expirations:
                for exp, dte in valid_expirations[:3]:
                    print(f"      - {exp} (DTE: {dte})")
            
            # Get ATM option
            if valid_expirations:
                target_exp = valid_expirations[0][0]
                atm_option = options_feed.get_atm_options(test_symbol, target_exp, 'call')
                print(f"   ATM Option Available: {'✅ YES' if atm_option else '❌ NO'}")
                if atm_option:
                    print(f"      Symbol: {atm_option.get('symbol', 'N/A')}")
                    print(f"      Strike: ${atm_option.get('strike_price', 'N/A')}")
        
        return True
    except Exception as e:
        print(f"❌ Options Data Check Failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_signal_generation():
    print_section("5. SIGNAL GENERATION CHECK")
    try:
        from alpaca_client import AlpacaClient
        from core.multi_agent_orchestrator import MultiAgentOrchestrator
        
        client = AlpacaClient(
            Config.ALPACA_API_KEY,
            Config.ALPACA_SECRET_KEY,
            Config.ALPACA_BASE_URL
        )
        
        orchestrator = MultiAgentOrchestrator(client)
        
        # Test with one symbol
        test_symbol = "AAPL"
        print(f"Testing signal generation for {test_symbol}...")
        
        # Get bars (minimal test)
        from datetime import timedelta
        end_date = datetime.now()
        start_date = end_date - timedelta(days=60)
        
        from services.massive_price_feed import MassivePriceFeed
        massive_feed = MassivePriceFeed()
        
        bars = None
        if massive_feed.is_available():
            bars = massive_feed.get_daily_bars(test_symbol, start_date, end_date)
        
        if bars is None or bars.empty:
            bars = client.get_historical_bars(test_symbol, TimeFrame.Day, start_date, end_date)
        
        if bars.empty or len(bars) < 30:
            print(f"   ❌ Insufficient data: {len(bars)} bars (need 30+)")
            return False
        
        print(f"   ✅ Data Available: {len(bars)} bars")
        
        # Generate signal
        intent = orchestrator.analyze_symbol(test_symbol, bars)
        
        if intent:
            print(f"   ✅ Signal Generated")
            print(f"      Direction: {intent.direction.value}")
            print(f"      Confidence: {intent.confidence:.2%}")
            print(f"      Agent: {intent.agent_name}")
            print(f"      Is LONG: {'✅ YES' if intent.direction.value == 'LONG' else '❌ NO'}")
        else:
            print(f"   ❌ No Signal Generated")
        
        return True
    except Exception as e:
        print(f"❌ Signal Generation Check Failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_risk_manager():
    print_section("6. RISK MANAGER CHECK")
    try:
        from core.risk.advanced_risk_manager import AdvancedRiskManager
        
        risk_manager = AdvancedRiskManager(
            initial_balance=100000,
            daily_loss_limit_pct=0.02,
            max_drawdown_pct=0.10,
            max_loss_streak=3,
            use_iv_regimes=True
        )
        
        status = risk_manager.get_risk_status()
        print(f"✅ Risk Manager Initialized")
        print(f"   Risk Level: {status['risk_level']}")
        print(f"   Daily P&L: ${status['daily_pnl']:,.2f}")
        print(f"   Can Trade: {'✅ YES' if status['risk_level'] not in ['danger', 'blocked'] else '❌ NO'}")
        
        return True
    except Exception as e:
        print(f"❌ Risk Manager Check Failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("\n" + "=" * 60)
    print("  TRADENOVA SYSTEM DIAGNOSTICS")
    print("=" * 60)
    
    results = {}
    
    # Run all checks
    results['config'] = check_config()
    client, market_open = check_alpaca()
    results['alpaca'] = client is not None
    results['market_open'] = market_open
    results['massive'] = check_massive()
    
    if client:
        results['options'] = check_options_data(client)
    
    results['signals'] = check_signal_generation()
    results['risk'] = check_risk_manager()
    
    # Summary
    print_section("SUMMARY")
    print("\nComponent Status:")
    for component, status in results.items():
        status_icon = "✅" if status else "❌"
        print(f"  {status_icon} {component.replace('_', ' ').title()}")
    
    print("\n⚠️  CRITICAL CHECKS:")
    if not results['market_open']:
        print("  ❌ Market is CLOSED - System won't trade outside market hours")
        print("     Market hours: 9:30 AM - 4:00 PM ET (Mon-Fri)")
    
    if not results['alpaca']:
        print("  ❌ Alpaca connection failed - Trading cannot proceed")
    
    if not results.get('options', False):
        print("  ❌ Options data unavailable - Cannot execute options trades")
    
    print("\n💡 NEXT STEPS:")
    print("  1. Check logs: tail -f logs/tradenova_daily.log")
    print("  2. Monitor during market hours (9:30 AM - 4:00 PM ET)")
    print("  3. Check for 'Signal found', 'EXECUTING', or 'BLOCKED' messages")
    print("  4. Verify Massive API key is configured if using Massive data")
    
    print("\n" + "=" * 60)

if __name__ == '__main__':
    main()




