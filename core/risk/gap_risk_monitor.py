"""
Gap Risk Monitor
Identifies and reacts to high-impact events (earnings, FOMC, macro) that cause price gaps
Critical for 0-30 DTE options trading
"""
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, date, timedelta
from enum import Enum

logger = logging.getLogger(__name__)

class GapRiskLevel(Enum):
    """Gap risk levels"""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class GapRiskMonitor:
    """
    Monitor for gap risk events
    
    Tracks:
    - Earnings announcements
    - FOMC meetings
    - CPI releases
    - Fed speakers
    - Other macro events
    
    Rules:
    - Earnings ≤ 3 days: Reduce size by 50%, block new trades
    - Earnings today: Force exit before close
    - FOMC/CPI: Block new trades, reduce size
    """
    
    def __init__(self):
        """Initialize Gap Risk Monitor"""
        # Event calendar (can be loaded from external source)
        self.earnings_calendar: Dict[str, List[date]] = {}  # symbol -> [earnings dates]
        self.macro_events: List[Dict] = []  # [{date, type, description}]
        
        # Risk thresholds
        self.earnings_warning_days = 3  # Warn/restrict 3 days before earnings
        self.earnings_block_days = 1  # Block new trades 1 day before earnings
        self.macro_warning_days = 1  # Warn 1 day before macro events
        
    def add_earnings_date(self, symbol: str, earnings_date: date):
        """
        Add earnings date for a symbol
        
        Args:
            symbol: Stock symbol
            earnings_date: Earnings announcement date
        """
        if symbol not in self.earnings_calendar:
            self.earnings_calendar[symbol] = []
        
        if earnings_date not in self.earnings_calendar[symbol]:
            self.earnings_calendar[symbol].append(earnings_date)
            self.earnings_calendar[symbol].sort()
            logger.info(f"Added earnings date for {symbol}: {earnings_date}")
    
    def add_macro_event(self, event_date: date, event_type: str, description: str = ""):
        """
        Add macro event (FOMC, CPI, etc.)
        
        Args:
            event_date: Event date
            event_type: Event type (FOMC, CPI, FED_SPEAKER, etc.)
            description: Event description
        """
        event = {
            'date': event_date,
            'type': event_type,
            'description': description
        }
        
        if event not in self.macro_events:
            self.macro_events.append(event)
            self.macro_events.sort(key=lambda x: x['date'])
            logger.info(f"Added macro event: {event_type} on {event_date}")
    
    def get_gap_risk(
        self,
        symbol: str,
        current_date: Optional[date] = None
    ) -> Tuple[GapRiskLevel, str, Dict]:
        """
        Get gap risk for a symbol
        
        Args:
            symbol: Stock symbol
            current_date: Current date (defaults to today)
            
        Returns:
            Tuple of (risk_level, reason, details)
        """
        if current_date is None:
            current_date = datetime.now().date()
        
        details = {
            'earnings_days_away': None,
            'earnings_date': None,
            'macro_events': [],
            'position_size_multiplier': 1.0,
            'block_new_trades': False,
            'force_exit': False
        }
        
        # Check earnings
        earnings_risk = self._check_earnings_risk(symbol, current_date)
        if earnings_risk:
            risk_level, reason, earnings_details = earnings_risk
            details.update(earnings_details)
            return (risk_level, reason, details)
        
        # Check macro events
        macro_risk = self._check_macro_risk(current_date)
        if macro_risk:
            risk_level, reason, macro_details = macro_risk
            details.update(macro_details)
            return (risk_level, reason, details)
        
        # No gap risk
        return (GapRiskLevel.NONE, "No gap risk events", details)
    
    def _check_earnings_risk(
        self,
        symbol: str,
        current_date: date
    ) -> Optional[Tuple[GapRiskLevel, str, Dict]]:
        """Check earnings risk for symbol"""
        if symbol not in self.earnings_calendar:
            return None
        
        earnings_dates = self.earnings_calendar[symbol]
        
        for earnings_date in earnings_dates:
            days_away = (earnings_date - current_date).days
            
            # Earnings today - CRITICAL
            if days_away == 0:
                return (
                    GapRiskLevel.CRITICAL,
                    f"Earnings TODAY for {symbol} - force exit before close",
                    {
                        'earnings_days_away': 0,
                        'earnings_date': earnings_date,
                        'position_size_multiplier': 0.0,  # Block all new trades
                        'block_new_trades': True,
                        'force_exit': True
                    }
                )
            
            # Earnings tomorrow - HIGH
            elif days_away == 1:
                return (
                    GapRiskLevel.HIGH,
                    f"Earnings TOMORROW for {symbol} - block new trades, reduce size",
                    {
                        'earnings_days_away': 1,
                        'earnings_date': earnings_date,
                        'position_size_multiplier': 0.0,  # Block new trades
                        'block_new_trades': True,
                        'force_exit': False
                    }
                )
            
            # Earnings in 2-3 days - MEDIUM
            elif 2 <= days_away <= self.earnings_warning_days:
                return (
                    GapRiskLevel.MEDIUM,
                    f"Earnings in {days_away} days for {symbol} - reduce size by 50%",
                    {
                        'earnings_days_away': days_away,
                        'earnings_date': earnings_date,
                        'position_size_multiplier': 0.5,  # 50% size reduction
                        'block_new_trades': False,
                        'force_exit': False
                    }
                )
            
            # Earnings in 4-7 days - LOW
            elif 4 <= days_away <= 7:
                return (
                    GapRiskLevel.LOW,
                    f"Earnings in {days_away} days for {symbol} - monitor closely",
                    {
                        'earnings_days_away': days_away,
                        'earnings_date': earnings_date,
                        'position_size_multiplier': 0.8,  # 20% size reduction
                        'block_new_trades': False,
                        'force_exit': False
                    }
                )
        
        return None
    
    def _check_macro_risk(
        self,
        current_date: date
    ) -> Optional[Tuple[GapRiskLevel, str, Dict]]:
        """Check macro event risk with time-based blocking"""
        import pytz
        from datetime import datetime, time as dt_time
        
        ET = pytz.timezone('America/New_York')
        now_et = datetime.now(ET)
        current_time = now_et.time()
        
        relevant_events = []
        
        for event in self.macro_events:
            days_away = (event['date'] - current_date).days
            
            # Event today or tomorrow
            if 0 <= days_away <= self.macro_warning_days:
                relevant_events.append({
                    'event': event,
                    'days_away': days_away
                })
        
        if not relevant_events:
            return None
        
        # Determine risk level based on event type
        critical_events = ['FOMC', 'CPI', 'NFP']  # Non-farm payrolls
        high_events = ['FED_SPEAKER', 'ECB', 'BOJ']
        
        event_types = [e['event']['type'] for e in relevant_events]
        today_events = [e for e in relevant_events if e['days_away'] == 0]
        
        # Time-based blocking for same-day events
        # NFP/CPI: Released at 8:30 AM ET, volatile until ~10:30 AM
        # FOMC: Released at 2:00 PM ET, volatile until ~3:30 PM
        block_trades = False
        
        for event in today_events:
            event_type = event['event']['type']
            if event_type in ['NFP', 'CPI']:
                # Block from 8:00 AM to 10:30 AM ET
                volatile_start = dt_time(8, 0)
                volatile_end = dt_time(10, 30)
                if volatile_start <= current_time <= volatile_end:
                    block_trades = True
                    logger.info(f"Blocking trades: {event_type} volatile window {volatile_start}-{volatile_end} ET (current: {current_time})")
            elif event_type == 'FOMC':
                # Block from 1:30 PM to 3:30 PM ET
                volatile_start = dt_time(13, 30)
                volatile_end = dt_time(15, 30)
                if volatile_start <= current_time <= volatile_end:
                    block_trades = True
                    logger.info(f"Blocking trades: {event_type} volatile window {volatile_start}-{volatile_end} ET (current: {current_time})")
        
        if any(et in critical_events for et in event_types):
            risk_level = GapRiskLevel.HIGH
            reason = f"Critical macro event: {', '.join(event_types)}"
        elif any(et in high_events for et in event_types):
            risk_level = GapRiskLevel.MEDIUM
            reason = f"Macro event: {', '.join(event_types)}"
        else:
            risk_level = GapRiskLevel.MEDIUM
            reason = f"Macro event: {', '.join(event_types)}"
        
        # Only block during volatile time windows, not all day
        if not block_trades and today_events:
            logger.info(f"Outside volatile window for {event_types} - trading allowed with reduced size")
        
        return (
            risk_level,
            reason,
            {
                'macro_events': relevant_events,
                'position_size_multiplier': 0.5 if risk_level == GapRiskLevel.HIGH else 0.8,
                'block_new_trades': block_trades,  # Only block during volatile windows
                'force_exit': False
            }
        )
    
    def can_trade(
        self,
        symbol: str,
        current_date: Optional[date] = None
    ) -> Tuple[bool, str]:
        """
        Check if trading is allowed for symbol
        
        Args:
            symbol: Stock symbol
            current_date: Current date (defaults to today)
            
        Returns:
            Tuple of (allowed, reason)
        """
        risk_level, reason, details = self.get_gap_risk(symbol, current_date)
        
        if details.get('block_new_trades', False):
            return (False, reason)
        
        if details.get('force_exit', False):
            return (False, reason)
        
        return (True, reason)
    
    def get_position_size_multiplier(
        self,
        symbol: str,
        current_date: Optional[date] = None
    ) -> float:
        """
        Get position size multiplier based on gap risk
        
        Args:
            symbol: Stock symbol
            current_date: Current date (defaults to today)
            
        Returns:
            Multiplier (0.0 to 1.0)
        """
        _, _, details = self.get_gap_risk(symbol, current_date)
        return details.get('position_size_multiplier', 1.0)
    
    def should_force_exit(
        self,
        symbol: str,
        current_date: Optional[date] = None
    ) -> bool:
        """
        Check if position should be forced to exit
        
        Args:
            symbol: Stock symbol
            current_date: Current date (defaults to today)
            
        Returns:
            True if position should be forced to exit
        """
        _, _, details = self.get_gap_risk(symbol, current_date)
        return details.get('force_exit', False)
    
    def get_all_risks(
        self,
        symbols: List[str],
        current_date: Optional[date] = None
    ) -> Dict[str, Dict]:
        """
        Get gap risk for multiple symbols
        
        Args:
            symbols: List of stock symbols
            current_date: Current date (defaults to today)
            
        Returns:
            Dictionary mapping symbol -> gap risk details
        """
        if current_date is None:
            current_date = datetime.now().date()
        
        risks = {}
        
        for symbol in symbols:
            risk_level, reason, details = self.get_gap_risk(symbol, current_date)
            risks[symbol] = {
                'risk_level': risk_level.value,
                'reason': reason,
                **details
            }
        
        return risks




