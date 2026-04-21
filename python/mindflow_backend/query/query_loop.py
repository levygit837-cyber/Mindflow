"""Backward-compatible shim — canonical location:
``mindflow_backend.query.strategies.react``.

The ReAct loop previously defined here has been moved under
``query/strategies/react.py`` as part of the unified-engine migration. This
module re-exports the public names so existing callers (notably
``nodes/implementations/orchestrator/route_node.py``) keep working until
Fase 4 deletes the LangGraph orchestrator.

See .windsurf/plans/unified-engine-47796c.md §4 Phase 1.
"""

from __future__ import annotations

from mindflow_backend.query.strategies.react import (  # noqa: F401
    ReActLoopState as QueryLoopState,
)
from mindflow_backend.query.strategies.react import react_loop as query_loop

__all__ = ["query_loop", "QueryLoopState"]
