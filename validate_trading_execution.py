#!/usr/bin/env python3
"""
Trading Execution Validation
Checks why positions are not opening
"""
import sys
from pathlib import Path
from datetime import datetime
import logging

sys.path.insert(0, str(Path(__file__).parent))

from config import Config
from alpaca_client import AlpacaClient
from core.multi_agent_orchestrator import MultiAgentOrchestrator
from core.live.integrated_trader import IntegratedTrader
from core.risk.advanced_risk_manager import AdvancedRiskManager

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def check_1_market_status():
    """Check 1: Is market open?"""
    print("\n" + "="*60)
    print("CHECK 1: Market Status")
    print("="*60)
    
    try:
        client = AlpacaClient(
            Config.ALPACA_API_KEY,
            Config.ALPACA_SECRET_KEY,
            "https://paper-api.alpaca.markets"
        )
        
        is_open = client.is_market_open()
        print(f"✅ Market Status: {'OPEN' if is_open else 'CLOSED'}")
        
        if not is_open:
            print("⚠️  WARNING: Market is CLOSED")
            print("   - No trades will execute when market is closed")
            print("   - Market hours: 9:30 AM - 4:00 PM ET")
            return False
        
        return True
    except Exception as e:
        print(f"❌ Error checking market: {e}")
        return False

def check_2_trading_system_running():
    """Check 2: Is trading system running?"""
    print("\n" + "="*60)
    print("CHECK 2: Trading System Status")
    print("="*60)
    
    try:
        import subprocess
        result = subprocess.run(['pgrep', '-f', 'run_daily.py'], 
                              capture_output=True, text=True, timeout=2)
        
        if result.returncode == 0 and result.stdout.strip():
            print("✅ Trading system is RUNNING")
            print(f"   Process ID: {result.stdout.strip()}")
            return True
        else:
            print("❌ Trading system is NOT running")
            print("   Start with: ./start_trading.sh --paper")
            return False
    except Exception as e:
        print(f"⚠️  Cannot check process: {e}")
        # Check log file instead
        log_file = Path('logs/tradenova_daily.log')
        if log_file.exists():
            import time
            mod_time = log_file.stat().st_mtime
            if time.time() - mod_time < 300:
                print("✅ Log file recently updated (system may be running)")
                return True
        return False

def check_3_agent_signals():
    """Check 3: Are agents generating signals?"""
    print("\n" + "="*60)
    print("CHECK 3: Agent Signal Generation")
    print("="*60)
    
    try:
        client = AlpacaClient(
            Config.ALPACA_API_KEY,
            Config.ALPACA_SECRET_KEY,
            "https://paper-api.alpaca.markets"
        )
        
        orchestrator = MultiAgentOrchestrator(client)
        
        # Test with a few tickers
        test_tickers = Config.TICKERS[:3]  # Test first 3
        print(f"Testing signal generation for: {', '.join(test_tickers)}")
        
        signals_found = 0
        for ticker in test_tickers:
            try:
                # Get signals from orchestrator
                signals = orchestrator.get_signals_for_ticker(ticker)
                
                if signals:
                    print(f"✅ {ticker}: {len(signals)} signal(s) found")
                    for signal in signals[:2]:  # Show first 2
                        print(f"   - {signal.get('agent_name', 'Unknown')}: {signal.get('action', 'N/A')} "
                              f"(confidence: {signal.get('confidence', 0):.2f})")
                    signals_found += len(signals)
                else:
                    print(f"⚠️  {ticker}: No signals generated")
            except Exception as e:
                print(f"❌ {ticker}: Error - {e}")
        
        if signals_found > 0:
            print(f"\n✅ Total signals found: {signals_found}")
            return True
        else:
            print("\n⚠️  No signals generated")
            print("   Possible reasons:")
            print("   - Market conditions not favorable")
            print("   - Agents waiting for better setups")
            print("   - Risk filters blocking signals")
            return False
            
    except Exception as e:
        print(f"❌ Error checking signals: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_4_risk_manager():
    """Check 4: Is risk manager blocking trades?"""
    print("\n" + "="*60)
    print("CHECK 4: Risk Manager Status")
    print("="*60)
    
    try:
        client = AlpacaClient(
            Config.ALPACA_API_KEY,
            Config.ALPACA_SECRET_KEY,
            "https://paper-api.alpaca.markets"
        )
        
        account = client.get_account()
        equity = float(account['equity'])
        
        risk_manager = AdvancedRiskManager(
            initial_balance=equity,
            daily_loss_limit_pct=0.02,
            max_drawdown_pct=0.10,
            max_loss_streak=3
        )
        
        risk_status = risk_manager.get_risk_status()
        
        print(f"✅ Risk Manager Status:")
        print(f"   Risk Level: {risk_status['risk_level']}")
        print(f"   Daily Loss: {risk_status.get('daily_loss', 0):.2f}%")
        print(f"   Max Drawdown: {risk_status.get('max_drawdown', 0):.2f}%")
        print(f"   Loss Streak: {risk_status.get('loss_streak', 0)}")
        
        # Check if risk manager would allow trades
        can_trade = risk_manager.can_trade()
        if can_trade:
            print(f"\n✅ Risk Manager: ALLOWING trades")
        else:
            print(f"\n❌ Risk Manager: BLOCKING trades")
            print("   Reason: Risk limits exceeded")
            return False
        
        # Check position limits
        current_positions = len(client.get_positions())
        max_positions = Config.MAX_ACTIVE_TRADES
        
        print(f"\n✅ Position Limits:")
        print(f"   Current Positions: {current_positions}")
        print(f"   Max Positions: {max_positions}")
        
        if current_positions >= max_positions:
            print(f"\n⚠️  WARNING: Max positions reached ({max_positions})")
            print("   No new positions will open until existing ones close")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error checking risk manager: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_5_integrated_trader():
    """Check 5: Can IntegratedTrader execute trades?"""
    print("\n" + "="*60)
    print("CHECK 5: IntegratedTrader Status")
    print("="*60)
    
    try:
        trader = IntegratedTrader(
            rl_model_path=None,
            use_rl=False,
            dry_run=True,  # Dry run for testing
            paper_trading=True
        )
        
        print("✅ IntegratedTrader initialized")
        print(f"   Paper Trading: {trader.paper_trading}")
        print(f"   Dry Run: {trader.dry_run}")
        print(f"   Current Positions: {len(trader.positions)}")
        
        # Check if it can run a trading cycle
        try:
            print("\n✅ Testing trading cycle execution...")
            trader.run_trading_cycle()
            print("✅ Trading cycle executed successfully")
            return True
        except Exception as e:
            print(f"❌ Error in trading cycle: {e}")
            import traceback
            traceback.print_exc()
            return False
            
    except Exception as e:
        print(f"❌ Error initializing IntegratedTrader: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_6_configuration():
    """Check 6: Configuration settings"""
    print("\n" + "="*60)
    print("CHECK 6: Configuration")
    print("="*60)
    
    try:
        print(f"✅ Configuration:")
        print(f"   Tickers: {len(Config.TICKERS)} configured")
        print(f"   Max Active Trades: {Config.MAX_ACTIVE_TRADES}")
        print(f"   Position Size: {Config.POSITION_SIZE_PCT*100}%")
        print(f"   Stop Loss: {Config.STOP_LOSS_PCT*100}%")
        
        if Config.MAX_ACTIVE_TRADES <= 0:
            print("❌ ERROR: MAX_ACTIVE_TRADES is 0 or negative")
            return False
        
        if len(Config.TICKERS) == 0:
            print("❌ ERROR: No tickers configured")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error checking configuration: {e}")
        return False

def check_7_logs():
    """Check 7: Recent log entries"""
    print("\n" + "="*60)
    print("CHECK 7: Recent Log Entries")
    print("="*60)
    
    try:
        log_file = Path('logs/tradenova_daily.log')
        if not log_file.exists():
            print("⚠️  Log file not found")
            return True
        
        # Read last 50 lines
        with open(log_file, 'r') as f:
            lines = f.readlines()
            recent_lines = lines[-50:] if len(lines) > 50 else lines
        
        print(f"✅ Last {len(recent_lines)} log entries:")
        
        # Look for key patterns
        errors = [l for l in recent_lines if 'ERROR' in l or 'error' in l.lower()]
        warnings = [l for l in recent_lines if 'WARNING' in l or 'warning' in l.lower()]
        trades = [l for l in recent_lines if 'trade' in l.lower() or 'position' in l.lower()]
        
        if errors:
            print(f"\n⚠️  Found {len(errors)} error(s) in recent logs:")
            for err in errors[-5:]:  # Show last 5
                print(f"   {err.strip()}")
        
        if warnings:
            print(f"\n⚠️  Found {len(warnings)} warning(s) in recent logs:")
            for warn in warnings[-5:]:  # Show last 5
                print(f"   {warn.strip()}")
        
        if trades:
            print(f"\n✅ Found {len(trades)} trade-related log entries")
            for trade in trades[-3:]:  # Show last 3
                print(f"   {trade.strip()}")
        else:
            print("\n⚠️  No trade-related log entries found")
        
        # Show last few lines
        print(f"\n📋 Last 5 log lines:")
        for line in recent_lines[-5:]:
            print(f"   {line.strip()}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error reading logs: {e}")
        return False

def main():
    """Run all validation checks"""
    print("\n" + "="*60)
    print("TRADING EXECUTION VALIDATION")
    print("="*60)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    checks = [
        ("Market Status", check_1_market_status),
        ("Trading System Running", check_2_trading_system_running),
        ("Agent Signals", check_3_agent_signals),
        ("Risk Manager", check_4_risk_manager),
        ("IntegratedTrader", check_5_integrated_trader),
        ("Configuration", check_6_configuration),
        ("Logs", check_7_logs),
    ]
    
    results = {}
    for name, check_func in checks:
        try:
            results[name] = check_func()
        except Exception as e:
            print(f"\n❌ Exception in {name}: {e}")
            results[name] = False
    
    # Summary
    print("\n" + "="*60)
    print("VALIDATION SUMMARY")
    print("="*60)
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    failed = total - passed
    
    print(f"\nTotal Checks: {total}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    
    if failed == 0:
        print("\n✅ ALL CHECKS PASSED")
        print("\n💡 If no positions are opening, possible reasons:")
        print("   1. Market is closed (check market hours)")
        print("   2. No trading signals generated (agents waiting)")
        print("   3. Risk filters blocking trades")
        print("   4. Max positions already reached")
        print("   5. System in dry-run mode (check logs)")
    else:
        print("\n❌ SOME CHECKS FAILED")
        print("\n💡 Fix the issues above to enable trading")
    
    # Specific recommendations
    print("\n" + "="*60)
    print("RECOMMENDATIONS")
    print("="*60)
    
    if not results.get("Market Status", False):
        print("\n⚠️  Market is CLOSED")
        print("   → Wait for market hours (9:30 AM - 4:00 PM ET)")
    
    if not results.get("Trading System Running", False):
        print("\n⚠️  Trading system NOT running")
        print("   → Start with: ./start_trading.sh --paper")
    
    if not results.get("Agent Signals", False):
        print("\n⚠️  No signals generated")
        print("   → This is normal - agents wait for good setups")
        print("   → Check market conditions and agent parameters")
    
    if not results.get("Risk Manager", False):
        print("\n⚠️  Risk manager blocking trades")
        print("   → Check risk limits and daily loss")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    main()

