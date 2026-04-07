"""Research specialist tools for RESEARCHER agents.

Provides tools for web search, browser automation, source validation,
and content analysis specifically designed for research tasks.
Also includes research agent components and utilities.
"""

from __future__ import annotations

from .analysis import *

# Web search tools
from .browser_search import *

# Research components
from .core import *
from .search_web import *

__all__ = [
    # Web search tools
    "browser_search",
    "search_web",
    
    # Core components
    "get_enhanced_query_planner",
    
    # Analysis components
    "get_result_synthesizer", 
    "get_source_trust_engine",
]
