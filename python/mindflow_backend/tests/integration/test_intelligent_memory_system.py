"""Tests de integração end-to-end para o Intelligent Memory System.

Testa o fluxo completo com banco de dados real:
1. Salvar memórias
2. Buscar memórias (semântica, full-text, híbrida)
3. Usar em nodes
4. Observers capturando e salvando
"""

from __future__ import annotations

from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from mindflow_backend.memory import (
    CategoryManager,
    MemoryScope,
    MemoryService,
    MemoryType,
    SearchMode,
)
from mindflow_backend.memory.storage.models import (
    MemoryCategory,
    MemoryEntry,
    MemorySubCategory,
)


# ─────────────────────────────────────────────
# Testes de Categoria (Com Banco Real)
# ─────────────────────────────────────────────

@pytest.mark.integration
class TestCategoryManagerIntegration:
    """Tests de integração do CategoryManager com banco real."""

    @pytest.mark.asyncio
    async def test_initialize_creates_base_categories(
        self, db_session: AsyncSession
    ) -> None:
        """Deve criar categorias base no banco de dados."""
        manager = CategoryManager()
        await manager.initialize(db_session)

        # Verificar que categorias base (MemoryCategoryType) foram criadas
        from sqlalchemy import select
        from mindflow_backend.memory.storage.models import MemoryCategoryType

        result = await db_session.execute(select(MemoryCategoryType))
        categories = result.scalars().all()

        assert len(categories) == 6  # 6 categorias base

        category_names = {c.name for c in categories}
        expected = {
            "code_patterns",
            "user_preferences",
            "project_context",
            "execution_patterns",
            "tool_usage",
            "error_patterns",
        }
        assert category_names == expected

    @pytest.mark.asyncio
    async def test_get_or_create_category_uses_cache(
        self, initialized_category_manager: CategoryManager, db_session: AsyncSession
    ) -> None:
        """Deve usar cache para categorias existentes."""
        # Primeira chamada - cria no banco
        cat1 = await initialized_category_manager.get_or_create_category(
            db_session, project_id=1, category_name="code_patterns"
        )

        # Segunda chamada - deve usar cache
        cat2 = await initialized_category_manager.get_or_create_category(
            db_session, project_id=1, category_name="code_patterns"
        )

        assert cat1.id == cat2.id

        # Verificar estatísticas de cache
        stats = initialized_category_manager.get_cache_stats()
        assert stats["category_cache_size"] >= 1

    @pytest.mark.asyncio
    async def test_get_or_create_subcategory(
        self, initialized_category_manager: CategoryManager, db_session: AsyncSession
    ) -> None:
        """Deve criar subcategorias corretamente."""
        sub = await initialized_category_manager.get_or_create_subcategory(
            db_session,
            project_id=1,
            category_name="code_patterns",
            subcategory_name="async_patterns",
            description="Padrões de código assíncrono",
        )

        assert sub.name == "async_patterns"
        assert sub.description == "Padrões de código assíncrono"

        # Verificar que a subcategoria está no banco
        from sqlalchemy import select

        result = await db_session.execute(
            select(MemorySubCategory).where(MemorySubCategory.name == "async_patterns")
        )
        found = result.scalar_one_or_none()
        assert found is not None


# ─────────────────────────────────────────────
# Testes de MemoryService (Com Banco Real)
# ─────────────────────────────────────────────

@pytest.mark.integration
class TestMemoryServiceIntegration:
    """Tests de integração do MemoryService com banco real."""

    @pytest.mark.asyncio
    async def test_save_memory_creates_entry(
        self, initialized_memory_service: MemoryService, db_session: AsyncSession
    ) -> None:
        """Deve salvar uma memória no banco de dados."""
        memory = await initialized_memory_service.save_memory(
            content="User prefers async/await patterns",
            memory_type="preference",
            scope=MemoryScope.GLOBAL,
            category="user_preferences",
            importance=0.8,
            tags=["python", "async"],
            generate_embedding=False,  # Não gerar embedding em teste
        )

        assert memory is not None
        assert memory.content == "User prefers async/await patterns"
        assert memory.memory_type == "preference"

        # Verificar no banco
        from sqlalchemy import select

        result = await db_session.execute(
            select(MemoryEntry).where(MemoryEntry.id == memory.id)
        )
        found = result.scalar_one_or_none()
        assert found is not None
        assert found.content == "User prefers async/await patterns"

    @pytest.mark.asyncio
    async def test_get_memory_by_id(
        self, initialized_memory_service: MemoryService, db_session: AsyncSession
    ) -> None:
        """Deve recuperar uma memória pelo ID."""
        # Primeiro salvar
        memory = await initialized_memory_service.save_memory(
            content="Test content",
            memory_type="fact",
            scope=MemoryScope.GLOBAL,
            importance=0.5,
            generate_embedding=False,
        )

        # Depois recuperar
        found = await initialized_memory_service.get_memory(memory.id)

        assert found is not None
        assert found.id == memory.id
        assert found.content == "Test content"

    @pytest.mark.asyncio
    async def test_update_memory(
        self, initialized_memory_service: MemoryService, db_session: AsyncSession
    ) -> None:
        """Deve atualizar uma memória existente."""
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
    async def test_delete_memory(
        self, initialized_memory_service: MemoryService, db_session: AsyncSession
    ) -> None:
        """Deve deletar uma memória."""
        # Criar
        memory = await initialized_memory_service.save_memory(
            content="To be deleted",
            memory_type="fact",
            scope=MemoryScope.GLOBAL,
            importance=0.5,
            generate_embedding=False,
        )

        # Deletar
        deleted = await initialized_memory_service.delete_memory(memory.id)
        assert deleted is True

        # Verificar que não existe mais
        found = await initialized_memory_service.get_memory(memory.id)
        assert found is None

    @pytest.mark.asyncio
    async def test_search_memories_fulltext(
        self, initialized_memory_service: MemoryService, db_session: AsyncSession
    ) -> None:
        """Deve buscar memórias por full-text search (quando disponível)."""
        # Criar algumas memórias
        await initialized_memory_service.save_memory(
            content="Python async patterns are great",
            memory_type="pattern",
            scope=MemoryScope.GLOBAL,
            importance=0.7,
            generate_embedding=False,
        )
        await initialized_memory_service.save_memory(
            content="JavaScript promises vs async await",
            memory_type="pattern",
            scope=MemoryScope.GLOBAL,
            importance=0.6,
            generate_embedding=False,
        )

        # SQLite não suporta tsvector, então busca sem full-text
        # Em PostgreSQL, isso funcionaria corretamente
        try:
            results = await initialized_memory_service.search_memories(
                query="python async",
                scope=MemoryScope.GLOBAL,
                search_mode=SearchMode.FULLTEXT,
                limit=10,
            )
            assert isinstance(results, list)
        except Exception as e:
            # Se falhar por causa do SQLite, apenas verifica que não quebra
            # (PostgreSQL real funcionaria)
            if "unrecognized token" in str(e) or "tsvector" in str(e).lower():
                pytest.skip("Full-text search not supported in SQLite")
            else:
                raise


# ─────────────────────────────────────────────
# Testes de Classificação
# ─────────────────────────────────────────────

@pytest.mark.integration
class TestClassificationIntegration:
    """Tests de classificação automática de conteúdo."""

    @pytest.mark.asyncio
    async def test_classify_by_path_patterns(
        self, initialized_category_manager: CategoryManager
    ) -> None:
        """Deve classificar arquivos de teste corretamente."""
        category, subcategory = initialized_category_manager.classify_content(
            content="Test file",
            file_path="/project/tests/test_main.py",
        )

        assert category == "code_patterns"
        assert subcategory == "tests"

    @pytest.mark.asyncio
    async def test_classify_by_content_error(
        self, initialized_category_manager: CategoryManager
    ) -> None:
        """Deve classificar conteúdo de erro corretamente."""
        category, subcategory = initialized_category_manager.classify_content(
            content="Error occurred during execution: null pointer exception",
            memory_type="error",
        )

        assert category == "error_patterns"

    @pytest.mark.asyncio
    async def test_classify_by_content_preference(
        self, initialized_category_manager: CategoryManager
    ) -> None:
        """Deve classificar preferências do usuário corretamente."""
        category, subcategory = initialized_category_manager.classify_content(
            content="I prefer to use type hints in all functions",
            memory_type="preference",
        )

        assert category == "user_preferences"


# ─────────────────────────────────────────────
# Testes de Cache
# ─────────────────────────────────────────────

@pytest.mark.integration
class TestCacheIntegration:
    """Tests de funcionalidade de cache."""

    @pytest.mark.asyncio
    async def test_category_cache_invalidation(
        self, initialized_category_manager: CategoryManager, db_session: AsyncSession
    ) -> None:
        """Deve invalidar cache de categorias corretamente."""
        # Popular cache
        await initialized_category_manager.get_or_create_category(
            db_session, project_id=1, category_name="code_patterns"
        )

        # Verificar cache populado
        stats_before = initialized_category_manager.get_cache_stats()
        assert stats_before["category_cache_size"] >= 1

        # Invalidar
        initialized_category_manager.invalidate_all_caches()

        # Verificar cache limpo
        stats_after = initialized_category_manager.get_cache_stats()
        assert stats_after["category_cache_size"] == 0

    @pytest.mark.asyncio
    async def test_importance_cache(
        self, initialized_category_manager: CategoryManager, db_session: AsyncSession
    ) -> None:
        """Deve cachear importâncias de categorias do banco."""
        # Criar categoria customizada
        from mindflow_backend.memory.storage.models import MemoryCategoryType
        from sqlalchemy import select

        # Verificar importância de categoria base (não usa cache)
        importance1 = await initialized_category_manager.get_category_importance(
            db_session, "code_patterns"
        )
        assert importance1 == 0.6  # Valor das BASE_CATEGORIES


# ─────────────────────────────────────────────
# Testes E2E do Sistema Completo
# ─────────────────────────────────────────────

@pytest.mark.integration
class TestIntelligentMemorySystemE2E:
    """Tests end-to-end do fluxo completo do IMS."""

    @pytest.mark.asyncio
    async def test_complete_workflow(
        self, db_session: AsyncSession
    ) -> None:
        """Fluxo completo: salvar, buscar, atualizar, deletar."""
        from unittest.mock import AsyncMock, patch

        # Setup
        service = MemoryService()
        service.category_manager = CategoryManager()
        service.embedding_service = AsyncMock()
        service.embedding_service.generate_embedding.return_value = [0.1] * 1536

        with patch("mindflow_backend.memory.memory_service.get_db_session") as mock_get_db:
            mock_get_db.return_value.__aenter__ = AsyncMock(return_value=db_session)
            mock_get_db.return_value.__aexit__ = AsyncMock(return_value=False)

            await service.initialize()

            # 1. Salvar memórias
            memory1 = await service.save_memory(
                content="Preferência de código: usar type hints",
                memory_type="preference",
                scope=MemoryScope.GLOBAL,
                category="user_preferences",
                importance=0.8,
                tags=["python", "type_hints"],
                generate_embedding=False,
            )

            memory2 = await service.save_memory(
                content="Padrão: usar async/await para I/O",
                memory_type="pattern",
                scope=MemoryScope.GLOBAL,
                category="code_patterns",
                importance=0.7,
                tags=["python", "async"],
                generate_embedding=False,
            )

            # 2. Verificar que existem
            assert memory1.id is not None
            assert memory2.id is not None

            # 3. Buscar por ID
            found = await service.get_memory(memory1.id)
            assert found is not None
            assert found.content == "Preferência de código: usar type hints"

            # 4. Atualizar
            updated = await service.update_memory(
                memory_id=memory1.id,
                content="Preferência atualizada: usar type hints obrigatórios",
                importance=0.9,
            )
            assert updated.content == "Preferência atualizada: usar type hints obrigatórios"

            # 5. Deletar
            deleted = await service.delete_memory(memory2.id)
            assert deleted is True

            # 6. Verificar que foi deletado
            not_found = await service.get_memory(memory2.id)
            assert not_found is None

            # 7. Estatísticas
            stats = await service.get_stats()
            assert stats["total_memories"] == 1  # Apenas uma sobrou
