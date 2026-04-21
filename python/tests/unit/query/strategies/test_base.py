"""Contract tests for query.strategies base module."""

from __future__ import annotations

import pytest

from mindflow_backend.query.strategies import (
    BaseStrategy,
    QueryStrategy,
    StrategyContext,
    StrategyResult,
    get_strategy,
)


def test_query_strategy_enum_members():
    members = {s.value for s in QueryStrategy}
    assert members == {"direct", "react", "decomposition", "deep_work"}


def test_strategy_context_minimal_construction():
    ctx = StrategyContext(message="hi")
    assert ctx.message == "hi"
    assert ctx.tools == []
    assert ctx.messages == []
    assert ctx.services == {}
    assert ctx.metadata == {}
    assert ctx.token_budget is None
    assert ctx.max_turns == 50
    assert ctx.max_depth == 1000


def test_strategy_result_defaults():
    result = StrategyResult()
    assert result.response == ""
    assert result.error is None
    assert result.turn_count == 0
    assert result.messages == []
    assert result.metadata == {}


@pytest.mark.parametrize("member", list(QueryStrategy))
def test_get_strategy_resolves_every_enum_member(member: QueryStrategy):
    impl = get_strategy(member)
    assert isinstance(impl, BaseStrategy)
    assert impl.strategy is member


def test_get_strategy_rejects_unknown_value():
    with pytest.raises(ValueError):
        QueryStrategy("nope")
