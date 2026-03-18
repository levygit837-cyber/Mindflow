"""Execution memory service facade.

Provides durable storage for agent execution state, checkpoints, external
effects, and resumable session state.
"""

from __future__ import annotations

from mindflow_backend.execution_memory.service import ExecutionMemoryService

_execution_memory_service: ExecutionMemoryService | None = None


def get_execution_memory_service() -> ExecutionMemoryService:
    global _execution_memory_service
    if _execution_memory_service is None:
        _execution_memory_service = ExecutionMemoryService()
    return _execution_memory_service


__all__ = ["ExecutionMemoryService", "get_execution_memory_service"]
