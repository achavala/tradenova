#!/usr/bin/env python3
"""
TradeNova Daemon - Runs trading scheduler continuously
Auto-restarts on failure, logs everything, runs in background
"""
import sys
import os
import signal
import time
import logging
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from core.live.integrated_trader import IntegratedTrader
from core.live.trading_scheduler import TradingScheduler
from config import Config

# Setup logging
log_dir = Path('logs')
log_dir.mkdir(exist_ok=True)

# Setup error handler separately (FileHandler doesn't accept level parameter)
error_handler = logging.FileHandler(log_dir / 'tradenova_daemon_error.log')
error_handler.setLevel(logging.ERROR)

logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / 'tradenova_daemon.log'),
        error_handler,
    ]
)
logger = logging.getLogger(__name__)

class TradeNovaDaemon:
    """Daemon that runs trading scheduler continuously"""
    
    def __init__(self, paper_trading=True, dry_run=False):
        self.paper_trading = paper_trading
        self.dry_run = dry_run
        self.running = True
        self.restart_count = 0
        self.max_restarts = 1000  # Prevent infinite restart loops
        self.restart_delay = 5  # Seconds to wait before restart
        
        # Setup signal handlers
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        
        # PID file
        self.pid_file = Path('tradenova_daemon.pid')
        
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False
    
    def _write_pid(self):
        """Write PID file"""
        try:
            with open(self.pid_file, 'w') as f:
                f.write(str(os.getpid()))
        except Exception as e:
            logger.error(f"Failed to write PID file: {e}")
    
    def _remove_pid(self):
        """Remove PID file"""
        try:
            if self.pid_file.exists():
                self.pid_file.unlink()
        except Exception as e:
            logger.error(f"Failed to remove PID file: {e}")
    
    def run(self):
        """Main daemon loop"""
        logger.info("="*70)
        logger.info("TRADENOVA DAEMON STARTING")
        logger.info("="*70)
        logger.info(f"Paper Trading: {self.paper_trading}")
        logger.info(f"Dry Run: {self.dry_run}")
        logger.info(f"PID: {os.getpid()}")
        
        self._write_pid()
        
        while self.running and self.restart_count < self.max_restarts:
            try:
                logger.info(f"\n{'='*70}")
                logger.info(f"Starting trading scheduler (attempt {self.restart_count + 1})")
                logger.info(f"{'='*70}\n")
                
                # Setup and start the daily trading runner (which includes scheduler)
                from run_daily import DailyTradingRunner
                runner = DailyTradingRunner(
                    dry_run=self.dry_run,
                    paper_trading=self.paper_trading
                )
                
                # Start the runner (this starts the scheduler)
                logger.info("Trading scheduler started - running continuously...")
                
                # Run the scheduler in the main thread (it blocks, which is what we want)
                # This will keep running until stopped
                try:
                    runner.run()  # This calls scheduler.start() internally
                except KeyboardInterrupt:
                    logger.info("Received keyboard interrupt in runner")
                    runner.scheduler.stop()
                
                # If we get here, the scheduler stopped
                logger.info("Scheduler stopped, will restart if running flag is still True")
                break
                
            except KeyboardInterrupt:
                logger.info("Received keyboard interrupt, shutting down...")
                self.running = False
                break
                
            except Exception as e:
                self.restart_count += 1
                logger.error(f"Error in trading scheduler (attempt {self.restart_count}): {e}", exc_info=True)
                
                if self.running and self.restart_count < self.max_restarts:
                    logger.info(f"Restarting in {self.restart_delay} seconds...")
                    time.sleep(self.restart_delay)
                else:
                    logger.error(f"Max restarts ({self.max_restarts}) reached, shutting down")
                    self.running = False
        
        self._remove_pid()
        logger.info("TradeNova daemon stopped")

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='TradeNova Daemon')
    parser.add_argument('--paper', action='store_true', help='Use paper trading')
    parser.add_argument('--dry-run', action='store_true', help='Dry run mode')
    parser.add_argument('--daemon', action='store_true', help='Run as daemon (fork to background)')
    
    args = parser.parse_args()
    
    # Default to paper trading
    paper_trading = args.paper if args.paper else True
    dry_run = args.dry_run
    
    if args.daemon:
        # Fork to background
        try:
            pid = os.fork()
            if pid > 0:
                # Parent process
                print(f"Daemon started with PID: {pid}")
                sys.exit(0)
            else:
                # Child process
                os.setsid()  # Create new session
                os.chdir('/')  # Change to root directory
                os.umask(0)  # Reset file mode
                
                # Close file descriptors
                for fd in range(3):
                    try:
                        os.close(fd)
                    except:
                        pass
        except OSError as e:
            logger.error(f"Failed to fork daemon: {e}")
            sys.exit(1)
    
    daemon = TradeNovaDaemon(paper_trading=paper_trading, dry_run=dry_run)
    daemon.run()

if __name__ == '__main__':
    main()

