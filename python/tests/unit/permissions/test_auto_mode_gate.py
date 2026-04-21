"""Tests for Auto Mode Gate."""

import pytest
from datetime import datetime, timedelta
from mindflow_backend.permissions.auto_mode_gate import (
    AutoModeGate,
    AutoModeGateConfig,
)


class TestAutoModeGate:
    """Test suite for AutoModeGate."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = AutoModeGateConfig(
            cooldown_minutes=5,
            max_consecutive_approvals=10,
            approval_window_minutes=30,
            danger_threshold=3,
        )
        self.gate = AutoModeGate(config=self.config)
    
    @pytest.mark.asyncio
    async def test_can_activate_with_consent(self):
        """Test that activation is allowed with user consent."""
        can_activate, reason = await self.gate.can_activate(
            session_id="test-session",
            user_consent=True,
        )
        assert can_activate is True
        assert reason == "Auto Mode can be activated"
    
    @pytest.mark.asyncio
    async def test_cannot_activate_without_consent(self):
        """Test that activation is blocked without user consent."""
        can_activate, reason = await self.gate.can_activate(
            session_id="test-session",
            user_consent=False,
        )
        assert can_activate is False
        assert "consent" in reason.lower()
    
    @pytest.mark.asyncio
    async def test_cannot_activate_during_cooldown(self):
        """Test that activation is blocked during cooldown."""
        # First activation
        self.gate.activate()
        
        # Try to activate again immediately
        can_activate, reason = await self.gate.can_activate(
            session_id="test-session",
            user_consent=True,
        )
        assert can_activate is False
        assert "Cooldown" in reason
    
    @pytest.mark.asyncio
    async def test_can_activate_after_cooldown(self):
        """Test that activation is allowed after cooldown."""
        # First activation
        self.gate.activate()
        
        # Simulate cooldown passing
        self.gate._last_activation = datetime.now() - timedelta(minutes=6)
        
        can_activate, reason = await self.gate.can_activate(
            session_id="test-session",
            user_consent=True,
        )
        assert can_activate is True
    
    @pytest.mark.asyncio
    async def test_cannot_activate_with_too_many_dangers(self):
        """Test that activation is blocked with too many dangerous actions."""
        # Record 3 dangerous actions
        for _ in range(3):
            self.gate.record_danger()
        
        can_activate, reason = await self.gate.can_activate(
            session_id="test-session",
            user_consent=True,
        )
        assert can_activate is False
        assert "dangerous" in reason.lower()
    
    @pytest.mark.asyncio
    async def test_cannot_activate_with_too_many_approvals(self):
        """Test that activation is blocked with too many consecutive approvals."""
        # Record 10 approvals
        for _ in range(10):
            self.gate.record_approval()
        
        can_activate, reason = await self.gate.can_activate(
            session_id="test-session",
            user_consent=True,
        )
        assert can_activate is False
        assert "consecutive" in reason.lower()
    
    def test_record_approval(self):
        """Test recording an approval."""
        initial_count = len(self.gate._approval_history)
        self.gate.record_approval()
        assert len(self.gate._approval_history) == initial_count + 1
    
    def test_record_danger(self):
        """Test recording a dangerous action."""
        initial_count = len(self.gate._danger_history)
        self.gate.record_danger()
        assert len(self.gate._danger_history) == initial_count + 1
    
    def test_activate(self):
        """Test activating the gate."""
        self.gate.activate()
        assert self.gate._last_activation is not None
    
    def test_get_stats(self):
        """Test getting gate statistics."""
        # Record some actions
        self.gate.record_approval()
        self.gate.record_approval()
        self.gate.record_danger()
        self.gate.activate()
        
        stats = self.gate.get_stats()
        
        assert "recent_approvals" in stats
        assert "recent_dangers" in stats
        assert "last_activation" in stats
        assert "config" in stats
        assert stats["recent_approvals"] == 2
        assert stats["recent_dangers"] == 1
        assert stats["last_activation"] is not None
    
    def test_cleanup_old_records(self):
        """Test cleanup of old records."""
        # Add old record
        old_time = datetime.now() - timedelta(hours=2)
        self.gate._approval_history.append(old_time)
        self.gate._danger_history.append(old_time)
        
        # Add recent record
        self.gate.record_approval()
        
        # Cleanup should remove old records
        self.gate._cleanup_old_records()
        
        # Only recent records should remain
        assert len(self.gate._approval_history) == 1
        assert len(self.gate._danger_history) == 0
    
    @pytest.mark.asyncio
    async def test_multiple_sessions_independent(self):
        """Test that different sessions are independent."""
        # Activate for session 1
        self.gate.activate()
        
        # Session 2 should still be able to activate
        can_activate, reason = await self.gate.can_activate(
            session_id="session-2",
            user_consent=True,
        )
        # Note: Gate is global, not per-session in current implementation
        # This test documents current behavior
        assert can_activate is False  # Cooldown is global