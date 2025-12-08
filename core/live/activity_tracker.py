"""
Activity Tracker
Tracks current system activity for real-time dashboard display
Production-grade with atomic writes and consistent schema
"""
import logging
import os
import json
from datetime import datetime, timezone
from typing import Dict, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class ActivityTracker:
    """Tracks current system activity with atomic writes"""
    
    # Status constants
    STATUS_IDLE = 'idle'
    STATUS_SCANNING = 'scanning'
    STATUS_ANALYZING = 'analyzing'
    STATUS_EXECUTING = 'executing'
    STATUS_MONITORING = 'monitoring'
    STATUS_ERROR = 'error'
    
    def __init__(self, activity_file: str = "logs/current_activity.json"):
        self.activity_file = Path(activity_file)
        self.temp_file = self.activity_file.with_suffix('.tmp')
        self.activity_file.parent.mkdir(exist_ok=True)
    
    def update_activity(
        self,
        status: str,
        ticker: Optional[str] = None,
        message: Optional[str] = None,
        details: Optional[str] = None,
        step: Optional[int] = None,
        total_steps: Optional[int] = None,
        cycle_id: Optional[str] = None
    ):
        """
        Update current activity with atomic write
        
        Args:
            status: One of STATUS_IDLE, STATUS_SCANNING, etc.
            ticker: Current ticker being processed (if applicable)
            message: Short headline message
            details: Detailed description
            step: Current step number (for progress)
            total_steps: Total steps (for progress)
            cycle_id: Optional cycle identifier
        """
        # Build activity object with consistent schema
        activity = {
            'status': status.upper(),
            'ticker': ticker,
            'message': message or self._default_message(status),
            'details': details or '',
            'last_updated': datetime.now(timezone.utc).isoformat(),
            'step': step,
            'total_steps': total_steps,
            'cycle_id': cycle_id
        }
        
        # Atomic write: write to temp file, then replace
        try:
            # Write to temporary file first
            with open(self.temp_file, 'w') as f:
                json.dump(activity, f, indent=2)
            
            # Atomic replace
            os.replace(self.temp_file, self.activity_file)
            
        except Exception as e:
            logger.error(f"Error updating activity: {e}")
            # Clean up temp file if it exists
            try:
                if self.temp_file.exists():
                    self.temp_file.unlink()
            except:
                pass
    
    def _default_message(self, status: str) -> str:
        """Get default message for status"""
        messages = {
            'idle': 'Idle – waiting for next cycle',
            'scanning': 'Scanning tickers for opportunities',
            'analyzing': 'Analyzing ticker',
            'executing': 'Executing trade',
            'monitoring': 'Monitoring positions',
            'error': 'Error occurred'
        }
        return messages.get(status.lower(), 'Unknown status')
    
    def get_current_activity(self) -> Dict:
        """
        Get current activity with safe error handling
        
        Returns:
            Activity dictionary with consistent schema
        """
        default_activity = {
            'status': 'IDLE',
            'ticker': None,
            'message': 'No recent activity',
            'details': 'System is idle or activity tracking unavailable',
            'last_updated': datetime.now(timezone.utc).isoformat(),
            'step': None,
            'total_steps': None,
            'cycle_id': None
        }
        
        try:
            if not self.activity_file.exists():
                return default_activity
            
            with open(self.activity_file, 'r') as f:
                activity = json.load(f)
            
            # Validate and normalize schema
            return {
                'status': activity.get('status', 'IDLE').upper(),
                'ticker': activity.get('ticker') or activity.get('current_ticker'),
                'message': activity.get('message') or activity.get('action', 'Unknown'),
                'details': activity.get('details', ''),
                'last_updated': activity.get('last_updated') or activity.get('timestamp'),
                'step': activity.get('step'),
                'total_steps': activity.get('total_steps'),
                'cycle_id': activity.get('cycle_id')
            }
            
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON in activity file: {e}")
            return default_activity
        except Exception as e:
            logger.debug(f"Error reading activity: {e}")
            return default_activity
    
    def clear_activity(self):
        """Clear activity (set to idle)"""
        self.update_activity(
            status=self.STATUS_IDLE,
            message='System idle',
            details='Waiting for next trading cycle'
        )

