#!/usr/bin/env python3
"""
Update Calendars Script
Updates earnings and macro event calendars for Gap Risk Monitor
Run daily to keep calendars current
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
from datetime import date
from services.earnings_calendar import EarningsCalendar
from services.macro_calendar import MacroCalendar
from core.risk.gap_risk_monitor import GapRiskMonitor
from config import Config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def update_calendars():
    """Update earnings and macro event calendars"""
    
    print("="*80)
    print("CALENDAR UPDATE")
    print("="*80)
    print(f"Date: {date.today().strftime('%Y-%m-%d')}\n")
    
    # Initialize services
    earnings_cal = EarningsCalendar()
    macro_cal = MacroCalendar()
    gap_risk = GapRiskMonitor()
    
    # Update earnings calendar
    print("Updating Earnings Calendar...")
    print("-" * 80)
    
    earnings_cal.update_gap_risk_monitor(
        gap_risk,
        Config.TICKERS,
        lookahead_days=90
    )
    
    # Count earnings dates
    earnings_count = sum(
        len(gap_risk.earnings_calendar.get(symbol, []))
        for symbol in Config.TICKERS
    )
    print(f"\n✅ Earnings dates: {earnings_count} total")
    
    # Show upcoming earnings
    today = date.today()
    upcoming = []
    for symbol in Config.TICKERS:
        if symbol in gap_risk.earnings_calendar:
            for earnings_date in gap_risk.earnings_calendar[symbol]:
                if earnings_date >= today:
                    days_away = (earnings_date - today).days
                    upcoming.append((symbol, earnings_date, days_away))
    
    if upcoming:
        upcoming.sort(key=lambda x: x[1])
        print(f"\nUpcoming earnings (next 30 days):")
        for symbol, earnings_date, days_away in upcoming[:10]:
            print(f"  {symbol}: {earnings_date} ({days_away} days)")
    
    print()
    
    # Update macro calendar
    print("Updating Macro Event Calendar...")
    print("-" * 80)
    
    macro_cal.update_gap_risk_monitor(gap_risk, lookahead_days=90)
    
    # Count macro events
    macro_count = len(gap_risk.macro_events)
    print(f"\n✅ Macro events: {macro_count} total")
    
    # Show upcoming events
    upcoming_macro = [
        e for e in gap_risk.macro_events
        if e['date'] >= today
    ]
    
    if upcoming_macro:
        upcoming_macro.sort(key=lambda x: x['date'])
        print(f"\nUpcoming macro events (next 30 days):")
        for event in upcoming_macro[:10]:
            days_away = (event['date'] - today).days
            print(f"  {event['type']}: {event['date']} ({days_away} days) - {event['description']}")
    
    print()
    
    print("="*80)
    print("CALENDAR UPDATE COMPLETE")
    print("="*80)
    print()
    print("Summary:")
    print(f"  Earnings dates: {earnings_count}")
    print(f"  Macro events: {macro_count}")
    print()
    print("💡 Run this script daily to keep calendars current")
    
    return True

if __name__ == "__main__":
    success = update_calendars()
    sys.exit(0 if success else 1)




