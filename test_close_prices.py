#!/usr/bin/env python3
"""Check close_price values for NVDA options"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from alpaca_client import AlpacaClient
from config import Config
from services.options_data_feed import OptionsDataFeed

client = AlpacaClient(Config.ALPACA_API_KEY, Config.ALPACA_SECRET_KEY, Config.ALPACA_BASE_URL)
feed = OptionsDataFeed(client)

chain = feed.get_options_chain("NVDA")
current_price = client.get_latest_price("NVDA")

print(f"NVDA Current Price: ${current_price:.2f}")
print(f"\nChecking CALL options with close_price in range $0.20-$10.00:")
print("="*80)

count = 0
for c in chain[:50]:  # Check first 50
    if isinstance(c, dict):
        option_type = c.get('type', '').lower()
        strike = float(c.get('strike_price', 0))
        close = float(c.get('close_price', 0)) if c.get('close_price') else 0
        dte_str = c.get('expiration_date', 'N/A')
        symbol = c.get('symbol', 'N/A')
    else:
        option_type = (getattr(c, 'type', '') or '').lower()
        strike = float(getattr(c, 'strike_price', 0))
        close = float(getattr(c, 'close_price', 0)) if getattr(c, 'close_price', None) else 0
        dte_str = str(getattr(c, 'expiration_date', 'N/A'))
        symbol = getattr(c, 'symbol', 'N/A')
    
    if option_type == 'call' and 0.20 <= close <= 10.00:
        count += 1
        itm_otm = "ITM" if strike < current_price else "OTM"
        print(f"  ✅ {symbol[:20]:20s} | Strike: ${strike:6.2f} ({itm_otm:3s}) | Close: ${close:6.2f} | Expiry: {dte_str}")

print(f"\nFound {count} CALL options with close_price in $0.20-$10.00 range")

