"""Research module for enhanced agent capabilities.

Contains enhanced query planning, source trust evaluation,
result synthesis, and monitoring utilities for PitchTab integration.
"""

from __future__ import annotations

def _missing(name: str):  # noqa: ANN001
    def _fn(*_args, **_kwargs):
        raise RuntimeError(f"Research component '{name}' is not available in this build.")

    return _fn


try:
    from .enhanced_query_planner import get_enhanced_query_planner  # type: ignore
except Exception:  # pragma: no cover
    get_enhanced_query_planner = _missing("enhanced_query_planner")  # type: ignore[assignment]

try:
    from .enhanced_researcher import get_enhanced_researcher_agent  # type: ignore
except Exception:  # pragma: no cover
    get_enhanced_researcher_agent = _missing("enhanced_researcher")  # type: ignore[assignment]

try:
    from .pitchtab_monitor import get_pitchtab_monitor  # type: ignore
except Exception:  # pragma: no cover
    get_pitchtab_monitor = _missing("pitchtab_monitor")  # type: ignore[assignment]

try:
    from .result_synthesizer import get_result_synthesizer  # type: ignore
except Exception:  # pragma: no cover
    get_result_synthesizer = _missing("result_synthesizer")  # type: ignore[assignment]

try:
    from .source_trust_engine import get_source_trust_engine  # type: ignore
except Exception:  # pragma: no cover
    get_source_trust_engine = _missing("source_trust_engine")  # type: ignore[assignment]

try:
    from .pinchtab_service import get_pinchtab_service  # type: ignore
except Exception:  # pragma: no cover
    get_pinchtab_service = _missing("pinchtab_service")  # type: ignore[assignment]

try:
    from .browser_search import get_browser_search_tool  # type: ignore
except Exception:  # pragma: no cover
    get_browser_search_tool = _missing("browser_search")  # type: ignore[assignment]

try:
    from .action_trail import get_action_trail_logger  # type: ignore
except Exception:  # pragma: no cover
    get_action_trail_logger = _missing("action_trail")  # type: ignore[assignment]

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
