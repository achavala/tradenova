"""
Trading Scheduler
Automated scheduling for trading activities
"""
import logging
import schedule
import time
from datetime import datetime, time as dt_time
from typing import Callable, Optional
import pytz

logger = logging.getLogger(__name__)

# Market timezone (Eastern Time)
ET = pytz.timezone('America/New_York')

class TradingScheduler:
    """Scheduler for automated trading"""
    
    def __init__(self):
        """Initialize scheduler"""
        self.jobs = []
        self.running = False
        
    def schedule_pre_market_warmup(self, callback: Callable, time_str: str = "08:00"):
        """
        Schedule pre-market warmup
        
        Args:
            callback: Function to call
            time_str: Time in HH:MM format
        """
        job = schedule.every().day.at(time_str).do(callback)
        self.jobs.append(('pre_market_warmup', job))
        logger.info(f"Scheduled pre-market warmup at {time_str}")
    
    def schedule_market_open(self, callback: Callable, time_str: str = "09:30"):
        """
        Schedule market open activation
        
        Args:
            callback: Function to call
            time_str: Time in HH:MM format
        """
        job = schedule.every().day.at(time_str).do(callback)
        self.jobs.append(('market_open', job))
        logger.info(f"Scheduled market open at {time_str}")
    
    def schedule_market_close_flatten(self, callback: Callable, time_str: str = "15:50"):
        """
        Schedule position flattening before market close
        
        Args:
            callback: Function to call
            time_str: Time in HH:MM format
        """
        job = schedule.every().day.at(time_str).do(callback)
        self.jobs.append(('market_close_flatten', job))
        logger.info(f"Scheduled market close flatten at {time_str}")
    
    def schedule_daily_report(self, callback: Callable, time_str: str = "16:05"):
        """
        Schedule daily report generation
        
        Args:
            callback: Function to call
            time_str: Time in HH:MM format
        """
        job = schedule.every().day.at(time_str).do(callback)
        self.jobs.append(('daily_report', job))
        logger.info(f"Scheduled daily report at {time_str}")
    
    def schedule_recurring(self, callback: Callable, interval_minutes: int = 5):
        """
        Schedule recurring task
        
        Args:
            callback: Function to call
            interval_minutes: Interval in minutes
        """
        job = schedule.every(interval_minutes).minutes.do(callback)
        self.jobs.append(('recurring', job))
        logger.info(f"Scheduled recurring task every {interval_minutes} minutes")
    
    def start(self):
        """Start scheduler"""
        self.running = True
        logger.info("Trading scheduler started")
        
        try:
            while self.running:
                schedule.run_pending()
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Scheduler stopped by user")
            self.stop()
    
    def stop(self):
        """Stop scheduler"""
        self.running = False
        schedule.clear()
        self.jobs = []
        logger.info("Trading scheduler stopped")
    
    def is_market_hours(self) -> bool:
        """Check if current time is during market hours (Eastern Time)"""
        # Use Eastern Time for market hours
        et_now = datetime.now(ET).time()
        market_open = dt_time(9, 30)
        market_close = dt_time(16, 0)
        
        is_open = market_open <= et_now <= market_close
        logger.debug(f"Market hours check: ET={et_now}, open={market_open}, close={market_close}, is_open={is_open}")
        return is_open
    
    def is_pre_market(self) -> bool:
        """Check if current time is pre-market (Eastern Time)"""
        et_now = datetime.now(ET).time()
        pre_market_start = dt_time(4, 0)
        market_open = dt_time(9, 30)
        
        return pre_market_start <= et_now < market_open
    
    def is_after_hours(self) -> bool:
        """Check if current time is after hours (Eastern Time)"""
        et_now = datetime.now(ET).time()
        market_close = dt_time(16, 0)
        after_hours_end = dt_time(20, 0)
        
        return market_close < et_now <= after_hours_end

