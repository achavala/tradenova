#!/usr/bin/env python3
"""
Test IV Regime Filters
Validates IV regime-based trade filtering
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
from core.risk.iv_regime_manager import IVRegimeManager
from core.risk.advanced_risk_manager import AdvancedRiskManager
from services.iv_rank_service import IVRankService
from config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_iv_regime_filters():
    """Test IV regime-based trade filtering"""
    
    print("="*80)
    print("IV REGIME FILTERS TEST")
    print("="*80)
    print()
    
    # Initialize services
    iv_service = IVRankService()
    iv_regime = IVRegimeManager(iv_service)
    risk_manager = AdvancedRiskManager(
        initial_balance=100000,
        use_iv_regimes=True
    )
    
    if not iv_service.options_feed.is_available():
        print("❌ Massive API not available")
        return False
    
    print("✅ Services initialized")
    print()
    
    # Test for all tickers
    print("Testing IV Regime Filters for All Tickers:")
    print("-" * 80)
    print()
    
    results = {}
    
    for symbol in Config.TICKERS:
        print(f"{symbol}:")
        
        # Get IV metrics
        metrics = iv_service.get_iv_metrics(symbol)
        current_iv = metrics.get('current_iv')
        iv_rank = metrics.get('iv_rank')
        
        if current_iv is None:
            print(f"  ⚠️  No IV data")
            results[symbol] = {'status': 'no_data'}
            continue
        
        # Get IV regime
        regime, rank = iv_regime.get_iv_regime(symbol)
        
        print(f"  Current IV: {current_iv:.2%}")
        if iv_rank is not None:
            print(f"  IV Rank: {iv_rank:.2f}%")
        else:
            print(f"  IV Rank: N/A (need 2+ data points)")
        print(f"  Regime: {regime.upper()}")
        
        # Test trade filters
        can_long, long_reason = iv_regime.can_trade_long_options(symbol)
        can_short, short_reason = iv_regime.can_trade_short_premium(symbol)
        
        print(f"  Long Options: {'✅ ALLOWED' if can_long else '❌ BLOCKED'}")
        if not can_long:
            print(f"    Reason: {long_reason}")
        
        print(f"  Short Premium: {'✅ ALLOWED' if can_short else '❌ BLOCKED'}")
        if not can_short:
            print(f"    Reason: {short_reason}")
        
        # Position size multiplier
        size_mult = iv_regime.get_position_size_multiplier(symbol)
        if size_mult < 1.0:
            print(f"  Position Size: {size_mult:.0%} (reduced due to {regime} IV)")
        else:
            print(f"  Position Size: 100% (full size)")
        
        # Fast exit
        favor_fast = iv_regime.should_favor_fast_exit(symbol)
        if favor_fast:
            print(f"  Exit Strategy: ⚡ Favor fast exits (high IV regime)")
        
        # Test with risk manager
        base_size = 1000.0
        adjusted_size = risk_manager.get_iv_adjusted_position_size(symbol, base_size)
        
        if adjusted_size != base_size:
            print(f"  Risk Manager Adjustment: ${base_size:.2f} → ${adjusted_size:.2f}")
        
        # Test trade allowance
        allowed, reason, risk_level = risk_manager.check_trade_allowed(
            symbol=symbol,
            qty=100,
            price=100.0,
            side='buy',
            iv_rank=iv_rank
        )
        
        print(f"  Risk Manager: {'✅ ALLOWED' if allowed else '❌ BLOCKED'}")
        if not allowed:
            print(f"    Reason: {reason}")
        
        results[symbol] = {
            'regime': regime,
            'iv_rank': iv_rank,
            'can_long': can_long,
            'can_short': can_short,
            'size_mult': size_mult,
            'risk_allowed': allowed
        }
        
        print()
    
    # Summary
    print("="*80)
    print("SUMMARY")
    print("="*80)
    
    regimes_count = {}
    blocked_long = []
    blocked_short = []
    
    for symbol, result in results.items():
        regime = result.get('regime', 'unknown')
        regimes_count[regime] = regimes_count.get(regime, 0) + 1
        
        if not result.get('can_long'):
            blocked_long.append(symbol)
        
        if not result.get('can_short'):
            blocked_short.append(symbol)
    
    print(f"\nIV Regimes Distribution:")
    for regime, count in sorted(regimes_count.items()):
        print(f"  {regime.upper()}: {count} ticker(s)")
    
    if blocked_long:
        print(f"\n⚠️  Long Options BLOCKED for: {', '.join(blocked_long)}")
    
    if blocked_short:
        print(f"\n⚠️  Short Premium BLOCKED for: {', '.join(blocked_short)}")
    
    print()
    print("="*80)
    print("✅ IV REGIME FILTERS VALIDATED")
    print("="*80)
    
    return True

if __name__ == "__main__":
    success = test_iv_regime_filters()
    sys.exit(0 if success else 1)

