"""Legacy research module - redirected to tools.

This module provides backward compatibility by redirecting imports
to the new location: agents.tools.specialist.research
"""

from __future__ import annotations

# Redirect all imports to the new location
from .tools.specialist.research import *  # noqa: F401,F403

# Maintain backward compatibility for explicit imports
__all__ = [
    "browser_search",
    "search_web",
    "get_enhanced_researcher_agent",
    "get_enhanced_query_planner",
    "get_result_synthesizer", 
    "get_source_trust_engine",
    "get_action_trail_logger",
    "get_pitchtab_monitor",
    "get_pinchtab_service",
]
