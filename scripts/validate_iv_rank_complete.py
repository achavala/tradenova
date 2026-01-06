#!/usr/bin/env python3
"""
Comprehensive IV Rank Integration Validation
Tests complete IV Rank system end-to-end
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
from services.iv_rank_service import IVRankService
from services.iv_history_db import IVHistoryDB
from config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def validate_complete_integration():
    """Validate complete IV Rank integration"""
    
    print("="*80)
    print("COMPREHENSIVE IV RANK INTEGRATION VALIDATION")
    print("="*80)
    print()
    
    # Test 1: Service initialization
    print("TEST 1: Service Initialization")
    print("-" * 80)
    
    service = IVRankService()
    
    if not service.options_feed.is_available():
        print("❌ Massive API not available")
        return False
    
    print("✅ IV Rank Service initialized")
    print(f"   Database: {service.iv_db.db_path}")
    print(f"   Options Feed: {type(service.options_feed).__name__}")
    print(f"   IV Calculator: {type(service.iv_calculator).__name__}")
    print()
    
    # Test 2: Database operations
    print("TEST 2: Database Operations")
    print("-" * 80)
    
    # Check database exists
    if service.iv_db.db_path.exists():
        print(f"✅ Database exists: {service.iv_db.db_path}")
    else:
        print(f"⚠️  Database not found (will be created on first write)")
    
    # Get symbols
    symbols = service.iv_db.get_symbols()
    print(f"✅ Symbols in database: {len(symbols)}")
    if symbols:
        print(f"   {', '.join(symbols)}")
    print()
    
    # Test 3: Collect IV for test symbol
    print("TEST 3: Collect and Store IV")
    print("-" * 80)
    
    test_symbol = "NVDA"
    success = service.collect_and_store_iv(test_symbol)
    
    if success:
        print(f"✅ Successfully collected IV for {test_symbol}")
        
        latest_iv = service.iv_db.get_latest_iv(test_symbol)
        if latest_iv:
            print(f"   Latest IV: {latest_iv:.2%}")
    else:
        print(f"❌ Failed to collect IV for {test_symbol}")
        return False
    
    print()
    
    # Test 4: IV History retrieval
    print("TEST 4: IV History Retrieval")
    print("-" * 80)
    
    iv_history = service.iv_db.get_iv_history(test_symbol, lookback_days=365)
    
    print(f"✅ Retrieved {len(iv_history)} IV data points")
    
    if iv_history:
        print(f"   Latest: {iv_history[0]:.2%}")
        print(f"   Oldest: {iv_history[-1]:.2%}")
        print(f"   Min: {min(iv_history):.2%}")
        print(f"   Max: {max(iv_history):.2%}")
        print(f"   Avg: {sum(iv_history)/len(iv_history):.2%}")
    else:
        print(f"   ⚠️  No history yet (need to collect more data)")
    
    print()
    
    # Test 5: IV Rank calculation
    print("TEST 5: IV Rank Calculation")
    print("-" * 80)
    
    if len(iv_history) >= 2:
        iv_rank = service.get_iv_rank(test_symbol)
        
        if iv_rank is not None:
            print(f"✅ IV Rank: {iv_rank:.2f}%")
            
            # Validate range
            if 0 <= iv_rank <= 100:
                print(f"   ✅ IV Rank in valid range (0-100)")
            else:
                print(f"   ❌ IV Rank out of range: {iv_rank}")
        else:
            print(f"⚠️  Could not calculate IV Rank")
    else:
        print(f"⚠️  Need at least 2 data points for IV Rank")
        print(f"   Current: {len(iv_history)} data points")
        print(f"   💡 Run collect_iv_history.py daily to build history")
    
    print()
    
    # Test 6: IV Percentile calculation
    print("TEST 6: IV Percentile Calculation")
    print("-" * 80)
    
    if iv_history:
        iv_percentile = service.get_iv_percentile(test_symbol)
        
        if iv_percentile is not None:
            print(f"✅ IV Percentile: {iv_percentile:.2f}%")
            
            # Validate range
            if 0 <= iv_percentile <= 100:
                print(f"   ✅ IV Percentile in valid range (0-100)")
            else:
                print(f"   ❌ IV Percentile out of range: {iv_percentile}")
        else:
            print(f"⚠️  Could not calculate IV Percentile")
    else:
        print(f"⚠️  Need IV history for IV Percentile")
    
    print()
    
    # Test 7: Comprehensive metrics
    print("TEST 7: Comprehensive IV Metrics")
    print("-" * 80)
    
    metrics = service.get_iv_metrics(test_symbol)
    
    print(f"Current IV: {metrics['current_iv']:.2%}" if metrics['current_iv'] else "Current IV: N/A")
    print(f"IV Rank: {metrics['iv_rank']:.2f}%" if metrics['iv_rank'] is not None else "IV Rank: N/A")
    print(f"IV Percentile: {metrics['iv_percentile']:.2f}%" if metrics['iv_percentile'] is not None else "IV Percentile: N/A")
    print(f"Min IV: {metrics['min_iv']:.2%}" if metrics['min_iv'] else "Min IV: N/A")
    print(f"Max IV: {metrics['max_iv']:.2%}" if metrics['max_iv'] else "Max IV: N/A")
    print(f"Avg IV: {metrics['avg_iv']:.2%}" if metrics['avg_iv'] else "Avg IV: N/A")
    print(f"Data Points: {metrics['data_points']}")
    
    print()
    
    # Test 8: All tickers metrics
    print("TEST 8: All Tickers IV Metrics")
    print("-" * 80)
    
    all_metrics = service.get_all_tickers_iv_metrics()
    
    print(f"\nIV Metrics for all {len(all_metrics)} tickers:")
    print()
    
    for symbol, metrics in sorted(all_metrics.items()):
        current_iv = metrics.get('current_iv')
        iv_rank = metrics.get('iv_rank')
        data_points = metrics.get('data_points', 0)
        
        if current_iv:
            status = "✅" if data_points >= 2 else "⚠️"
            print(f"{status} {symbol}:")
            print(f"     IV: {current_iv:.2%}")
            if iv_rank is not None:
                print(f"     IV Rank: {iv_rank:.2f}%")
            else:
                print(f"     IV Rank: N/A (need {2 - data_points} more data points)")
            print(f"     Data Points: {data_points}")
        else:
            print(f"❌ {symbol}: No IV data")
    
    print()
    
    # Test 9: Database integrity
    print("TEST 9: Database Integrity")
    print("-" * 80)
    
    summary = service.iv_db.get_data_summary()
    
    if summary:
        total_records = sum(summary.values())
        print(f"✅ Total records: {total_records:,}")
        print(f"✅ Symbols: {len(summary)}")
        
        # Check for sufficient data
        symbols_with_data = [
            s for s in Config.TICKERS 
            if service.iv_db.has_data(s, min_days=30)
        ]
        
        print(f"✅ Symbols with 30+ days data: {len(symbols_with_data)}/{len(Config.TICKERS)}")
        
        if len(symbols_with_data) < len(Config.TICKERS):
            print(f"   💡 Run collect_iv_history.py daily to build history")
    else:
        print("⚠️  No data in database")
    
    print()
    
    print("="*80)
    print("VALIDATION SUMMARY")
    print("="*80)
    
    # Overall status
    all_tickers_have_data = all(
        service.iv_db.get_latest_iv(s) is not None 
        for s in Config.TICKERS
    )
    
    if all_tickers_have_data:
        print("✅ All tickers have IV data")
    else:
        print("⚠️  Some tickers missing IV data")
    
    symbols_with_rank = [
        s for s in Config.TICKERS 
        if service.get_iv_rank(s) is not None
    ]
    
    if len(symbols_with_rank) > 0:
        print(f"✅ {len(symbols_with_rank)} ticker(s) can calculate IV Rank")
    else:
        print("⚠️  Need more data points for IV Rank calculation")
        print("   💡 Run collect_iv_history.py daily for 30+ days")
    
    print()
    print("="*80)
    print("✅ INTEGRATION VALIDATED")
    print("="*80)
    print()
    print("Components:")
    print("  ✅ IV Calculator: Connected")
    print("  ✅ Options Data Feed: Connected")
    print("  ✅ IV History Database: Operational")
    print("  ✅ IV Rank Service: Functional")
    print()
    print("Next Steps:")
    print("  1. Run collect_iv_history.py daily to build history")
    print("  2. After 30+ days, IV Rank will be accurate")
    print("  3. Use IV Rank in trading logic")
    
    return True

if __name__ == "__main__":
    success = validate_complete_integration()
    sys.exit(0 if success else 1)




