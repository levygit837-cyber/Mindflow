"""Supervisor node for the orchestrator graph.

Evaluates the quality of the execute node's output and decides whether to
accept it or retry with a stronger specialist.
"""

from __future__ import annotations

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)

_SHORT_RESPONSE_THRESHOLD = 80
_QUALITY_THRESHOLD = 0.5
_MAX_RETRIES = 2


class SupervisorNode:
    """Evaluates response quality and returns 'accept' or 'retry'."""

    async def evaluate(self, state: dict) -> str:
        """Return 'accept' or 'retry' based on response quality."""
        response: str = state.get("response") or ""
        error = state.get("error")
        retry_count: int = state.get("retry_count", 0)

        if error or not response.strip():
            quality = 0.0
        elif len(response) < _SHORT_RESPONSE_THRESHOLD:
            quality = 0.3
        else:
            quality = 0.8

        _logger.info(
            "supervisor_evaluate",
            quality=quality,
            retry_count=retry_count,
            response_len=len(response),
        )

        if quality < _QUALITY_THRESHOLD and retry_count < _MAX_RETRIES:
            return "retry"
        return "accept"
