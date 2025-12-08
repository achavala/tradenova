"""
News and Event Filter
Blocks trading during high-impact news events
"""
import logging
from typing import Dict, List, Set, Optional
from datetime import datetime, time
import re

logger = logging.getLogger(__name__)

class NewsFilter:
    """Filters trading during news events"""
    
    # High-impact events
    FOMC_MEETINGS = [
        # Add FOMC meeting dates (example format)
        # "2024-01-31", "2024-03-20", etc.
    ]
    
    ECONOMIC_RELEASES = {
        'cpi': ['08:30', '12:00'],  # CPI release times
        'ppi': ['08:30', '12:00'],  # PPI release times
        'unemployment': ['08:30'],  # Jobs report
        'gdp': ['08:30'],  # GDP release
    }
    
    # Days of week to avoid (0=Monday, 6=Sunday)
    AVOID_DAYS = set()  # Empty by default
    
    # Time windows to avoid (market hours only)
    AVOID_TIME_WINDOWS = [
        (time(8, 30), time(9, 15)),  # Pre-market volatility
        (time(15, 45), time(16, 0)),  # Close volatility
    ]
    
    def __init__(
        self,
        block_fomc: bool = True,
        block_economic_releases: bool = True,
        block_time_windows: bool = True,
        block_high_volatility: bool = True,
        vix_threshold: float = 30.0
    ):
        """
        Initialize news filter
        
        Args:
            block_fomc: Block trading during FOMC meetings
            block_economic_releases: Block during economic releases
            block_time_windows: Block during volatile time windows
            block_high_volatility: Block when VIX is high
            vix_threshold: VIX threshold for blocking
        """
        self.block_fomc = block_fomc
        self.block_economic_releases = block_economic_releases
        self.block_time_windows = block_time_windows
        self.block_high_volatility = block_high_volatility
        self.vix_threshold = vix_threshold
        
        # Track current VIX (would be updated from market data)
        self.current_vix = None
    
    def is_blocked(self, current_time: Optional[datetime] = None) -> tuple:
        """
        Check if trading should be blocked
        
        Args:
            current_time: Current time (default: now)
            
        Returns:
            (is_blocked, reason)
        """
        if current_time is None:
            current_time = datetime.now()
        
        # Check FOMC meetings
        if self.block_fomc:
            date_str = current_time.strftime('%Y-%m-%d')
            if date_str in self.FOMC_MEETINGS:
                return True, f"FOMC meeting on {date_str}"
        
        # Check economic releases
        if self.block_economic_releases:
            current_time_str = current_time.strftime('%H:%M')
            for release_type, times in self.ECONOMIC_RELEASES.items():
                if current_time_str in times:
                    return True, f"{release_type.upper()} release at {current_time_str}"
        
        # Check time windows
        if self.block_time_windows:
            current_time_only = current_time.time()
            for start_time, end_time in self.AVOID_TIME_WINDOWS:
                if start_time <= current_time_only <= end_time:
                    return True, f"Volatile time window {start_time}-{end_time}"
        
        # Check day of week
        if current_time.weekday() in self.AVOID_DAYS:
            return True, f"Avoid trading on {current_time.strftime('%A')}"
        
        # Check VIX
        if self.block_high_volatility and self.current_vix:
            if self.current_vix > self.vix_threshold:
                return True, f"VIX {self.current_vix:.1f} exceeds threshold {self.vix_threshold:.1f}"
        
        return False, None
    
    def update_vix(self, vix_value: float):
        """Update current VIX value"""
        self.current_vix = vix_value
    
    def add_fomc_date(self, date_str: str):
        """Add FOMC meeting date"""
        self.FOMC_MEETINGS.append(date_str)
        logger.info(f"Added FOMC date: {date_str}")
    
    def add_economic_release(self, release_type: str, time_str: str):
        """Add economic release time"""
        if release_type not in self.ECONOMIC_RELEASES:
            self.ECONOMIC_RELEASES[release_type] = []
        self.ECONOMIC_RELEASES[release_type].append(time_str)
        logger.info(f"Added {release_type} release at {time_str}")
    
    def get_status(self) -> Dict:
        """Get current filter status"""
        is_blocked, reason = self.is_blocked()
        return {
            'is_blocked': is_blocked,
            'reason': reason,
            'current_vix': self.current_vix,
            'vix_threshold': self.vix_threshold,
            'fomc_blocked': self.block_fomc,
            'economic_releases_blocked': self.block_economic_releases,
            'time_windows_blocked': self.block_time_windows
        }

