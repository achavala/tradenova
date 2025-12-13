"""
Test script to validate trade generation with new thresholds
"""
import sys
from pathlib import Path
import logging
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.live.integrated_trader import IntegratedTrader
from config import Config
from alpaca_trade_api.rest import TimeFrame

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_trade_generation():
    """Test that trades are being generated with new thresholds"""
    print("\n" + "="*60)
    print("🧪 TESTING TRADE GENERATION WITH LOWERED THRESHOLDS")
    print("="*60)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Initialize trader in dry-run mode
    trader = IntegratedTrader(
        rl_model_path='models/ppo_final.zip',
        use_rl=True,
        dry_run=True,  # Don't actually trade
        paper_trading=True
    )
    
    print("📊 Configuration:")
    print(f"  • Confidence Threshold: 0.3 (30%)")
    print(f"  • RL Action Threshold: 0.2 (20%)")
    print(f"  • Regime Confidence: 0.3 (30%)")
    print(f"  • Tickers: {len(Config.TICKERS)} tickers")
    print(f"  • Mode: DRY RUN (no actual trades)")
    print()
    
    # Run one scan cycle
    print("🔍 Running scan cycle...")
    print("-" * 60)
    
    try:
        trader.run_trading_cycle()
        
        print("\n" + "="*60)
        print("✅ SCAN CYCLE COMPLETED")
        print("="*60)
        print("\n📋 Check logs for:")
        print("  • [SIGNAL] entries - signals generated")
        print("  • [SKIP] entries - why trades were skipped")
        print("  • [EXECUTING] entries - trades that would execute")
        print("\n💡 If no trades:")
        print("  1. Check market hours (must be open)")
        print("  2. Check [SIGNAL] logs for confidence levels")
        print("  3. Check [SKIP] logs for reasons")
        print("  4. Verify data availability for tickers")
        
    except Exception as e:
        logger.error(f"Error during scan: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == '__main__':
    success = test_trade_generation()
    sys.exit(0 if success else 1)

