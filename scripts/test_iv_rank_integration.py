#!/usr/bin/env python3
"""
Test IV Rank Integration
Validates complete IV Rank system
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

def test_iv_rank_integration():
    """Test complete IV Rank integration"""
    
    print("="*80)
    print("IV RANK INTEGRATION TEST")
    print("="*80)
    print()
    
    service = IVRankService()
    
    if not service.options_feed.is_available():
        print("❌ Massive API not available")
        return False
    
    print("✅ IV Rank Service initialized")
    print()
    
    # Test 1: Collect IV for a symbol
    print("TEST 1: Collect and Store IV")
    print("-" * 80)
    
    test_symbol = "NVDA"
    success = service.collect_and_store_iv(test_symbol)
    
    if success:
        print(f"✅ Successfully collected IV for {test_symbol}")
        
        # Verify stored
        latest_iv = service.iv_db.get_latest_iv(test_symbol)
        if latest_iv:
            print(f"   Stored IV: {latest_iv:.2%}")
        else:
            print(f"   ⚠️  IV not found in database")
    else:
        print(f"❌ Failed to collect IV for {test_symbol}")
        return False
    
    print()
    
    # Test 2: Get IV history
    print("TEST 2: Retrieve IV History")
    print("-" * 80)
    
    iv_history = service.iv_db.get_iv_history(test_symbol, lookback_days=365)
    
    if iv_history:
        print(f"✅ Retrieved {len(iv_history)} IV data points")
        print(f"   Latest IV: {iv_history[0]:.2%}")
        print(f"   Oldest IV: {iv_history[-1]:.2%}")
        print(f"   Min IV: {min(iv_history):.2%}")
        print(f"   Max IV: {max(iv_history):.2%}")
    else:
        print(f"⚠️  No IV history found (need to collect more data)")
    
    print()
    
    # Test 3: Calculate IV Rank
    print("TEST 3: Calculate IV Rank")
    print("-" * 80)
    
    if iv_history and len(iv_history) >= 2:
        iv_rank = service.get_iv_rank(test_symbol)
        
        if iv_rank is not None:
            print(f"✅ IV Rank: {iv_rank:.2f}%")
        else:
            print(f"⚠️  Could not calculate IV Rank")
    else:
        print(f"⚠️  Need at least 2 data points for IV Rank")
        print(f"   Current data points: {len(iv_history) if iv_history else 0}")
    
    print()
    
    # Test 4: Calculate IV Percentile
    print("TEST 4: Calculate IV Percentile")
    print("-" * 80)
    
    if iv_history:
        iv_percentile = service.get_iv_percentile(test_symbol)
        
        if iv_percentile is not None:
            print(f"✅ IV Percentile: {iv_percentile:.2f}%")
        else:
            print(f"⚠️  Could not calculate IV Percentile")
    else:
        print(f"⚠️  Need IV history for IV Percentile")
    
    print()
    
    # Test 5: Get comprehensive metrics
    print("TEST 5: Comprehensive IV Metrics")
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
    
    # Test 6: Database operations
    print("TEST 6: Database Operations")
    print("-" * 80)
    
    # Check if has data
    has_data = service.iv_db.has_data(test_symbol, min_days=30)
    print(f"Has sufficient data (30+ days): {has_data}")
    
    # Get IV range
    min_iv, max_iv = service.iv_db.get_iv_range(test_symbol, lookback_days=365)
    if min_iv and max_iv:
        print(f"52-week IV range: {min_iv:.2%} - {max_iv:.2%}")
    else:
        print(f"52-week IV range: N/A (need more data)")
    
    # Get all symbols
    symbols = service.iv_db.get_symbols()
    print(f"Symbols in database: {len(symbols)}")
    if symbols:
        print(f"  {', '.join(symbols[:10])}{'...' if len(symbols) > 10 else ''}")
    
    print()
    
    print("="*80)
    print("INTEGRATION TEST COMPLETE")
    print("="*80)
    
    return True

if __name__ == "__main__":
    success = test_iv_rank_integration()
    sys.exit(0 if success else 1)




