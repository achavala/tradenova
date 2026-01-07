#!/usr/bin/env python3
"""
Comprehensive Trading Analysis for Today
Analyzes all trades, P&L strategy, and system flow
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from alpaca_client import AlpacaClient
from config import Config
from datetime import datetime, timedelta
import pytz

def main():
    client = AlpacaClient(paper=True)
    et = pytz.timezone('America/New_York')
    today = datetime.now(et).strftime('%Y-%m-%d')

    print("="*80)
    print(f"COMPREHENSIVE TRADING ANALYSIS - {today}")
    print("="*80)

    # Get all orders from today
    orders = client.get_orders(status='all', limit=100)
    today_orders = [o for o in orders if str(o.get('created_at', ''))[:10] == today]

    print(f"\n📊 TOTAL ORDERS TODAY: {len(today_orders)}")
    print("="*80)

    # Separate by status
    filled = [o for o in today_orders if o.get('status') == 'filled']
    canceled = [o for o in today_orders if o.get('status') == 'canceled']
    pending = [o for o in today_orders if o.get('status') not in ['filled', 'canceled']]

    print(f"   Filled: {len(filled)}")
    print(f"   Canceled: {len(canceled)}")
    print(f"   Pending: {len(pending)}")

    # Detailed order analysis
    print("\n" + "="*80)
    print("📋 DETAILED ORDER HISTORY (Chronological)")
    print("="*80)

    buy_orders = {}
    sell_orders = {}

    for order in sorted(today_orders, key=lambda x: x.get('created_at', '')):
        symbol = order.get('symbol', 'N/A')
        side = order.get('side', 'N/A').upper()
        qty = order.get('filled_qty') or order.get('qty', 0)
        status = order.get('status', 'N/A')
        created = str(order.get('created_at', ''))[:19]
        filled_price = order.get('filled_avg_price')
        order_type = order.get('type', 'N/A')
        
        # Track buys and sells
        if status == 'filled':
            if side == 'BUY':
                buy_orders[symbol] = {'qty': float(qty), 'price': float(filled_price) if filled_price else 0, 'time': created}
            else:
                sell_orders[symbol] = {'qty': float(qty), 'price': float(filled_price) if filled_price else 0, 'time': created}
        
        # Determine action type
        if side == 'BUY':
            action = "🟢 OPENED"
        else:
            action = "🔴 CLOSED"
        
        print(f"\n{created} | {action} | {symbol}")
        print(f"   Side: {side} | Qty: {qty} | Status: {status}")
        if filled_price:
            print(f"   Fill Price: ${float(filled_price):.2f}")
        print(f"   Order Type: {order_type}")

    # Calculate realized P&L for closed trades
    print("\n" + "="*80)
    print("💵 REALIZED P&L (Closed Trades Today)")
    print("="*80)
    
    total_realized = 0
    for symbol in sell_orders:
        if symbol in buy_orders:
            buy = buy_orders[symbol]
            sell = sell_orders[symbol]
            qty = min(buy['qty'], sell['qty'])
            pnl = (sell['price'] - buy['price']) * qty * 100  # Options are 100 shares
            total_realized += pnl
            pnl_pct = ((sell['price'] - buy['price']) / buy['price']) * 100 if buy['price'] > 0 else 0
            
            print(f"\n{symbol}")
            print(f"   Buy: ${buy['price']:.2f} @ {buy['time']}")
            print(f"   Sell: ${sell['price']:.2f} @ {sell['time']}")
            print(f"   Qty: {int(qty)}")
            print(f"   P&L: ${pnl:,.2f} ({pnl_pct:+.1f}%)")
    
    if total_realized != 0:
        print(f"\n{'='*40}")
        print(f"TOTAL REALIZED P&L: ${total_realized:,.2f}")
    else:
        print("\n   No closed trades with matching buys today")

    # Current positions
    print("\n" + "="*80)
    print("📊 CURRENT OPEN POSITIONS")
    print("="*80)

    positions = client.get_positions()
    total_unrealized = 0
    total_cost = 0

    for pos in positions:
        symbol = pos['symbol']
        qty = int(float(pos['qty']))
        entry = float(pos['avg_entry_price'])
        current = float(pos['current_price'])
        pnl = float(pos['unrealized_pl'])
        pnl_pct = float(pos['unrealized_plpc']) * 100
        cost = float(pos['cost_basis'])
        market_value = float(pos['market_value'])
        
        total_unrealized += pnl
        total_cost += cost
        
        # Status indicator
        if pnl_pct >= 100:
            status = "🚀 TP3 HIT (100%+) - SHOULD TAKE 10%"
        elif pnl_pct >= 60:
            status = "📈 TP2 HIT (60%+) - SHOULD TAKE 20%"
        elif pnl_pct >= 40:
            status = "📈 TP1 HIT (40%+) - SHOULD TAKE 50%"
        elif pnl_pct >= 20:
            status = "🟢 Good profit - HOLD"
        elif pnl_pct >= 0:
            status = "🟡 Small profit - HOLD"
        elif pnl_pct >= -15:
            status = "🟠 Small loss - HOLD"
        elif pnl_pct >= -20:
            status = "⚠️ Approaching SL - MONITOR"
        else:
            status = "🔴 STOP LOSS TRIGGERED - SHOULD CLOSE"
        
        print(f"\n{'='*60}")
        print(f"📈 {symbol}")
        print(f"{'='*60}")
        print(f"   Qty: {qty} contracts")
        print(f"   Entry: ${entry:.2f} → Current: ${current:.2f}")
        print(f"   Cost Basis: ${cost:,.2f}")
        print(f"   Market Value: ${market_value:,.2f}")
        print(f"   P&L: ${pnl:,.2f} ({pnl_pct:+.1f}%)")
        print(f"   Status: {status}")
        
        # What should happen next
        print(f"\n   📋 DECISION LOGIC:")
        if pnl_pct >= 100:
            exit_qty = max(1, int(qty * 0.10))
            print(f"      → TP3 triggered: Exit {exit_qty} of {qty} contracts (10%)")
            print(f"      → Reason: Lock in 100%+ gains")
        elif pnl_pct >= 60:
            exit_qty = max(1, int(qty * 0.20))
            print(f"      → TP2 triggered: Exit {exit_qty} of {qty} contracts (20%)")
            print(f"      → Reason: Lock in 60%+ gains")
        elif pnl_pct >= 40:
            exit_qty = max(1, int(qty * 0.50))
            print(f"      → TP1 triggered: Exit {exit_qty} of {qty} contracts (50%)")
            print(f"      → Reason: Lock in 40%+ gains")
        elif pnl_pct <= -20:
            print(f"      → STOP LOSS: Exit ALL {qty} contracts")
            print(f"      → Reason: Loss exceeds -20% threshold")
        else:
            print(f"      → HOLD: No exit trigger")
            if pnl_pct > 0:
                print(f"      → Next target: TP1 at +40% (currently {pnl_pct:.1f}%)")
            else:
                print(f"      → Monitor: Stop loss at -20% (currently {pnl_pct:.1f}%)")

    print(f"\n{'='*80}")
    print(f"TOTAL UNREALIZED P&L: ${total_unrealized:,.2f}")
    print(f"TOTAL COST BASIS: ${total_cost:,.2f}")
    print(f"{'='*80}")

    # Account summary
    account = client.get_account()
    equity = float(account['equity'])
    last_equity = float(account.get('last_equity', equity))
    today_pnl = equity - last_equity
    
    print("\n" + "="*80)
    print("💰 ACCOUNT SUMMARY")
    print("="*80)
    print(f"   Equity: ${equity:,.2f}")
    print(f"   Cash: ${float(account['cash']):,.2f}")
    print(f"   Buying Power: ${float(account['buying_power']):,.2f}")
    print(f"   Today's Equity Change: ${today_pnl:,.2f}")

    # P&L Strategy
    print("\n" + "="*80)
    print("📋 P&L STRATEGY CONFIGURATION")
    print("="*80)
    print(f"""
    PROFIT TARGETS (Partial Exits):
    ┌─────────────────────────────────────────────────────────────┐
    │ TP1: +{Config.TP1_PCT*100:.0f}% profit → Exit {Config.TP1_EXIT_PCT*100:.0f}% of position            │
    │ TP2: +{Config.TP2_PCT*100:.0f}% profit → Exit {Config.TP2_EXIT_PCT*100:.0f}% of remaining           │
    │ TP3: +{Config.TP3_PCT*100:.0f}% profit → Exit {Config.TP3_EXIT_PCT*100:.0f}% of remaining           │
    │ TP4: +{Config.TP4_PCT*100:.0f}% profit → Exit {Config.TP4_EXIT_PCT*100:.0f}% of remaining          │
    │ TP5: +{Config.TP5_PCT*100:.0f}% profit → Exit {Config.TP5_EXIT_PCT*100:.0f}% (FULL EXIT)           │
    └─────────────────────────────────────────────────────────────┘
    
    STOP LOSS:
    ┌─────────────────────────────────────────────────────────────┐
    │ Trigger: -{Config.STOP_LOSS_PCT*100:.0f}% loss → Exit 100% of position        │
    └─────────────────────────────────────────────────────────────┘
    
    TRAILING STOP (after TP4):
    ┌─────────────────────────────────────────────────────────────┐
    │ Activates at: +{Config.TRAILING_STOP_ACTIVATION_PCT*100:.0f}%                               │
    │ Locks in minimum: +{Config.TRAILING_STOP_MIN_PROFIT_PCT*100:.0f}% profit                    │
    └─────────────────────────────────────────────────────────────┘
    
    POSITION LIMITS:
    ┌─────────────────────────────────────────────────────────────┐
    │ Max contracts per trade: {Config.MAX_CONTRACTS_PER_TRADE}                          │
    │ Max position size: {Config.MAX_POSITION_PCT*100:.0f}% of portfolio                   │
    │ Max portfolio heat: {Config.MAX_PORTFOLIO_HEAT*100:.0f}%                             │
    │ DTE range: {Config.MIN_DTE}-{Config.MAX_DTE} days                                    │
    └─────────────────────────────────────────────────────────────┘
    """)

    # System flow
    print("\n" + "="*80)
    print("🔄 SYSTEM FLOW - HOW DECISIONS ARE MADE")
    print("="*80)
    print("""
    ┌─────────────────────────────────────────────────────────────────────────────┐
    │                         TRADING CYCLE (Every 5 min)                          │
    └─────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
    ┌─────────────────────────────────────────────────────────────────────────────┐
    │  1. CHECK MARKET STATUS                                                      │
    │     - Is market open? (9:30 AM - 4:00 PM ET)                                 │
    │     - Is it a trading day?                                                   │
    └─────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
    ┌─────────────────────────────────────────────────────────────────────────────┐
    │  2. CHECK STOP LOSSES (queries Alpaca directly)                              │
    │     ┌───────────────────────────────────────────────────────────────────┐   │
    │     │ For each position:                                                 │   │
    │     │   IF unrealized_plpc <= -20%:                                      │   │
    │     │     → SELL ALL contracts (market order)                            │   │
    │     │     → Log: "🔴 STOP-LOSS TRIGGERED"                                │   │
    │     │   ELIF unrealized_plpc <= -15%:                                    │   │
    │     │     → Log: "⚠️ Approaching stop-loss"                              │   │
    │     └───────────────────────────────────────────────────────────────────┘   │
    └─────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
    ┌─────────────────────────────────────────────────────────────────────────────┐
    │  3. CHECK PROFIT TARGETS (queries Alpaca directly)                           │
    │     ┌───────────────────────────────────────────────────────────────────┐   │
    │     │ For each position with profit > 0:                                 │   │
    │     │   IF unrealized_plpc >= 100%:                                      │   │
    │     │     → SELL 10% (TP3)                                               │   │
    │     │   ELIF unrealized_plpc >= 60%:                                     │   │
    │     │     → SELL 20% (TP2)                                               │   │
    │     │   ELIF unrealized_plpc >= 40%:                                     │   │
    │     │     → SELL 50% (TP1)                                               │   │
    │     │   → Log: "🎯 PROFIT TARGET HIT"                                    │   │
    │     └───────────────────────────────────────────────────────────────────┘   │
    └─────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
    ┌─────────────────────────────────────────────────────────────────────────────┐
    │  4. SCAN FOR NEW TRADES (if positions < MAX_ACTIVE_TRADES)                   │
    │     ┌───────────────────────────────────────────────────────────────────┐   │
    │     │ For each ticker (NVDA, AAPL, TSLA, META, GOOG, MSFT, AMZN, etc):   │   │
    │     │   a. Run signal agents (EMA, Trend, MeanReversion, etc)            │   │
    │     │   b. If high-confidence signal found:                              │   │
    │     │      - Check portfolio heat (< 35%)                                │   │
    │     │      - Check position size (< 10% of portfolio)                    │   │
    │     │      - Find liquid option with DTE 0-14                            │   │
    │     │      - Calculate contract qty (max 10)                             │   │
    │     │      - Place BUY order                                             │   │
    │     │      → Log: "✅ EXECUTING TRADE"                                   │   │
    │     └───────────────────────────────────────────────────────────────────┘   │
    └─────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
    ┌─────────────────────────────────────────────────────────────────────────────┐
    │  5. LOG STATUS                                                               │
    │     → Balance, Positions, Risk Level, Daily P&L                              │
    └─────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
                               (Wait 5 minutes)
                                        │
                                        ▼
                               (Repeat cycle)
    """)

    # Log locations
    print("\n" + "="*80)
    print("📁 LOG FILES")
    print("="*80)
    print("""
    Main Trading Log:
    → /Users/chavala/TradeNova/logs/tradenova_daily.log
    
    Key log entries to look for:
    ┌─────────────────────────────────────────────────────────────────────────────┐
    │ 🟢 Trade Opens:                                                              │
    │    "✅ EXECUTING TRADE: {SYMBOL} {DIRECTION}"                               │
    │    "Options order placed: buy {qty} {symbol}"                               │
    │                                                                              │
    │ 🔴 Stop Loss:                                                                │
    │    "🔴 STOP-LOSS TRIGGERED for {symbol}"                                    │
    │    "✅ STOP-LOSS EXECUTED: Sold {qty} {symbol}"                             │
    │                                                                              │
    │ 🎯 Profit Taking:                                                            │
    │    "🎯 PROFIT TARGET HIT for {symbol}"                                      │
    │    "✅ PROFIT TAKEN: Sold {qty} {symbol} @ {TP level}"                      │
    │                                                                              │
    │ 📊 Status:                                                                   │
    │    "Status: Balance=${equity}, Positions={n}, Risk={level}"                 │
    │    "TRADING CYCLE COMPLETED"                                                │
    └─────────────────────────────────────────────────────────────────────────────┘
    """)

if __name__ == "__main__":
    main()

