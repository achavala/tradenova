"""
Macro Event Calendar Service
Fetches macro economic events (FOMC, CPI, NFP, Fed speakers, etc.)
"""
import logging
from typing import List, Dict, Optional
from datetime import datetime, date, timedelta
import requests
from config import Config

logger = logging.getLogger(__name__)

class MacroCalendar:
    """
    Macro event calendar service
    
    Tracks:
    - FOMC meetings
    - CPI releases
    - NFP (Non-Farm Payrolls)
    - Fed speakers
    - Other macro events
    """
    
    def __init__(self):
        """Initialize macro calendar"""
        self.massive_api_key = Config.MASSIVE_API_KEY
        
        # Cache for macro events
        self._events_cache: List[Dict] = []
        self._cache_date = None
    
    def get_macro_events(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        lookahead_days: int = 90
    ) -> List[Dict]:
        """
        Get macro events in date range
        
        Args:
            start_date: Start date (defaults to today)
            end_date: End date (defaults to today + lookahead_days)
            lookahead_days: Days to look ahead if end_date not provided
            
        Returns:
            List of event dicts with: {date, type, description}
        """
        if start_date is None:
            start_date = date.today()
        
        if end_date is None:
            end_date = start_date + timedelta(days=lookahead_days)
        
        # Check cache
        today = date.today()
        if self._cache_date != today:
            self._events_cache = []
            self._cache_date = today
        
        # Filter cached events
        cached_events = [
            e for e in self._events_cache
            if start_date <= e['date'] <= end_date
        ]
        
        if cached_events:
            return cached_events
        
        # Fetch new events
        events = []
        
        # Get FOMC meetings
        fomc_events = self._get_fomc_meetings(start_date, end_date)
        events.extend(fomc_events)
        
        # Get CPI releases
        cpi_events = self._get_cpi_releases(start_date, end_date)
        events.extend(cpi_events)
        
        # Get NFP releases
        nfp_events = self._get_nfp_releases(start_date, end_date)
        events.extend(nfp_events)
        
        # Get Fed speakers (major events only)
        fed_speaker_events = self._get_fed_speakers(start_date, end_date)
        events.extend(fed_speaker_events)
        
        # Cache events
        self._events_cache.extend(events)
        self._events_cache = sorted(self._events_cache, key=lambda x: x['date'])
        
        return events
    
    def _get_fomc_meetings(
        self,
        start_date: date,
        end_date: date
    ) -> List[Dict]:
        """
        Get FOMC meeting dates
        
        FOMC typically meets 8 times per year:
        - January, March, May, June, July, September, November, December
        
        Args:
            start_date: Start date
            end_date: End date
            
        Returns:
            List of FOMC event dicts
        """
        events = []
        
        # FOMC meeting pattern (approximate - actual dates vary)
        # Typically: 2nd Tuesday/Wednesday of the month
        current_date = start_date
        
        while current_date <= end_date:
            # Check if this month might have FOMC
            # FOMC months: Jan, Mar, May, Jun, Jul, Sep, Nov, Dec
            fomc_months = [1, 3, 5, 6, 7, 9, 11, 12]
            
            if current_date.month in fomc_months:
                # Approximate: 2nd Tuesday of month
                first_day = date(current_date.year, current_date.month, 1)
                # Find first Tuesday
                days_until_tuesday = (1 - first_day.weekday()) % 7
                if days_until_tuesday == 0:
                    days_until_tuesday = 7
                first_tuesday = first_day + timedelta(days=days_until_tuesday)
                # Second Tuesday
                fomc_date = first_tuesday + timedelta(days=7)
                
                if start_date <= fomc_date <= end_date:
                    events.append({
                        'date': fomc_date,
                        'type': 'FOMC',
                        'description': f'Federal Open Market Committee Meeting - {fomc_date.strftime("%B %Y")}'
                    })
            
            # Move to next month
            if current_date.month == 12:
                current_date = date(current_date.year + 1, 1, 1)
            else:
                current_date = date(current_date.year, current_date.month + 1, 1)
        
        return events
    
    def _get_cpi_releases(
        self,
        start_date: date,
        end_date: date
    ) -> List[Dict]:
        """
        Get CPI (Consumer Price Index) release dates
        
        CPI is typically released around the 10th-15th of each month
        
        Args:
            start_date: Start date
            end_date: End date
            
        Returns:
            List of CPI event dicts
        """
        events = []
        current_date = start_date
        
        while current_date <= end_date:
            # CPI typically released around 10th-15th of month
            # Approximate: 13th of month
            cpi_date = date(current_date.year, current_date.month, 13)
            
            # Adjust if weekend
            if cpi_date.weekday() >= 5:  # Saturday or Sunday
                # Move to next Monday
                days_to_monday = (7 - cpi_date.weekday()) % 7
                if days_to_monday == 0:
                    days_to_monday = 1
                cpi_date = cpi_date + timedelta(days=days_to_monday)
            
            if start_date <= cpi_date <= end_date:
                events.append({
                    'date': cpi_date,
                    'type': 'CPI',
                    'description': f'Consumer Price Index Release - {cpi_date.strftime("%B %Y")}'
                })
            
            # Move to next month
            if current_date.month == 12:
                current_date = date(current_date.year + 1, 1, 1)
            else:
                current_date = date(current_date.year, current_date.month + 1, 1)
        
        return events
    
    def _get_nfp_releases(
        self,
        start_date: date,
        end_date: date
    ) -> List[Dict]:
        """
        Get NFP (Non-Farm Payrolls) release dates
        
        NFP is typically released on the first Friday of each month
        
        Args:
            start_date: Start date
            end_date: End date
            
        Returns:
            List of NFP event dicts
        """
        events = []
        current_date = start_date
        
        while current_date <= end_date:
            # NFP is first Friday of month
            first_day = date(current_date.year, current_date.month, 1)
            # Find first Friday
            days_until_friday = (4 - first_day.weekday()) % 7
            if days_until_friday == 0 and first_day.weekday() != 4:
                days_until_friday = 7
            nfp_date = first_day + timedelta(days=days_until_friday)
            
            if start_date <= nfp_date <= end_date:
                events.append({
                    'date': nfp_date,
                    'type': 'NFP',
                    'description': f'Non-Farm Payrolls Release - {nfp_date.strftime("%B %Y")}'
                })
            
            # Move to next month
            if current_date.month == 12:
                current_date = date(current_date.year + 1, 1, 1)
            else:
                current_date = date(current_date.year, current_date.month + 1, 1)
        
        return events
    
    def _get_fed_speakers(
        self,
        start_date: date,
        end_date: date
    ) -> List[Dict]:
        """
        Get major Fed speaker events
        
        This is a simplified version - in production, you'd fetch from:
        - Fed calendar API
        - Economic calendar services
        - News feeds
        
        Args:
            start_date: Start date
            end_date: End date
            
        Returns:
            List of Fed speaker event dicts (major events only)
        """
        # For now, return empty - can be enhanced with actual Fed calendar
        # Major Fed speeches are typically scheduled and can be scraped
        return []
    
    def update_gap_risk_monitor(
        self,
        gap_risk_monitor,
        lookahead_days: int = 90
    ):
        """
        Update Gap Risk Monitor with macro events
        
        Args:
            gap_risk_monitor: GapRiskMonitor instance
            lookahead_days: Days to look ahead
        """
        events = self.get_macro_events(lookahead_days=lookahead_days)
        
        for event in events:
            gap_risk_monitor.add_macro_event(
                event['date'],
                event['type'],
                event['description']
            )
        
        logger.info(f"Updated Gap Risk Monitor with {len(events)} macro events")




