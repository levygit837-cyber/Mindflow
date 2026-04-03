"""Tests for Autocomplete System."""

from __future__ import annotations

import pytest

from mindflow_backend.runtime.autocomplete.engine import (
    AutocompleteEngine,
    AutocompleteRequest,
    Suggestion,
    SuggestionCategory,
)
from mindflow_backend.runtime.autocomplete.matchers.fuzzy_matcher import fuzzy_match
from mindflow_backend.runtime.autocomplete.matchers.prefix_matcher import prefix_match
from mindflow_backend.runtime.autocomplete.cache.suggestion_cache import SuggestionCache
from mindflow_backend.runtime.autocomplete.providers.command_provider import CommandProvider


class TestFuzzyMatcher:
    """Tests for fuzzy matching."""

    def test_exact_match(self) -> None:
        score = fuzzy_match("help", "help")
        assert score == 1.0

    def test_prefix_match(self) -> None:
        score = fuzzy_match("hel", "help")
        assert score > 0.5

    def test_subsequence_match(self) -> None:
        score = fuzzy_match("rdfl", "read_file")
        assert score > 0

    def test_no_match(self) -> None:
        score = fuzzy_match("xyz", "help")
        assert score == 0.0

    def test_empty_query(self) -> None:
        score = fuzzy_match("", "help")
        assert score == 0.0


class TestPrefixMatcher:
    """Tests for prefix matching."""

    def test_exact_match(self) -> None:
        score = prefix_match("/help", "/help")
        assert score == 1.0

    def test_prefix_match(self) -> None:
        score = prefix_match("/hel", "/help")
        assert score > 0.5

    def test_no_match(self) -> None:
        score = prefix_match("/xyz", "/help")
        assert score == 0.0


class TestSuggestionCache:
    """Tests for suggestion cache."""

    def test_set_and_get(self) -> None:
        cache = SuggestionCache(ttl=60, max_entries=100)
        suggestions = [Suggestion(text="test")]
        cache.set("key", suggestions)
        result = cache.get("key")
        assert result is not None
        assert len(result) == 1

    def test_get_missing_key(self) -> None:
        cache = SuggestionCache()
        result = cache.get("missing")
        assert result is None


class TestCommandProvider:
    """Tests for command provider."""

    @pytest.mark.asyncio
    async def test_suggest_commands(self) -> None:
        provider = CommandProvider()
        request = AutocompleteRequest(input_text="/hel")
        suggestions = await provider.get_suggestions(request)
        assert len(suggestions) > 0
        assert any(s.text == "/help" for s in suggestions)

    @pytest.mark.asyncio
    async def test_no_suggestions_without_slash(self) -> None:
        provider = CommandProvider()
        request = AutocompleteRequest(input_text="hello")
        suggestions = await provider.get_suggestions(request)
        assert len(suggestions) == 0


class TestAutocompleteEngine:
    """Tests for autocomplete engine."""

    @pytest.mark.asyncio
    async def test_suggest_with_provider(self) -> None:
        engine = AutocompleteEngine()
        engine.register_provider(CommandProvider())

        request = AutocompleteRequest(input_text="/hel")
        response = await engine.suggest(request)
        assert len(response.suggestions) > 0
        assert response.latency_ms >= 0

    @pytest.mark.asyncio
    async def test_suggest_empty_input(self) -> None:
        engine = AutocompleteEngine()
        engine.register_provider(CommandProvider())

        request = AutocompleteRequest(input_text="")
        response = await engine.suggest(request)
        assert len(response.suggestions) == 0