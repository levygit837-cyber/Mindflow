"""Compatibility adapter for the canonical intelligent router.

This module preserves the older import path
``mindflow_backend.orchestrator.routing.router`` while forwarding all routing
to the authoritative LLM-based router + planner flow.
"""

from __future__ import annotations

import re

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.schemas.orchestration.orchestrator import (
    AgentType,
    OrchestratorDecision,
    Priority,
    ThinkingLevel,
    ToolScope,
)

_logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Legacy keyword maps (deprecated - kept for reference only)
# ---------------------------------------------------------------------------

# These are kept for documentation purposes but no longer used.
# The new intelligent router uses LLM-powered intent analysis instead.


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def route_message(
    message: str,
    folder_path: str | None = None,
) -> OrchestratorDecision:
    """Route a user message using intelligent LLM analysis.

    This COMPLETELY replaces the old keyword-based routing with intelligent 
    intent analysis that uses LLM to understand user intent and make 
    informed delegation decisions.
    
    The new system:
    - Uses LLM to analyze user intent (not keywords)
    - Can delegate to Analyst for context when needed
    - Makes informed decisions based on structured findings
    - Preserves individual agent context windows
    - Eliminates keyword matching fragility
    - Handles complex and ambiguous requests intelligently
    """
    from mindflow_backend.orchestrator.routing.intelligent_router import route_message_intelligently
    
    # Use intelligent routing instead of keyword matching
    return await route_message_intelligently(message, folder_path=folder_path)
