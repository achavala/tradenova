#!/usr/bin/env python3
"""
Test Gap Risk Monitor
Validates gap risk detection and trade restrictions
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
from datetime import date, timedelta
from core.risk.gap_risk_monitor import GapRiskMonitor, GapRiskLevel
from core.risk.advanced_risk_manager import AdvancedRiskManager
from config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_gap_risk_monitor():
    """Test Gap Risk Monitor"""
    
    print("="*80)
    print("GAP RISK MONITOR TEST")
    print("="*80)
    print()
    
    monitor = GapRiskMonitor()
    
    # Test 1: Add earnings dates
    print("TEST 1: Add Earnings Dates")
    print("-" * 80)
    
    today = date.today()
    
    # Add earnings for NVDA (today)
    monitor.add_earnings_date('NVDA', today)
    print(f"✅ Added earnings for NVDA: {today}")
    
    # Add earnings for AAPL (tomorrow)
    monitor.add_earnings_date('AAPL', today + timedelta(days=1))
    print(f"✅ Added earnings for AAPL: {today + timedelta(days=1)}")
    
    # Add earnings for TSLA (3 days away)
    monitor.add_earnings_date('TSLA', today + timedelta(days=3))
    print(f"✅ Added earnings for TSLA: {today + timedelta(days=3)}")
    
    # Add earnings for META (7 days away)
    monitor.add_earnings_date('META', today + timedelta(days=7))
    print(f"✅ Added earnings for META: {today + timedelta(days=7)}")
    
    print()
    
    # Test 2: Check gap risk
    print("TEST 2: Check Gap Risk")
    print("-" * 80)
    
    test_symbols = ['NVDA', 'AAPL', 'TSLA', 'META', 'GOOG']
    
    for symbol in test_symbols:
        risk_level, reason, details = monitor.get_gap_risk(symbol)
        
        print(f"{symbol}:")
        print(f"  Risk Level: {risk_level.value.upper()}")
        print(f"  Reason: {reason}")
        
        if details.get('earnings_days_away') is not None:
            print(f"  Earnings: {details['earnings_days_away']} days away")
        
        print(f"  Position Size Multiplier: {details['position_size_multiplier']:.0%}")
        print(f"  Block New Trades: {'❌ YES' if details['block_new_trades'] else '✅ NO'}")
        print(f"  Force Exit: {'⚠️  YES' if details['force_exit'] else '✅ NO'}")
        print()
    
    # Test 3: Trade allowance
    print("TEST 3: Trade Allowance")
    print("-" * 80)
    
    for symbol in test_symbols:
        can_trade, reason = monitor.can_trade(symbol)
        status = "✅ ALLOWED" if can_trade else "❌ BLOCKED"
        print(f"{symbol}: {status}")
        if not can_trade:
            print(f"  Reason: {reason}")
    
    print()
    
    # Test 4: Position size multipliers
    print("TEST 4: Position Size Multipliers")
    print("-" * 80)
    
    base_size = 1000.0
    
    for symbol in test_symbols:
        multiplier = monitor.get_position_size_multiplier(symbol)
        adjusted_size = base_size * multiplier
        print(f"{symbol}: ${base_size:.2f} → ${adjusted_size:.2f} ({multiplier:.0%})")
    
    print()
    
    # Test 5: Macro events
    print("TEST 5: Macro Events")
    print("-" * 80)
    
    # Add FOMC meeting (tomorrow)
    monitor.add_macro_event(
        today + timedelta(days=1),
        'FOMC',
        'Federal Open Market Committee Meeting'
    )
    print(f"✅ Added FOMC meeting: {today + timedelta(days=1)}")
    
    # Add CPI release (3 days away)
    monitor.add_macro_event(
        today + timedelta(days=3),
        'CPI',
        'Consumer Price Index Release'
    )
    print(f"✅ Added CPI release: {today + timedelta(days=3)}")
    
    # Check macro risk
    risk_level, reason, details = monitor._check_macro_risk(today)
    if risk_level != GapRiskLevel.NONE:
        print(f"\nMacro Risk: {risk_level.value.upper()}")
        print(f"Reason: {reason}")
        print(f"Position Size Multiplier: {details['position_size_multiplier']:.0%}")
        print(f"Block New Trades: {'❌ YES' if details['block_new_trades'] else '✅ NO'}")
    else:
        print("\nNo macro risk detected")
    
    print()
    
    # Test 6: Risk Manager Integration
    print("TEST 6: Risk Manager Integration")
    print("-" * 80)
    
    risk_manager = AdvancedRiskManager(
        initial_balance=100000,
        use_iv_regimes=True
    )
    
    if risk_manager.use_gap_risk:
        print("✅ Gap Risk Monitor enabled in Risk Manager")
        
        # Test trade allowance with gap risk
        for symbol in ['NVDA', 'AAPL', 'TSLA']:
            allowed, reason, risk_level = risk_manager.check_trade_allowed(
                symbol=symbol,
                qty=100,
                price=100.0,
                side='buy'
            )
            
            status = "✅ ALLOWED" if allowed else "❌ BLOCKED"
            print(f"{symbol}: {status}")
            if not allowed:
                print(f"  Reason: {reason}")
            
            # Get gap risk status
            gap_status = risk_manager.get_gap_risk_status(symbol)
            print(f"  Gap Risk: {gap_status['risk_level']}")
            print(f"  Size Multiplier: {gap_status['position_size_multiplier']:.0%}")
        
        # Test position size adjustment
        print("\nPosition Size Adjustments:")
        base_size = 1000.0
        for symbol in ['NVDA', 'AAPL', 'TSLA']:
            final_size = risk_manager.get_final_position_size(symbol, base_size)
            print(f"{symbol}: ${base_size:.2f} → ${final_size:.2f}")
        
        # Test force exit
        print("\nForce Exit Checks:")
        for symbol in ['NVDA', 'AAPL', 'TSLA']:
            should_exit = risk_manager.should_force_exit_position(symbol)
            status = "⚠️  YES" if should_exit else "✅ NO"
            print(f"{symbol}: {status}")
    else:
        print("❌ Gap Risk Monitor not enabled")
    
    print()
    
    # Test 7: All risks for all tickers
    print("TEST 7: All Risks for All Tickers")
    print("-" * 80)
    
    all_risks = monitor.get_all_risks(Config.TICKERS)
    
    for symbol, risk_info in sorted(all_risks.items()):
        if risk_info['risk_level'] != 'none':
            print(f"{symbol}: {risk_info['risk_level'].upper()}")
            print(f"  {risk_info['reason']}")
            print(f"  Size Multiplier: {risk_info['position_size_multiplier']:.0%}")
    
    print()
    
    print("="*80)
    print("✅ GAP RISK MONITOR TEST COMPLETE")
    print("="*80)
    
    return True

if __name__ == "__main__":
    success = test_gap_risk_monitor()
    sys.exit(0 if success else 1)

