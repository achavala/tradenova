#!/usr/bin/env python3
"""
PHASE A VALIDATION: Execution Layer Correctness
Validates that all execution components are wired correctly
"""
import sys
import os
from pathlib import Path
from datetime import datetime
import json

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def print_section(title):
    print(f"\n{'='*70}")
    print(f" {title}")
    print('='*70)

def print_check(name, passed, details=""):
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"  {status}: {name}")
    if details:
        print(f"         {details}")

def validate_options_broker_client():
    """Validate OptionsBrokerClient signature and behavior"""
    print_section("1. VALIDATING OptionsBrokerClient")
    
    all_passed = True
    
    # Check import
    try:
        from core.live.options_broker_client import OptionsBrokerClient
        print_check("Import OptionsBrokerClient", True)
    except Exception as e:
        print_check("Import OptionsBrokerClient", False, str(e))
        return False
    
    # Check constructor signature
    import inspect
    sig = inspect.signature(OptionsBrokerClient.__init__)
    params = list(sig.parameters.keys())
    
    expected_params = ['self', 'alpaca_client']
    if params == expected_params:
        print_check("Constructor signature", True, f"params: {params}")
    else:
        print_check("Constructor signature", False, f"Expected {expected_params}, got {params}")
        all_passed = False
    
    # Check place_option_order signature
    sig = inspect.signature(OptionsBrokerClient.place_option_order)
    params = list(sig.parameters.keys())
    
    if 'option_symbol' in params:
        print_check("place_option_order uses 'option_symbol'", True)
    elif 'symbol' in params:
        print_check("place_option_order uses 'option_symbol'", False, "Uses 'symbol' instead - may cause confusion")
        all_passed = False
    
    return all_passed

def validate_broker_executor():
    """Validate BrokerExecutor signature and behavior"""
    print_section("2. VALIDATING BrokerExecutor")
    
    all_passed = True
    
    # Check import
    try:
        from core.live.broker_executor import BrokerExecutor
        print_check("Import BrokerExecutor", True)
    except Exception as e:
        print_check("Import BrokerExecutor", False, str(e))
        return False
    
    # Check execute_market_order signature
    import inspect
    sig = inspect.signature(BrokerExecutor.execute_market_order)
    params = list(sig.parameters.keys())
    
    if 'is_option' in params:
        print_check("execute_market_order has 'is_option' param", True)
    else:
        print_check("execute_market_order has 'is_option' param", False)
        all_passed = False
    
    # Check execute_limit_order signature
    sig = inspect.signature(BrokerExecutor.execute_limit_order)
    params = list(sig.parameters.keys())
    
    if 'is_option' in params:
        print_check("execute_limit_order has 'is_option' param", True)
    else:
        print_check("execute_limit_order has 'is_option' param", False)
        all_passed = False
    
    return all_passed

def validate_integrated_trader():
    """Validate IntegratedTrader execution paths"""
    print_section("3. VALIDATING IntegratedTrader Execution Paths")
    
    all_passed = True
    
    # Check source code for correct patterns
    integrated_trader_path = Path(__file__).parent.parent / 'core' / 'live' / 'integrated_trader.py'
    
    if not integrated_trader_path.exists():
        print_check("IntegratedTrader file exists", False)
        return False
    
    print_check("IntegratedTrader file exists", True)
    
    content = integrated_trader_path.read_text()
    
    # Check for correct OptionsBrokerClient initialization
    if "OptionsBrokerClient(self.client)" in content:
        print_check("OptionsBrokerClient initialized with self.client", True)
    else:
        print_check("OptionsBrokerClient initialized with self.client", False, 
                   "May be passing wrong arguments")
        all_passed = False
    
    # Check for is_option=True in execute_market_order calls
    if "is_option=True" in content:
        print_check("execute_market_order called with is_option=True", True)
    else:
        print_check("execute_market_order called with is_option=True", False)
        all_passed = False
    
    # Check for option_symbol parameter usage
    if "option_symbol=symbol" in content or "option_symbol=" in content:
        print_check("place_option_order uses option_symbol parameter", True)
    else:
        print_check("place_option_order uses option_symbol parameter", False)
        all_passed = False
    
    return all_passed

def validate_option_symbol_handling():
    """Validate option symbol format handling"""
    print_section("4. VALIDATING Option Symbol Handling")
    
    all_passed = True
    
    # Check for O: prefix handling
    integrated_trader_path = Path(__file__).parent.parent / 'core' / 'live' / 'integrated_trader.py'
    content = integrated_trader_path.read_text()
    
    if "replace('O:', '')" in content:
        print_check("Massive O: prefix stripped from symbols", True)
    else:
        print_check("Massive O: prefix stripped from symbols", False, 
                   "May send invalid symbols to Alpaca")
        all_passed = False
    
    # Check for symbol validation before execution
    if "if not option_symbol:" in content:
        print_check("Null option_symbol check before execution", True)
    else:
        print_check("Null option_symbol check before execution", False)
        all_passed = False
    
    # Test symbol format validation
    test_symbols = [
        ("NVDA250117C00140000", True, "Valid Alpaca format"),
        ("O:NVDA250117C00140000", False, "Massive format - needs stripping"),
        ("NVDA", False, "Stock symbol - not options"),
        ("", False, "Empty symbol"),
    ]
    
    print("\n  Option Symbol Format Tests:")
    for symbol, expected_valid, description in test_symbols:
        # Alpaca options format: [SYMBOL][YYMMDD][C/P][STRIKE*1000]
        is_option = len(symbol) > 10 and any(c in symbol for c in ['C', 'P'])
        has_prefix = symbol.startswith('O:')
        
        if has_prefix:
            clean_symbol = symbol.replace('O:', '')
            status = "⚠️  NEEDS CLEANING"
        elif is_option and not has_prefix:
            status = "✅ VALID"
        elif symbol == "":
            status = "❌ EMPTY"
        else:
            status = "⚠️  NOT OPTION"
        
        print(f"    {status}: '{symbol}' - {description}")
    
    return all_passed

def validate_price_routing():
    """Validate options price routing (Massive for pricing, Alpaca for execution)"""
    print_section("5. VALIDATING Price Routing")
    
    all_passed = True
    
    integrated_trader_path = Path(__file__).parent.parent / 'core' / 'live' / 'integrated_trader.py'
    content = integrated_trader_path.read_text()
    
    # Check for Massive as primary price source
    if "massive_price_feed" in content.lower() or "massive" in content.lower():
        print_check("Massive API referenced for data", True)
    else:
        print_check("Massive API referenced for data", False)
        all_passed = False
    
    # Check for quote fallback logic
    if "Fallback to Alpaca" in content or "fallback" in content.lower():
        print_check("Fallback logic for pricing exists", True)
    else:
        print_check("Fallback logic for pricing exists", False)
        all_passed = False
    
    # Check for close_price fallback
    if "close_price" in content:
        print_check("close_price fallback for options pricing", True)
    else:
        print_check("close_price fallback for options pricing", False)
        all_passed = False
    
    return all_passed

def validate_execution_fail_safe():
    """Validate execution fail-safe mechanisms"""
    print_section("6. VALIDATING Execution Fail-Safes")
    
    all_passed = True
    
    broker_executor_path = Path(__file__).parent.parent / 'core' / 'live' / 'broker_executor.py'
    content = broker_executor_path.read_text()
    
    # Check for retry logic
    if "retry" in content.lower() and "max_retries" in content:
        print_check("Retry logic with max_retries", True)
    else:
        print_check("Retry logic with max_retries", False)
        all_passed = False
    
    # Check for exponential backoff
    if "exponential" in content.lower() or "backoff" in content.lower():
        print_check("Exponential backoff", True)
    else:
        print_check("Exponential backoff", False)
        all_passed = False
    
    # Check for non-retryable error detection
    if "non_retryable" in content.lower() or "invalid symbol" in content.lower():
        print_check("Non-retryable error detection", True)
    else:
        print_check("Non-retryable error detection", False)
        all_passed = False
    
    # Check for logging on failures
    if "logger.error" in content:
        print_check("Error logging on failures", True)
    else:
        print_check("Error logging on failures", False)
        all_passed = False
    
    return all_passed

def check_recent_logs():
    """Check recent logs for execution errors"""
    print_section("7. CHECKING RECENT LOGS FOR EXECUTION ERRORS")
    
    log_path = Path(__file__).parent.parent / 'logs' / 'tradenova_daily.log'
    
    if not log_path.exists():
        print("  ⚠️  No daily log file found")
        return True
    
    # Read last 500 lines
    with open(log_path, 'r') as f:
        lines = f.readlines()[-500:]
    
    error_patterns = [
        ("unexpected keyword argument", "API signature mismatch"),
        ("invalid symbol", "Symbol format error"),
        ("Error placing", "Order placement failure"),
        ("Error executing", "Execution failure"),
        ("TypeError", "Type error in code"),
        ("AttributeError", "Missing attribute"),
    ]
    
    errors_found = {}
    for line in lines:
        for pattern, description in error_patterns:
            if pattern.lower() in line.lower():
                if pattern not in errors_found:
                    errors_found[pattern] = 0
                errors_found[pattern] += 1
    
    if errors_found:
        print("  ⚠️  EXECUTION ERRORS DETECTED:")
        for pattern, count in errors_found.items():
            print(f"      - '{pattern}': {count} occurrences")
        return False
    else:
        print("  ✅ No execution errors in recent logs")
        return True

def run_live_validation():
    """Attempt live validation with Alpaca (paper)"""
    print_section("8. LIVE API VALIDATION (Paper Account)")
    
    try:
        from alpaca_client import AlpacaClient
        from config import Config
        
        client = AlpacaClient(
            api_key=Config.ALPACA_API_KEY,
            secret_key=Config.ALPACA_SECRET_KEY,
            base_url=Config.ALPACA_BASE_URL
        )
        
        # Test account access
        account = client.get_account()
        print_check("Alpaca account access", True, f"Equity: ${float(account['equity']):,.2f}")
        
        # Test positions access
        positions = client.get_positions()
        option_positions = [p for p in positions if len(p['symbol']) > 10]
        print_check("Position retrieval", True, f"{len(option_positions)} option positions")
        
        # Test orders access
        orders = client.get_orders(status='all', limit=10)
        print_check("Order history retrieval", True, f"{len(orders)} recent orders")
        
        return True
        
    except Exception as e:
        print_check("Live API validation", False, str(e))
        return False

def main():
    print("\n" + "="*70)
    print(" PHASE A VALIDATION: EXECUTION LAYER CORRECTNESS")
    print(" Goal: 'Trades always execute correctly or fail safely'")
    print("="*70)
    
    results = {}
    
    # Run all validations
    results['options_broker_client'] = validate_options_broker_client()
    results['broker_executor'] = validate_broker_executor()
    results['integrated_trader'] = validate_integrated_trader()
    results['symbol_handling'] = validate_option_symbol_handling()
    results['price_routing'] = validate_price_routing()
    results['fail_safes'] = validate_execution_fail_safe()
    results['recent_logs'] = check_recent_logs()
    results['live_api'] = run_live_validation()
    
    # Summary
    print_section("VALIDATION SUMMARY")
    
    all_passed = all(results.values())
    passed_count = sum(results.values())
    total_count = len(results)
    
    print(f"\n  Results: {passed_count}/{total_count} checks passed\n")
    
    for check_name, passed in results.items():
        status = "✅" if passed else "❌"
        print(f"    {status} {check_name.replace('_', ' ').title()}")
    
    print("\n" + "="*70)
    if all_passed:
        print(" ✅ PHASE A VALIDATION: ALL CHECKS PASSED")
        print(" Execution layer is correctly wired.")
    else:
        print(" ❌ PHASE A VALIDATION: ISSUES DETECTED")
        print(" Review failed checks above and fix before trading.")
    print("="*70 + "\n")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())

