#!/usr/bin/env python3
"""
Detailed Analysis: Why Positions with 100%+ Profit Are Not Being Closed
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from alpaca_client import AlpacaClient
from config import Config

def main():
    print("="*80)
    print("DETAILED PROFIT MANAGEMENT ANALYSIS")
    print("="*80)
    
    client = AlpacaClient(paper=True)
    positions = client.get_positions()
    
    # Current Profit Target Configuration
    print("\n" + "="*80)
    print("📋 CURRENT PROFIT TARGET CONFIGURATION")
    print("="*80)
    print(f"""
    TP1: +{Config.TP1_PCT*100:.0f}% profit → Exit {Config.TP1_EXIT_PCT*100:.0f}% of position
    TP2: +{Config.TP2_PCT*100:.0f}% profit → Exit {Config.TP2_EXIT_PCT*100:.0f}% of remaining
    TP3: +{Config.TP3_PCT*100:.0f}% profit → Exit {Config.TP3_EXIT_PCT*100:.0f}% of remaining
    TP4: +{Config.TP4_PCT*100:.0f}% profit → Exit {Config.TP4_EXIT_PCT*100:.0f}% of remaining
    TP5: +{Config.TP5_PCT*100:.0f}% profit → Exit {Config.TP5_EXIT_PCT*100:.0f}% (FULL EXIT)
    
    Trailing Stop Activation: +{Config.TRAILING_STOP_ACTIVATION_PCT*100:.0f}%
    Trailing Stop Lock-in: +{Config.TRAILING_STOP_MIN_PROFIT_PCT*100:.0f}%
    Stop Loss: -{Config.STOP_LOSS_PCT*100:.0f}%
    """)
    
    # Analyze each position
    print("\n" + "="*80)
    print("📊 DETAILED POSITION ANALYSIS")
    print("="*80)
    
    for pos in positions:
        symbol = pos['symbol']
        qty = int(float(pos['qty']))
        entry = float(pos['avg_entry_price'])
        current = float(pos['current_price'])
        pnl_pct = float(pos['unrealized_plpc']) * 100
        pnl_dollar = float(pos['unrealized_pl'])
        
        print(f"\n{'='*60}")
        print(f"📈 {symbol}")
        print(f"{'='*60}")
        print(f"   Quantity: {qty} contracts")
        print(f"   Entry Price: ${entry:.2f}")
        print(f"   Current Price: ${current:.2f}")
        print(f"   P&L: ${pnl_dollar:,.2f} ({pnl_pct:+.1f}%)")
        
        # Which TP should have triggered?
        print(f"\n   📍 PROFIT TARGET ANALYSIS:")
        if pnl_pct >= 200:
            print(f"   ⚠️  TP5 ({Config.TP5_PCT*100:.0f}%) SHOULD HAVE TRIGGERED - FULL EXIT!")
        elif pnl_pct >= 150:
            print(f"   ⚠️  TP4 ({Config.TP4_PCT*100:.0f}%) SHOULD HAVE TRIGGERED")
        elif pnl_pct >= 100:
            print(f"   ⚠️  TP3 ({Config.TP3_PCT*100:.0f}%) SHOULD HAVE TRIGGERED")
        elif pnl_pct >= 60:
            print(f"   ⚠️  TP2 ({Config.TP2_PCT*100:.0f}%) SHOULD HAVE TRIGGERED")
        elif pnl_pct >= 40:
            print(f"   ⚠️  TP1 ({Config.TP1_PCT*100:.0f}%) SHOULD HAVE TRIGGERED")
        elif pnl_pct <= -20:
            print(f"   🔴 STOP LOSS SHOULD HAVE TRIGGERED!")
        else:
            print(f"   ✅ No profit target hit yet")
        
        # Why it wasn't triggered
        print(f"\n   ❓ WHY NOT TRIGGERED:")
        print(f"   The ProfitManager only tracks positions added to its")
        print(f"   internal dictionary via add_position(). If the trading")
        print(f"   system was RESTARTED after these positions were opened,")
        print(f"   they are NOT being monitored for profit targets.")
        print(f"   ")
        print(f"   The _monitor_positions() function iterates ONLY over")
        print(f"   self.positions (in-memory), NOT actual Alpaca positions.")
    
    # System Flow
    print("\n" + "="*80)
    print("🔄 CURRENT SYSTEM FLOW")
    print("="*80)
    print("""
    ┌─────────────────────────────────────────────────────────────────┐
    │                    TRADING CYCLE                                 │
    └─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
    ┌─────────────────────────────────────────────────────────────────┐
    │  1. run_trading_cycle()                                          │
    │     - Gets account info                                          │
    │     - Calls _monitor_positions()                                 │
    │     - Calls _check_stop_losses()                                 │
    │     - Calls _scan_and_trade()                                    │
    └─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
    ┌─────────────────────────────────────────────────────────────────┐
    │  2. _monitor_positions()                                         │
    │     ⚠️  PROBLEM: Only monitors self.positions (in-memory dict)   │
    │     - Does NOT sync with actual Alpaca positions                 │
    │     - Lost on system restart                                     │
    └─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
    ┌─────────────────────────────────────────────────────────────────┐
    │  3. ProfitManager.check_exits()                                  │
    │     ⚠️  PROBLEM: Only checks positions in profit_manager.positions│
    │     - TP1-TP5 levels configured but NOT applied to orphan trades │
    └─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
    ┌─────────────────────────────────────────────────────────────────┐
    │  4. _check_stop_losses()                                         │
    │     ✅ WORKS: Fetches live positions from Alpaca                 │
    │     - Checks -20% threshold against actual positions             │
    └─────────────────────────────────────────────────────────────────┘

    ═══════════════════════════════════════════════════════════════════
                              🔴 THE ROOT CAUSE
    ═══════════════════════════════════════════════════════════════════
    
    The STOP-LOSS logic queries Alpaca directly:
        positions = self.client.get_positions()
    
    The PROFIT-TAKING logic queries in-memory dictionary:
        for symbol, position_info in list(self.positions.items()):
    
    On system restart, self.positions is EMPTY, so profit targets
    are NEVER checked for existing positions!
    """)
    
    # Solution
    print("\n" + "="*80)
    print("✅ RECOMMENDED FIX")
    print("="*80)
    print("""
    1. Add _sync_positions_from_alpaca() method that:
       - Fetches all positions from Alpaca
       - Adds any missing positions to self.positions
       - Adds any missing positions to profit_manager
    
    2. Call sync on startup and periodically
    
    3. Implement profit-taking in _check_stop_losses() style:
       - Query Alpaca directly
       - Apply TP logic to ALL positions
    """)
    
    print("\n" + "="*80)

if __name__ == "__main__":
    main()

