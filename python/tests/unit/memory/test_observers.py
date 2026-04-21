"""Tests unitários para os Observers do Intelligent Memory System.

Testa a lógica real dos observers com banco de dados quando necessário.
"""

from __future__ import annotations

import hashlib
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from mindflow_backend.memory.observers import (
    EventBusMemoryObserver,
    PostToolUseObserver,
    DynamicCodeParser,
    MemoryObserverCoordinator,
    ObserverConfig,
)
from mindflow_backend.memory.memory_service import MemoryService
from mindflow_backend.memory.category_manager import CategoryManager


# ─────────────────────────────────────────────
# DynamicCodeParser Tests
# ─────────────────────────────────────────────

class TestDynamicCodeParser:
    """Tests para o parser de código."""

    def test_parse_python_file(self):
        """Deve extrair estrutura de código Python."""
        code = """
import os
import sys
from datetime import datetime

class MyClass:
    def method(self, value):
        return value

def my_function(x, y):
    return x + y

async def async_func(name: str) -> int:
    return len(name)
"""
        parser = DynamicCodeParser()
        analysis = parser.parse("/test/file.py", code)

        assert analysis.language == "py"
        assert analysis.has_patterns is True
        assert len(analysis.functions) >= 2
        assert len(analysis.classes) == 1
        assert "os" in analysis.imports
        assert "sys" in analysis.imports

    def test_parse_javascript_file(self):
        """Deve extrair estrutura de código JavaScript."""
        code = """
import React from 'react';
import { useState, useEffect } from 'react';

function MyComponent(props) {
    return <div>Hello</div>;
}

const myFunc = (x, y) => x + y;
"""
        parser = DynamicCodeParser()
        analysis = parser.parse("/test/file.js", code)

        assert analysis.language == "js"
        assert analysis.has_patterns is True
        assert len(analysis.functions) >= 1
        assert "react" in analysis.imports

    def test_parse_empty_file(self):
        """Deve lidar com arquivo vazio."""
        parser = DynamicCodeParser()
        analysis = parser.parse("/test/empty.py", "")

        assert analysis.has_patterns is False
        assert len(analysis.functions) == 0


# ─────────────────────────────────────────────
# ObserverConfig Tests
# ─────────────────────────────────────────────

class TestObserverConfig:
    """Tests para configuração de observers."""

    def test_default_config(self):
        """Deve criar config com valores padrão."""
        config = ObserverConfig()

        assert config.event_buffer_interval == 30.0
        assert config.event_rate_limit == 20
        assert config.event_bus_enabled is True
        assert config.post_tool_enabled is True

    def test_custom_config(self):
        """Deve aceitar valores customizados."""
        config = ObserverConfig(
            event_buffer_interval=60.0,
            event_rate_limit=50,
            event_bus_enabled=False,
            post_tool_enabled=False,
        )

        assert config.event_buffer_interval == 60.0
        assert config.event_rate_limit == 50
        assert config.event_bus_enabled is False


# ─────────────────────────────────────────────
# EventBusMemoryObserver Tests (Lógica)
# ─────────────────────────────────────────────

class TestEventBusMemoryObserverLogic:
    """Tests para lógica do EventBusMemoryObserver."""

    @pytest.mark.asyncio
    async def test_event_deduplication(self, db_session: AsyncSession):
        """Deve deduplicar eventos idênticos."""
        from unittest.mock import MagicMock, AsyncMock

        service = MagicMock()
        service.save_memory = AsyncMock()

        observer = EventBusMemoryObserver(
            memory_service=service,
            buffer_interval=0.1,
        )
        observer._running = True  # Simular estado de execução

        event = {"agent_id": "agent1", "type": "test", "timestamp": "123", "message": "test event"}

        # Adicionar mesmo evento duas vezes
        await observer._on_event(event)
        await observer._on_event(event)  # Deve ser deduplicado

        # Verificar que apenas um event_id foi processado
        assert len(observer._processed_events) == 1

    @pytest.mark.asyncio
    async def test_event_id_generation(self, db_session: AsyncSession):
        """Deve gerar ID consistente para eventos."""
        from unittest.mock import MagicMock

        service = MagicMock()
        observer = EventBusMemoryObserver(
            memory_service=service,
            buffer_interval=0.1,
        )

        event = {"agent_id": "agent1", "type": "test", "timestamp": "123", "message": "test event"}
        event_id1 = observer._get_event_id(event)
        event_id2 = observer._get_event_id(event)

        assert event_id1 == event_id2
        assert isinstance(event_id1, str)
        assert len(event_id1) == 16  # ID truncado em 16 chars

    @pytest.mark.asyncio
    async def test_observer_stats(self, db_session: AsyncSession):
        """Deve retornar estatísticas do observer."""
        from unittest.mock import MagicMock

        service = MagicMock()
        observer = EventBusMemoryObserver(
            memory_service=service,
            buffer_interval=0.1,
        )

        stats = observer.get_stats()

        assert "running" in stats
        assert "buffer_size" in stats
        assert "processed_events" in stats


# ─────────────────────────────────────────────
# PostToolUseObserver Tests (Lógica)
# ─────────────────────────────────────────────

class TestPostToolUseObserverLogic:
    """Tests para lógica do PostToolUseObserver."""

    def test_extract_file_path_from_tool_result(self):
        """Deve extrair file_path de tool result."""
        from unittest.mock import MagicMock

        service = MagicMock()
        observer = PostToolUseObserver(memory_service=service)

        result = {
            "file_path": "/src/main.py",
            "old_string": "def old():",
            "new_string": "def new():",
        }

        file_path = observer._extract_file_path(result)

        assert file_path == "/src/main.py"

    def test_extract_content_from_tool_result(self):
        """Deve extrair content de tool result."""
        from unittest.mock import MagicMock

        service = MagicMock()
        observer = PostToolUseObserver(memory_service=service)

        result = {
            "file_path": "/src/new.py",
            "content": "# New file",
        }

        content = observer._extract_content(result)

        assert content == "# New file"

    def test_can_analyze_writable_tools(self):
        """Deve retornar True para ferramentas de escrita."""
        from unittest.mock import MagicMock

        service = MagicMock()
        observer = PostToolUseObserver(memory_service=service)

        assert observer.can_analyze("write_file") is True
        assert observer.can_analyze("edit_file") is True
        assert observer.can_analyze("replace_in_file") is True

    def test_can_analyze_other_tools(self):
        """Deve retornar False para ferramentas não-escrita."""
        from unittest.mock import MagicMock

        service = MagicMock()
        observer = PostToolUseObserver(memory_service=service)

        assert observer.can_analyze("search") is False
        assert observer.can_analyze("grep") is False


# ─────────────────────────────────────────────
# MemoryObserverCoordinator Tests (Lógica)
# ─────────────────────────────────────────────

class TestMemoryObserverCoordinatorLogic:
    """Tests para lógica do MemoryObserverCoordinator."""

    @pytest.mark.asyncio
    async def test_coordinator_created_with_service(self, db_session: AsyncSession):
        """Deve criar coordinator com serviço de memória."""
        from unittest.mock import MagicMock, AsyncMock

        service = MemoryService()
        service.category_manager = CategoryManager()
        service.embedding_service = AsyncMock()

        coordinator = MemoryObserverCoordinator(memory_service=service)

        assert coordinator.memory_service is not None
        assert coordinator._post_tool_observer is not None
