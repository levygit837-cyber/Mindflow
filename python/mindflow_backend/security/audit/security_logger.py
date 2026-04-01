"""Security audit logger for MindFlow.

Centralized logging for security events including:
- Command blocks
- Secret detections
- Network access denials
- Authentication failures
- Permission violations
"""

from datetime import datetime, UTC
from enum import Enum
from typing import Any

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


class SecurityEventType(Enum):
    """Security event types."""
    COMMAND_BLOCKED = "command_blocked"
    SECRET_DETECTED = "secret_detected"
    NETWORK_BLOCKED = "network_blocked"
    AUTH_FAILED = "auth_failed"
    PERMISSION_DENIED = "permission_denied"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    SANDBOX_VIOLATION = "sandbox_violation"


class SecuritySeverity(Enum):
    """Security event severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class SecurityLogger:
    """Centralized security event logger.

    Features:
    - Structured logging with context
    - Severity levels
    - Event categorization
    - Audit trail
    """

    def __init__(self):
        """Initialize security logger."""
        self._logger = get_logger("security_audit")

    def log_event(
        self,
        event_type: SecurityEventType,
        severity: SecuritySeverity,
        message: str,
        context: dict[str, Any] | None = None,
    ) -> None:
        """Log security event.

        Args:
            event_type: Type of security event
            severity: Severity level
            message: Event message
            context: Additional context data
        """
        log_data = {
            "event_type": event_type.value,
            "severity": severity.value,
            "message": message,
            "timestamp": datetime.now(UTC).isoformat(),
            **(context or {}),
        }

        # Log at appropriate level based on severity
        if severity == SecuritySeverity.CRITICAL:
            self._logger.critical("security_event", extra=log_data)
        elif severity == SecuritySeverity.HIGH:
            self._logger.error("security_event", extra=log_data)
        elif severity == SecuritySeverity.MEDIUM:
            self._logger.warning("security_event", extra=log_data)
        else:
            self._logger.info("security_event", extra=log_data)

    def log_command_blocked(
        self,
        command: str,
        reason: str,
        validator: str | None = None,
        user_id: str | None = None,
    ) -> None:
        """Log blocked command execution.

        Args:
            command: Command that was blocked
            reason: Reason for blocking
            validator: Validator that blocked the command
            user_id: User who attempted the command
        """
        self.log_event(
            event_type=SecurityEventType.COMMAND_BLOCKED,
            severity=SecuritySeverity.HIGH,
            message=f"Command blocked: {reason}",
            context={
                "command": command[:200],  # Truncate long commands
                "reason": reason,
                "validator": validator,
                "user_id": user_id,
            },
        )

    def log_secret_detected(
        self,
        secret_type: str,
        file_path: str,
        line_number: int,
        severity: str = "critical",
    ) -> None:
        """Log detected secret in code.

        Args:
            secret_type: Type of secret detected
            file_path: File containing the secret
            line_number: Line number of the secret
            severity: Severity level
        """
        severity_enum = SecuritySeverity.CRITICAL if severity == "critical" else SecuritySeverity.HIGH

        self.log_event(
            event_type=SecurityEventType.SECRET_DETECTED,
            severity=severity_enum,
            message=f"Secret detected: {secret_type}",
            context={
                "secret_type": secret_type,
                "file_path": file_path,
                "line_number": line_number,
            },
        )

    def log_network_blocked(
        self,
        url: str,
        reason: str,
        command: str | None = None,
        user_id: str | None = None,
    ) -> None:
        """Log blocked network access.

        Args:
            url: URL that was blocked
            reason: Reason for blocking
            command: Command that attempted network access
            user_id: User who attempted the access
        """
        self.log_event(
            event_type=SecurityEventType.NETWORK_BLOCKED,
            severity=SecuritySeverity.MEDIUM,
            message=f"Network access blocked: {reason}",
            context={
                "url": url,
                "reason": reason,
                "command": command[:200] if command else None,
                "user_id": user_id,
            },
        )

    def log_auth_failed(
        self,
        username: str | None = None,
        method: str | None = None,
        reason: str | None = None,
        ip_address: str | None = None,
    ) -> None:
        """Log authentication failure.

        Args:
            username: Username that failed authentication
            method: Authentication method used
            reason: Reason for failure
            ip_address: IP address of the attempt
        """
        self.log_event(
            event_type=SecurityEventType.AUTH_FAILED,
            severity=SecuritySeverity.MEDIUM,
            message="Authentication failed",
            context={
                "username": username,
                "method": method,
                "reason": reason,
                "ip_address": ip_address,
            },
        )

    def log_permission_denied(
        self,
        user_id: str,
        resource: str,
        action: str,
        reason: str | None = None,
    ) -> None:
        """Log permission denial.

        Args:
            user_id: User who was denied
            resource: Resource that was accessed
            action: Action that was attempted
            reason: Reason for denial
        """
        self.log_event(
            event_type=SecurityEventType.PERMISSION_DENIED,
            severity=SecuritySeverity.MEDIUM,
            message=f"Permission denied: {action} on {resource}",
            context={
                "user_id": user_id,
                "resource": resource,
                "action": action,
                "reason": reason,
            },
        )

    def log_suspicious_activity(
        self,
        activity: str,
        details: dict[str, Any] | None = None,
        severity: SecuritySeverity = SecuritySeverity.HIGH,
    ) -> None:
        """Log suspicious activity.

        Args:
            activity: Description of suspicious activity
            details: Additional details
            severity: Severity level
        """
        self.log_event(
            event_type=SecurityEventType.SUSPICIOUS_ACTIVITY,
            severity=severity,
            message=f"Suspicious activity: {activity}",
            context=details or {},
        )

    def log_sandbox_violation(
        self,
        violation: str,
        command: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Log sandbox violation.

        Args:
            violation: Description of violation
            command: Command that caused violation
            details: Additional details
        """
        context = details or {}
        if command:
            context["command"] = command[:200]

        self.log_event(
            event_type=SecurityEventType.SANDBOX_VIOLATION,
            severity=SecuritySeverity.HIGH,
            message=f"Sandbox violation: {violation}",
            context=context,
        )


# Global security logger instance
_security_logger: SecurityLogger | None = None


def get_security_logger() -> SecurityLogger:
    """Get global security logger instance.

    Returns:
        SecurityLogger instance
    """
    global _security_logger
    if _security_logger is None:
        _security_logger = SecurityLogger()
    return _security_logger
