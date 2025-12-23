"""
TradeNova Main Execution Script
"""
import logging
import time
import schedule
from datetime import datetime
from colorama import init, Fore, Style

from tradenova import TradeNova
from config import Config

# Initialize colorama for colored output
init(autoreset=True)

# Configure logging
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('tradenova.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class TradeNovaRunner:
    """Main runner for TradeNova agent"""
    
    def __init__(self):
        """Initialize runner"""
        self.agent = TradeNova()
        self.running = False
    
    def run_cycle(self):
        """Run one trading cycle"""
        try:
            logger.info("="*80)
            logger.info("Starting trading cycle")
            logger.info("="*80)
            
            # Sync positions with Alpaca
            self.agent.sync_positions()
            
            # Monitor existing positions
            self.agent.monitor_positions()
            
            # Scan for new opportunities
            self.agent.scan_and_trade()
            
            # Print status
            self.agent.print_status()
            
            logger.info("Trading cycle completed")
            
        except Exception as e:
            logger.error(f"Error in trading cycle: {e}", exc_info=True)
    
    def run_daily_close(self):
        """Run daily close routine"""
        try:
            logger.info("Running daily close routine")
            self.agent.run_daily_close()
            logger.info("Daily close completed")
        except Exception as e:
            logger.error(f"Error in daily close: {e}", exc_info=True)
    
    def start(self, mode: str = 'continuous'):
        """
        Start TradeNova agent
        
        Args:
            mode: 'continuous' for continuous monitoring, 'once' for single run
        """
        print(Fore.CYAN + Style.BRIGHT + """
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║                          TRADENOVA TRADING AGENT                            ║
║                                                                              ║
║  Advanced Options Trading System with Profit Target Scaling                 ║
║  Goal: Turn $10K into $400K in one year                                     ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
        """ + Style.RESET_ALL)
        
        logger.info("TradeNova starting...")
        logger.info(f"Mode: {mode}")
        logger.info(f"Tickers: {', '.join(Config.TICKERS)}")
        logger.info(f"Max Active Trades: {Config.MAX_ACTIVE_TRADES}")
        logger.info(f"Position Size: {Config.POSITION_SIZE_PCT*100}% of previous day balance")
        logger.info(f"Stop Loss: {Config.STOP_LOSS_PCT*100}%")
        
        if mode == 'once':
            # Run once
            self.run_cycle()
        else:
            # Continuous mode
            self.running = True
            
            # Schedule trading cycles (every 5 minutes during market hours)
            schedule.every(5).minutes.do(self.run_cycle)
            
            # Schedule daily close (at market close: 4:00 PM ET)
            schedule.every().day.at("16:00").do(self.run_daily_close)
            
            # Run initial cycle
            self.run_cycle()
            
            print(Fore.GREEN + "\nTradeNova is running. Press Ctrl+C to stop.\n" + Style.RESET_ALL)
            
            try:
                while self.running:
                    schedule.run_pending()
                    time.sleep(1)
            except KeyboardInterrupt:
                print(Fore.YELLOW + "\n\nStopping TradeNova..." + Style.RESET_ALL)
                self.running = False
                logger.info("TradeNova stopped by user")
                
                # Final status
                self.agent.print_status()
                
                # Run final daily close
                self.run_daily_close()

def main():
    """Main entry point"""
    import sys
    
    mode = 'continuous'
    if len(sys.argv) > 1:
        mode = sys.argv[1]
    
    runner = TradeNovaRunner()
    runner.start(mode=mode)

if __name__ == '__main__':
    main()


