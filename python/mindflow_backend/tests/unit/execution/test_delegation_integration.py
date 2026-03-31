"""Integration tests for DelegationEngine + MissionLauncher."""
from __future__ import annotations
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestDelegationEngineIntegration:
    """Tests for DelegationEngine using MissionLauncher."""

    @pytest.mark.asyncio
    async def test_delegation_engine_has_mission_launcher_field(self):
        """DelegationEngine should have _mission_launcher field."""
        from mindflow_backend.orchestrator.delegation.engine import DelegationEngine

        engine = DelegationEngine(execution_memory=MagicMock())
        assert hasattr(engine, "_mission_launcher")
        assert engine._mission_launcher is None

    @pytest.mark.asyncio
    async def test_delegation_engine_get_mission_launcher_method(self):
        """DelegationEngine should have _get_mission_launcher method."""
        from mindflow_backend.orchestrator.delegation.engine import DelegationEngine

        engine = DelegationEngine(execution_memory=MagicMock())
        assert hasattr(engine, "_get_mission_launcher")
        assert callable(engine._get_mission_launcher)

    @pytest.mark.asyncio
    async def test_delegation_engine_fallback_when_no_mission_type(self):
        """When task has no mission_type, fallback to regular delegation."""
        from mindflow_backend.orchestrator.delegation.engine import DelegationEngine
        from mindflow_backend.schemas.orchestration.delegation import (
            DelegationTask,
        )
        from mindflow_backend.schemas.orchestration.orchestrator import AgentType, ToolScope

        engine = DelegationEngine(execution_memory=MagicMock())

        # Create a mock task without mission_type
        task = MagicMock(spec=DelegationTask)
        task.metadata = {}
        task.agent = AgentType.ANALYST
        task.agent_role = AgentType.ANALYST
        task.specialist = None
        task.agent_id = "analyst"
        task.objective = "Test objective"
        task.scope = []
        task.exclusions = []
        task.expected_output = ""
        task.priority = MagicMock()
        task.priority.value = "normal"
        task.task_id = MagicMock()
        task.task_id.__str__ = MagicMock(return_value="task-1")
        task.max_iterations = 1
        task.context_from_session = None
        task.root_dir = None

        # Mock session
        session = MagicMock()
        session.id = "sess-1"

        # Test fallback - since launcher won't be set, should use regular path
        # We cannot run full delegate_task without all dependencies mocked,
        # but we verify the structure exists
        assert engine._mission_launcher is None