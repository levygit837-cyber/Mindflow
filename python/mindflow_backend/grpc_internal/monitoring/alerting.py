"""Alerting system for gRPC monitoring.

Provides proactive notifications for performance issues, service degradation,
and critical events with multiple notification channels.
"""

from __future__ import annotations

import asyncio
import smtplib
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

try:
    from email.mime.multipart import MimeMultipart
    from email.mime.text import MimeText
except ImportError:
    MimeText = None
    MimeMultipart = None

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertStatus(Enum):
    """Alert status states."""
    ACTIVE = "active"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"
    ACKNOWLEDGED = "acknowledged"


class NotificationChannel(Enum):
    """Notification channel types."""
    WEBHOOK = "webhook"
    EMAIL = "email"
    SLACK = "slack"
    LOG = "log"
    CALLBACK = "callback"


@dataclass
class AlertCondition:
    """Alert condition definition."""
    name: str
    metric_name: str
    threshold_value: float
    comparison_operator: str  # ">", "<", ">=", "<=", "=="
    severity: AlertSeverity
    duration_seconds: float = 0.0  # 0 = instant, >0 = sustained
    cooldown_seconds: float = 300.0  # 5 minutes between same alerts
    
    def evaluate(self, current_value: float, duration_seconds: float) -> bool:
        """Evaluate if alert condition is met."""
        # Check threshold
        threshold_met = self._compare_values(current_value, self.threshold_value, self.comparison_operator)
        
        # Check duration requirement
        if self.duration_seconds > 0:
            duration_met = duration_seconds >= self.duration_seconds
        else:
            duration_met = True
        
        return threshold_met and duration_met
    
    def _compare_values(self, current: float, threshold: float, operator: str) -> bool:
        """Compare values based on operator."""
        if operator == ">":
            return current > threshold
        elif operator == "<":
            return current < threshold
        elif operator == ">=":
            return current >= threshold
        elif operator == "<=":
            return current <= threshold
        elif operator == "==":
            return abs(current - threshold) < 0.001  # Float comparison
        else:
            return False


@dataclass
class AlertConfig:
    """Configuration for alerting system."""
    
    # General settings
    enabled: bool = True
    max_active_alerts: int = 1000
    alert_retention_hours: int = 24 * 7  # 1 week
    
    # Notification settings
    notification_channels: list[NotificationChannel] = field(default_factory=lambda: [NotificationChannel.LOG])
    webhook_url: str | None = None
    webhook_timeout_seconds: float = 10.0
    webhook_retry_attempts: int = 3
    
    # Email settings
    smtp_server: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    email_from: str | None = None
    email_to: list[str] = field(default_factory=list)
    
    # Slack settings
    slack_webhook_url: str | None = None
    slack_channel: str | None = None
    
    # Rate limiting
    enable_rate_limiting: bool = True
    max_alerts_per_hour: int = 50
    rate_limit_window_hours: int = 1
    
    # Deduplication
    enable_deduplication: bool = True
    deduplication_window_minutes: int = 10


@dataclass
class Alert:
    """Alert instance."""
    
    id: str
    condition_name: str
    severity: AlertSeverity
    status: AlertStatus
    current_value: float
    threshold_value: float
    message: str
    created_at: float
    updated_at: float
    resolved_at: float | None = None
    acknowledged_at: float | None = None
    notification_sent: dict[str, float] = field(default_factory=dict)
    
    @property
    def age_seconds(self) -> float:
        """Get alert age in seconds."""
        return time.time() - self.created_at
    
    @property
    def is_active(self) -> bool:
        """Check if alert is active."""
        return self.status == AlertStatus.ACTIVE
    
    @property
    def duration_seconds(self) -> float:
        """Get alert duration in seconds."""
        if self.resolved_at:
            return self.resolved_at - self.created_at
        return time.time() - self.created_at


class AlertManager:
    """Manages alert conditions, notifications, and alert lifecycle."""
    
    def __init__(self, config: AlertConfig | None = None):
        self.config = config or AlertConfig()
        
        # Alert management
        self._conditions: dict[str, AlertCondition] = {}
        self._active_alerts: dict[str, Alert] = {}
        self._alert_history: deque = deque(maxlen=self.config.max_active_alerts)
        self._alert_lock = threading.Lock()
        
        # Rate limiting
        self._alert_timestamps: deque = deque(maxlen=1000)
        
        # Metrics
        self._metrics = {
            'total_alerts': 0,
            'alerts_by_severity': {s.value: 0 for s in AlertSeverity},
            'alerts_by_condition': {},
            'notifications_sent': 0,
            'notifications_failed': 0,
        }
        
        _logger.info(
            "alert_manager_initialized",
            enabled=self.config.enabled,
            channels=[c.value for c in self.config.notification_channels]
        )
    
    def add_condition(self, condition: AlertCondition) -> None:
        """Add an alert condition."""
        self._conditions[condition.name] = condition
        _logger.info("alert_condition_added", name=condition.name, severity=condition.severity.value)
    
    def remove_condition(self, condition_name: str) -> None:
        """Remove an alert condition."""
        if condition_name in self._conditions:
            del self._conditions[condition_name]
            _logger.info("alert_condition_removed", name=condition_name)
    
    def evaluate_metric(self, metric_name: str, value: float, metadata: dict[str, Any] | None = None) -> None:
        """Evaluate metric against alert conditions."""
        if not self.config.enabled:
            return
        
        current_time = time.time()
        
        with self._alert_lock:
            for condition_name, condition in self._conditions.items():
                if condition.metric_name != metric_name:
                    continue
                
                # Get duration for this condition
                duration = self._get_condition_duration(condition_name, current_time)
                
                # Check if alert should be triggered
                if condition.evaluate(value, duration):
                    self._trigger_alert(condition, value, metadata)
                else:
                    # Check if existing alert should be resolved
                    self._resolve_alert_if_needed(condition_name, value, duration)
    
    def _get_condition_duration(self, condition_name: str, current_time: float) -> float:
        """Get duration for which condition has been failing."""
        if condition_name not in self._active_alerts:
            return 0.0
        
        alert = self._active_alerts[condition_name]
        
        # Find when the condition started failing
        for hist_alert in reversed(self._alert_history):
            if (hist_alert.condition_name == condition_name and 
                hist_alert.status == AlertStatus.ACTIVE):
                return current_time - hist_alert.created_at
        
        return current_time - alert.created_at
    
    def _trigger_alert(self, condition: AlertCondition, value: float, metadata: dict[str, Any] | None) -> None:
        """Trigger a new alert or update existing one."""
        alert_id = f"{condition.name}_{int(time.time())}"
        
        # Check rate limiting
        if self.config.enable_rate_limiting and self._is_rate_limited(condition.name):
            _logger.warning("alert_rate_limited", condition=condition.name)
            return
        
        # Check deduplication
        if self.config.enable_deduplication and self._is_duplicate_alert(condition.name, value):
            _logger.debug("alert_deduplication_skipped", condition=condition.name)
            return
        
        # Create or update alert
        if condition.name in self._active_alerts:
            # Update existing alert
            alert = self._active_alerts[condition.name]
            alert.updated_at = time.time()
            alert.current_value = value
            alert.status = AlertStatus.ACTIVE
        else:
            # Create new alert
            alert = Alert(
                id=alert_id,
                condition_name=condition.name,
                severity=condition.severity,
                status=AlertStatus.ACTIVE,
                current_value=value,
                threshold_value=condition.threshold_value,
                message=self._generate_alert_message(condition, value, metadata),
                created_at=time.time(),
                updated_at=time.time()
            )
            
            self._active_alerts[condition.name] = alert
            self._alert_history.append(alert)
            
            # Update metrics
            self._metrics['total_alerts'] += 1
            self._metrics['alerts_by_severity'][condition.severity.value] += 1
            self._metrics['alerts_by_condition'][condition.name] = (
                self._metrics['alerts_by_condition'].get(condition.name, 0) + 1
            )
        
        _logger.warning(
            "alert_triggered",
            condition=condition.name,
            severity=condition.severity.value,
            value=value,
            threshold=condition.threshold_value
        )
        
        # Send notifications
        asyncio.create_task(self._send_notifications(alert, metadata))
    
    def _resolve_alert_if_needed(self, condition_name: str, value: float, duration: float) -> None:
        """Resolve alert if condition is no longer met."""
        if condition_name not in self._active_alerts:
            return
        
        condition = self._conditions[condition_name]
        alert = self._active_alerts[condition_name]
        
        if not condition.evaluate(value, duration):
            alert.status = AlertStatus.RESOLVED
            alert.resolved_at = time.time()
            alert.updated_at = time.time()
            
            _logger.info(
                "alert_resolved",
                condition=condition_name,
                duration_seconds=duration
            )
            
            # Send resolution notification
            asyncio.create_task(self._send_resolution_notification(alert))
    
    def _is_rate_limited(self, condition_name: str) -> bool:
        """Check if alert is rate limited."""
        current_time = time.time()
        window_start = current_time - (self.config.rate_limit_window_hours * 3600)
        
        # Count recent alerts for this condition
        recent_count = sum(
            1 for timestamp in self._alert_timestamps
            if timestamp >= window_start and self._get_condition_from_timestamp(timestamp) == condition_name
        )
        
        return recent_count >= self.config.max_alerts_per_hour
    
    def _is_duplicate_alert(self, condition_name: str, value: float) -> bool:
        """Check if alert is duplicate within deduplication window."""
        if not self.config.enable_deduplication:
            return False
        
        window_start = time.time() - (self.config.deduplication_window_minutes * 60)
        
        # Check for similar recent alert
        for timestamp in self._alert_timestamps:
            if timestamp >= window_start:
                hist_alert = self._get_alert_from_timestamp(timestamp)
                if (hist_alert and 
                    hist_alert.condition_name == condition_name and 
                    hist_alert.status == AlertStatus.ACTIVE and
                    abs(hist_alert.current_value - value) < 0.01):  # Same value
                    return True
        
        return False
    
    def _get_condition_from_timestamp(self, timestamp: float) -> Alert | None:
        """Get alert from timestamp."""
        for alert in reversed(self._alert_history):
            if abs(alert.created_at - timestamp) < 1.0:  # Within 1 second
                return alert
        return None
    
    def _get_alert_from_timestamp(self, timestamp: float) -> Alert | None:
        """Get alert from timestamp (duplicate method name fix)."""
        for alert in reversed(self._alert_history):
            if abs(alert.created_at - timestamp) < 1.0:
                return alert
        return None
    
    def _generate_alert_message(self, condition: AlertCondition, value: float, metadata: dict[str, Any] | None) -> str:
        """Generate alert message."""
        base_message = f"Alert: {condition.name} - {condition.metric_name} is {condition.comparison_operator} {condition.threshold_value} (current: {value})"
        
        if metadata:
            metadata_str = ", ".join([f"{k}={v}" for k, v in metadata.items()])
            base_message += f" | Metadata: {metadata_str}"
        
        return base_message
    
    async def _send_notifications(self, alert: Alert, metadata: dict[str, Any] | None) -> None:
        """Send notifications through configured channels."""
        for channel in self.config.notification_channels:
            try:
                if channel == NotificationChannel.WEBHOOK:
                    await self._send_webhook_notification(alert, metadata)
                elif channel == NotificationChannel.EMAIL:
                    await self._send_email_notification(alert, metadata)
                elif channel == NotificationChannel.SLACK:
                    await self._send_slack_notification(alert, metadata)
                elif channel == NotificationChannel.LOG:
                    self._send_log_notification(alert, metadata)
                elif channel == NotificationChannel.CALLBACK:
                    await self._send_callback_notification(alert, metadata)
                
                # Record notification sent
                alert.notification_sent[channel.value] = time.time()
                self._metrics['notifications_sent'] += 1
                
            except Exception as e:
                _logger.error("notification_send_failed", 
                             channel=channel.value, 
                             alert_id=alert.id,
                             error=str(e))
                self._metrics['notifications_failed'] += 1
    
    async def _send_webhook_notification(self, alert: Alert, metadata: dict[str, Any] | None) -> None:
        """Send webhook notification."""
        if not self.config.webhook_url:
            return
        
        payload = {
            'alert_id': alert.id,
            'condition_name': alert.condition_name,
            'severity': alert.severity.value,
            'status': alert.status.value,
            'message': alert.message,
            'current_value': alert.current_value,
            'threshold_value': alert.threshold_value,
            'created_at': alert.created_at,
            'metadata': metadata or {},
        }
        
        import aiohttp
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.config.webhook_timeout_seconds)) as session:
            for attempt in range(self.config.webhook_retry_attempts):
                try:
                    async with session.post(self.config.webhook_url, json=payload) as response:
                        if response.status == 200:
                            _logger.info("webhook_notification_sent", alert_id=alert.id)
                            return
                        else:
                            _logger.warning("webhook_notification_failed", 
                                         alert_id=alert.id,
                                         status=response.status)
                
                except Exception as e:
                    if attempt == self.config.webhook_retry_attempts - 1:
                        raise
                    _logger.warning("webhook_notification_retry", 
                                     alert_id=alert.id,
                                     attempt=attempt + 1,
                                     error=str(e))
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
    
    async def _send_email_notification(self, alert: Alert, metadata: dict[str, Any] | None) -> None:
        """Send email notification."""
        if not all([self.config.smtp_server, self.config.email_from, self.config.email_to]):
            return
        
        if MimeText is None or MimeMultipart is None:
            _logger.warning("email_notification_unavailable", alert_id=alert.id)
            return
        
        subject = f"[{alert.severity.value.upper()}] gRPC Alert: {alert.condition_name}"
        
        body = f"""
Alert Details:
- ID: {alert.id}
- Condition: {alert.condition_name}
- Severity: {alert.severity.value}
- Status: {alert.status.value}
- Message: {alert.message}
- Current Value: {alert.current_value}
- Threshold: {alert.threshold_value}
- Created: {time.ctime(alert.created_at)}

"""
        
        if metadata:
            body += "Metadata:\n"
            for k, v in metadata.items():
                body += f"- {k}: {v}\n"
        
        msg = MimeMultipart()
        msg['From'] = self.config.email_from
        msg['To'] = ', '.join(self.config.email_to)
        msg['Subject'] = subject
        
        msg.attach(MimeText(body, 'plain'))
        
        try:
            with smtplib.SMTP(self.config.smtp_server, self.config.smtp_port) as server:
                if self.config.smtp_username and self.config.smtp_password:
                    server.starttls()
                    server.login(self.config.smtp_username, self.config.smtp_password)
                
                server.send_message(msg)
                _logger.info("email_notification_sent", alert_id=alert.id)
        
        except Exception as e:
            _logger.error("email_notification_failed", alert_id=alert.id, error=str(e))
    
    async def _send_slack_notification(self, alert: Alert, metadata: dict[str, Any] | None) -> None:
        """Send Slack notification."""
        if not self.config.slack_webhook_url:
            return
        
        color = {
            AlertSeverity.INFO: "good",
            AlertSeverity.WARNING: "warning", 
            AlertSeverity.ERROR: "danger",
            AlertSeverity.CRITICAL: "danger"
        }.get(alert.severity, "warning")
        
        payload = {
            "username": "gRPC Monitor",
            "channel": self.config.slack_channel or "#alerts",
            "attachments": [{
                "color": color,
                "title": f"gRPC Alert: {alert.condition_name}",
                "text": alert.message,
                "fields": [
                    {"title": "Severity", "value": alert.severity.value, "short": True},
                    {"title": "Current Value", "value": str(alert.current_value), "short": True},
                    {"title": "Threshold", "value": str(alert.threshold_value), "short": True},
                    {"title": "Time", "value": time.ctime(alert.created_at), "short": True},
                ],
                "footer": f"Alert ID: {alert.id}",
                "ts": alert.created_at
            }]
        }
        
        import aiohttp
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10.0)) as session:
            async with session.post(self.config.slack_webhook_url, json=payload) as response:
                if response.status == 200:
                    _logger.info("slack_notification_sent", alert_id=alert.id)
                else:
                    _logger.warning("slack_notification_failed", 
                                         alert_id=alert.id,
                                         status=response.status)
    
    def _send_log_notification(self, alert: Alert, metadata: dict[str, Any] | None) -> None:
        """Send log notification."""
        log_message = f"ALERT [{alert.severity.value.upper()}] {alert.message}"
        
        if alert.severity == AlertSeverity.CRITICAL:
            _logger.critical(log_message)
        elif alert.severity == AlertSeverity.ERROR:
            _logger.error(log_message)
        elif alert.severity == AlertSeverity.WARNING:
            _logger.warning(log_message)
        else:
            _logger.info(log_message)
    
    async def _send_callback_notification(self, alert: Alert, metadata: dict[str, Any] | None) -> None:
        """Send callback notification (placeholder for custom implementation)."""
        # This would be implemented based on specific callback requirements
        _logger.info("callback_notification_triggered", alert_id=alert.id)
    
    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert."""
        with self._alert_lock:
            for alert in self._active_alerts.values():
                if alert.id == alert_id:
                    alert.status = AlertStatus.ACKNOWLEDGED
                    alert.acknowledged_at = time.time()
                    _logger.info("alert_acknowledged", alert_id=alert_id)
                    return True
        return False
    
    def resolve_alert(self, alert_id: str) -> bool:
        """Manually resolve an alert."""
        with self._alert_lock:
            for alert in self._active_alerts.values():
                if alert.id == alert_id:
                    alert.status = AlertStatus.RESOLVED
                    alert.resolved_at = time.time()
                    _logger.info("alert_resolved_manually", alert_id=alert_id)
                    return True
        return False
    
    def get_active_alerts(self) -> list[Alert]:
        """Get all active alerts."""
        with self._alert_lock:
            return list(self._active_alerts.values())
    
    def get_alert_metrics(self) -> dict[str, Any]:
        """Get alerting system metrics."""
        with self._alert_lock:
            return {
                'total_alerts': self._metrics['total_alerts'],
                'active_alerts_count': len(self._active_alerts),
                'alerts_by_severity': self._metrics['alerts_by_severity'].copy(),
                'alerts_by_condition': self._metrics['alerts_by_condition'].copy(),
                'notifications_sent': self._metrics['notifications_sent'],
                'notifications_failed': self._metrics['notifications_failed'],
                'configured_conditions': list(self._conditions.keys()),
                'configured_channels': [c.value for c in self.config.notification_channels],
            }
    
    def clear_resolved_alerts(self, max_age_hours: float = 24.0) -> int:
        """Clear old resolved alerts."""
        current_time = time.time()
        cutoff_time = current_time - (max_age_hours * 3600)
        
        with self._alert_lock:
            original_count = len(self._alert_history)
            
            # Remove old alerts from history
            self._alert_history = deque(
                (alert for alert in self._alert_history if alert.created_at > cutoff_time),
                maxlen=self.config.max_active_alerts
            )
            
            # Remove resolved active alerts
            resolved_alerts = []
            for name, alert in list(self._active_alerts.items()):
                if (alert.status == AlertStatus.RESOLVED and 
                    alert.resolved_at and alert.resolved_at < cutoff_time):
                    del self._active_alerts[name]
                    resolved_alerts.append(alert)
            
            cleared_count = original_count - len(self._alert_history)
            _logger.info("resolved_alerts_cleared", count=cleared_count, max_age_hours=max_age_hours)
            
            return cleared_count
