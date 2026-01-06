"""
Alert Manager
Sends alerts through multiple channels (email, Slack, Telegram, macOS)
"""
import os
import json
import logging
import subprocess
import smtplib
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, List
import requests

from .alert_config import AlertConfig

logger = logging.getLogger(__name__)

# State file path
STATE_DIR = Path(__file__).parent.parent.parent / 'logs'
ALERT_STATE_FILE = STATE_DIR / 'alert_state.json'
ALERT_LOG_FILE = STATE_DIR / 'alerts.log'


class AlertLevel(Enum):
    """Alert severity levels"""
    DEBUG = 'debug'
    INFO = 'info'
    WARNING = 'warning'
    ERROR = 'error'
    CRITICAL = 'critical'


class AlertManager:
    """
    Multi-channel alert manager for TradeNova
    
    Supports:
    - Email (SMTP)
    - macOS Notifications
    - Slack (webhook)
    - Telegram Bot
    
    Features:
    - Cooldown to prevent alert spam
    - Alert state persistence
    - Multiple severity levels
    """
    
    def __init__(self, config: Optional[AlertConfig] = None):
        """Initialize alert manager with optional custom config"""
        self.config = config or AlertConfig()
        self.alert_state = self._load_state()
    
    def _load_state(self) -> Dict:
        """Load alert state from file"""
        if ALERT_STATE_FILE.exists():
            try:
                with open(ALERT_STATE_FILE) as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load alert state: {e}")
        return {'last_alerts': {}, 'alert_count': 0, 'daily_counts': {}}
    
    def _save_state(self):
        """Save alert state to file"""
        try:
            STATE_DIR.mkdir(parents=True, exist_ok=True)
            with open(ALERT_STATE_FILE, 'w') as f:
                json.dump(self.alert_state, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save alert state: {e}")
    
    def _can_alert(self, alert_type: str) -> bool:
        """Check if we can send this alert (respects cooldown)"""
        last_alert = self.alert_state['last_alerts'].get(alert_type)
        if not last_alert:
            return True
        
        try:
            last_time = datetime.fromisoformat(last_alert)
            cooldown = timedelta(minutes=self.config.alert_cooldown_minutes)
            if datetime.now() - last_time > cooldown:
                return True
        except (ValueError, TypeError):
            return True
        
        return False
    
    def send_alert(
        self,
        alert_type: str,
        title: str,
        message: str,
        level: AlertLevel = AlertLevel.WARNING,
        force: bool = False,
        data: Optional[Dict] = None
    ) -> bool:
        """
        Send alert through configured channels
        
        Args:
            alert_type: Unique identifier for the alert type (for cooldown)
            title: Alert title/subject
            message: Alert message body
            level: Alert severity level
            force: Force send even if in cooldown
            data: Optional additional data to include
            
        Returns:
            True if alert was sent, False if blocked by cooldown
        """
        if not force and not self._can_alert(alert_type):
            logger.debug(f"Alert {alert_type} blocked by cooldown")
            return False
        
        # Update state
        now = datetime.now()
        self.alert_state['last_alerts'][alert_type] = now.isoformat()
        self.alert_state['alert_count'] += 1
        
        # Track daily counts
        today = now.strftime('%Y-%m-%d')
        if today not in self.alert_state['daily_counts']:
            self.alert_state['daily_counts'] = {today: 0}
        self.alert_state['daily_counts'][today] = \
            self.alert_state['daily_counts'].get(today, 0) + 1
        
        self._save_state()
        
        # Log the alert
        self._log_alert(alert_type, title, message, level)
        
        # Send through channels
        sent_to = []
        
        # macOS Notification
        if self.config.enable_macos_notifications:
            if self._send_macos_notification(title, message, level):
                sent_to.append('macos')
        
        # Email
        if self.config.enable_email_alerts and self.config.email_configured:
            if self._send_email(title, message, level, data):
                sent_to.append('email')
        
        # Slack
        if self.config.enable_slack_alerts and self.config.slack_configured:
            if self._send_slack(title, message, level, data):
                sent_to.append('slack')
        
        # Telegram
        if self.config.enable_telegram_alerts and self.config.telegram_configured:
            if self._send_telegram(title, message, level, data):
                sent_to.append('telegram')
        
        logger.info(f"Alert sent [{level.value}]: {title} (channels: {sent_to})")
        return bool(sent_to)
    
    def _log_alert(self, alert_type: str, title: str, message: str, level: AlertLevel):
        """Write alert to log file and logging system"""
        # Log to Python logger
        log_method = getattr(logger, level.value if level.value != 'critical' else 'error')
        log_method(f"ALERT [{level.value.upper()}] {title}: {message}")
        
        # Write to dedicated alert log
        try:
            STATE_DIR.mkdir(parents=True, exist_ok=True)
            with open(ALERT_LOG_FILE, 'a') as f:
                entry = f"{datetime.now().isoformat()} | {level.value.upper():8} | {alert_type:20} | {title} | {message}\n"
                f.write(entry)
        except Exception as e:
            logger.error(f"Failed to write alert log: {e}")
    
    def _send_macos_notification(self, title: str, message: str, level: AlertLevel) -> bool:
        """Send macOS notification"""
        try:
            # Choose sound based on severity
            sounds = {
                AlertLevel.DEBUG: 'Pop',
                AlertLevel.INFO: 'Ping',
                AlertLevel.WARNING: 'Purr',
                AlertLevel.ERROR: 'Basso',
                AlertLevel.CRITICAL: 'Sosumi'
            }
            sound = sounds.get(level, 'Ping')
            
            # Escape special characters
            title_escaped = title.replace('"', '\\"')
            message_escaped = message.replace('"', '\\"')[:200]  # Limit length
            
            script = f'''
            display notification "{message_escaped}" with title "TradeNova" subtitle "{title_escaped}" sound name "{sound}"
            '''
            
            result = subprocess.run(
                ['osascript', '-e', script],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
            
        except Exception as e:
            logger.debug(f"macOS notification failed: {e}")
            return False
    
    def _send_email(self, title: str, message: str, level: AlertLevel, data: Optional[Dict] = None) -> bool:
        """Send email alert"""
        try:
            msg = MIMEMultipart('alternative')
            msg['From'] = self.config.smtp_user
            msg['To'] = self.config.alert_email
            msg['Subject'] = f"[TradeNova {level.value.upper()}] {title}"
            
            # Plain text version
            text_body = f"""
TradeNova Alert
===============
Severity: {level.value.upper()}
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Type: {title}

Message:
{message}
"""
            if data:
                text_body += f"\nAdditional Data:\n{json.dumps(data, indent=2, default=str)}"
            
            text_body += """
---
This is an automated alert from TradeNova.
To configure alerts, update your .env file.
"""
            
            # HTML version
            html_body = f"""
<html>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; padding: 20px;">
    <div style="max-width: 600px; margin: 0 auto; background: #f5f5f5; padding: 20px; border-radius: 10px;">
        <h2 style="color: {'#d32f2f' if level in [AlertLevel.ERROR, AlertLevel.CRITICAL] else '#ff9800' if level == AlertLevel.WARNING else '#1976d2'};">
            TradeNova Alert: {title}
        </h2>
        <table style="width: 100%; margin: 20px 0;">
            <tr><td style="color: #666;"><strong>Severity:</strong></td><td>{level.value.upper()}</td></tr>
            <tr><td style="color: #666;"><strong>Time:</strong></td><td>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</td></tr>
        </table>
        <div style="background: white; padding: 15px; border-radius: 5px; margin: 15px 0;">
            <p style="white-space: pre-wrap;">{message}</p>
        </div>
        {'<pre style="background: #f0f0f0; padding: 10px; border-radius: 5px; font-size: 12px; overflow-x: auto;">' + json.dumps(data, indent=2, default=str) + '</pre>' if data else ''}
        <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
        <p style="color: #999; font-size: 12px;">This is an automated alert from TradeNova.</p>
    </div>
</body>
</html>
"""
            
            msg.attach(MIMEText(text_body, 'plain'))
            msg.attach(MIMEText(html_body, 'html'))
            
            with smtplib.SMTP(self.config.smtp_server, self.config.smtp_port, timeout=10) as server:
                server.starttls()
                server.login(self.config.smtp_user, self.config.smtp_password)
                server.send_message(msg)
            
            logger.debug(f"Email alert sent to {self.config.alert_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
            return False
    
    def _send_slack(self, title: str, message: str, level: AlertLevel, data: Optional[Dict] = None) -> bool:
        """Send Slack alert via webhook"""
        try:
            # Choose color based on severity
            colors = {
                AlertLevel.DEBUG: '#808080',
                AlertLevel.INFO: '#36a64f',
                AlertLevel.WARNING: '#ff9800',
                AlertLevel.ERROR: '#d32f2f',
                AlertLevel.CRITICAL: '#b71c1c'
            }
            
            payload = {
                'channel': self.config.slack_channel,
                'attachments': [{
                    'color': colors.get(level, '#808080'),
                    'title': f"TradeNova Alert: {title}",
                    'text': message,
                    'fields': [
                        {'title': 'Severity', 'value': level.value.upper(), 'short': True},
                        {'title': 'Time', 'value': datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'short': True}
                    ],
                    'footer': 'TradeNova Alert System',
                    'ts': int(datetime.now().timestamp())
                }]
            }
            
            response = requests.post(
                self.config.slack_webhook_url,
                json=payload,
                timeout=10
            )
            
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Failed to send Slack alert: {e}")
            return False
    
    def _send_telegram(self, title: str, message: str, level: AlertLevel, data: Optional[Dict] = None) -> bool:
        """Send Telegram alert via bot"""
        try:
            # Choose emoji based on severity
            emojis = {
                AlertLevel.DEBUG: '🔍',
                AlertLevel.INFO: 'ℹ️',
                AlertLevel.WARNING: '⚠️',
                AlertLevel.ERROR: '❌',
                AlertLevel.CRITICAL: '🚨'
            }
            
            text = f"""
{emojis.get(level, '📢')} *TradeNova Alert*

*{title}*
_{level.value.upper()}_

{message}

_Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_
"""
            
            url = f"https://api.telegram.org/bot{self.config.telegram_bot_token}/sendMessage"
            payload = {
                'chat_id': self.config.telegram_chat_id,
                'text': text,
                'parse_mode': 'Markdown'
            }
            
            response = requests.post(url, json=payload, timeout=10)
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Failed to send Telegram alert: {e}")
            return False
    
    def get_alert_stats(self) -> Dict:
        """Get alert statistics"""
        today = datetime.now().strftime('%Y-%m-%d')
        return {
            'total_alerts': self.alert_state.get('alert_count', 0),
            'alerts_today': self.alert_state.get('daily_counts', {}).get(today, 0),
            'last_alerts': self.alert_state.get('last_alerts', {}),
            'channels_configured': self.config.validate()
        }
    
    def test_alerts(self) -> Dict:
        """Send test alerts to all configured channels"""
        results = {}
        
        if self.config.enable_macos_notifications:
            results['macos'] = self._send_macos_notification(
                "Test Alert", "This is a test from TradeNova", AlertLevel.INFO
            )
        
        if self.config.enable_email_alerts and self.config.email_configured:
            results['email'] = self._send_email(
                "Test Alert", "This is a test email from TradeNova", AlertLevel.INFO
            )
        
        if self.config.enable_slack_alerts and self.config.slack_configured:
            results['slack'] = self._send_slack(
                "Test Alert", "This is a test from TradeNova", AlertLevel.INFO
            )
        
        if self.config.enable_telegram_alerts and self.config.telegram_configured:
            results['telegram'] = self._send_telegram(
                "Test Alert", "This is a test from TradeNova", AlertLevel.INFO
            )
        
        return results


# Global alert manager instance
_alert_manager: Optional[AlertManager] = None


def get_alert_manager() -> AlertManager:
    """Get or create global alert manager instance"""
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = AlertManager()
    return _alert_manager


def send_alert(
    alert_type: str,
    title: str,
    message: str,
    level: AlertLevel = AlertLevel.WARNING,
    **kwargs
) -> bool:
    """Convenience function to send alert via global manager"""
    return get_alert_manager().send_alert(alert_type, title, message, level, **kwargs)


