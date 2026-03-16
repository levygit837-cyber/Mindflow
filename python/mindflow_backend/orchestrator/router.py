"""Compatibility router module (adapter only).

The routing implementation lives under `mindflow_backend.orchestrator.routing`.
This shim preserves the older import path `mindflow_backend.orchestrator.router`.
"""

from __future__ import annotations

from mindflow_backend.orchestrator.routing.router import route_message
from mindflow_backend.orchestrator.routing.intelligent_router import route_message_intelligently

__all__ = ["route_message", "route_message_intelligently"]
