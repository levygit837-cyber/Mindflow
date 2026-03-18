"""Legacy research module - redirected to tools.

This module provides backward compatibility by redirecting imports
to the new location: agents.tools.specialist.research
"""

from __future__ import annotations

import importlib
import sys

# Redirect all imports to the new location
from .tools.specialist.research import *  # noqa: F401,F403

# Emulate the old package structure so imports like
# `mindflow_backend.agents.research.query_engine` keep working.
__path__: list[str] = []

_LEGACY_SUBMODULES = {
    "query_engine": "mindflow_backend.agents.tools.specialist.research.core.query_engine",
    "enhanced_query_planner": "mindflow_backend.agents.tools.specialist.research.core.enhanced_query_planner",
    "enhanced_researcher": "mindflow_backend.agents.tools.specialist.research.core.enhanced_researcher",
    "browser_search": "mindflow_backend.agents.tools.specialist.research.browser_search",
    "search_web": "mindflow_backend.agents.tools.specialist.research.search_web",
    "result_synthesizer": "mindflow_backend.agents.tools.specialist.research.analysis.result_synthesizer",
    "source_trust_engine": "mindflow_backend.agents.tools.specialist.research.analysis.source_trust_engine",
    "pinchtab_service": "mindflow_backend.agents.tools.specialist.research.monitoring.pinchtab_service",
}

for _legacy_name, _target in _LEGACY_SUBMODULES.items():
    sys.modules.setdefault(f"{__name__}.{_legacy_name}", importlib.import_module(_target))

# Maintain backward compatibility for explicit imports
__all__ = [
    "browser_search",
    "search_web",
    "get_research_query_engine",
    "get_enhanced_researcher_agent",
    "get_enhanced_query_planner",
    "get_result_synthesizer", 
    "get_source_trust_engine",
    "get_pinchtab_service",
]
