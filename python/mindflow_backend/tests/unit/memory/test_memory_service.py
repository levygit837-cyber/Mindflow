"""Tests unitários para MemoryService do Intelligent Memory System.

Testa com banco de dados real (SQLite em memória):
- Salvamento de memórias
- Busca e recuperação
- Atualização e deleção
- Estatísticas
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from mindflow_backend.memory.memory_service import (
    MemoryService,
    SearchMode,
)
from mindflow_backend.memory.category_manager import (
    CategoryManager,
    MemoryScope,
)
from mindflow_backend.memory.storage.models import (
    MemoryEntry,
    MemoryCategory,
)


# ─────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────

@pytest_asyncio.fixture
async def initialized_memory_service(db_session: AsyncSession) -> MemoryService:
    """Fixture para MemoryService inicializado com banco real."""
    service = MemoryService()
    service.category_manager = CategoryManager()
    service.embedding_service = AsyncMock()
    service.embedding_service.generate_embedding.return_value = [0.1] * 1536
    service.embedding_service.generate_batch_embeddings.return_value = [[0.1] * 1536]

    # Patch para usar nossa session de teste
    with patch("mindflow_backend.memory.memory_service.get_db_session") as mock_get_db:
        mock_get_db.return_value.__aenter__ = AsyncMock(return_value=db_session)
        mock_get_db.return_value.__aexit__ = AsyncMock(return_value=False)
        await service.initialize()
        yield service


# ─────────────────────────────────────────────
# Save Memory Tests
# ─────────────────────────────────────────────

class TestSaveMemory:
    """Tests para salvamento de memórias."""

    @pytest.mark.asyncio
    async def test_save_memory_basic(
        self, initialized_memory_service: MemoryService, db_session: AsyncSession
    ):
        """Deve salvar uma memória básica."""
        with patch("mindflow_backend.memory.memory_service.get_db_session") as mock_get_db:
            mock_get_db.return_value.__aenter__ = AsyncMock(return_value=db_session)
            mock_get_db.return_value.__aexit__ = AsyncMock(return_value=False)

            memory = await initialized_memory_service.save_memory(
                content="Test memory content",
                memory_type="fact",
                scope=MemoryScope.GLOBAL,
                importance=0.7,
                generate_embedding=False,
            )

        assert memory is not None
        assert memory.content == "Test memory content"
        assert memory.memory_type == "fact"
        assert memory.scope == "global"

    @pytest.mark.asyncio
    async def test_save_memory_with_category(
        self, initialized_memory_service: MemoryService, db_session: AsyncSession
    ):
        """Deve salvar memória com categoria específica."""
        with patch("mindflow_backend.memory.memory_service.get_db_session") as mock_get_db:
            mock_get_db.return_value.__aenter__ = AsyncMock(return_value=db_session)
            mock_get_db.return_value.__aexit__ = AsyncMock(return_value=False)

            memory = await initialized_memory_service.save_memory(
                content="User prefers type hints",
                memory_type="preference",
                scope=MemoryScope.GLOBAL,
                category="user_preferences",
                importance=0.8,
                tags=["python", "typing"],
                generate_embedding=False,
            )

        assert memory is not None
        assert memory.importance == 0.8

    @pytest.mark.asyncio
    async def test_save_memory_project_scope_requires_project_id(
        self, initialized_memory_service: MemoryService
    ):
        """Deve falhar ao salvar memória de projeto sem project_id."""
        with pytest.raises(ValueError, match="project_id is required"):
            await initialized_memory_service.save_memory(
                content="Project specific",
                memory_type="fact",
                scope=MemoryScope.PROJECT,
                generate_embedding=False,
            )


# ─────────────────────────────────────────────
# Get Memory Tests
# ─────────────────────────────────────────────

class TestGetMemory:
    """Tests para recuperação de memórias."""

    @pytest.mark.asyncio
    async def test_get_memory_found(
        self, initialized_memory_service: MemoryService, db_session: AsyncSession
    ):
        """Deve recuperar memória existente."""
        with patch("mindflow_backend.memory.memory_service.get_db_session") as mock_get_db:
            mock_get_db.return_value.__aenter__ = AsyncMock(return_value=db_session)
            mock_get_db.return_value.__aexit__ = AsyncMock(return_value=False)

            # Criar memória
            memory = await initialized_memory_service.save_memory(
                content="Find me",
                memory_type="fact",
                scope=MemoryScope.GLOBAL,
                generate_embedding=False,
            )

            # Recuperar
            found = await initialized_memory_service.get_memory(memory.id)

        assert found is not None
        assert found.id == memory.id
        assert found.content == "Find me"

    @pytest.mark.asyncio
    async def test_get_memory_not_found(
        self, initialized_memory_service: MemoryService
    ):
        """Deve retornar None para memória inexistente."""
        found = await initialized_memory_service.get_memory(999999)
        assert found is None


# ─────────────────────────────────────────────
# Update Memory Tests
# ─────────────────────────────────────────────

class TestUpdateMemory:
    """Tests para atualização de memórias."""

    @pytest.mark.asyncio
    async def test_update_memory_success(
        self, initialized_memory_service: MemoryService, db_session: AsyncSession
    ):
        """Deve atualizar memória existente."""
        with patch("mindflow_backend.memory.memory_service.get_db_session") as mock_get_db:
            mock_get_db.return_value.__aenter__ = AsyncMock(return_value=db_session)
            mock_get_db.return_value.__aexit__ = AsyncMock(return_value=False)

            # Criar
            memory = await initialized_memory_service.save_memory(
                content="Original content",
                memory_type="fact",
                scope=MemoryScope.GLOBAL,
                importance=0.5,
                generate_embedding=False,
            )

            # Atualizar
            updated = await initialized_memory_service.update_memory(
                memory_id=memory.id,
                content="Updated content",
                importance=0.9,
            )

        assert updated is not None
        assert updated.content == "Updated content"
        assert updated.importance == 0.9

    @pytest.mark.asyncio
    async def test_update_memory_not_found(
        self, initialized_memory_service: MemoryService
    ):
        """Deve retornar None ao atualizar memória inexistente."""
        updated = await initialized_memory_service.update_memory(
            memory_id=999999,
            content="New content",
        )
        assert updated is None


# ─────────────────────────────────────────────
# Delete Memory Tests
# ─────────────────────────────────────────────

class TestDeleteMemory:
    """Tests para deleção de memórias."""

    @pytest.mark.asyncio
    async def test_delete_memory_success(
        self, initialized_memory_service: MemoryService, db_session: AsyncSession
    ):
        """Deve deletar memória existente."""
        with patch("mindflow_backend.memory.memory_service.get_db_session") as mock_get_db:
            mock_get_db.return_value.__aenter__ = AsyncMock(return_value=db_session)
            mock_get_db.return_value.__aexit__ = AsyncMock(return_value=False)

            # Criar
            memory = await initialized_memory_service.save_memory(
                content="Delete me",
                memory_type="fact",
                scope=MemoryScope.GLOBAL,
                generate_embedding=False,
            )

            # Deletar
            deleted = await initialized_memory_service.delete_memory(memory.id)

        assert deleted is True

        # Verificar que não existe mais
        found = await initialized_memory_service.get_memory(memory.id)
        assert found is None

    @pytest.mark.asyncio
    async def test_delete_memory_not_found(
        self, initialized_memory_service: MemoryService
    ):
        """Deve retornar False ao deletar memória inexistente."""
        deleted = await initialized_memory_service.delete_memory(999999)
        assert deleted is False


# ─────────────────────────────────────────────
# Stats Tests
# ─────────────────────────────────────────────

class TestMemoryStats:
    """Tests para estatísticas do sistema."""

    @pytest.mark.asyncio
    async def test_get_stats_returns_correct_structure(
        self, initialized_memory_service: MemoryService, db_session: AsyncSession
    ):
        """Deve retornar estatísticas corretas."""
        with patch("mindflow_backend.memory.memory_service.get_db_session") as mock_get_db:
            mock_get_db.return_value.__aenter__ = AsyncMock(return_value=db_session)
            mock_get_db.return_value.__aexit__ = AsyncMock(return_value=False)

            # Criar algumas memórias
            await initialized_memory_service.save_memory(
                content="Memory 1",
                memory_type="fact",
                scope=MemoryScope.GLOBAL,
                generate_embedding=False,
            )
            await initialized_memory_service.save_memory(
                content="Memory 2",
                memory_type="preference",
                scope=MemoryScope.GLOBAL,
                generate_embedding=False,
            )

            stats = await initialized_memory_service.get_stats()

        assert "total_memories" in stats
        assert stats["total_memories"] == 2
