#!/usr/bin/env python3
"""
TradeNova Watchdog - Process Monitoring and Health Checking

This script monitors the trading system and sends alerts when issues are detected.
Run this as a separate LaunchAgent to ensure trading never goes unnoticed.
"""

import os
import sys
import json
import logging
import subprocess
import smtplib
from datetime import datetime, timedelta
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Dict, List
import pytz

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Configuration
LOG_DIR = PROJECT_ROOT / "logs"
WATCHDOG_LOG = LOG_DIR / "watchdog.log"
ALERT_STATE_FILE = LOG_DIR / "watchdog_state.json"

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(WATCHDOG_LOG),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('watchdog')


class AlertManager:
    """Manages alerts via multiple channels"""
    
    def __init__(self):
        self.alert_state = self._load_state()
        
        # Email config from environment
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_user = os.getenv('SMTP_USER', '')
        self.smtp_password = os.getenv('SMTP_PASSWORD', '')
        self.alert_email = os.getenv('ALERT_EMAIL', '')
        
        # Cooldown to prevent alert spam (minutes)
        self.alert_cooldown = int(os.getenv('ALERT_COOLDOWN_MINUTES', '30'))
    
    def _load_state(self) -> Dict:
        """Load alert state from file"""
        if ALERT_STATE_FILE.exists():
            try:
                with open(ALERT_STATE_FILE) as f:
                    return json.load(f)
            except:
                pass
        return {'last_alerts': {}, 'alert_count': 0}
    
    def _save_state(self):
        """Save alert state to file"""
        try:
            with open(ALERT_STATE_FILE, 'w') as f:
                json.dump(self.alert_state, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save alert state: {e}")
    
    def _can_alert(self, alert_type: str) -> bool:
        """Check if we can send this alert type (respects cooldown)"""
        last_alert = self.alert_state['last_alerts'].get(alert_type)
        if not last_alert:
            return True
        
        try:
            last_time = datetime.fromisoformat(last_alert)
            if datetime.now() - last_time > timedelta(minutes=self.alert_cooldown):
                return True
        except:
            return True
        
        return False
    
    def send_alert(self, alert_type: str, title: str, message: str, severity: str = 'warning'):
        """Send alert via configured channels"""
        if not self._can_alert(alert_type):
            logger.debug(f"Skipping alert {alert_type} - in cooldown period")
            return
        
        # Update state
        self.alert_state['last_alerts'][alert_type] = datetime.now().isoformat()
        self.alert_state['alert_count'] += 1
        self._save_state()
        
        # Log the alert
        log_method = logger.error if severity == 'critical' else logger.warning
        log_method(f"ALERT [{severity.upper()}] {title}: {message}")
        
        # Send email if configured
        if self.smtp_user and self.alert_email:
            self._send_email(title, message, severity)
        
        # Send macOS notification
        self._send_macos_notification(title, message, severity)
        
        # Write to alert log file
        self._write_alert_log(alert_type, title, message, severity)
    
    def _send_email(self, title: str, message: str, severity: str):
        """Send email alert"""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.smtp_user
            msg['To'] = self.alert_email
            msg['Subject'] = f"[TradeNova {severity.upper()}] {title}"
            
            body = f"""
TradeNova Alert
===============
Severity: {severity.upper()}
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

{message}

---
This is an automated alert from TradeNova Watchdog.
            """
            msg.attach(MIMEText(body, 'plain'))
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"Email alert sent to {self.alert_email}")
            
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
    
    def _send_macos_notification(self, title: str, message: str, severity: str):
        """Send macOS notification"""
        try:
            sound = 'Basso' if severity == 'critical' else 'Ping'
            script = f'''
            display notification "{message}" with title "TradeNova Alert" subtitle "{title}" sound name "{sound}"
            '''
            subprocess.run(['osascript', '-e', script], capture_output=True)
            logger.debug("macOS notification sent")
        except Exception as e:
            logger.debug(f"Failed to send macOS notification: {e}")
    
    def _write_alert_log(self, alert_type: str, title: str, message: str, severity: str):
        """Write alert to dedicated log file"""
        alert_log = LOG_DIR / "alerts.log"
        try:
            with open(alert_log, 'a') as f:
                f.write(f"{datetime.now().isoformat()} | {severity.upper()} | {alert_type} | {title} | {message}\n")
        except Exception as e:
            logger.error(f"Failed to write alert log: {e}")


class TradingWatchdog:
    """Main watchdog class for monitoring trading system health"""
    
    def __init__(self):
        self.alert_manager = AlertManager()
        self.et_tz = pytz.timezone('US/Eastern')
    
    def is_market_hours(self) -> bool:
        """Check if we're in market hours (9:30 AM - 4:00 PM ET)"""
        now_et = datetime.now(self.et_tz)
        
        # Skip weekends
        if now_et.weekday() >= 5:  # Saturday=5, Sunday=6
            return False
        
        market_open = now_et.replace(hour=9, minute=30, second=0, microsecond=0)
        market_close = now_et.replace(hour=16, minute=0, second=0, microsecond=0)
        
        return market_open <= now_et <= market_close
    
    def is_trading_hours(self) -> bool:
        """Check if we're in expected trading hours (8 AM - 5 PM ET)"""
        now_et = datetime.now(self.et_tz)
        
        # Skip weekends
        if now_et.weekday() >= 5:
            return False
        
        start = now_et.replace(hour=8, minute=0, second=0, microsecond=0)
        end = now_et.replace(hour=17, minute=0, second=0, microsecond=0)
        
        return start <= now_et <= end
    
    def check_process_running(self) -> Dict:
        """Check if trading process is running"""
        result = {
            'running': False,
            'pid': None,
            'uptime': None,
            'cpu': None,
            'memory': None
        }
        
        try:
            # Check for python run_daily.py process
            ps_output = subprocess.run(
                ['pgrep', '-f', 'run_daily.py'],
                capture_output=True,
                text=True
            )
            
            if ps_output.returncode == 0:
                pid = ps_output.stdout.strip().split('\n')[0]
                result['running'] = True
                result['pid'] = int(pid)
                
                # Get process details
                ps_detail = subprocess.run(
                    ['ps', '-p', pid, '-o', 'etime=,pcpu=,pmem='],
                    capture_output=True,
                    text=True
                )
                
                if ps_detail.returncode == 0:
                    parts = ps_detail.stdout.strip().split()
                    if len(parts) >= 3:
                        result['uptime'] = parts[0]
                        result['cpu'] = parts[1]
                        result['memory'] = parts[2]
        
        except Exception as e:
            logger.error(f"Error checking process: {e}")
        
        return result
    
    def check_recent_log_activity(self, max_age_minutes: int = 10) -> Dict:
        """Check for recent log activity"""
        result = {
            'has_recent_activity': False,
            'last_log_time': None,
            'last_log_age_minutes': None,
            'errors_in_last_hour': 0
        }
        
        error_log = LOG_DIR / "trading_automation.error.log"
        
        if not error_log.exists():
            return result
        
        try:
            # Get last modification time
            mtime = error_log.stat().st_mtime
            last_time = datetime.fromtimestamp(mtime)
            age_minutes = (datetime.now() - last_time).total_seconds() / 60
            
            result['last_log_time'] = last_time.isoformat()
            result['last_log_age_minutes'] = round(age_minutes, 1)
            result['has_recent_activity'] = age_minutes < max_age_minutes
            
            # Count recent errors
            one_hour_ago = datetime.now() - timedelta(hours=1)
            with open(error_log, 'r') as f:
                # Read last 1000 lines
                lines = f.readlines()[-1000:]
                for line in lines:
                    if 'ERROR' in line:
                        try:
                            timestamp_str = line.split(' - ')[0]
                            log_time = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S,%f')
                            if log_time > one_hour_ago:
                                result['errors_in_last_hour'] += 1
                        except:
                            continue
        
        except Exception as e:
            logger.error(f"Error checking logs: {e}")
        
        return result
    
    def check_launchd_status(self) -> Dict:
        """Check launchd status of trading service"""
        result = {
            'loaded': False,
            'running': False,
            'pid': None,
            'exit_code': None
        }
        
        try:
            launchctl = subprocess.run(
                ['launchctl', 'list', 'com.tradenova.trading'],
                capture_output=True,
                text=True
            )
            
            if launchctl.returncode == 0:
                result['loaded'] = True
                
                # Parse output
                for line in launchctl.stdout.split('\n'):
                    if 'PID' in line or line.strip().isdigit():
                        parts = line.strip().split()
                        if parts:
                            try:
                                result['pid'] = int(parts[0])
                                result['running'] = True
                            except:
                                pass
        
        except Exception as e:
            logger.error(f"Error checking launchd: {e}")
        
        return result
    
    def check_account_connectivity(self) -> Dict:
        """Check if we can connect to Alpaca"""
        result = {
            'connected': False,
            'account_status': None,
            'balance': None,
            'error': None
        }
        
        try:
            from dotenv import load_dotenv
            load_dotenv(PROJECT_ROOT / '.env')
            
            from alpaca_client import AlpacaClient
            client = AlpacaClient(paper=True)
            account = client.get_account()
            
            if account:
                result['connected'] = True
                result['account_status'] = account.get('status')
                result['balance'] = float(account.get('equity', 0))
        
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"Account connectivity check failed: {e}")
        
        return result
    
    def run_health_check(self) -> Dict:
        """Run full health check"""
        logger.info("Running health check...")
        
        health = {
            'timestamp': datetime.now().isoformat(),
            'is_trading_hours': self.is_trading_hours(),
            'is_market_hours': self.is_market_hours(),
            'process': self.check_process_running(),
            'logs': self.check_recent_log_activity(),
            'launchd': self.check_launchd_status(),
            'overall_status': 'healthy'
        }
        
        issues = []
        
        # Check process status during trading hours
        if health['is_trading_hours']:
            if not health['process']['running']:
                issues.append('Trading process not running during market hours')
                self.alert_manager.send_alert(
                    'process_down',
                    'Trading Process Down',
                    'The trading process is not running during market hours. Launchd should restart it automatically.',
                    'critical'
                )
            
            # Check for stale logs during market hours
            if health['is_market_hours']:
                if not health['logs']['has_recent_activity']:
                    age = health['logs'].get('last_log_age_minutes', 'unknown')
                    issues.append(f'No log activity in {age} minutes')
                    self.alert_manager.send_alert(
                        'stale_logs',
                        'No Trading Activity',
                        f'No log activity in {age} minutes. System may be frozen.',
                        'warning'
                    )
        
        # Check for high error rate
        if health['logs']['errors_in_last_hour'] > 100:
            issues.append(f"High error rate: {health['logs']['errors_in_last_hour']} errors in last hour")
            self.alert_manager.send_alert(
                'high_errors',
                'High Error Rate Detected',
                f"Detected {health['logs']['errors_in_last_hour']} errors in the last hour. Check logs immediately.",
                'warning'
            )
        
        # Update overall status
        if issues:
            health['overall_status'] = 'degraded' if len(issues) == 1 else 'unhealthy'
            health['issues'] = issues
        
        # Log result
        status_emoji = '✅' if health['overall_status'] == 'healthy' else '⚠️' if health['overall_status'] == 'degraded' else '❌'
        logger.info(f"{status_emoji} Health check complete: {health['overall_status']}")
        
        # Save health status to file
        health_file = LOG_DIR / "health_status.json"
        try:
            with open(health_file, 'w') as f:
                json.dump(health, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save health status: {e}")
        
        return health
    
    def try_restart_process(self):
        """Attempt to restart the trading process via launchd"""
        logger.warning("Attempting to restart trading process...")
        
        try:
            # Unload and reload the launch agent
            subprocess.run(
                ['launchctl', 'unload', os.path.expanduser('~/Library/LaunchAgents/com.tradenova.trading.plist')],
                capture_output=True
            )
            subprocess.run(
                ['launchctl', 'load', os.path.expanduser('~/Library/LaunchAgents/com.tradenova.trading.plist')],
                capture_output=True
            )
            
            logger.info("Restart command sent")
            
            self.alert_manager.send_alert(
                'restart_triggered',
                'Process Restart Triggered',
                'Trading process restart was triggered by watchdog.',
                'info'
            )
            
        except Exception as e:
            logger.error(f"Failed to restart process: {e}")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='TradeNova Watchdog')
    parser.add_argument('--check', action='store_true', help='Run single health check')
    parser.add_argument('--daemon', action='store_true', help='Run as daemon (continuous monitoring)')
    parser.add_argument('--interval', type=int, default=5, help='Check interval in minutes (for daemon mode)')
    parser.add_argument('--test-alert', action='store_true', help='Send test alert')
    args = parser.parse_args()
    
    watchdog = TradingWatchdog()
    
    if args.test_alert:
        watchdog.alert_manager.send_alert(
            'test',
            'Test Alert',
            'This is a test alert from TradeNova Watchdog.',
            'info'
        )
        return
    
    if args.check:
        health = watchdog.run_health_check()
        print(json.dumps(health, indent=2, default=str))
        return
    
    if args.daemon:
        import time
        logger.info(f"Starting watchdog daemon (interval: {args.interval} minutes)")
        
        while True:
            try:
                watchdog.run_health_check()
            except Exception as e:
                logger.error(f"Health check failed: {e}")
            
            time.sleep(args.interval * 60)
    
    # Default: single check
    health = watchdog.run_health_check()
    print(json.dumps(health, indent=2, default=str))


if __name__ == '__main__':
    main()


