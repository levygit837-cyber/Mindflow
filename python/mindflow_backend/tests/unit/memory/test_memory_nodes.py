"""Tests unitários para Memory Nodes (RecallNode e SaveNode).

Testa:
- MemoryRecallNode: busca e formatação de memórias
- MemorySaveNode: salvamento de memórias
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, ANY
import asyncio

from mindflow_backend.nodes.implementations.memory import (
    MemoryRecallNode,
    MemorySaveNode,
)
from mindflow_backend.memory.memory_service import MemoryService, MemorySearchResult
from mindflow_backend.memory.storage.models import MemoryEntry


# ─────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────

@pytest.fixture
def mock_memory_service():
    """Fixture para MemoryService mock."""
    service = MagicMock(spec=MemoryService)
    service.search_memories = AsyncMock(return_value=[])
    service.save_memory = AsyncMock()
    service.initialize = AsyncMock()
    return service


@pytest.fixture
def sample_memory():
    """Fixture para MemoryEntry mock."""
    memory = MagicMock(spec=MemoryEntry)
    memory.id = 1
    memory.content = "Test memory about Python async patterns"
    memory.memory_type = "pattern"
    memory.scope = "project"
    memory.importance = 0.8
    memory.category = MagicMock()
    memory.category.name = "code_patterns"
    memory.created_at = MagicMock()
    memory.created_at.isoformat.return_value = "2024-01-01T00:00:00"
    return memory


@pytest.fixture
def recall_node(mock_memory_service):
    """Fixture para MemoryRecallNode."""
    node = MemoryRecallNode(node_id="memory_recall_test")
    node._memory_service = mock_memory_service
    return node


@pytest.fixture
def save_node(mock_memory_service):
    """Fixture para MemorySaveNode."""
    node = MemorySaveNode(node_id="memory_save_test")
    node._memory_service = mock_memory_service
    return node


# ─────────────────────────────────────────────
# MemoryRecallNode Tests
# ─────────────────────────────────────────────

class TestMemoryRecallNode:
    """Tests para MemoryRecallNode."""

    @pytest.mark.asyncio
    async def test_execute_basic_search(self, recall_node, mock_memory_service, sample_memory):
        """Deve executar busca básica de memórias."""
        # Setup
        mock_result = MagicMock(spec=MemorySearchResult)
        mock_result.memory = sample_memory
        mock_result.score = 0.85
        mock_result.search_type = "hybrid"
        mock_memory_service.search_memories.return_value = [mock_result]

        state = {
            "task_description": "How to use async in Python",
            "project_id": 1,
        }

        # Execute
        result = await recall_node.execute(state)

        # Verify
        assert "context_summary" in result
        assert "memories_found" in result
        assert result["memories_found"] == 1
        assert len(result["memories"]) == 1

    @pytest.mark.asyncio
    async def test_execute_with_recent_context(self, recall_node, mock_memory_service, sample_memory):
        """Deve usar recent_context para enriquecer busca."""
        mock_result = MagicMock(spec=MemorySearchResult)
        mock_result.memory = sample_memory
        mock_result.score = 0.9
        mock_result.search_type = "semantic"
        mock_memory_service.search_memories.return_value = [mock_result]

        state = {
            "task_description": "Async patterns",
            "recent_context": "Previous discussion about Python",
            "scope": "project",
            "project_id": 1,
        }

        result = await recall_node.execute(state)

        # Deve ter chamado search_memories com query combinada
        mock_memory_service.search_memories.assert_called_once()
        call_args = mock_memory_service.search_memories.call_args[1]
        assert "query" in call_args or any("recent" in str(arg) for arg in call_args.values())

    @pytest.mark.asyncio
    async def test_execute_with_filters(self, recall_node, mock_memory_service, sample_memory):
        """Deve aplicar filtros de categoria e tipo."""
        mock_result = MagicMock(spec=MemorySearchResult)
        mock_result.memory = sample_memory
        mock_result.score = 0.75
        mock_memory_service.search_memories.return_value = [mock_result]

        state = {
            "task_description": "Code patterns",
            "categories": ["code_patterns"],
            "memory_types": ["pattern"],
            "tags": ["python"],
            "min_importance": 0.6,
            "limit": 5,
        }

        result = await recall_node.execute(state)

        mock_memory_service.search_memories.assert_called_once()
        call_kwargs = mock_memory_service.search_memories.call_args[1]
        assert call_kwargs.get("categories") == ["code_patterns"]
        assert call_kwargs.get("memory_types") == ["pattern"]

    @pytest.mark.asyncio
    async def test_execute_no_results(self, recall_node, mock_memory_service):
        """Deve lidar com busca sem resultados."""
        mock_memory_service.search_memories.return_value = []

        state = {"task_description": "Unknown topic"}
        result = await recall_node.execute(state)

        assert result["memories_found"] == 0
        assert result["memories"] == []
        assert result["context_summary"] == ""

    @pytest.mark.asyncio
    async def test_execute_graceful_failure(self, recall_node, mock_memory_service):
        """Deve falhar gracefully quando serviço falha."""
        mock_memory_service.search_memories.side_effect = Exception("Service error")

        state = {"task_description": "Test"}
        result = await recall_node.execute(state)

        assert result["memories_found"] == 0
        assert "error" in result["search_metadata"]

    def test_validate_inputs_missing_task(self, recall_node):
        """Deve validar que task_description é obrigatório."""
        state = {}  # Sem task_description
        errors = recall_node.validate_inputs(state)

        assert len(errors) == 1
        assert "task_description" in errors[0]

    def test_validate_inputs_valid(self, recall_node):
        """Deve aceitar state válido."""
        state = {"task_description": "Valid task"}
        errors = recall_node.validate_inputs(state)

        assert len(errors) == 0

    def test_build_search_query_with_context(self, recall_node):
        """Deve combinar task com recent context."""
        query = recall_node._build_search_query(
            task_description="How to use async",
            recent_context="Previous code review",
        )

        assert "How to use async" in query
        assert "Previous code review" in query

    def test_build_search_query_without_context(self, recall_node):
        """Deve usar apenas task se não houver contexto."""
        query = recall_node._build_search_query(
            task_description="Python patterns",
            recent_context=None,
        )

        assert query == "Python patterns"

    def test_format_context_summary_with_results(self, recall_node, sample_memory):
        """Deve formatar summary com resultados agrupados por categoria."""
        mock_result = MagicMock(spec=MemorySearchResult)
        mock_result.memory = sample_memory

        summary = recall_node._format_context_summary([mock_result])

        assert "## Relevant Context" in summary
        assert "### Code Patterns" in summary
        assert "Test memory" in summary

    def test_format_context_summary_empty(self, recall_node):
        """Deve retornar string vazia se não houver resultados."""
        summary = recall_node._format_context_summary([])
        assert summary == ""

    def test_get_input_schema(self, recall_node):
        """Deve retornar schema de input."""
        schema = recall_node.get_input_schema()
        assert schema is not None

    def test_get_output_schema(self, recall_node):
        """Deve retornar schema de output."""
        schema = recall_node.get_output_schema()
        assert schema is not None


# ─────────────────────────────────────────────
# MemorySaveNode Tests
# ─────────────────────────────────────────────

class TestMemorySaveNode:
    """Tests para MemorySaveNode."""

    @pytest.mark.asyncio
    async def test_execute_basic_save(self, save_node, mock_memory_service):
        """Deve salvar memória básica."""
        # Setup retorno do save_memory
        mock_memory = MagicMock()
        mock_memory.id = 123
        mock_memory.category = MagicMock()
        mock_memory.category.name = "code_patterns"
        mock_memory.scope = "project"
        mock_memory.importance = 0.7
        mock_memory_service.save_memory.return_value = mock_memory

        state = {
            "content": "User prefers async functions with type hints",
            "memory_type": "preference",
            "scope": "project",
            "project_id": 1,
            "agent_id": "coder_agent",
        }

        result = await save_node.execute(state)

        assert result["saved_successfully"] is True
        assert result["memory_id"] == 123
        mock_memory_service.save_memory.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_with_category(self, save_node, mock_memory_service):
        """Deve usar categoria especificada."""
        mock_memory = MagicMock()
        mock_memory.id = 456
        mock_memory.category = MagicMock()
        mock_memory.category.name = "user_preferences"
        mock_memory.scope = "global"
        mock_memory.importance = 0.8
        mock_memory_service.save_memory.return_value = mock_memory

        state = {
            "content": "Prefer dark mode",
            "memory_type": "preference",
            "scope": "global",
            "category": "user_preferences",
            "subcategory": "ui",
            "importance": 0.9,
            "tags": ["ui", "theme"],
        }

        result = await save_node.execute(state)

        call_args = mock_memory_service.save_memory.call_args[1]
        assert call_args["category"] == "user_preferences"
        assert call_args["subcategory"] == "ui"
        assert call_args["importance"] == 0.9

    @pytest.mark.asyncio
    async def test_execute_with_source_context(self, save_node, mock_memory_service):
        """Deve adicionar source_context ao conteúdo."""
        mock_memory = MagicMock()
        mock_memory.id = 789
        mock_memory.category = None
        mock_memory.scope = "session"
        mock_memory.importance = 0.5
        mock_memory_service.save_memory.return_value = mock_memory

        state = {
            "content": "Important insight",
            "source_context": "From code review discussion",
            "scope": "session",
        }

        await save_node.execute(state)

        call_args = mock_memory_service.save_memory.call_args[1]
        assert "From code review discussion" in call_args["content"]

    @pytest.mark.asyncio
    async def test_execute_with_structured_data(self, save_node, mock_memory_service):
        """Deve incluir structured_data se fornecido."""
        mock_memory = MagicMock()
        mock_memory.id = 111
        mock_memory.category = None
        mock_memory.scope = "project"
        mock_memory.importance = 0.6
        mock_memory_service.save_memory.return_value = mock_memory

        structured = {"functions": ["foo", "bar"], "lines": 42}
        state = {
            "content": "Code analysis",
            "scope": "project",
            "project_id": 1,
            "structured_data": structured,
        }

        await save_node.execute(state)

        call_args = mock_memory_service.save_memory.call_args[1]
        assert call_args["structured_data"] == structured

    @pytest.mark.asyncio
    async def test_execute_graceful_failure(self, save_node, mock_memory_service):
        """Deve falhar gracefully."""
        mock_memory_service.save_memory.side_effect = Exception("Database error")

        state = {"content": "Test content", "scope": "global"}
        result = await save_node.execute(state)

        assert result["saved_successfully"] is False
        assert "error" in result

    def test_validate_inputs_missing_content(self, save_node):
        """Deve exigir content."""
        state = {"scope": "global"}  # Sem content
        errors = save_node.validate_inputs(state)

        assert len(errors) >= 1
        assert any("content" in e.lower() for e in errors)

    def test_validate_inputs_short_content(self, save_node):
        """Deve rejeitar content muito curto."""
        state = {"content": "AB"}  # Menos de 10 caracteres
        errors = save_node.validate_inputs(state)

        assert any("short" in e.lower() for e in errors)

    def test_validate_inputs_invalid_scope(self, save_node):
        """Deve validar scope."""
        state = {
            "content": "Valid content",
            "scope": "invalid_scope",
        }
        errors = save_node.validate_inputs(state)

        assert any("scope" in e.lower() for e in errors)

    def test_validate_inputs_project_scope_without_id(self, save_node):
        """Deve exigir project_id quando scope é project."""
        state = {
            "content": "Valid content",
            "scope": "project",
            # project_id faltando
        }
        errors = save_node.validate_inputs(state)

        assert any("project_id" in e.lower() for e in errors)

    def test_validate_inputs_valid(self, save_node):
        """Deve aceitar input válido."""
        state = {
            "content": "Valid memory content",
            "scope": "global",
        }
        errors = save_node.validate_inputs(state)

        assert len(errors) == 0

    def test_get_input_schema(self, save_node):
        """Deve retornar schema de input."""
        schema = save_node.get_input_schema()
        assert schema is not None

    def test_get_output_schema(self, save_node):
        """Deve retornar schema de output."""
        schema = save_node.get_output_schema()
        assert schema is not None


# ─────────────────────────────────────────────
# Edge Cases Tests
# ─────────────────────────────────────────────

class TestEdgeCases:
    """Tests para casos edge."""

    @pytest.mark.asyncio
    async def test_recall_node_with_special_characters(self, recall_node, mock_memory_service, sample_memory):
        """Deve lidar com caracteres especiais na busca."""
        mock_result = MagicMock(spec=MemorySearchResult)
        mock_result.memory = sample_memory
        mock_memory_service.search_memories.return_value = [mock_result]

        state = {
            "task_description": "Código com acentuação: café, naïve",
            "scope": "global",
        }

        result = await recall_node.execute(state)

        assert "memories_found" in result

    @pytest.mark.asyncio
    async def test_save_node_with_very_long_content(self, save_node, mock_memory_service):
        """Deve lidar com conteúdo muito longo."""
        mock_memory = MagicMock()
        mock_memory.id = 999
        mock_memory.category = None
        mock_memory.scope = "global"
        mock_memory.importance = 0.5
        mock_memory_service.save_memory.return_value = mock_memory

        long_content = "A" * 10000
        state = {
            "content": long_content,
            "scope": "global",
        }

        result = await save_node.execute(state)

        assert result["saved_successfully"] is True

    @pytest.mark.asyncio
    async def test_recall_node_with_many_results(self, recall_node, mock_memory_service, sample_memory):
        """Deve lidar com muitos resultados."""
        # Criar 20 resultados mock
        results = []
        for i in range(20):
            mock_result = MagicMock(spec=MemorySearchResult)
            mock_result.memory = sample_memory
            mock_result.score = 0.8 - (i * 0.01)
            mock_result.search_type = "semantic"
            results.append(mock_result)

        mock_memory_service.search_memories.return_value = results

        state = {
            "task_description": "General query",
            "limit": 50,
        }

        result = await recall_node.execute(state)

        assert result["memories_found"] == 20
