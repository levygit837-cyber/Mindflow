"""Stub nodes for coding graphs (Fase 2A)."""

from __future__ import annotations

from typing import Any

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.nodes.base.node import BaseNode, NodeCategory

_logger = get_logger(__name__)


class CodingInitializeNode(BaseNode):
    """Initialize coding context: sandbox, tools, memory read."""

    def __init__(self, node_id: str = "initialize") -> None:
        super().__init__(
            node_id=node_id,
            name="Coding Initialize",
            description="Setup sandbox, tools, and memory for coding task.",
            category=NodeCategory.INITIALIZATION,
        )

    async def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        _logger.debug("coding_initialize_node", node_id=self.node_id)
        return {
            "verify_passed": False,
            "verify_retries": 0,
            "current_phase": "initialized",
        }


class PlanNode(BaseNode):
    """Decompose task into implementation steps."""

    def __init__(self, node_id: str = "plan") -> None:
        super().__init__(
            node_id=node_id,
            name="Plan",
            description="Decompose coding task into implementation steps.",
            category=NodeCategory.PLANNING,
        )

    async def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        _logger.debug("plan_node", node_id=self.node_id)
        return {"current_phase": "planned"}


class ImplementNode(BaseNode):
    """Execute implementation steps."""

    def __init__(self, node_id: str = "implement") -> None:
        super().__init__(
            node_id=node_id,
            name="Implement",
            description="Execute implementation steps.",
            category=NodeCategory.EXECUTION,
        )

    async def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        _logger.debug("implement_node", node_id=self.node_id)
        return {"current_phase": "implemented"}


class VerifyNode(BaseNode):
    """Verify implementation: lint, typecheck, tests."""

    def __init__(self, node_id: str = "verify") -> None:
        super().__init__(
            node_id=node_id,
            name="Verify",
            description="Verify implementation: lint, typecheck, tests.",
            category=NodeCategory.VALIDATION,
        )

    async def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        verify_retries = state.get("verify_retries", 0) + 1
        _logger.debug("verify_node", node_id=self.node_id, retries=verify_retries)
        return {
            "verify_passed": True,
            "verify_retries": verify_retries,
            "current_phase": "verified",
        }


class TestNode(BaseNode):
    """Run test suite."""

    def __init__(self, node_id: str = "test") -> None:
        super().__init__(
            node_id=node_id,
            name="Test",
            description="Run test suite.",
            category=NodeCategory.VALIDATION,
        )

    async def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        _logger.debug("test_node", node_id=self.node_id)
        return {"current_phase": "tested"}


class CodingReportNode(BaseNode):
    """Generate coding task report."""

    def __init__(self, node_id: str = "report") -> None:
        super().__init__(
            node_id=node_id,
            name="Coding Report",
            description="Generate coding task report.",
            category=NodeCategory.REPORTING,
        )

    async def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        _logger.debug("coding_report_node", node_id=self.node_id)
        return {
            "current_phase": "completed",
            "result": {
                "verify_passed": state.get("verify_passed", False),
                "verify_retries": state.get("verify_retries", 0),
            },
        }