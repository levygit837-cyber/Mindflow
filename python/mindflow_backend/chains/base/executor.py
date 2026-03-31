"""Chain executor abstraction.

Some parts of the codebase import `ChainExecutor`/`ExecutionContext` from
`mindflow_backend.chains.base`. Earlier iterations referenced an executor module
that did not exist; this file provides a minimal implementation.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from mindflow_backend.chains.base.types import ExecutionContext


class ChainExecutor(ABC):
    """Abstract executor for chain steps."""

    @abstractmethod
    async def execute(self, chain_id: str, context: dict[str, Any]) -> ExecutionContext:
        """Execute a chain with an initial context."""
        raise NotImplementedError

