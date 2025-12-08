#!/usr/bin/env python3
"""Check current positions"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from config import Config
from alpaca_client import AlpacaClient
from core.live.options_broker_client import OptionsBrokerClient

client = AlpacaClient(Config.ALPACA_API_KEY, Config.ALPACA_SECRET_KEY, Config.ALPACA_BASE_URL)
options_client = OptionsBrokerClient(client)

positions = client.get_positions()
option_positions = options_client.get_all_option_positions()

print('='*70)
print('CURRENT POSITIONS SUMMARY')
print('='*70)
print(f'\nStock Positions: {len(positions)}')
for pos in positions:
    print(f'  {pos["symbol"]}: {pos["qty"]} @ ${pos["avg_entry_price"]:.2f} | P/L: ${pos["unrealized_pl"]:.2f}')

print(f'\nOptions Positions: {len(option_positions)}')
for pos in option_positions:
    print(f'  {pos["symbol"]}: {pos["qty"]} @ ${pos["avg_entry_price"]:.2f} | P/L: ${pos["unrealized_pl"]:.2f}')

print('\n✅ All positions confirmed!')

