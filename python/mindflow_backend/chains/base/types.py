"""Shared types for chain execution.

This module exists to provide a stable import surface for chain builders/managers.
The current chain system mixes two approaches:
- Template chains implemented as Python callables (builder-based)
- Agent-driven chains executed by the orchestrator (newer)

We keep these types minimal and dependency-free.
"""

from __future__ import annotations

from typing import Any, Dict, TypedDict

from pydantic import BaseModel, Field

from mindflow_backend.chains.base.chain import ChainType


class ChainConfig(BaseModel):
    """Runtime configuration for chain execution."""

    chain_type: ChainType = ChainType.SEQUENTIAL
    max_execution_time: float | None = Field(default=300.0, gt=0.0)
    continue_on_error: bool = False
    enable_streaming: bool = False
    retry_failed_steps: bool = True
    max_step_retries: int = Field(default=3, ge=0)

    class Config:
        use_enum_values = True


class ExecutionContext(TypedDict, total=False):
    """Loose execution context passed through chain steps."""

    input: Dict[str, Any]
    output: Dict[str, Any]
    error: str
    metadata: Dict[str, Any]

