"""Autocomplete System for MindFlow.

Provides intelligent suggestions for commands, files, tools,
and history-based inputs.
"""

from .engine import AutocompleteEngine, AutocompleteRequest, AutocompleteResponse, Suggestion
from .cache.suggestion_cache import SuggestionCache
from .matchers.fuzzy_matcher import fuzzy_match
from .matchers.prefix_matcher import prefix_match

__all__ = [
    "AutocompleteEngine",
    "AutocompleteRequest",
    "AutocompleteResponse",
    "Suggestion",
    "SuggestionCache",
    "fuzzy_match",
    "prefix_match",
]