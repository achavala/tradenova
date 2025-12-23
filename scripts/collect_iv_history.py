#!/usr/bin/env python3
"""
Collect IV History for All Tickers
Runs daily to build IV history database
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
from datetime import datetime
from services.iv_rank_service import IVRankService
from config import Config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def collect_iv_history():
    """Collect IV history for all tickers"""
    
    print("="*80)
    print("IV HISTORY COLLECTION")
    print("="*80)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    service = IVRankService()
    
    if not service.options_feed.is_available():
        print("❌ Massive API not available")
        print("   Set MASSIVE_API_KEY or POLYGON_API_KEY in .env")
        return False
    
    print("✅ IV Rank Service initialized")
    print(f"   Database: {service.iv_db.db_path}")
    print(f"   Lookback: {service.lookback_days} days")
    print()
    
    # Collect IV for all tickers
    print("Collecting IV data...")
    print("-" * 80)
    
    results = service.collect_all_tickers_iv()
    
    # Summary
    print("\n" + "="*80)
    print("COLLECTION SUMMARY")
    print("="*80)
    
    successful = sum(1 for success in results.values() if success)
    total = len(results)
    
    print(f"\nSuccessfully collected: {successful}/{total}\n")
    
    for symbol, success in results.items():
        status = "✅" if success else "❌"
        print(f"  {status} {symbol}")
    
    # Show database summary
    print("\n" + "="*80)
    print("DATABASE SUMMARY")
    print("="*80)
    
    summary = service.iv_db.get_data_summary()
    
    if summary:
        print(f"\nRecords per symbol:")
        for symbol, count in sorted(summary.items()):
            print(f"  {symbol}: {count:,} records")
        
        total_records = sum(summary.values())
        print(f"\nTotal records: {total_records:,}")
    else:
        print("\nNo data in database yet")
    
    print()
    
    if successful == total:
        print("✅ All tickers collected successfully")
        return True
    else:
        print(f"⚠️  {total - successful} ticker(s) failed")
        return False

if __name__ == "__main__":
    success = collect_iv_history()
    sys.exit(0 if success else 1)

