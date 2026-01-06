#!/usr/bin/env python3
"""System Validation Script"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import Config
from alpaca_client import AlpacaClient
from core.live.trading_scheduler import TradingScheduler

def main():
    print("="*80)
    print("TRADENOVA COMPREHENSIVE SYSTEM VALIDATION")
    print("="*80)

    # 1. Configuration
    print("\n📋 CONFIGURATION:")
    print(f"   MAX_CONTRACTS_PER_TRADE: {Config.MAX_CONTRACTS_PER_TRADE}")
    print(f"   MAX_POSITION_PCT: {Config.MAX_POSITION_PCT*100}%")
    print(f"   MAX_PORTFOLIO_HEAT: {Config.MAX_PORTFOLIO_HEAT*100}%")
    print(f"   STOP_LOSS_PCT: {Config.STOP_LOSS_PCT*100}%")
    print(f"   MIN_DTE: {Config.MIN_DTE} days")
    print(f"   MAX_DTE: {Config.MAX_DTE} days")
    print(f"   Tickers: {len(Config.TICKERS)} symbols")

    # 2. Alpaca connection
    print("\n🔌 ALPACA CONNECTION:")
    client = AlpacaClient(paper=True)
    account = client.get_account()
    clock = client.api.get_clock()
    print("   ✅ Connected")
    equity = float(account["equity"])
    buying_power = float(account["buying_power"])
    print(f"   Equity: ${equity:,.2f}")
    print(f"   Buying Power: ${buying_power:,.2f}")
    print(f"   Market Open: {clock.is_open}")

    # 3. Positions
    print("\n📊 CURRENT POSITIONS:")
    positions = client.get_positions()
    total_pnl = 0
    if positions:
        for pos in positions:
            symbol = pos['symbol']
            qty = float(pos['qty'])
            pnl = float(pos['unrealized_pl'])
            pct = float(pos['unrealized_plpc']) * 100
            total_pnl += pnl
            status = "🟢" if pnl >= 0 else "🔴"
            print(f"   {status} {symbol}: {qty:.0f} @ P&L ${pnl:,.2f} ({pct:+.1f}%)")
    else:
        print("   No open positions")
    print(f"   Total Positions: {len(positions)}")
    print(f"   Total Unrealized P&L: ${total_pnl:,.2f}")

    # 4. Scheduler
    print("\n⏰ SCHEDULER STATUS:")
    scheduler = TradingScheduler()
    print(f"   Is Market Hours (ET): {scheduler.is_market_hours()}")
    print(f"   Is Pre-Market: {scheduler.is_pre_market()}")
    print(f"   Is After-Hours: {scheduler.is_after_hours()}")

    # 5. Calculate position capital
    print("\n💰 POSITION SIZING CHECK:")
    max_position = equity * Config.MAX_POSITION_PCT
    print(f"   Account Equity: ${equity:,.2f}")
    print(f"   Max Position (10%): ${max_position:,.2f}")
    print(f"   Max Contracts Cap: {Config.MAX_CONTRACTS_PER_TRADE}")
    print(f"   Affordable contracts at $0.10: {int(max_position / 10)}")
    print(f"   Affordable contracts at $1.00: {int(max_position / 100)}")
    print(f"   Affordable contracts at $5.00: {int(max_position / 500)}")

    # 6. Recent orders
    print("\n📝 RECENT ORDERS (last 10):")
    orders = client.get_orders(status='all', limit=10)
    for order in orders[:10]:
        symbol = order.get('symbol', 'N/A')
        side = order.get('side', 'N/A')
        status = order.get('status', 'N/A')
        qty = order.get('filled_qty') or order.get('qty', 0)
        created = str(order.get('created_at', ''))[:19]
        print(f"   {created}: {side.upper()} {qty} {symbol} - {status}")

    # 7. Issues check
    print("\n⚠️  POTENTIAL ISSUES:")
    issues = []
    
    # Check if max contracts is too restrictive
    if max_position / 100 < Config.MAX_CONTRACTS_PER_TRADE:
        issues.append(f"Position capital (${max_position:.0f}) may not afford {Config.MAX_CONTRACTS_PER_TRADE} contracts of expensive options")
    
    # Check if positions have large losses
    for pos in positions:
        pct = float(pos['unrealized_plpc']) * 100
        if pct <= -20:
            issues.append(f"{pos['symbol']} is at {pct:.1f}% loss - should trigger stop-loss")
    
    if issues:
        for issue in issues:
            print(f"   ⚠️  {issue}")
    else:
        print("   ✅ No critical issues detected")

    print("\n" + "="*80)
    print("✅ VALIDATION COMPLETE")
    print("="*80)

if __name__ == "__main__":
    main()

