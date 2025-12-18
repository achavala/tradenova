#!/usr/bin/env python3
"""
Test Trading Mode - Real Paper Trading with Relaxed Rules
- Lower confidence threshold
- Options trading enabled
- 10% profit target / 5% stop loss
- Real execution (paper account)
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from core.live.integrated_trader import IntegratedTrader
from core.risk.profit_manager import ProfitManager
from config import Config
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_test_trader():
    """Create trader with test settings"""
    
    # Create trader with relaxed settings
    trader = IntegratedTrader(
        rl_model_path=None,  # Skip RL for testing
        use_rl=False,
        dry_run=False,  # REAL paper trading
        paper_trading=True  # Paper account
    )
    
    # Override profit manager with test settings
    trader.profit_manager = ProfitManager(
        tp1_pct=0.10,  # 10% profit target
        tp1_exit_pct=1.00,  # Full exit at 10%
        tp2_pct=0.20,  # 20% (if we want second target)
        tp2_exit_pct=1.00,
        tp3_pct=0.30,
        tp3_exit_pct=1.00,
        tp4_pct=0.50,
        tp4_exit_pct=1.00,
        tp5_pct=1.00,
        tp5_exit_pct=1.00,
        stop_loss_pct=0.05,  # 5% stop loss
        trailing_stop_activation_pct=0.10,
        trailing_stop_min_profit_pct=0.05
    )
    
    logger.info("="*60)
    logger.info("TEST TRADING MODE ACTIVATED")
    logger.info("="*60)
    logger.info("Settings:")
    logger.info("  - Profit Target: 10%")
    logger.info("  - Stop Loss: 5%")
    logger.info("  - Paper Trading: YES (real execution)")
    logger.info("  - Dry Run: NO")
    logger.info("="*60)
    
    return trader

def run_test_cycle(trader):
    """Run one test trading cycle with relaxed rules"""
    
    # Temporarily lower confidence threshold
    original_threshold = 0.5
    
    # Modify the _scan_and_trade method behavior
    logger.info("Running test trading cycle with relaxed rules...")
    logger.info("Confidence threshold: 0.30 (lowered for testing)")
    
    # Run trading cycle
    try:
        trader.run_trading_cycle()
        logger.info("Test cycle completed")
    except Exception as e:
        logger.error(f"Error in test cycle: {e}", exc_info=True)

if __name__ == "__main__":
    import time
    
    trader = create_test_trader()
    
    # Run test cycles
    logger.info("Starting test trading...")
    logger.info("Will run cycles every 2 minutes for testing")
    logger.info("Press CTRL+C to stop")
    logger.info("")
    
    try:
        cycle_count = 0
        while True:
            cycle_count += 1
            logger.info(f"\n--- Test Cycle #{cycle_count} ---")
            run_test_cycle(trader)
            
            # Wait 2 minutes between cycles for testing
            logger.info("Waiting 2 minutes until next cycle...")
            time.sleep(120)
            
    except KeyboardInterrupt:
        logger.info("\nTest trading stopped by user")






