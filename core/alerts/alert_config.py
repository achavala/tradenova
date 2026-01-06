"""
Alert Configuration
Manages alert settings from environment variables
"""
import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


@dataclass
class AlertConfig:
    """Alert configuration loaded from environment"""
    
    # Email Settings
    smtp_server: str = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    smtp_port: int = int(os.getenv('SMTP_PORT', '587'))
    smtp_user: str = os.getenv('SMTP_USER', '')
    smtp_password: str = os.getenv('SMTP_PASSWORD', '')
    alert_email: str = os.getenv('ALERT_EMAIL', '')
    
    # Slack Settings (optional)
    slack_webhook_url: str = os.getenv('SLACK_WEBHOOK_URL', '')
    slack_channel: str = os.getenv('SLACK_CHANNEL', '#trading-alerts')
    
    # Telegram Settings (optional)
    telegram_bot_token: str = os.getenv('TELEGRAM_BOT_TOKEN', '')
    telegram_chat_id: str = os.getenv('TELEGRAM_CHAT_ID', '')
    
    # Alert Behavior
    alert_cooldown_minutes: int = int(os.getenv('ALERT_COOLDOWN_MINUTES', '30'))
    enable_macos_notifications: bool = os.getenv('ENABLE_MACOS_NOTIFICATIONS', 'true').lower() == 'true'
    enable_email_alerts: bool = os.getenv('ENABLE_EMAIL_ALERTS', 'true').lower() == 'true'
    enable_slack_alerts: bool = os.getenv('ENABLE_SLACK_ALERTS', 'false').lower() == 'true'
    enable_telegram_alerts: bool = os.getenv('ENABLE_TELEGRAM_ALERTS', 'false').lower() == 'true'
    
    # Alert Thresholds
    error_threshold_per_hour: int = int(os.getenv('ERROR_THRESHOLD_PER_HOUR', '100'))
    stale_log_threshold_minutes: int = int(os.getenv('STALE_LOG_THRESHOLD_MINUTES', '10'))
    daily_loss_threshold_pct: float = float(os.getenv('DAILY_LOSS_THRESHOLD_PCT', '5.0'))
    
    @property
    def email_configured(self) -> bool:
        """Check if email is properly configured"""
        return bool(self.smtp_user and self.smtp_password and self.alert_email)
    
    @property
    def slack_configured(self) -> bool:
        """Check if Slack is properly configured"""
        return bool(self.slack_webhook_url)
    
    @property
    def telegram_configured(self) -> bool:
        """Check if Telegram is properly configured"""
        return bool(self.telegram_bot_token and self.telegram_chat_id)
    
    def validate(self) -> dict:
        """Validate configuration and return status"""
        return {
            'email': {
                'configured': self.email_configured,
                'enabled': self.enable_email_alerts,
                'status': 'ready' if self.email_configured and self.enable_email_alerts else 'disabled'
            },
            'slack': {
                'configured': self.slack_configured,
                'enabled': self.enable_slack_alerts,
                'status': 'ready' if self.slack_configured and self.enable_slack_alerts else 'disabled'
            },
            'telegram': {
                'configured': self.telegram_configured,
                'enabled': self.enable_telegram_alerts,
                'status': 'ready' if self.telegram_configured and self.enable_telegram_alerts else 'disabled'
            },
            'macos': {
                'configured': True,
                'enabled': self.enable_macos_notifications,
                'status': 'ready' if self.enable_macos_notifications else 'disabled'
            }
        }


