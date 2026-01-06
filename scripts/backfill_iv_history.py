#!/usr/bin/env python3
"""
Backfill IV History
Collects historical IV data for the past N days to build initial database
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

def backfill_iv_history(days: int = 30):
    """
    Backfill IV history for past N days
    
    Note: This uses current IV data (Massive API doesn't provide historical IV easily)
    For true historical backfill, you'd need to:
    1. Use historical options prices
    2. Calculate IV using Black-Scholes
    3. Or use a service that provides historical IV
    
    This script collects current IV and stores it, which should be run daily
    to build history over time.
    """
    
    print("="*80)
    print("IV HISTORY BACKFILL")
    print("="*80)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    service = IVRankService()
    
    if not service.options_feed.is_available():
        print("❌ Massive API not available")
        return False
    
    print(f"⚠️  Note: Massive API provides current IV only.")
    print(f"   For historical backfill, we'll collect current IV for all tickers.")
    print(f"   Run this script daily to build history over time.\n")
    
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
            print(f"  {symbol}: {count:,} records (Latest IV: {latest_iv:.2%}" if latest_iv else f"  {symbol}: {count:,} records")
        
        total_records = sum(summary.values())
        print(f"\nTotal records: {total_records:,}")
        print(f"\n💡 Run this script daily to build IV history over time")
        print(f"   After 30+ days, IV Rank and Percentile will be accurate")
    else:
        print("\nNo data in database")
    
    return successful == total

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Backfill IV history')
    parser.add_argument('--days', type=int, default=30, help='Days to backfill (note: collects current IV only)')
    
    args = parser.parse_args()
    
    success = backfill_iv_history(days=args.days)
    sys.exit(0 if success else 1)




