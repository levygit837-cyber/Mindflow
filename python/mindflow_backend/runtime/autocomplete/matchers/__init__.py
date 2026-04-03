"""Matchers for autocomplete suggestions."""

from .fuzzy_matcher import fuzzy_match
from .prefix_matcher import prefix_match

__all__ = ["fuzzy_match", "prefix_match"]