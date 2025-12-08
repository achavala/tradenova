"""
Activity Heartbeat
Periodically updates activity tracker to show system is alive
"""
import logging
import threading
import time
from datetime import datetime, timezone
from core.live.activity_tracker import ActivityTracker

logger = logging.getLogger(__name__)

class ActivityHeartbeat:
    """Heartbeat mechanism to keep activity tracker updated"""
    
    def __init__(self, activity_tracker: ActivityTracker, interval_seconds: int = 30):
        """
        Initialize heartbeat
        
        Args:
            activity_tracker: ActivityTracker instance to update
            interval_seconds: How often to update (default: 30 seconds)
        """
        self.activity_tracker = activity_tracker
        self.interval_seconds = interval_seconds
        self.running = False
        self.thread = None
    
    def start(self):
        """Start heartbeat thread"""
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self.thread.start()
        logger.info(f"💓 Activity heartbeat started (updates every {self.interval_seconds}s)")
    
    def stop(self):
        """Stop heartbeat thread"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
        logger.info("💓 Activity heartbeat stopped")
    
    def _heartbeat_loop(self):
        """Heartbeat loop - updates activity tracker periodically"""
        while self.running:
            try:
                # Get current activity
                current = self.activity_tracker.get_current_activity()
                status = current.get('status', 'IDLE')
                
                # Update timestamp for all states to show system is alive
                # This preserves the current status and details but refreshes the timestamp
                # Active states (SCANNING, ANALYZING, EXECUTING) will still be updated
                # by the trading cycle, but this keeps the timestamp fresh
                self.activity_tracker.update_activity(
                    status=status,
                    ticker=current.get('ticker'),
                    message=current.get('message', 'System ready'),
                    details=current.get('details', 'Waiting for next trading cycle'),
                    step=current.get('step'),
                    total_steps=current.get('total_steps'),
                    cycle_id=current.get('cycle_id')
                )
                
            except Exception as e:
                logger.debug(f"Error in heartbeat: {e}")
            
            # Sleep for interval
            time.sleep(self.interval_seconds)

