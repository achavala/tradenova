#!/usr/bin/env python3
"""Test positions display"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from alpaca_client import AlpacaClient
from config import Config

client = AlpacaClient(
    Config.ALPACA_API_KEY,
    Config.ALPACA_SECRET_KEY,
    Config.ALPACA_BASE_URL
)

positions = client.get_positions()
print(f'Found {len(positions)} positions:')
for pos in positions:
    print(f"  {pos['symbol']}: {pos['qty']} @ ${pos['avg_entry_price']:.2f} | P/L: ${pos['unrealized_pl']:.2f} ({pos['unrealized_plpc']*100:.2f}%)")

