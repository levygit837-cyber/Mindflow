"""Research specialist tools for RESEARCHER agents.

Provides tools for web search, browser automation, source validation,
and content analysis specifically designed for research tasks.
Also includes research agent components and utilities.
"""

from __future__ import annotations

# Web search tools
from .browser_search import *
from .search_web import *

# Research components
from .core import *
from .analysis import *
from .monitoring import *

__all__ = [
    # Web search tools
    "browser_search",
    "search_web",
    
    # Core components
    "get_enhanced_researcher_agent",
    "get_enhanced_query_planner",
    
    # Analysis components
    "get_result_synthesizer", 
    "get_source_trust_engine",
    
    # Monitoring components
    "get_action_trail_logger",
    "get_pitchtab_monitor",
    "get_pinchtab_service",
]
