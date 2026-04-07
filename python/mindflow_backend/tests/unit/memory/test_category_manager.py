"""Tests unitários para CategoryManager do Intelligent Memory System.

Testa com banco de dados real (SQLite em memória):
- Inicialização de categorias base
- Criação e recuperação de categorias/subcategorias
- Classificação automática de conteúdo
- Caching de categorias
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mindflow_backend.memory.category_manager import (
    CategoryManager,
    MemoryScope,
    MemoryType,
)
from mindflow_backend.memory.storage.models import (
    MemoryCategory,
    MemoryCategoryType,
    MemorySubCategory,
)


# ─────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────

@pytest_asyncio.fixture
async def initialized_manager(db_session: AsyncSession) -> CategoryManager:
    """Fixture para CategoryManager inicializado com banco real."""
    manager = CategoryManager()
    await manager.initialize(db_session)
    return manager


# ─────────────────────────────────────────────
# Inicialização Tests
# ─────────────────────────────────────────────

class TestCategoryManagerInitialization:
    """Tests para inicialização do CategoryManager."""

    @pytest.mark.asyncio
    async def test_initialize_creates_base_categories(self, db_session: AsyncSession):
        """Deve criar categorias base (MemoryCategoryType) no banco."""
        manager = CategoryManager()
        await manager.initialize(db_session)

        # Verificar que MemoryCategoryType foram criadas
        result = await db_session.execute(select(MemoryCategoryType))
        categories = result.scalars().all()

        assert len(categories) == 6

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
        assert manager._initialized is True

    @pytest.mark.asyncio
    async def test_initialize_idempotent(self, db_session: AsyncSession):
        """Inicialização deve ser idempotente."""
        manager = CategoryManager()

        # Primeira inicialização
        await manager.initialize(db_session)
        result = await db_session.execute(select(MemoryCategoryType))
        count_after_first = len(result.scalars().all())

        # Segunda inicialização (não deve criar duplicatas)
        await manager.initialize(db_session)
        result = await db_session.execute(select(MemoryCategoryType))
        count_after_second = len(result.scalars().all())

        assert count_after_first == count_after_second == 6


# ─────────────────────────────────────────────
# Category Management Tests
# ─────────────────────────────────────────────

class TestCategoryManagement:
    """Tests para gerenciamento de categorias."""

    @pytest.mark.asyncio
    async def test_get_or_create_category_new(self, initialized_manager: CategoryManager, db_session: AsyncSession):
        """Deve criar nova categoria se não existir."""
        category = await initialized_manager.get_or_create_category(
            db_session, project_id=1, category_name="code_patterns"
        )

        assert category is not None
        assert category.name == "code_patterns"
        assert category.project_id == 1

        # Verificar no banco
        result = await db_session.execute(
            select(MemoryCategory).where(MemoryCategory.id == category.id)
        )
        found = result.scalar_one_or_none()
        assert found is not None
        assert found.name == "code_patterns"

    @pytest.mark.asyncio
    async def test_get_or_create_category_existing(self, initialized_manager: CategoryManager, db_session: AsyncSession):
        """Deve retornar categoria existente."""
        # Primeira chamada - cria
        cat1 = await initialized_manager.get_or_create_category(
            db_session, project_id=1, category_name="code_patterns"
        )

        # Segunda chamada - recupera existente
        cat2 = await initialized_manager.get_or_create_category(
            db_session, project_id=1, category_name="code_patterns"
        )

        assert cat1.id == cat2.id

    @pytest.mark.asyncio
    async def test_get_or_create_subcategory(self, initialized_manager: CategoryManager, db_session: AsyncSession):
        """Deve criar subcategoria corretamente."""
        sub = await initialized_manager.get_or_create_subcategory(
            db_session,
            project_id=1,
            category_name="code_patterns",
            subcategory_name="async_patterns",
            description="Padrões assíncronos",
        )

        assert sub.name == "async_patterns"
        assert sub.description == "Padrões assíncronos"

        # Verificar no banco
        result = await db_session.execute(
            select(MemorySubCategory).where(MemorySubCategory.name == "async_patterns")
        )
        found = result.scalar_one_or_none()
        assert found is not None


# ─────────────────────────────────────────────
# Content Classification Tests
# ─────────────────────────────────────────────

class TestContentClassification:
    """Tests para classificação automática de conteúdo."""

    @pytest.mark.asyncio
    async def test_classify_by_path_tests(self, initialized_manager: CategoryManager):
        """Deve classificar arquivos de teste."""
        category, subcategory = initialized_manager.classify_content(
            content="Test file",
            file_path="/project/tests/test_main.py",
        )

        assert category == "code_patterns"
        assert subcategory == "tests"

    @pytest.mark.asyncio
    async def test_classify_by_path_api(self, initialized_manager: CategoryManager):
        """Deve classificar arquivos de API."""
        category, subcategory = initialized_manager.classify_content(
            content="API routes",
            file_path="/project/src/routes/users.py",
        )

        assert category == "code_patterns"
        assert subcategory == "api"

    @pytest.mark.asyncio
    async def test_classify_by_content_error(self, initialized_manager: CategoryManager):
        """Deve classificar conteúdo de erro."""
        category, subcategory = initialized_manager.classify_content(
            content="Error occurred during execution",
            memory_type="error",
        )

        assert category == "error_patterns"

    @pytest.mark.asyncio
    async def test_classify_by_content_preference(self, initialized_manager: CategoryManager):
        """Deve classificar preferências."""
        category, subcategory = initialized_manager.classify_content(
            content="I prefer to use type hints",
            memory_type="preference",
        )

        assert category == "user_preferences"

    @pytest.mark.asyncio
    async def test_classify_default(self, initialized_manager: CategoryManager):
        """Deve retornar categoria padrão para conteúdo desconhecido."""
        category, subcategory = initialized_manager.classify_content(
            content="Some generic content",
        )

        assert category == "project_context"
        assert subcategory is None


# ─────────────────────────────────────────────
# Category Importance Tests
# ─────────────────────────────────────────────

class TestCategoryImportance:
    """Tests para importância de categorias."""

    @pytest.mark.asyncio
    async def test_get_category_importance_from_base(self, initialized_manager: CategoryManager, db_session: AsyncSession):
        """Deve retornar importância das categorias base."""
        importance = await initialized_manager.get_category_importance(
            db_session, "code_patterns"
        )

        assert importance == 0.6  # Valor das BASE_CATEGORIES

    @pytest.mark.asyncio
    async def test_get_category_importance_default(self, initialized_manager: CategoryManager, db_session: AsyncSession):
        """Deve retornar importância padrão para categoria desconhecida."""
        importance = await initialized_manager.get_category_importance(
            db_session, "unknown_category"
        )

        assert importance == 0.5  # Valor padrão


# ─────────────────────────────────────────────
# Cache Tests
# ─────────────────────────────────────────────

class TestCategoryCache:
    """Tests para funcionalidade de cache."""

    @pytest.mark.asyncio
    async def test_category_cache_populated(self, initialized_manager: CategoryManager, db_session: AsyncSession):
        """Cache deve ser populado após busca."""
        # Primeira chamada
        await initialized_manager.get_or_create_category(
            db_session, project_id=1, category_name="code_patterns"
        )

        stats = initialized_manager.get_cache_stats()
        assert stats["category_cache_size"] >= 1

    @pytest.mark.asyncio
    async def test_cache_invalidation(self, initialized_manager: CategoryManager, db_session: AsyncSession):
        """Deve invalidar cache corretamente."""
        # Popular cache
        await initialized_manager.get_or_create_category(
            db_session, project_id=1, category_name="code_patterns"
        )

        stats_before = initialized_manager.get_cache_stats()
        assert stats_before["category_cache_size"] >= 1

        # Invalidar
        initialized_manager.invalidate_all_caches()

        stats_after = initialized_manager.get_cache_stats()
        assert stats_after["category_cache_size"] == 0


# ─────────────────────────────────────────────
# Category Listing Tests
# ─────────────────────────────────────────────

class TestCategoryListing:
    """Tests para listagem de categorias."""

    @pytest.mark.asyncio
    async def test_list_categories_by_project(self, initialized_manager: CategoryManager, db_session: AsyncSession):
        """Deve listar categorias por projeto."""
        # Criar categorias para projeto
        await initialized_manager.get_or_create_category(
            db_session, project_id=1, category_name="code_patterns"
        )
        await initialized_manager.get_or_create_category(
            db_session, project_id=1, category_name="user_preferences"
        )

        categories = await initialized_manager.list_categories(db_session, project_id=1)

        assert len(categories) == 2
        category_names = {c.name for c in categories}
        assert "code_patterns" in category_names
        assert "user_preferences" in category_names

    @pytest.mark.asyncio
    async def test_list_all_categories(self, initialized_manager: CategoryManager, db_session: AsyncSession):
        """Deve listar todas as categorias."""
        # Criar categorias para diferentes projetos
        await initialized_manager.get_or_create_category(
            db_session, project_id=1, category_name="code_patterns"
        )
        await initialized_manager.get_or_create_category(
            db_session, project_id=2, category_name="user_preferences"
        )

        all_categories = await initialized_manager.list_categories(db_session)

        assert len(all_categories) == 2

    @pytest.mark.asyncio
    async def test_list_subcategories(self, initialized_manager: CategoryManager, db_session: AsyncSession):
        """Deve listar subcategorias."""
        # Criar categoria e subcategorias
        cat = await initialized_manager.get_or_create_category(
            db_session, project_id=1, category_name="code_patterns"
        )
        await initialized_manager.get_or_create_subcategory(
            db_session, project_id=1, category_name="code_patterns",
            subcategory_name="async_patterns"
        )
        await initialized_manager.get_or_create_subcategory(
            db_session, project_id=1, category_name="code_patterns",
            subcategory_name="api_design"
        )

        # Listar usando category_id
        subcategories = await initialized_manager.list_subcategories(
            db_session, category_id=cat.id
        )

        assert len(subcategories) == 2
        sub_names = {s.name for s in subcategories}
        assert "async_patterns" in sub_names
        assert "api_design" in sub_names
