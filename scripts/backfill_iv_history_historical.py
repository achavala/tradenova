#!/usr/bin/env python3
"""
Backfill IV History (Historical)
Attempts to backfill IV history using available historical data
Note: Massive API may not provide historical IV directly
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
from datetime import datetime, date, timedelta
from services.iv_rank_service import IVRankService
from services.polygon_options_feed import MassiveOptionsFeed
from config import Config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def backfill_iv_history():
    """
    Attempt to backfill IV history
    
    Note: This is limited by what Massive API provides.
    For true historical backfill, you'd need:
    1. Historical options prices
    2. Calculate IV using Black-Scholes
    3. Or use a service that provides historical IV
    """
    
    print("="*80)
    print("IV HISTORY BACKFILL")
    print("="*80)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    service = IVRankService()
    
    if not service.options_feed.is_available():
        print("❌ Massive API not available")
        return False
    
    print("⚠️  Note: Massive API provides current IV only.")
    print("   Historical IV backfill requires:")
    print("   1. Historical options prices (not available via snapshot endpoint)")
    print("   2. Calculate IV from prices using Black-Scholes")
    print("   3. Or use a service with historical IV data")
    print()
    print("   For now, we'll collect current IV for all tickers.")
    print("   Run collect_iv_history.py daily to build history over time.\n")
    
    # Collect current IV for all tickers
    print("Collecting current IV data...")
    print("-" * 80)
    
    results = service.collect_all_tickers_iv()
    
    successful = sum(1 for success in results.values() if success)
    total = len(results)
    
    print(f"\n✅ Collected IV for {successful}/{total} tickers")
    
    # Show what we have
    print("\n" + "="*80)
    print("CURRENT DATABASE STATUS")
    print("="*80)
    
    summary = service.iv_db.get_data_summary()
    
    if summary:
        print(f"\nRecords per symbol:")
        for symbol, count in sorted(summary.items()):
            latest_iv = service.iv_db.get_latest_iv(symbol)
            if latest_iv:
                print(f"  {symbol}: {count:,} records (Latest IV: {latest_iv:.2%})")
            else:
                print(f"  {symbol}: {count:,} records")
        
        total_records = sum(summary.values())
        print(f"\nTotal records: {total_records:,}")
        
        # Calculate days of data
        symbols_with_data = [
            s for s in Config.TICKERS 
            if service.iv_db.has_data(s, min_days=30)
        ]
        
        print(f"\nSymbols with 30+ days data: {len(symbols_with_data)}/{len(Config.TICKERS)}")
        
        if len(symbols_with_data) < len(Config.TICKERS):
            print(f"\n💡 Run collect_iv_history.py daily to build history")
            print(f"   After 30+ days, IV Rank will be accurate")
    else:
        print("\nNo data in database")
    
    print()
    
    return successful == total

if __name__ == "__main__":
    success = backfill_iv_history()
    sys.exit(0 if success else 1)

