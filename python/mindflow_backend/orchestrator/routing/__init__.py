"""Routing sub-package — intent analysis and agent selection.

Keep imports lightweight: higher-level modules can import individual components
directly to avoid pulling optional dependencies at import-time.

Two-Tier Hybrid Router:
    HybridRouter   — Main entry point (Tier 1 triage + Tier 2 auction)
    SquadRegistry  — Pre-configured multi-agent squad templates
    RoutingMetrics — Observability for routing cost/latency
"""

from mindflow_backend.orchestrator.routing.hybrid_router import (  # noqa: F401
    HybridRouter,
    get_hybrid_router,
)
from mindflow_backend.orchestrator.routing.decentralized_router import (  # noqa: F401
    DecentralizedRouter,
    route_message_decentralized,
)
from mindflow_backend.orchestrator.routing.proposal_collector import (  # noqa: F401
    ProposalCollector,
)
from mindflow_backend.orchestrator.routing.proposal_evaluator import (  # noqa: F401
    ProposalEvaluator,
)
from mindflow_backend.orchestrator.routing.routing_metrics import (  # noqa: F401
    RoutingMetrics,
)
from mindflow_backend.orchestrator.routing.squad_registry import (  # noqa: F401
    SquadRegistry,
    SquadTemplate,
    get_squad_registry,
)
from mindflow_backend.orchestrator.routing.intelligent_router import (  # noqa: F401
    IntelligentRouter,
    route_message_intelligently,
)
from mindflow_backend.orchestrator.routing.orchestration_router import (  # noqa: F401
    OrchestrationRouter,
    RoutingContext,
    get_orchestration_router,
    route_message,
)

__all__ = [
    # Primary entry point (use this)
    "HybridRouter",
    "get_hybrid_router",
    # Squad templates
    "SquadRegistry",
    "SquadTemplate",
    "get_squad_registry",
    # Metrics / observability
    "RoutingMetrics",
    "OrchestrationRouter",
    "RoutingContext",
    "get_orchestration_router",
    # Tier 1 (kept for direct use)
    "route_message",
    "route_message_intelligently",
    "IntelligentRouter",
    # Tier 2 (kept for direct use and backward compat)
    "DecentralizedRouter",
    "route_message_decentralized",
    "ProposalCollector",
    "ProposalEvaluator",
]
