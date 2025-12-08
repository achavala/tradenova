#!/usr/bin/env python3
"""
Test Alpaca Paper Trading Connection
Run this before first paper trading day
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from alpaca_client import AlpacaClient
from config import Config

def test_paper_connection():
    """Test Alpaca paper trading connection"""
    print("="*60)
    print("ALPACA PAPER TRADING CONNECTION TEST")
    print("="*60)
    print()
    
    # Test 1: Configuration
    print("1. Testing configuration...")
    try:
        Config.validate()
        print("   ✅ Configuration valid")
    except Exception as e:
        print(f"   ❌ Configuration error: {e}")
        return False
    print()
    
    # Test 2: Paper API Connection
    print("2. Testing paper API connection...")
    try:
        paper_url = "https://paper-api.alpaca.markets"
        client = AlpacaClient(
            Config.ALPACA_API_KEY,
            Config.ALPACA_SECRET_KEY,
            paper_url
        )
        print(f"   ✅ Client initialized with paper URL: {paper_url}")
    except Exception as e:
        print(f"   ❌ Connection error: {e}")
        return False
    print()
    
    # Test 3: Account Status
    print("3. Testing account status...")
    try:
        account = client.get_account()
        print(f"   ✅ Account Status: {account.get('status', 'UNKNOWN')}")
        print(f"   ✅ Account Equity: ${float(account.get('equity', 0)):,.2f}")
        print(f"   ✅ Buying Power: ${float(account.get('buying_power', 0)):,.2f}")
        print(f"   ✅ Paper Trading: {account.get('pattern_day_trader', False)}")
    except Exception as e:
        print(f"   ❌ Account error: {e}")
        return False
    print()
    
    # Test 4: Market Clock
    print("4. Testing market clock...")
    try:
        clock = client.api.get_clock()
        print(f"   ✅ Market Status: {clock.is_open}")
        print(f"   ✅ Current Time: {clock.timestamp}")
        if clock.is_open:
            print(f"   ✅ Market is OPEN")
        else:
            print(f"   ℹ️  Market is CLOSED (expected if outside hours)")
    except Exception as e:
        print(f"   ❌ Clock error: {e}")
        return False
    print()
    
    # Test 5: Positions
    print("5. Checking existing positions...")
    try:
        positions = client.get_positions()
        print(f"   ✅ Open Positions: {len(positions)}")
        if len(positions) > 0:
            print("   ⚠️  Warning: You have open positions")
            for pos in positions:
                # Handle both dict and object formats
                symbol = pos.get('symbol') if isinstance(pos, dict) else getattr(pos, 'symbol', 'UNKNOWN')
                qty = pos.get('qty') if isinstance(pos, dict) else getattr(pos, 'qty', 0)
                print(f"      - {symbol}: {qty} shares")
        else:
            print("   ✅ No open positions (clean start)")
    except Exception as e:
        print(f"   ❌ Positions error: {e}")
        return False
    print()
    
    # Test 6: Orders
    print("6. Checking pending orders...")
    try:
        orders = client.api.list_orders(status='open')
        print(f"   ✅ Pending Orders: {len(orders)}")
        if len(orders) > 0:
            print("   ⚠️  Warning: You have pending orders")
            for order in orders:
                print(f"      - {order.symbol}: {order.side} {order.qty} @ {order.type}")
        else:
            print("   ✅ No pending orders (clean start)")
    except Exception as e:
        print(f"   ❌ Orders error: {e}")
        return False
    print()
    
    print("="*60)
    print("✅ ALL TESTS PASSED - PAPER TRADING READY")
    print("="*60)
    print()
    print("You can proceed with:")
    print("  python run_daily.py --paper")
    print()
    
    return True

if __name__ == '__main__':
    success = test_paper_connection()
    sys.exit(0 if success else 1)

