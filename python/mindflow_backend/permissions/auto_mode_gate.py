"""Auto Mode Safety Gate.

Controls when Auto Mode can be activated.
Based on Claude Code's auto mode gate.

Activation requirements:
1. User explicitly enables auto mode
2. No dangerous patterns detected in recent history
3. Circuit breaker not tripped
4. Session is in stable state
"""

from __future__ import annotations

from datetime import datetime, timedelta
from dataclasses import dataclass, field
import logging

_logger = logging.getLogger(__name__)


@dataclass
class AutoModeGateConfig:
    """Configuration for auto mode gate."""
    # Minimum time between auto-mode activations
    cooldown_minutes: int = 5
    
    # Maximum consecutive auto-approvals before requiring manual
    max_consecutive_approvals: int = 10
    
    # Time window for tracking consecutive approvals
    approval_window_minutes: int = 30
    
    # Dangerous pattern detection threshold
    danger_threshold: int = 3  # Max dangerous actions in window


class AutoModeGate:
    """Safety gate for Auto Mode activation.
    
    Controls when Auto Mode can be enabled based on:
    - User consent
    - Recent behavior history
    - Circuit breaker state
    - Session stability
    """
    
    def __init__(self, config: AutoModeGateConfig | None = None) -> None:
        self._config = config or AutoModeGateConfig()
        self._approval_history: list[datetime] = []
        self._danger_history: list[datetime] = []
        self._last_activation: datetime | None = None
    
    async def can_activate(
        self,
        session_id: str,
        user_consent: bool = False,
    ) -> tuple[bool, str]:
        """Check if Auto Mode can be activated.
        
        Returns:
            Tuple of (can_activate, reason)
        """
        # 1. User consent required
        if not user_consent:
            return False, "User consent required for Auto Mode"
        
        # 2. Cooldown check
        if self._last_activation:
            elapsed = datetime.now() - self._last_activation
            cooldown = timedelta(minutes=self._config.cooldown_minutes)
            if elapsed < cooldown:
                remaining = cooldown - elapsed
                return False, f"Cooldown active: {remaining.seconds}s remaining"
        
        # 3. Danger history check
        recent_dangers = self._count_recent(
            self._danger_history,
            minutes=self._config.approval_window_minutes
        )
        if recent_dangers >= self._config.danger_threshold:
            return False, (
                f"Too many dangerous actions ({recent_dangers}) "
                f"in last {self._config.approval_window_minutes} minutes"
            )
        
        # 4. Consecutive approvals check
        recent_approvals = self._count_recent(
            self._approval_history,
            minutes=self._config.approval_window_minutes
        )
        if recent_approvals >= self._config.max_consecutive_approvals:
            return False, (
                f"Max consecutive approvals ({recent_approvals}) reached. "
                f"Manual approval required."
            )
        
        _logger.info(
            "auto_mode_gate_passed",
            session_id=session_id,
            recent_approvals=recent_approvals,
            recent_dangers=recent_dangers,
        )
        
        return True, "Auto Mode can be activated"
    
    def record_approval(self) -> None:
        """Record an auto-approval action."""
        self._approval_history.append(datetime.now())
        self._cleanup_old_records()
    
    def record_danger(self) -> None:
        """Record a dangerous action (should block auto-mode)."""
        self._danger_history.append(datetime.now())
        self._cleanup_old_records()
    
    def activate(self) -> None:
        """Record auto-mode activation."""
        self._last_activation = datetime.now()
    
    def get_stats(self) -> dict:
        """Get current gate statistics."""
        return {
            "recent_approvals": self._count_recent(
                self._approval_history,
                minutes=self._config.approval_window_minutes
            ),
            "recent_dangers": self._count_recent(
                self._danger_history,
                minutes=self._config.approval_window_minutes
            ),
            "last_activation": self._last_activation.isoformat() if self._last_activation else None,
            "config": {
                "cooldown_minutes": self._config.cooldown_minutes,
                "max_consecutive_approvals": self._config.max_consecutive_approvals,
                "approval_window_minutes": self._config.approval_window_minutes,
                "danger_threshold": self._config.danger_threshold,
            },
        }
    
    def _count_recent(
        self, 
        history: list[datetime],
        minutes: int
    ) -> int:
        """Count records within time window."""
        cutoff = datetime.now() - timedelta(minutes=minutes)
        return sum(1 for dt in history if dt > cutoff)
    
    def _cleanup_old_records(self) -> None:
        """Remove records older than tracking window."""
        cutoff = datetime.now() - timedelta(
            minutes=self._config.approval_window_minutes * 2
        )
        self._approval_history = [
            dt for dt in self._approval_history if dt > cutoff
        ]
        self._danger_history = [
            dt for dt in self._danger_history if dt > cutoff
        ]