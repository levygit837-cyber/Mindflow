"""Decomposition node stub."""

from __future__ import annotations

from typing import Any

from mindflow_backend.nodes.base.node import BaseNode, NodeCategory, NodeType


class DecompositionNode(BaseNode):
    """Node responsible for task decomposition in the orchestrator pipeline."""

    def __init__(self, node_id: str = "decomposition", description: str = "Task decomposition") -> None:
        super().__init__(
            node_id=node_id,
            node_type=NodeType.PROCESSING,
            category=NodeCategory.ORCHESTRATOR,
            description=description,
        )

    async def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        return {"result": None, "metadata": {"node_id": self.node_id}}
