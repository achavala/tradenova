#!/usr/bin/env python3
"""Test profit-taking logic"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from alpaca_client import AlpacaClient
from core.live.options_broker_client import OptionsBrokerClient
from config import Config
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')

def main():
    client = AlpacaClient(paper=True)
    positions = client.get_positions()

    # Profit target levels
    tp1_pct = Config.TP1_PCT  # 40%
    tp2_pct = Config.TP2_PCT  # 60%
    tp3_pct = Config.TP3_PCT  # 100%

    tp1_exit = Config.TP1_EXIT_PCT  # 50%
    tp2_exit = Config.TP2_EXIT_PCT  # 20%
    tp3_exit = Config.TP3_EXIT_PCT  # 10%

    print(f"\nProfit Target Configuration:")
    print(f"  TP1: {tp1_pct*100}% → Exit {tp1_exit*100}%")
    print(f"  TP2: {tp2_pct*100}% → Exit {tp2_exit*100}%")
    print(f"  TP3: {tp3_pct*100}% → Exit {tp3_exit*100}%")
    print("\n" + "="*60)

    for pos in positions:
        symbol = pos['symbol']
        pnl_pct = float(pos['unrealized_plpc'])
        pnl = float(pos['unrealized_pl'])
        qty = int(float(pos['qty']))
        
        if pnl_pct <= 0 or qty <= 0:
            continue
        
        exit_qty = 0
        tp_level = ""
        
        if pnl_pct >= tp3_pct:
            exit_qty = max(1, int(qty * tp3_exit))
            tp_level = "TP3 (100%+)"
        elif pnl_pct >= tp2_pct:
            exit_qty = max(1, int(qty * tp2_exit))
            tp_level = "TP2 (60%+)"
        elif pnl_pct >= tp1_pct:
            exit_qty = max(1, int(qty * tp1_exit))
            tp_level = "TP1 (40%+)"
        
        if exit_qty > 0:
            print(f"\n🎯 PROFIT TARGET HIT: {symbol}")
            print(f"   Profit: {pnl_pct*100:.1f}% (${pnl:.2f})")
            print(f"   Level: {tp_level}")
            print(f"   Exit: {exit_qty} of {qty} contracts")
            
            # Execute
            options_client = OptionsBrokerClient(client)
            result = options_client.place_option_order(
                option_symbol=symbol,
                qty=exit_qty,
                side='sell',
                order_type='market'
            )
            if result:
                print(f"   ✅ SOLD {exit_qty} contracts")
            else:
                print(f"   ❌ Failed to sell")

    print("\n" + "="*60)
    print("Profit-taking complete!")

if __name__ == "__main__":
    main()

