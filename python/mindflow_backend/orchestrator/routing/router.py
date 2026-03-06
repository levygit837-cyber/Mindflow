"""Orchestrator router — keyword-based message routing.

Analyzes the user message and produces an ``OrchestratorDecision``
selecting the most appropriate agent personality, tool scopes, and
execution parameters.

Phase 2 uses heuristic keyword matching.  Phase 3 will add LLM-powered
intent classification for higher accuracy.

TODO (Phase 3): Replace keyword-based routing with an LLM-powered intent
classifier. Current approach is fragile — it relies on fixed keyword lists
that miss synonyms, context, and multi-intent messages. The replacement
should call an LLM with a structured prompt (e.g. function-calling or
constrained output) to classify the user message into an AgentType, and
should fall back to CODER on low-confidence or ambiguous responses.
See ``route_message()`` below for the current implementation.
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


async def route_message(message: str) -> OrchestratorDecision:
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
    from mindflow_backend.orchestrator.intelligent_router import route_message_intelligently
    
    # Use intelligent routing instead of keyword matching
    return await route_message_intelligently(message)
