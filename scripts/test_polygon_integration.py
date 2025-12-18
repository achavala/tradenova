#!/usr/bin/env python3
"""
Test Polygon.io Options Data Integration
Validates that Polygon API integration works correctly
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
from datetime import datetime, timedelta
from services.polygon_options_feed import PolygonOptionsFeed
from config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_polygon_feed():
    """Test Polygon options feed"""
    print("="*80)
    print("POLYGON.IO OPTIONS DATA FEED TEST")
    print("="*80)
    print()
    
    # Initialize feed
    feed = PolygonOptionsFeed()
    
    if not feed.is_available():
        print("❌ Polygon API key not configured")
        print()
        print("To configure:")
        print("1. Sign up at https://polygon.io/")
        print("2. Get your API key from dashboard")
        print("3. Add to .env file: POLYGON_API_KEY=your_key_here")
        print()
        return False
    
    print("✅ Polygon API key configured")
    print()
    
    # Test 1: Get expiration dates
    print("Test 1: Getting expiration dates for NVDA...")
    symbol = "NVDA"
    expirations = feed.get_expiration_dates(symbol)
    
    if expirations:
        print(f"✅ Found {len(expirations)} expiration dates")
        print(f"   First 5: {expirations[:5]}")
    else:
        print("⚠️  No expiration dates found (API may be rate-limited or symbol not available)")
    print()
    
    # Test 2: Get options chain
    print("Test 2: Getting options chain for NVDA...")
    chain = feed.get_options_chain(symbol)  # Get all contracts (will be paginated)
    
    if chain:
        print(f"✅ Retrieved {len(chain)} option contracts")
        if chain:
            sample = chain[0]
            print(f"   Sample contract:")
            print(f"     Ticker: {sample.get('ticker', 'N/A')}")
            print(f"     Strike: {sample.get('strike_price', 'N/A')}")
            print(f"     Expiration: {sample.get('expiration_date', 'N/A')}")
            print(f"     Type: {sample.get('contract_type', 'N/A')}")
    else:
        print("⚠️  No options chain data retrieved")
    print()
    
    # Test 3: Get ATM option
    if expirations:
        print("Test 3: Getting ATM call option...")
        expiration = expirations[0]  # Use first expiration
        atm_option = feed.get_atm_options(symbol, expiration, 'call')
        
        if atm_option:
            print(f"✅ Found ATM option:")
            print(f"   Strike: {atm_option.get('strike_price', 'N/A')}")
            print(f"   Expiration: {atm_option.get('expiration_date', 'N/A')}")
        else:
            print("⚠️  Could not find ATM option")
        print()
    
    # Test 4: Point-in-time data (if historical data available)
    print("Test 4: Testing point-in-time data retrieval...")
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    # Skip weekends
    if datetime.now().weekday() < 5:  # Not a weekend
        historical_chain = feed.get_options_chain(symbol, date=yesterday)
        if historical_chain:
            print(f"✅ Retrieved historical chain for {yesterday}: {len(historical_chain)} contracts")
        else:
            print(f"⚠️  No historical data for {yesterday} (may need paid Polygon plan)")
    else:
        print("⚠️  Skipping historical test (weekend)")
    print()
    
    print("="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    if expirations and chain:
        print("✅ Polygon integration is working!")
        print("   You can now use Polygon for options data in TradeNova")
        return True
    else:
        print("⚠️  Polygon API is configured but returned no data")
        print("   Possible reasons:")
        print("   - Rate limiting (free tier: 5 requests/min)")
        print("   - Symbol not available")
        print("   - Need paid plan for historical data")
        return False

if __name__ == "__main__":
    success = test_polygon_feed()
    sys.exit(0 if success else 1)

