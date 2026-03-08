"""Chain catalog for Orchestrator execution.

The orchestrator needs a stable way to resolve `chain_id` → executable chain.
This module intentionally returns concrete chain instances with an async
`execute(context)` method.
"""

from __future__ import annotations

from typing import Any, Callable

from mindflow_backend.chains.templates.coding_task_chain import (
    CodingTaskChain,
    CodingTaskChainConfig,
)


ChainFactory = Callable[[], Any]


def _coding_task_chain_factory() -> CodingTaskChain:
    return CodingTaskChain(CodingTaskChainConfig(chain_id="coding_task"))


CHAIN_CATALOG: dict[str, ChainFactory] = {
    "coding_task": _coding_task_chain_factory,
}


def get_chain(chain_id: str) -> Any:
    """Return a new chain instance for `chain_id`."""
    try:
        factory = CHAIN_CATALOG[chain_id]
    except KeyError as exc:
        raise KeyError(f"Unknown chain_id={chain_id!r}. Available: {sorted(CHAIN_CATALOG)}") from exc
    return factory()

