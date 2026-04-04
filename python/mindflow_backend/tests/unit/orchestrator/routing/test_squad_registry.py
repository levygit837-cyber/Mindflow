"""Tests for SquadRegistry — Pre-configured squad templates.

Covers:
- SquadTemplate matching by keywords
- SquadRegistry find_squad logic
- get_squad_by_name lookup
- All predefined squad templates
"""

from __future__ import annotations

import pytest

from mindflow_backend.orchestrator.routing.squad_registry import (
    ANALYSIS_SQUAD,
    FEATURE_SQUAD,
    REFACTORING_SQUAD,
    RESEARCH_SQUAD,
    SECURITY_SQUAD,
    SquadRegistry,
    SquadTemplate,
    get_squad_registry,
)


# =========================================================================
# SquadTemplate Tests
# =========================================================================


class TestSquadTemplate:
    """Tests for SquadTemplate matching logic."""

    def test_matches_keyword_case_insensitive(self) -> None:
        """Template matches keywords regardless of case."""
        tmpl = SquadTemplate(
            name="test",
            description="test",
            agent_ids=("analyst",),
            leader="analyst",
            intent_keywords=("refactor", "cleanup"),
        )
        assert tmpl.matches("Please REFACTOR this module") is True
        assert tmpl.matches("do a Cleanup pass") is True

    def test_no_match_returns_false(self) -> None:
        """Template returns False when no keyword matches."""
        tmpl = SquadTemplate(
            name="test",
            description="test",
            agent_ids=("analyst",),
            leader="analyst",
            intent_keywords=("refactor",),
        )
        assert tmpl.matches("add a unit test for this function") is False

    def test_empty_keywords_never_match(self) -> None:
        """Template with no keywords never matches."""
        tmpl = SquadTemplate(
            name="test",
            description="test",
            agent_ids=("analyst",),
            leader="analyst",
        )
        assert tmpl.matches("refactor the authentication module") is False

    def test_matches_partial_word(self) -> None:
        """Keyword matches substrings within words."""
        tmpl = SquadTemplate(
            name="test",
            description="test",
            agent_ids=("analyst",),
            leader="analyst",
            intent_keywords=("research",),
        )
        # 'research' should match 'pesquise' separately but 'researching' yes
        assert tmpl.matches("researching best patterns") is True

    def test_squad_template_is_frozen(self) -> None:
        """SquadTemplate is immutable (frozen dataclass)."""
        with pytest.raises((AttributeError, TypeError)):
            REFACTORING_SQUAD.name = "changed"  # type: ignore[misc]


# =========================================================================
# Predefined Squads Tests
# =========================================================================


class TestPredefinedSquads:
    """Tests for predefined squad templates."""

    def test_refactoring_squad_matches(self) -> None:
        assert REFACTORING_SQUAD.matches("refactor the auth module") is True
        assert REFACTORING_SQUAD.matches("clean code smell in services") is True
        assert REFACTORING_SQUAD.matches("reestruturar o módulo de pagamentos") is True

    def test_feature_squad_matches(self) -> None:
        assert FEATURE_SQUAD.matches("implement JWT authentication") is True
        assert FEATURE_SQUAD.matches("criar feature de exportação PDF") is True
        assert FEATURE_SQUAD.matches("build a REST endpoint for users") is True

    def test_analysis_squad_matches(self) -> None:
        assert ANALYSIS_SQUAD.matches("analyze the database schema") is True
        assert ANALYSIS_SQUAD.matches("analisar performance do pipeline") is True
        assert ANALYSIS_SQUAD.matches("audit the permission system") is True

    def test_research_squad_matches(self) -> None:
        assert RESEARCH_SQUAD.matches("research best practices for OAuth") is True
        assert RESEARCH_SQUAD.matches("pesquise alternativas ao Redis") is True
        assert RESEARCH_SQUAD.matches("compare frameworks de ORM") is True

    def test_security_squad_matches(self) -> None:
        assert SECURITY_SQUAD.matches("security review of the API layer") is True
        assert SECURITY_SQUAD.matches("check for SQL injection vulnerabilities") is True
        assert SECURITY_SQUAD.matches("analise a autenticação por JWT") is True

    def test_squad_has_valid_leader(self) -> None:
        """Each squad's leader must be in its agent_ids."""
        for squad in (
            REFACTORING_SQUAD,
            FEATURE_SQUAD,
            ANALYSIS_SQUAD,
            RESEARCH_SQUAD,
            SECURITY_SQUAD,
        ):
            assert squad.leader in squad.agent_ids, (
                f"Squad '{squad.name}' leader '{squad.leader}' "
                f"not in agent_ids {squad.agent_ids}"
            )

    def test_squad_has_at_least_two_agents(self) -> None:
        """Each squad requires at least 2 agents."""
        for squad in (
            REFACTORING_SQUAD,
            FEATURE_SQUAD,
            ANALYSIS_SQUAD,
            RESEARCH_SQUAD,
            SECURITY_SQUAD,
        ):
            assert len(squad.agent_ids) >= 2, (
                f"Squad '{squad.name}' has fewer than 2 agents"
            )


# =========================================================================
# SquadRegistry Tests
# =========================================================================


class TestSquadRegistry:
    """Tests for SquadRegistry orchestration logic."""

    def setup_method(self) -> None:
        """Fresh registry for each test."""
        self.registry = SquadRegistry()

    def test_find_squad_refactoring(self) -> None:
        """find_squad returns REFACTORING_SQUAD for refactoring intent."""
        result = self.registry.find_squad("refactor the payment module")
        assert result is not None
        assert result.name == "refactoring"

    def test_find_squad_security_takes_precedence(self) -> None:
        """SECURITY_SQUAD is checked before more generic squads."""
        result = self.registry.find_squad("security audit of authentication module")
        assert result is not None
        assert result.name == "security_review"

    def test_find_squad_returns_none_on_no_match(self) -> None:
        """find_squad returns None when no squad matches."""
        result = self.registry.find_squad("what time is it?")
        assert result is None

    def test_find_squad_research(self) -> None:
        result = self.registry.find_squad("pesquise sobre WebSockets vs SSE")
        assert result is not None
        assert result.name == "research"

    def test_get_squad_by_name_found(self) -> None:
        result = self.registry.get_squad_by_name("feature_development")
        assert result is not None
        assert result.name == "feature_development"

    def test_get_squad_by_name_not_found(self) -> None:
        result = self.registry.get_squad_by_name("nonexistent_squad")
        assert result is None

    def test_all_squads_returns_all(self) -> None:
        assert len(self.registry.all_squads) == 5

    def test_custom_squads_in_registry(self) -> None:
        """Registry can be initialized with custom squads."""
        custom = SquadTemplate(
            name="custom",
            description="Custom squad",
            agent_ids=("analyst", "coder"),
            leader="analyst",
            intent_keywords=("custom_keyword",),
        )
        registry = SquadRegistry(squads=(custom,))
        assert registry.find_squad("use custom_keyword here") is not None
        assert registry.find_squad("refactor code") is None


# =========================================================================
# Singleton Tests
# =========================================================================


class TestGetSquadRegistry:
    """Tests for global singleton."""

    def test_singleton_returns_same_instance(self) -> None:
        reg1 = get_squad_registry()
        reg2 = get_squad_registry()
        assert reg1 is reg2

    def test_singleton_has_all_squads(self) -> None:
        reg = get_squad_registry()
        assert len(reg.all_squads) >= 4
