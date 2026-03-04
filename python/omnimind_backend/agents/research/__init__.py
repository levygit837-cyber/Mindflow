"""Research module for enhanced agent capabilities.

Contains enhanced query planning, source trust evaluation,
result synthesis, and monitoring utilities for PitchTab integration.
"""

from __future__ import annotations

from .enhanced_query_planner import get_enhanced_query_planner
from .enhanced_researcher import get_enhanced_researcher_agent
from .pitchtab_monitor import get_pitchtab_monitor
from .result_synthesizer import get_result_synthesizer
from .source_trust_engine import get_source_trust_engine
from .pinchtab_service import get_pinchtab_service
from .browser_search import get_browser_search_tool
from .action_trail import get_action_trail_logger

__all__ = [
    "get_enhanced_query_planner",
    "get_enhanced_researcher_agent", 
    "get_pitchtab_monitor",
    "get_result_synthesizer",
    "get_source_trust_engine",
    "get_pinchtab_service",
    "get_browser_search_tool",
    "get_action_trail_logger",
]
