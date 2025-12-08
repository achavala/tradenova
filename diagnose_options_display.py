#!/usr/bin/env python3
"""
Diagnose Options Display
Detailed analysis of why options positions are/aren't showing in dashboard
"""
import logging
import sys
from pathlib import Path
from datetime import datetime, date
import re

sys.path.insert(0, str(Path(__file__).parent))

from alpaca_client import AlpacaClient
from config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def parse_option_symbol(symbol: str):
    """
    Parse Alpaca option symbol format: TICKER + YYMMDD + C/P + STRIKE
    Example: AAPL251205C00150000 = AAPL, Dec 5 2025, Call, $150 strike
    """
    pattern = r'^([A-Z]{1,5})(\d{6})([CP])(\d{8})$'
    match = re.match(pattern, symbol)
    
    if not match:
        return None
    
    underlying = match.group(1)
    date_str = match.group(2)
    option_type = 'CALL' if match.group(3) == 'C' else 'PUT'
    strike_str = match.group(4)
    
    try:
        year = 2000 + int(date_str[0:2])
        month = int(date_str[2:4])
        day = int(date_str[4:6])
        expiry_date = datetime(year, month, day).date()
    except:
        return None
    
    try:
        strike = float(strike_str) / 1000.0
    except:
        return None
    
    return {
        'underlying': underlying,
        'expiry_date': expiry_date,
        'option_type': option_type,
        'strike': strike
    }

def diagnose_options_display():
    """Comprehensive diagnosis of options display"""
    print("="*80)
    print("🔍 OPTIONS DISPLAY DIAGNOSIS")
    print("="*80)
    print()
    
    # Initialize client
    client = AlpacaClient(
        Config.ALPACA_API_KEY,
        Config.ALPACA_SECRET_KEY,
        Config.ALPACA_BASE_URL
    )
    
    # Get all positions
    print("1️⃣  FETCHING ALL POSITIONS FROM ALPACA")
    print("="*80)
    positions = client.get_positions()
    print(f"Total positions in account: {len(positions)}")
    print()
    
    if not positions:
        print("❌ NO POSITIONS FOUND in Alpaca account")
        print("   → This is why the dashboard shows no options")
        print("   → The system needs to execute option trades first")
        return
    
    # Display criteria
    print("2️⃣  DISPLAY CRITERIA")
    print("="*80)
    print(f"✅ Must be an OPTION (not a stock)")
    print(f"✅ Underlying must be in: {Config.TICKERS}")
    print(f"✅ DTE must be: 0-30 days")
    print(f"✅ Must not be expired (DTE >= 0)")
    print()
    
    # Analyze each position
    print("3️⃣  POSITION ANALYSIS")
    print("="*80)
    
    today = date.today()
    options_found = 0
    options_shown = 0
    stocks_found = 0
    
    for i, pos in enumerate(positions, 1):
        symbol = pos['symbol']
        qty = pos['qty']
        side = pos['side']
        entry_price = pos['avg_entry_price']
        current_price = pos['current_price']
        unrealized_pl = pos['unrealized_pl']
        
        print(f"\n📊 Position #{i}: {symbol}")
        print(f"   Quantity: {qty} | Side: {side.upper()}")
        print(f"   Entry: ${entry_price:.2f} | Current: ${current_price:.2f} | P/L: ${unrealized_pl:.2f}")
        
        # Parse option symbol
        option_info = parse_option_symbol(symbol)
        
        if not option_info:
            # This is a stock
            stocks_found += 1
            print(f"   ❌ TYPE: STOCK (not an option)")
            print(f"   ❌ REASON: Symbol doesn't match option format (TICKER+YYMMDD+C/P+STRIKE)")
            print(f"   ❌ RESULT: Filtered out (dashboard only shows options)")
            continue
        
        # It's an option
        options_found += 1
        underlying = option_info['underlying']
        expiry_date = option_info['expiry_date']
        option_type = option_info['option_type']
        strike = option_info['strike']
        days_to_expiry = (expiry_date - today).days
        
        print(f"   ✅ TYPE: OPTION")
        print(f"   📋 Details: {underlying} {option_type} ${strike:.2f} Strike")
        print(f"   📅 Expiry: {expiry_date} ({days_to_expiry} days to expiry)")
        
        # Check criteria
        criteria_met = []
        criteria_failed = []
        
        # Criterion 1: Underlying in TICKERS
        if underlying in Config.TICKERS:
            criteria_met.append(f"✅ Underlying '{underlying}' is in configured tickers")
        else:
            criteria_failed.append(f"❌ Underlying '{underlying}' NOT in configured tickers: {Config.TICKERS}")
        
        # Criterion 2: DTE >= 0 (not expired)
        if days_to_expiry >= 0:
            criteria_met.append(f"✅ Not expired ({days_to_expiry} DTE >= 0)")
        else:
            criteria_failed.append(f"❌ Expired ({days_to_expiry} DTE < 0)")
        
        # Criterion 3: DTE <= 30
        if days_to_expiry <= 30:
            criteria_met.append(f"✅ Within DTE range ({days_to_expiry} DTE <= 30)")
        else:
            criteria_failed.append(f"❌ Outside DTE range ({days_to_expiry} DTE > 30)")
        
        # Summary
        if len(criteria_failed) == 0:
            options_shown += 1
            print(f"   ✅ ALL CRITERIA MET - WILL BE DISPLAYED")
        else:
            print(f"   ❌ FILTERED OUT:")
            for reason in criteria_failed:
                print(f"      {reason}")
    
    # Summary
    print()
    print("="*80)
    print("4️⃣  SUMMARY")
    print("="*80)
    print(f"Total Positions: {len(positions)}")
    print(f"  • Stocks: {stocks_found}")
    print(f"  • Options: {options_found}")
    print(f"  • Options that will display: {options_shown}")
    print(f"  • Options filtered out: {options_found - options_shown}")
    print()
    
    if options_shown == 0:
        print("⚠️  WHY NO OPTIONS ARE DISPLAYED:")
        print()
        
        if options_found == 0:
            print("❌ NO OPTIONS FOUND")
            print("   → All positions are stocks (not options)")
            print("   → The trading system needs to execute option trades")
            print("   → Check if the system is configured to trade options")
        else:
            print(f"❌ {options_found} OPTIONS FOUND BUT ALL FILTERED OUT")
            print()
            print("Common reasons:")
            print("  1. Underlying not in configured tickers")
            print("     → Add the underlying to Config.TICKERS")
            print("  2. DTE outside 0-30 day range")
            print("     → Options have >30 days to expiry or are expired")
            print("  3. Option symbol parsing failed")
            print("     → Symbol format doesn't match expected pattern")
    else:
        print(f"✅ {options_shown} OPTIONS WILL BE DISPLAYED")
        print("   → Refresh dashboard to see them")
    
    print()
    print("="*80)
    print("5️⃣  RECOMMENDATIONS")
    print("="*80)
    
    if options_found == 0:
        print("To see options in dashboard:")
        print("  1. Ensure trading system is configured to trade options")
        print("  2. Check integrated_trader.py - is it executing option trades?")
        print("  3. Verify options_broker_client.py is being used")
        print("  4. Check logs for option trade execution")
    elif options_shown == 0:
        print("To fix filtering:")
        if any(parse_option_symbol(p['symbol']) and parse_option_symbol(p['symbol'])['underlying'] not in Config.TICKERS for p in positions):
            print("  1. Add missing underlying tickers to Config.TICKERS")
        if any(parse_option_symbol(p['symbol']) and (parse_option_symbol(p['symbol'])['expiry_date'] - today).days > 30 for p in positions if parse_option_symbol(p['symbol'])):
            print("  2. Consider increasing DTE range if needed (currently 0-30)")
    
    print()
    print("="*80)

if __name__ == '__main__':
    diagnose_options_display()

