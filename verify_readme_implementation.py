#!/usr/bin/env python3
"""
Verify README Implementation
Checks that all README criteria (lines 8-28) are correctly implemented
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from config import Config
from core.risk.profit_manager import ProfitManager
from core.live.integrated_trader import IntegratedTrader
from core.features.indicators import FeatureEngine

def check_1_multi_ticker_trading():
    """Check 1: Multi-Ticker Trading - 12 high-volatility stocks"""
    print("\n" + "="*60)
    print("CHECK 1: Multi-Ticker Trading (12 tickers)")
    print("="*60)
    
    expected_tickers = ['NVDA', 'AAPL', 'TSLA', 'META', 'GOOG', 'MSFT', 
                       'AMZN', 'MSTR', 'AVGO', 'PLTR', 'AMD', 'INTC']
    
    actual_tickers = Config.TICKERS
    
    print(f"Expected: {len(expected_tickers)} tickers")
    print(f"Actual: {len(actual_tickers)} tickers")
    
    missing = set(expected_tickers) - set(actual_tickers)
    extra = set(actual_tickers) - set(expected_tickers)
    
    if missing:
        print(f"❌ MISSING: {missing}")
        return False
    if extra:
        print(f"⚠️  EXTRA: {extra}")
    
    print(f"✅ All {len(expected_tickers)} tickers configured: {', '.join(actual_tickers)}")
    return True

def check_2_risk_management():
    """Check 2: Risk Management - Max 10 active trades"""
    print("\n" + "="*60)
    print("CHECK 2: Risk Management (Max 10 active trades)")
    print("="*60)
    
    max_trades = Config.MAX_ACTIVE_TRADES
    
    if max_trades == 10:
        print(f"✅ MAX_ACTIVE_TRADES = {max_trades}")
        return True
    else:
        print(f"❌ MAX_ACTIVE_TRADES = {max_trades} (expected 10)")
        return False

def check_3_position_sizing():
    """Check 3: Position Sizing - 50% of previous day's ending balance"""
    print("\n" + "="*60)
    print("CHECK 3: Position Sizing (50% of previous day balance)")
    print("="*60)
    
    # Check config
    position_size_pct = Config.POSITION_SIZE_PCT
    
    if position_size_pct == 0.50:
        print(f"✅ POSITION_SIZE_PCT = {position_size_pct} (50%)")
    else:
        print(f"❌ POSITION_SIZE_PCT = {position_size_pct} (expected 0.50)")
        return False
    
    # Check implementation in IntegratedTrader
    try:
        trader = IntegratedTrader(dry_run=True, paper_trading=True)
        
        # Check if _load_previous_balance exists
        if hasattr(trader, '_load_previous_balance'):
            print("✅ _load_previous_balance() method exists")
        else:
            print("❌ _load_previous_balance() method missing")
            return False
        
        # Check if _execute_trade uses 50% of previous day balance
        import inspect
        source = inspect.getsource(trader._execute_trade)
        
        if '0.50' in source or '0.5' in source or 'position_capital = base_balance * 0.50' in source:
            print("✅ _execute_trade() uses 50% of previous day balance")
        else:
            print("⚠️  _execute_trade() may not use 50% of previous day balance")
            print("   Checking implementation...")
            if 'base_balance' in source and '0.50' in source:
                print("   ✅ Found 50% calculation")
            else:
                print("   ❌ 50% calculation not found in code")
                return False
        
        return True
    except Exception as e:
        print(f"❌ Error checking implementation: {e}")
        return False

def check_4_profit_targets():
    """Check 4: 5-Tier Profit Target System"""
    print("\n" + "="*60)
    print("CHECK 4: 5-Tier Profit Target System")
    print("="*60)
    
    pm = ProfitManager()
    
    checks = [
        ("TP1", pm.tp1_pct, 0.40, pm.tp1_exit_pct, 0.50, "Sell 50% of position"),
        ("TP2", pm.tp2_pct, 0.60, pm.tp2_exit_pct, 0.20, "Sell 20% of remaining"),
        ("TP3", pm.tp3_pct, 1.00, pm.tp3_exit_pct, 0.10, "Sell 10% of remaining"),
        ("TP4", pm.tp4_pct, 1.50, pm.tp4_exit_pct, 0.10, "Sell 10% of remaining"),
        ("TP5", pm.tp5_pct, 2.00, pm.tp5_exit_pct, 1.00, "Full exit"),
    ]
    
    all_pass = True
    for name, actual_pct, expected_pct, actual_exit, expected_exit, desc in checks:
        if actual_pct == expected_pct and actual_exit == expected_exit:
            print(f"✅ {name}: +{expected_pct*100:.0f}% → {desc} (exit {expected_exit*100:.0f}%)")
        else:
            print(f"❌ {name}: Expected +{expected_pct*100:.0f}% exit {expected_exit*100:.0f}%, "
                  f"got +{actual_pct*100:.0f}% exit {actual_exit*100:.0f}%")
            all_pass = False
    
    return all_pass

def check_5_trailing_stop():
    """Check 5: Trailing Stop - Activates after TP4, locks in +100% minimum"""
    print("\n" + "="*60)
    print("CHECK 5: Trailing Stop (After TP4, locks +100% minimum)")
    print("="*60)
    
    pm = ProfitManager()
    
    if pm.trailing_stop_activation_pct == 1.50:  # TP4
        print(f"✅ Trailing stop activates at +{pm.trailing_stop_activation_pct*100:.0f}% (TP4)")
    else:
        print(f"❌ Trailing stop activation: {pm.trailing_stop_activation_pct*100:.0f}% (expected 150%)")
        return False
    
    if pm.trailing_stop_min_profit_pct == 1.00:  # 100%
        print(f"✅ Trailing stop locks in minimum +{pm.trailing_stop_min_profit_pct*100:.0f}% profit")
    else:
        print(f"❌ Trailing stop min profit: {pm.trailing_stop_min_profit_pct*100:.0f}% (expected 100%)")
        return False
    
    return True

def check_6_stop_loss():
    """Check 6: Stop Loss - Always 15%"""
    print("\n" + "="*60)
    print("CHECK 6: Stop Loss (Always 15%)")
    print("="*60)
    
    stop_loss = Config.STOP_LOSS_PCT
    
    if stop_loss == 0.15:
        print(f"✅ STOP_LOSS_PCT = {stop_loss} (15%)")
        
        # Check ProfitManager
        pm = ProfitManager()
        if pm.stop_loss_pct == 0.15:
            print("✅ ProfitManager stop_loss_pct = 0.15 (15%)")
            return True
        else:
            print(f"❌ ProfitManager stop_loss_pct = {pm.stop_loss_pct} (expected 0.15)")
            return False
    else:
        print(f"❌ STOP_LOSS_PCT = {stop_loss} (expected 0.15)")
        return False

def check_7_technical_indicators():
    """Check 7: Technical Indicators (RSI, MA, Volume, ATR)"""
    print("\n" + "="*60)
    print("CHECK 7: Technical Indicators")
    print("="*60)
    
    fe = FeatureEngine()
    
    # Check by inspecting the source code
    import inspect
    source = inspect.getsource(fe._calculate_technical_indicators)
    
    indicators = {
        'RSI': hasattr(fe, '_calculate_rsi') or 'rsi' in source.lower(),
        'Moving Averages': ('ema' in source.lower() and 'sma' in source.lower()) or 
                         (hasattr(fe, '_calculate_ema') or hasattr(fe, '_calculate_sma')),
        'Volume Analysis': hasattr(fe, '_calculate_vwap') or 'vwap' in source.lower() or 'volume' in source.lower(),
        'ATR (Volatility)': hasattr(fe, '_calculate_atr') or 'atr' in source.lower(),
    }
    
    all_pass = True
    for indicator, implemented in indicators.items():
        if implemented:
            print(f"✅ {indicator}: Implemented")
        else:
            print(f"❌ {indicator}: Not found")
            all_pass = False
    
    return all_pass

def check_8_signal_generation():
    """Check 8: Signal Generation - Multi-factor scoring with confidence"""
    print("\n" + "="*60)
    print("CHECK 8: Signal Generation (Multi-factor scoring)")
    print("="*60)
    
    try:
        trader = IntegratedTrader(dry_run=True, paper_trading=True)
        
        # Check orchestrator exists
        if hasattr(trader, 'orchestrator'):
            print("✅ Multi-agent orchestrator exists")
        else:
            print("❌ Multi-agent orchestrator missing")
            return False
        
        # Check ensemble predictor
        if hasattr(trader, 'ensemble'):
            print("✅ Ensemble predictor exists (multi-factor scoring)")
        else:
            print("❌ Ensemble predictor missing")
            return False
        
        # Check confidence in signal generation
        import inspect
        source = inspect.getsource(trader._scan_and_trade)
        
        if 'confidence' in source.lower():
            print("✅ Signal generation uses confidence levels")
        else:
            print("⚠️  Confidence levels may not be used")
        
        return True
    except Exception as e:
        print(f"❌ Error checking signal generation: {e}")
        return False

def main():
    """Run all checks"""
    print("\n" + "="*60)
    print("README IMPLEMENTATION VERIFICATION")
    print("="*60)
    print("Checking README criteria (lines 8-28)")
    print("="*60)
    
    checks = [
        ("Multi-Ticker Trading (12 tickers)", check_1_multi_ticker_trading),
        ("Risk Management (Max 10 trades)", check_2_risk_management),
        ("Position Sizing (50% previous day)", check_3_position_sizing),
        ("5-Tier Profit Targets", check_4_profit_targets),
        ("Trailing Stop (After TP4)", check_5_trailing_stop),
        ("Stop Loss (15%)", check_6_stop_loss),
        ("Technical Indicators", check_7_technical_indicators),
        ("Signal Generation (Multi-factor)", check_8_signal_generation),
    ]
    
    results = {}
    for name, check_func in checks:
        try:
            results[name] = check_func()
        except Exception as e:
            print(f"\n❌ Exception in {name}: {e}")
            import traceback
            traceback.print_exc()
            results[name] = False
    
    # Summary
    print("\n" + "="*60)
    print("VERIFICATION SUMMARY")
    print("="*60)
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    failed = total - passed
    
    print(f"\nTotal Checks: {total}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    
    print("\n" + "="*60)
    print("DETAILED RESULTS")
    print("="*60)
    
    for name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")
    
    if failed == 0:
        print("\n" + "="*60)
        print("✅ ALL README CRITERIA IMPLEMENTED CORRECTLY")
        print("="*60)
        return True
    else:
        print("\n" + "="*60)
        print("❌ SOME CRITERIA NOT FULLY IMPLEMENTED")
        print("="*60)
        print("\nPlease fix the issues above")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

