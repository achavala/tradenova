#!/usr/bin/env python3
"""
Weekend Test Runner
Runs the trading system using real historical data for weekend testing
Simulates live market conditions without fake entries
"""
import logging
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta, date
import time
import argparse

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from core.live.integrated_trader import IntegratedTrader
from core.live.historical_replay_client import HistoricalReplayClient
from alpaca_client import AlpacaClient
from config import Config

logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/weekend_test.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class WeekendTestRunner:
    """Weekend testing with real historical data"""
    
    def __init__(
        self,
        test_date: date,
        rl_model_path: str = None,
        speed_multiplier: float = 10.0,
        use_intraday: bool = True
    ):
        """
        Initialize weekend test runner
        
        Args:
            test_date: Date to replay (e.g., date(2025, 12, 4))
            rl_model_path: Path to RL model (optional)
            speed_multiplier: Speed multiplier (1.0 = real-time, 10.0 = 10x speed)
            use_intraday: Use 5-minute bars for intraday replay
        """
        self.test_date = test_date
        self.speed_multiplier = speed_multiplier
        
        logger.info("="*80)
        logger.info("WEEKEND TEST RUNNER - HISTORICAL DATA REPLAY")
        logger.info("="*80)
        logger.info(f"📅 Test Date: {test_date}")
        logger.info(f"⏱️  Speed: {speed_multiplier}x")
        logger.info(f"📊 Mode: {'Intraday (5min)' if use_intraday else 'Daily'}")
        logger.info("="*80)
        
        # Initialize real Alpaca client for fetching historical data
        self.real_alpaca = AlpacaClient(
            Config.ALPACA_API_KEY,
            Config.ALPACA_SECRET_KEY,
            Config.ALPACA_BASE_URL
        )
        
        # Create historical replay client
        replay_date = datetime.combine(test_date, datetime.min.time())
        self.replay_client = HistoricalReplayClient(
            replay_date=replay_date,
            real_alpaca_client=self.real_alpaca,
            speed_multiplier=speed_multiplier,
            use_intraday=use_intraday
        )
        
        # Initialize integrated trader with replay client
        # We need to inject the replay client into the trader
        # Since IntegratedTrader creates its own client, we'll need to modify it
        # For now, we'll create a custom trader that uses our replay client
        
        # Find RL model
        if rl_model_path is None:
            grpo_model = Path("./models/grpo_final.zip")
            ppo_model = Path("./models/ppo_final.zip")
            
            if grpo_model.exists():
                rl_model_path = str(grpo_model)
            elif ppo_model.exists():
                rl_model_path = str(ppo_model)
        
        # Create trader with replay client
        self.trader = self._create_trader_with_replay_client(rl_model_path)
        
        # Update all components to use replay client
        self.trader.orchestrator.client = self.replay_client
        self.trader.executor.client = self.replay_client
        if hasattr(self.trader.executor, 'options_client'):
            self.trader.executor.options_client.client = self.replay_client
        
        logger.info("✅ Weekend test runner initialized")
        logger.info("✅ Using REAL historical data from Alpaca")
        logger.info("✅ No fake entries - all data is authentic")
    
    def _create_trader_with_replay_client(self, rl_model_path: str = None):
        """Create IntegratedTrader with historical replay client"""
        # Create trader in dry-run mode (we'll handle execution via replay client)
        trader = IntegratedTrader(
            rl_model_path=rl_model_path,
            use_rl=rl_model_path is not None,
            dry_run=False,  # We want to track trades, just simulate execution
            paper_trading=True
        )
        
        # Replace the client with our replay client
        trader.client = self.replay_client
        
        return trader
    
    def run_full_day(self):
        """Run full trading day simulation"""
        logger.info("="*80)
        logger.info("STARTING FULL DAY SIMULATION")
        logger.info("="*80)
        
        # Pre-market warmup (8:00 AM simulated)
        from pytz import UTC
        logger.info("🌅 PRE-MARKET WARMUP (8:00 AM)")
        self.replay_client.sim_time = UTC.localize(datetime.combine(
            self.test_date,
            datetime.strptime("08:00", "%H:%M").time()
        ))
        self._pre_market_warmup()
        
        # Market open (9:30 AM)
        from pytz import UTC
        logger.info("🔔 MARKET OPEN (9:30 AM)")
        self.replay_client.sim_time = UTC.localize(datetime.combine(
            self.test_date,
            datetime.strptime("09:30", "%H:%M").time()
        ))
        self.replay_client.sim_start_time = time.time()
        
        # Trading cycles every 5 minutes
        cycle_count = 0
        max_cycles = 78  # 6.5 hours * 12 cycles/hour = 78 cycles
        
        try:
            while cycle_count < max_cycles:
                current_sim = self.replay_client.get_current_sim_time()
                
                # Check if market is still open
                if not self.replay_client.is_market_open():
                    logger.info(f"🏁 Market closed at {current_sim.strftime('%H:%M:%S')}")
                    break
                
                logger.info("="*60)
                logger.info(f"TRADING CYCLE #{cycle_count + 1} - {current_sim.strftime('%H:%M:%S')}")
                logger.info("="*60)
                
                # Run trading cycle
                self.trader.run_trading_cycle()
                
                cycle_count += 1
                
                # Wait for next cycle (adjusted for speed multiplier)
                if self.speed_multiplier > 0:
                    wait_time = (5 * 60) / self.speed_multiplier  # 5 minutes / speed
                    time.sleep(wait_time)
                else:
                    # Manual mode - wait for user input
                    input("Press Enter to advance to next cycle...")
                    self.replay_client.advance_time(5 * 60)  # Advance 5 minutes
                
        except KeyboardInterrupt:
            logger.info("\n⚠️  Simulation interrupted by user")
        
        # Market close (4:00 PM)
        logger.info("🔔 MARKET CLOSE (4:00 PM)")
        self._market_close_routine()
        
        # Generate report
        self._generate_report()
    
    def _pre_market_warmup(self):
        """Pre-market warmup routine"""
        try:
            account = self.replay_client.get_account()
            logger.info(f"💰 Account Equity: ${float(account['equity']):,.2f}")
            logger.info(f"💵 Buying Power: ${float(account['buying_power']):,.2f}")
            
            risk_status = self.trader.risk_manager.get_risk_status()
            logger.info(f"🛡️  Risk Level: {risk_status['risk_level']}")
            
            # Reset daily tracking
            self.trader.risk_manager._reset_daily_if_needed()
            
        except Exception as e:
            logger.error(f"Error in pre-market warmup: {e}")
    
    def _market_close_routine(self):
        """Market close routine"""
        try:
            positions = self.trader.positions.copy()
            logger.info(f"📊 Closing {len(positions)} positions")
            
            for symbol, position_info in positions.items():
                current_price = self.replay_client.get_latest_price(symbol)
                if current_price is None:
                    continue
                
                entry_price = position_info['entry_price']
                qty = position_info['current_qty']
                side = position_info['side']
                
                # Calculate P&L
                if side == 'long':
                    pnl = (current_price - entry_price) * qty
                else:
                    pnl = (entry_price - current_price) * qty
                
                logger.info(f"📈 {symbol}: Entry=${entry_price:.2f}, Exit=${current_price:.2f}, P&L=${pnl:.2f}")
            
            logger.info("✅ Market close routine complete")
            
        except Exception as e:
            logger.error(f"Error in market close routine: {e}")
    
    def _generate_report(self):
        """Generate test report"""
        logger.info("="*80)
        logger.info("TEST REPORT")
        logger.info("="*80)
        
        try:
            # Get metrics
            metrics = self.trader.metrics_tracker.get_metrics()
            
            logger.info(f"📊 Total Trades: {metrics.get('total_trades', 0)}")
            logger.info(f"✅ Winning Trades: {metrics.get('winning_trades', 0)}")
            logger.info(f"❌ Losing Trades: {metrics.get('losing_trades', 0)}")
            logger.info(f"💰 Total P&L: ${metrics.get('total_pnl', 0):,.2f}")
            logger.info(f"📈 Win Rate: {metrics.get('win_rate', 0):.1f}%")
            
            # Save report
            report_file = Path("logs") / f"weekend_test_{self.test_date}.txt"
            report_file.parent.mkdir(exist_ok=True)
            
            with open(report_file, 'w') as f:
                f.write(f"Weekend Test Report - {self.test_date}\n")
                f.write("="*80 + "\n\n")
                f.write(f"Test Date: {self.test_date}\n")
                f.write(f"Speed Multiplier: {self.speed_multiplier}x\n")
                f.write(f"Total Trades: {metrics.get('total_trades', 0)}\n")
                f.write(f"Winning Trades: {metrics.get('winning_trades', 0)}\n")
                f.write(f"Losing Trades: {metrics.get('losing_trades', 0)}\n")
                f.write(f"Total P&L: ${metrics.get('total_pnl', 0):,.2f}\n")
                f.write(f"Win Rate: {metrics.get('win_rate', 0):.1f}%\n")
            
            logger.info(f"📄 Report saved to {report_file}")
            
        except Exception as e:
            logger.error(f"Error generating report: {e}")

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Weekend Test Runner - Historical Data Replay')
    parser.add_argument(
        '--date',
        type=str,
        default=None,
        help='Date to replay (YYYY-MM-DD). Default: yesterday'
    )
    parser.add_argument(
        '--speed',
        type=float,
        default=10.0,
        help='Speed multiplier (1.0 = real-time, 10.0 = 10x speed). Default: 10.0'
    )
    parser.add_argument(
        '--daily',
        action='store_true',
        help='Use daily bars instead of intraday (faster but less realistic)'
    )
    parser.add_argument(
        '--rl-model',
        type=str,
        default=None,
        help='Path to RL model (default: auto-detect)'
    )
    
    args = parser.parse_args()
    
    # Parse date
    if args.date:
        test_date = datetime.strptime(args.date, '%Y-%m-%d').date()
    else:
        # Default to yesterday
        test_date = (datetime.now() - timedelta(days=1)).date()
    
    # Validate date is not in the future
    if test_date > date.today():
        logger.error(f"❌ Cannot replay future date: {test_date}")
        sys.exit(1)
    
    # Validate date is a weekday
    if test_date.weekday() >= 5:
        logger.warning(f"⚠️  {test_date} is a weekend - market was closed, but will simulate anyway")
    
    # Create and run test
    runner = WeekendTestRunner(
        test_date=test_date,
        rl_model_path=args.rl_model,
        speed_multiplier=args.speed,
        use_intraday=not args.daily
    )
    
    try:
        runner.run_full_day()
    except KeyboardInterrupt:
        logger.info("\n⚠️  Test interrupted by user")
    except Exception as e:
        logger.error(f"❌ Error running test: {e}", exc_info=True)
        sys.exit(1)

if __name__ == '__main__':
    main()

