"""Tests for Mode Controller."""

import pytest
from mindflow_backend.permissions.mode_controller import ModeController, MODE_CYCLE
from mindflow_backend.permissions.types import PermissionMode


class TestModeController:
    """Test suite for ModeController."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.controller = ModeController()
    
    def test_get_next_mode_from_default(self):
        """Test getting next mode from DEFAULT."""
        next_mode = self.controller.get_next_mode(PermissionMode.DEFAULT)
        assert next_mode == PermissionMode.ACCEPT_EDITS
    
    def test_get_next_mode_from_accept_edits(self):
        """Test getting next mode from ACCEPT_EDITS."""
        next_mode = self.controller.get_next_mode(PermissionMode.ACCEPT_EDITS)
        assert next_mode == PermissionMode.PLAN
    
    def test_get_next_mode_from_plan(self):
        """Test getting next mode from PLAN."""
        next_mode = self.controller.get_next_mode(PermissionMode.PLAN)
        assert next_mode == PermissionMode.AUTO
    
    def test_get_next_mode_from_auto(self):
        """Test getting next mode from AUTO."""
        next_mode = self.controller.get_next_mode(PermissionMode.AUTO)
        assert next_mode == PermissionMode.BYPASS
    
    def test_get_next_mode_from_bypass(self):
        """Test getting next mode from BYPASS."""
        next_mode = self.controller.get_next_mode(PermissionMode.BYPASS)
        assert next_mode == PermissionMode.DONT_ASK
    
    def test_get_next_mode_from_dont_ask(self):
        """Test getting next mode from DONT_ASK (cycles back to DEFAULT)."""
        next_mode = self.controller.get_next_mode(PermissionMode.DONT_ASK)
        assert next_mode == PermissionMode.DEFAULT
    
    def test_get_previous_mode_from_default(self):
        """Test getting previous mode from DEFAULT (cycles to DONT_ASK)."""
        prev_mode = self.controller.get_previous_mode(PermissionMode.DEFAULT)
        assert prev_mode == PermissionMode.DONT_ASK
    
    def test_get_previous_mode_from_accept_edits(self):
        """Test getting previous mode from ACCEPT_EDITS."""
        prev_mode = self.controller.get_previous_mode(PermissionMode.ACCEPT_EDITS)
        assert prev_mode == PermissionMode.DEFAULT
    
    def test_get_previous_mode_from_plan(self):
        """Test getting previous mode from PLAN."""
        prev_mode = self.controller.get_previous_mode(PermissionMode.PLAN)
        assert prev_mode == PermissionMode.ACCEPT_EDITS
    
    def test_full_cycle_forward(self):
        """Test full cycle forward returns to start."""
        mode = PermissionMode.DEFAULT
        for _ in range(len(MODE_CYCLE)):
            mode = self.controller.get_next_mode(mode)
        assert mode == PermissionMode.DEFAULT
    
    def test_full_cycle_backward(self):
        """Test full cycle backward returns to start."""
        mode = PermissionMode.DEFAULT
        for _ in range(len(MODE_CYCLE)):
            mode = self.controller.get_previous_mode(mode)
        assert mode == PermissionMode.DEFAULT
    
    def test_get_mode_info_default(self):
        """Test getting mode info for DEFAULT."""
        info = self.controller.get_mode_info(PermissionMode.DEFAULT)
        assert info["name"] == "Default"
        assert info["icon"] == "🔒"
        assert info["color"] == "yellow"
    
    def test_get_mode_info_plan(self):
        """Test getting mode info for PLAN."""
        info = self.controller.get_mode_info(PermissionMode.PLAN)
        assert info["name"] == "Plan Mode"
        assert info["icon"] == "📋"
        assert info["color"] == "purple"
    
    def test_get_mode_info_auto(self):
        """Test getting mode info for AUTO."""
        info = self.controller.get_mode_info(PermissionMode.AUTO)
        assert info["name"] == "Auto Mode"
        assert info["icon"] == "🤖"
        assert info["color"] == "green"
    
    def test_validate_transition_plan_to_default(self):
        """Test valid transition from PLAN to DEFAULT."""
        is_valid, reason = self.controller.validate_transition(
            from_mode=PermissionMode.PLAN,
            to_mode=PermissionMode.DEFAULT,
        )
        assert is_valid is True
    
    def test_validate_transition_plan_to_auto_invalid(self):
        """Test invalid transition from PLAN to AUTO."""
        is_valid, reason = self.controller.validate_transition(
            from_mode=PermissionMode.PLAN,
            to_mode=PermissionMode.AUTO,
        )
        assert is_valid is False
        assert "confirm_plan" in reason
    
    def test_validate_transition_to_auto_without_gate(self):
        """Test invalid transition to AUTO without gate check."""
        is_valid, reason = self.controller.validate_transition(
            from_mode=PermissionMode.DEFAULT,
            to_mode=PermissionMode.AUTO,
            context={"auto_mode_available": False},
        )
        assert is_valid is False
        assert "gate check failed" in reason
    
    def test_validate_transition_to_bypass_without_sandbox(self):
        """Test invalid transition to BYPASS without sandbox."""
        is_valid, reason = self.controller.validate_transition(
            from_mode=PermissionMode.DEFAULT,
            to_mode=PermissionMode.BYPASS,
            context={"is_sandbox": False},
        )
        assert is_valid is False
        assert "sandbox" in reason
    
    def test_get_cycle_order(self):
        """Test getting cycle order."""
        cycle = self.controller.get_cycle_order()
        assert len(cycle) == len(MODE_CYCLE)
        assert cycle[0] == PermissionMode.DEFAULT
        assert cycle[-1] == PermissionMode.DONT_ASK
    
    def test_get_mode_index(self):
        """Test getting mode index."""
        assert self.controller.get_mode_index(PermissionMode.DEFAULT) == 0
        assert self.controller.get_mode_index(PermissionMode.ACCEPT_EDITS) == 1
        assert self.controller.get_mode_index(PermissionMode.PLAN) == 2
        assert self.controller.get_mode_index(PermissionMode.AUTO) == 3
        assert self.controller.get_mode_index(PermissionMode.BYPASS) == 4
        assert self.controller.get_mode_index(PermissionMode.DONT_ASK) == 5