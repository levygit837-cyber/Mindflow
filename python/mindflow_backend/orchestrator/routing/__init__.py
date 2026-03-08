"""Routing sub-package — intent analysis and agent selection.

Keep imports lightweight: higher-level modules can import individual components
directly to avoid pulling optional dependencies at import-time.
"""

from mindflow_backend.orchestrator.routing.router import route_message  # noqa: F401
from mindflow_backend.orchestrator.routing.intelligent_router import (  # noqa: F401
    IntelligentRouter,
    route_message_intelligently,
)

__all__ = ["route_message", "route_message_intelligently", "IntelligentRouter"]
