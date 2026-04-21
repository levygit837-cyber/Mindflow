"""
Tests unitários para Fase 3B — Memory Observer.

Testa:
- MemoryAnnotation schema (importance, significance)
- MemoryObserver scoring e classificação
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import asyncio

from mindflow_backend.schemas.memory.annotation import (
    MemoryAnnotation,
    EVENT_IMPORTANCE_MAP,
    IMPORTANCE_THRESHOLDS,
)
from mindflow_backend.execution.observers.memory_observer import MemoryObserver


# ─────────────────────────────────────────────
# MemoryAnnotation Tests
# ─────────────────────────────────────────────

class TestMemoryAnnotation:
    """Tests para MemoryAnnotation schema."""

    def test_is_significant_above_threshold(self):
        """Anotação com importance >= 0.3 é significativa."""
        ann = MemoryAnnotation(
            observer_agent_id="analyst",
            source_agent_id="coder",
            content="Test",
            importance=0.5,
        )
        assert ann.is_significant() is True

    def test_is_significant_below_threshold(self):
        """Anotação com importance < 0.3 não é significativa."""
        ann = MemoryAnnotation(
            observer_agent_id="analyst",
            source_agent_id="coder",
            content="Test",
            importance=0.2,
        )
        assert ann.is_significant() is False

    def test_is_significant_at_threshold(self):
        """Anotação com importance == 0.3 é significativa."""
        ann = MemoryAnnotation(
            observer_agent_id="analyst",
            source_agent_id="coder",
            content="Test",
            importance=0.3,
        )
        assert ann.is_significant() is True

    def test_to_memory_content_format(self):
        """to_memory_content retorna string formatada corretamente."""
        ann = MemoryAnnotation(
            observer_agent_id="analyst",
            source_agent_id="coder",
            content="SQL injection found",
            annotation_type="finding",
        )
        content = ann.to_memory_content()
        assert "[Observer: analyst]" in content
        assert "[Source: coder]" in content
        assert "[Type: finding]" in content
        assert "SQL injection found" in content

    def test_default_values(self):
        """Valores default estão corretos."""
        ann = MemoryAnnotation()
        assert ann.annotation_type == "observation"
        assert ann.importance == 0.5
        assert ann.observer_agent_id == ""
        assert ann.annotation_id is not None


# ─────────────────────────────────────────────
# MemoryObserver Scoring Tests
# ─────────────────────────────────────────────

class TestMemoryObserverScoring:
    """Tests para scoring e classificação do MemoryObserver."""

    def test_score_importance_error_event(self):
        """Eventos ERROR têm score alto."""
        event = {"type": "error", "level": "ERROR"}
        score = MemoryObserver._score_importance(event)
        assert score >= 0.9

    def test_score_importance_warning_event(self):
        """Eventos WARNING têm score elevado."""
        event = {"type": "tool_result", "level": "WARNING"}
        score = MemoryObserver._score_importance(event)
        assert score >= 0.7

    def test_score_importance_debug_event(self):
        """Eventos debug têm score baixo."""
        event = {"type": "debug", "level": "DEBUG"}
        score = MemoryObserver._score_importance(event)
        assert score < 0.3

    def test_score_importance_progress_event(self):
        """Eventos progress têm score baixo."""
        event = {"type": "progress", "level": "INFO"}
        score = MemoryObserver._score_importance(event)
        assert score < 0.3

    def test_score_importance_agent_decision(self):
        """Agent decision tem score médio-alto."""
        event = {"type": "agent_decision", "level": "INFO"}
        score = MemoryObserver._score_importance(event)
        assert score >= 0.5

    def test_classify_event_error_returns_warning(self):
        """Eventos ERROR são classificados como 'warning'."""
        event = {"type": "error", "level": "ERROR"}
        result = MemoryObserver._classify_event(event)
        assert result == "warning"

    def test_classify_event_agent_decision_returns_finding(self):
        """Agent decision é classificado como 'finding'."""
        event = {"type": "agent_decision", "level": "INFO"}
        result = MemoryObserver._classify_event(event)
        assert result == "finding"

    def test_classify_event_mission_complete_returns_insight(self):
        """Mission complete é classificado como 'insight'."""
        event = {"type": "mission_complete", "level": "INFO"}
        result = MemoryObserver._classify_event(event)
        assert result == "insight"

    def test_classify_event_default_returns_observation(self):
        """Eventos genéricos são classificados como 'observation'."""
        event = {"type": "tool_result", "level": "INFO"}
        result = MemoryObserver._classify_event(event)
        assert result == "observation"

    def test_summarize_event_with_message(self):
        """Summarize gera resumo com message."""
        event = {
            "agent_id": "coder",
            "type": "tool_result",
            "message": "File auth.py modified",
            "data": {},
        }
        result = MemoryObserver._summarize_event(event)
        assert "coder" in result
        assert "tool_result" in result
        assert "File auth.py modified" in result

    def test_summarize_event_with_data(self):
        """Summarize inclui dados relevantes."""
        event = {
            "agent_id": "coder",
            "type": "finding",
            "message": "Vulnerability detected",
            "data": {"file": "auth.py", "pattern": "SQL injection"},
        }
        result = MemoryObserver._summarize_event(event)
        assert "auth.py" in result
        assert "SQL injection" in result

    def test_summarize_event_empty(self):
        """Summarize retorna string vazia se sem message/data."""
        event = {"agent_id": "coder", "type": "test", "message": "", "data": {}}
        result = MemoryObserver._summarize_event(event)
        assert result == ""

    def test_extract_tags(self):
        """Tags extraídas corretamente."""
        event = {"type": "tool_result", "agent_id": "coder", "level": "ERROR"}
        tags = MemoryObserver._extract_tags(event)
        assert "event:tool_result" in tags
        assert "agent:coder" in tags
        assert "error" in tags


# ─────────────────────────────────────────────
# MemoryObserver Lifecycle Tests
# ─────────────────────────────────────────────

class TestMemoryObserverLifecycle:
    """Tests para lifecycle do MemoryObserver."""

    @pytest.mark.asyncio
    async def test_observer_starts_and_stops(self):
        """Observer inicia e para corretamente."""
        mock_memory = MagicMock()
        observer = MemoryObserver(
            observer_agent_id="analyst",
            memory_facade=mock_memory,
            session_id="test-session",
        )

        assert observer._running is False
        await observer.start_observing(["mission-1"])
        assert observer._running is True
        assert observer._task is not None

        await observer.stop_observing()
        assert observer._running is False

    @pytest.mark.asyncio
    async def test_observer_receive_event_enqueues(self):
        """receive_event enfileira evento quando running."""
        mock_memory = MagicMock()
        observer = MemoryObserver(
            observer_agent_id="analyst",
            memory_facade=mock_memory,
            session_id="test-session",
        )
        observer._running = True

        event = {
            "type": "tool_result",
            "agent_id": "coder",
            "mission_id": "mission-1",
            "level": "INFO",
            "message": "Test",
        }
        await observer.receive_event(event)
        assert observer._event_queue.qsize() == 1

    @pytest.mark.asyncio
    async def test_observer_receive_event_ignored_when_not_running(self):
        """receive_event ignora eventos quando não running."""
        mock_memory = MagicMock()
        observer = MemoryObserver(
            observer_agent_id="analyst",
            memory_facade=mock_memory,
            session_id="test-session",
        )
        # Não iniciar - _running é False

        event = {"type": "test", "agent_id": "coder", "level": "INFO", "message": "Test"}
        await observer.receive_event(event)
        assert observer._event_queue.qsize() == 0

    def test_observer_get_stats(self):
        """get_stats retorna estatísticas corretas."""
        mock_memory = MagicMock()
        observer = MemoryObserver(
            observer_agent_id="analyst",
            memory_facade=mock_memory,
            session_id="test-session",
        )
        observer._running = True
        observer._annotations_count = 5
        observer._observed_missions = {"mission-1", "mission-2"}

        stats = observer.get_stats()
        assert stats["observer_id"] == "analyst"
        assert stats["running"] is True
        assert stats["total_annotations"] == 5
        assert sorted(stats["observed_missions"]) == ["mission-1", "mission-2"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])