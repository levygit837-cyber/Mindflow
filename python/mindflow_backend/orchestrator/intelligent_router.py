"""Compatibility shim for intelligent routing.

The implementation lives in `mindflow_backend.orchestrator.routing.intelligent_router`.
Older modules import from `mindflow_backend.orchestrator.intelligent_router`.
"""

from __future__ import annotations

from mindflow_backend.orchestrator.routing.intelligent_router import (
    IntelligentRouter,
    get_intelligent_router,
    route_message_intelligently,
)

__all__ = ["IntelligentRouter", "get_intelligent_router", "route_message_intelligently"]

