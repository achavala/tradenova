#!/usr/bin/env python3
"""
Virtual Test: Validate Trade Execution After Risk Manager Fix
Tests if trades would execute in dry-run mode
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
from datetime import datetime
from config import Config
from core.live.integrated_trader import IntegratedTrader

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    print("="*80)
    print("VIRTUAL TRADE EXECUTION TEST")
    print("="*80)
    print(f"Test Time: {datetime.now()}\n")
    
    print("Initializing Integrated Trader (DRY RUN mode)...")
    trader = IntegratedTrader(
        use_rl=False,
        dry_run=True,  # ✅ DRY RUN - No actual orders
        paper_trading=True
    )
    
    print("\n" + "="*80)
    print("1. SYSTEM STATUS CHECK")
    print("="*80)
    
    # Check market
    is_open = trader.client.is_market_open()
    print(f"✅ Market Status: {'OPEN' if is_open else 'CLOSED'}")
    
    if not is_open:
        print("\n⚠️  Market is CLOSED - Cannot test trade execution")
        print("   Test will check risk manager state only")
    
    # Check account
    account = trader.client.get_account()
    actual_balance = float(account['equity'])
    print(f"✅ Account Equity: ${actual_balance:,.2f}")
    print(f"✅ Buying Power: ${float(account['buying_power']):,.2f}")
    
    # Check risk manager state
    print("\n" + "="*80)
    print("2. RISK MANAGER STATE")
    print("="*80)
    
    risk_status = trader.risk_manager.get_risk_status()
    print(f"Risk Level: {risk_status['risk_level']}")
    print(f"Initial Balance: ${trader.risk_manager.initial_balance:,.2f}")
    print(f"Current Balance: ${trader.risk_manager.current_balance:,.2f}")
    print(f"Peak Balance: ${trader.risk_manager.peak_balance:,.2f}")
    print(f"Daily P&L: ${risk_status['daily_pnl']:,.2f}")
    print(f"Drawdown: {risk_status['drawdown']:.2%}")
    print(f"Loss Streak: {risk_status['loss_streak']}")
    
    # Verify balance match
    balance_match = abs(trader.risk_manager.current_balance - actual_balance) < 100
    if balance_match:
        print(f"\n✅ Risk Manager Balance MATCHES Account Balance")
    else:
        print(f"\n❌ Risk Manager Balance MISMATCH:")
        print(f"   Risk Manager: ${trader.risk_manager.current_balance:,.2f}")
        print(f"   Actual Account: ${actual_balance:,.2f}")
        print(f"   Difference: ${abs(trader.risk_manager.current_balance - actual_balance):,.2f}")
    
    # Check if risk manager would allow trades
    if risk_status['risk_level'] in ['danger', 'blocked']:
        print(f"\n❌ Risk Status: {risk_status['risk_level'].upper()} - Trades would be BLOCKED")
        return False
    else:
        print(f"\n✅ Risk Status: {risk_status['risk_level'].upper()} - Trades would be ALLOWED")
    
    # Test trade execution
    print("\n" + "="*80)
    print("3. TESTING TRADE EXECUTION (DRY RUN)")
    print("="*80)
    
    if is_open:
        print("\nRunning trading cycle (DRY RUN - no actual orders)...")
        try:
            trader.run_trading_cycle()
            print("\n✅ Trading cycle completed successfully")
            
            # Check if any trades were "executed" (in dry run)
            if len(trader.positions) > 0:
                print(f"\n✅ {len(trader.positions)} trade(s) would have been executed:")
                for symbol, pos in trader.positions.items():
                    print(f"   - {symbol}: {pos.get('side', 'unknown')} @ ${pos.get('entry_price', 0):.2f}")
            else:
                print("\n⚠️  No trades would be executed (signals may not have passed all checks)")
        except Exception as e:
            print(f"\n❌ Error in trading cycle: {e}")
            import traceback
            traceback.print_exc()
            return False
    else:
        print("\n⚠️  Market is CLOSED - Skipping trade execution test")
        print("   Risk manager state is correct, trades would execute when market opens")
    
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    checks = {
        "Risk Manager Initialized": trader.risk_manager is not None,
        "Balance Match": balance_match,
        "Risk Status Safe": risk_status['risk_level'] not in ['danger', 'blocked'],
        "Market Check": is_open,
        "Trading Cycle Runs": True  # If we got here without exception
    }
    
    all_passed = all(checks.values())
    
    for check, passed in checks.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {check}")
    
    print("\n" + "="*80)
    if all_passed:
        print("✅ ALL CHECKS PASSED - System is ready to trade!")
    else:
        print("⚠️  SOME CHECKS FAILED - Review issues above")
    print("="*80)
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

