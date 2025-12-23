#!/usr/bin/env python3
"""
Daily Trading Runner
Automated daily trading with pre-market warmup, market hours trading, and end-of-day reports
"""
import logging
import sys
import os
from pathlib import Path
from datetime import datetime
import time
from dotenv import load_dotenv

# Load environment variables (critical for Fly.io deployment)
load_dotenv()

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from typing import Optional
from core.live.integrated_trader import IntegratedTrader
from core.live.trading_scheduler import TradingScheduler
from core.live.signal_capture import SignalCapture
from config import Config
from logs.metrics_tracker import MetricsTracker

logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/tradenova_daily.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DailyTradingRunner:
    """Daily trading automation"""
    
    def __init__(
        self,
        rl_model_path: Optional[str] = None,
        dry_run: bool = False,
        paper_trading: bool = False,
        shadow: bool = False,
        save_signals_path: Optional[str] = None
    ):
        """
        Initialize daily runner
        
        Args:
            rl_model_path: Path to RL model (optional)
            dry_run: If True, simulate trading without executing orders
            paper_trading: If True, use paper trading account
        """
        self.dry_run = dry_run
        self.paper_trading = paper_trading
        # Find latest model if not specified
        if rl_model_path is None:
            grpo_model = Path("./models/grpo_final.zip")
            ppo_model = Path("./models/ppo_final.zip")
            
            if grpo_model.exists():
                rl_model_path = str(grpo_model)
            elif ppo_model.exists():
                rl_model_path = str(ppo_model)
        
        self.trader = IntegratedTrader(
            rl_model_path=rl_model_path,
            use_rl=rl_model_path is not None,
            dry_run=dry_run or shadow,  # Shadow mode is also dry-run
            paper_trading=paper_trading
        )
        self.scheduler = TradingScheduler()
        self.metrics_tracker = MetricsTracker()
        
        # Signal capture (if shadow mode)
        self.shadow_mode = shadow
        self.signal_capture = SignalCapture() if shadow else None
        self.save_signals_path = save_signals_path
        
        # Setup scheduled tasks
        self._setup_schedule()
        
    def _setup_schedule(self):
        """Setup scheduled tasks"""
        # Pre-market warmup (8:00 AM)
        self.scheduler.schedule_pre_market_warmup(
            self.pre_market_warmup,
            "08:00"
        )
        
        # Market open (9:30 AM)
        self.scheduler.schedule_market_open(
            self.start_trading,
            "09:30"
        )
        
        # Recurring trading cycle (every 5 minutes during market hours)
        self.scheduler.schedule_recurring(
            self.trading_cycle,
            interval_minutes=5
        )
        
        # Market close flatten (3:50 PM)
        self.scheduler.schedule_market_close_flatten(
            self.flatten_positions,
            "15:50"
        )
        
        # Daily report (4:05 PM)
        self.scheduler.schedule_daily_report(
            self.generate_daily_report,
            "16:05"
        )
    
    def pre_market_warmup(self):
        """Pre-market warmup routine"""
        logger.info("="*60)
        logger.info("PRE-MARKET WARMUP")
        logger.info("="*60)
        
        try:
            # Update account status
            account = self.trader.client.get_account()
            logger.info(f"Account Equity: ${float(account['equity']):,.2f}")
            logger.info(f"Buying Power: ${float(account['buying_power']):,.2f}")
            
            # Check risk status
            risk_status = self.trader.risk_manager.get_risk_status()
            logger.info(f"Risk Level: {risk_status['risk_level']}")
            
            # Reset daily tracking if needed
            self.trader.risk_manager._reset_daily_if_needed()
            
            logger.info("Pre-market warmup complete")
            
        except Exception as e:
            logger.error(f"Error in pre-market warmup: {e}")
    
    def start_trading(self):
        """Start trading at market open"""
        logger.info("="*60)
        logger.info("MARKET OPEN - STARTING TRADING")
        logger.info("="*60)
        
        if not self.trader.client.is_market_open():
            logger.warning("Market is not open")
            return
        
        # Run initial trading cycle
        self.trading_cycle()
    
    def trading_cycle(self):
        """Execute trading cycle"""
        if not self.scheduler.is_market_hours():
            return
        
        try:
            self.trader.run_trading_cycle()
        except Exception as e:
            logger.error(f"Error in trading cycle: {e}")
    
    def flatten_positions(self):
        """Flatten all positions before market close"""
        logger.info("="*60)
        logger.info("FLATTENING POSITIONS BEFORE MARKET CLOSE")
        logger.info("="*60)
        
        try:
            positions = self.trader.positions.copy()
            
            for symbol, position_info in positions.items():
                try:
                    current_price = self.trader.client.get_latest_price(symbol)
                    if current_price is None:
                        continue
                    
                    qty = position_info['current_qty']
                    side = 'sell' if position_info['side'] == 'long' else 'buy'
                    
                    # Check if this is an options position
                    is_option = position_info.get('instrument_type') == 'option'
                    
                    order = self.trader.executor.execute_market_order(
                        symbol, qty, side, is_option=is_option
                    )
                    
                    if order:
                        # Record trade
                        entry_price = position_info['entry_price']
                        exit_price = current_price
                        pnl = (exit_price - entry_price) * qty if position_info['side'] == 'long' else (entry_price - exit_price) * qty
                        
                        self.trader.risk_manager.record_trade(
                            symbol, qty, entry_price, exit_price, pnl, position_info['side']
                        )
                        self.metrics_tracker.record_trade(
                            symbol, entry_price, exit_price, qty, position_info['side'],
                            pnl, position_info.get('agent_name')
                        )
                        
                        logger.info(f"Flattened: {symbol} P&L=${pnl:.2f}")
                        
                except Exception as e:
                    logger.error(f"Error flattening {symbol}: {e}")
            
            # Clear positions
            self.trader.positions.clear()
            
            logger.info("Position flattening complete")
            
        except Exception as e:
            logger.error(f"Error flattening positions: {e}")
    
    def generate_daily_report(self):
        """Generate daily report"""
        logger.info("="*60)
        logger.info("GENERATING DAILY REPORT")
        logger.info("="*60)
        
        try:
            report = self.metrics_tracker.generate_daily_report()
            logger.info(report)
            
            # Save report
            report_file = Path("logs") / f"daily_report_{datetime.now().date()}.txt"
            report_file.parent.mkdir(exist_ok=True)
            with open(report_file, 'w') as f:
                f.write(report)
            
            logger.info(f"Daily report saved to {report_file}")
            
            # Save signals if in shadow mode
            if self.shadow_mode and self.signal_capture:
                if self.save_signals_path:
                    self.signal_capture.save(self.save_signals_path)
                    self.signal_capture.save_csv(self.save_signals_path.replace('.json', '.csv'))
                else:
                    self.signal_capture.save()
                    self.signal_capture.save_csv()
                
                summary = self.signal_capture.get_summary()
                logger.info(f"Signal capture summary: {summary}")
                self.signal_capture.clear()
            
        except Exception as e:
            logger.error(f"Error generating daily report: {e}")
    
    def run(self):
        """Start the daily trading runner"""
        logger.info("="*60)
        logger.info("TRADENOVA DAILY TRADING RUNNER")
        logger.info("="*60)
        mode = 'SHADOW' if self.shadow_mode else ('DRY RUN' if self.dry_run else 'LIVE')
        logger.info(f"Mode: {mode}")
        logger.info(f"Account: {'PAPER' if self.paper_trading else Config.ALPACA_BASE_URL.split('.')[-2].upper()}")
        logger.info(f"RL Model: {'Enabled' if self.trader.use_rl else 'Disabled'}")
        logger.info(f"Max Positions: {Config.MAX_ACTIVE_TRADES}")
        logger.info(f"Position Size: {Config.POSITION_SIZE_PCT*100}%")
        if self.shadow_mode:
            logger.info(f"Signal Capture: Enabled (saving to {self.save_signals_path or 'default location'})")
        logger.info("="*60)
        logger.info("Starting scheduler...")
        logger.info("Press Ctrl+C to stop")
        logger.info("")
        
        try:
            self.scheduler.start()
        except KeyboardInterrupt:
            logger.info("\nStopping daily runner...")
            self.scheduler.stop()
            logger.info("Daily runner stopped")

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Daily Trading Runner')
    parser.add_argument('--rl-model', type=str, default=None,
                       help='Path to RL model (default: auto-detect)')
    parser.add_argument('--no-rl', action='store_true',
                       help='Disable RL predictions')
    parser.add_argument('--dry-run', action='store_true',
                       help='Dry run mode - no orders executed')
    parser.add_argument('--paper', action='store_true',
                       help='Use paper trading account (default: from config)')
    parser.add_argument('--shadow', action='store_true',
                       help='Shadow mode - capture all signals without trading')
    parser.add_argument('--save-signals', type=str, default=None,
                       help='Path to save captured signals (requires --shadow)')
    
    args = parser.parse_args()
    
    rl_model_path = None if args.no_rl else args.rl_model
    
    runner = DailyTradingRunner(
        rl_model_path=rl_model_path,
        dry_run=args.dry_run,
        paper_trading=args.paper,
        shadow=args.shadow,
        save_signals_path=args.save_signals
    )
    runner.run()

if __name__ == '__main__':
    main()

