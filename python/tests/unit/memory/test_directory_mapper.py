"""Unit tests for DirectoryMapper (Phase 1 - Memory Observer Enhanced)."""

from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy import create_engine, event, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import Session

from mindflow_backend.memory.classification.directory_mapper import DirectoryMapper
from mindflow_backend.memory.storage.models import (
    Base,
    MemoryCategory,
    MemorySubCategory,
    ProjectMemory,
)


@pytest.fixture
def mapper():
    """Create a DirectoryMapper instance with default patterns."""
    return DirectoryMapper()


@pytest.fixture
def in_memory_db():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")

    # Enable foreign keys for SQLite
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    return engine


@pytest_asyncio.fixture
async def async_db():
    """Create an async in-memory SQLite database for testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    return engine


@pytest_asyncio.fixture
async def async_session(async_db):
    """Create an async database session for testing."""
    async with AsyncSession(async_db) as session:
        yield session


# ============================================================================
# Pattern Matching Tests - API Category
# ============================================================================


def test_classify_api_direct(mapper: DirectoryMapper):
    """Test classification of files in api/ directory."""
    category, subcategory = mapper.classify("python/mindflow_backend/api/v1/chat.py")
    assert category == "api"
    assert subcategory == "v1"


def test_classify_api_routes(mapper: DirectoryMapper):
    """Test classification of files in routes/ directory (maps to api)."""
    category, subcategory = mapper.classify("src/routes/users/index.ts")
    assert category == "api"
    assert subcategory == "users"


def test_classify_api_endpoints(mapper: DirectoryMapper):
    """Test classification of files in endpoints/ directory (maps to api)."""
    category, subcategory = mapper.classify("app/endpoints/auth/login.py")
    assert category == "api"
    assert subcategory == "auth"


def test_classify_api_controllers(mapper: DirectoryMapper):
    """Test classification of files in controllers/ directory (maps to api)."""
    category, subcategory = mapper.classify("src/controllers/user_controller.rb")
    assert category == "api"
    assert subcategory is None  # No subcategory after controllers


# ============================================================================
# Pattern Matching Tests - Services Category
# ============================================================================


def test_classify_services_plural(mapper: DirectoryMapper):
    """Test classification of files in services/ directory."""
    category, subcategory = mapper.classify("python/mindflow_backend/services/auth/jwt.py")
    assert category == "services"
    assert subcategory == "auth"


def test_classify_service_singular(mapper: DirectoryMapper):
    """Test classification of files in service/ directory (singular)."""
    category, subcategory = mapper.classify("src/service/email/sender.ts")
    assert category == "services"
    assert subcategory == "email"


# ============================================================================
# Pattern Matching Tests - Models Category
# ============================================================================


def test_classify_models(mapper: DirectoryMapper):
    """Test classification of files in models/ directory."""
    category, subcategory = mapper.classify("python/mindflow_backend/models/user.py")
    assert category == "models"
    assert subcategory is None


def test_classify_schemas(mapper: DirectoryMapper):
    """Test classification of files in schemas/ directory (maps to models)."""
    category, subcategory = mapper.classify("src/schemas/user_schema.ts")
    assert category == "models"
    assert subcategory is None


def test_classify_entities(mapper: DirectoryMapper):
    """Test classification of files in entities/ directory (maps to models)."""
    category, subcategory = mapper.classify("app/entities/product.rb")
    assert category == "models"
    assert subcategory is None


# ============================================================================
# Pattern Matching Tests - Tests Category
# ============================================================================


def test_classify_tests_directory(mapper: DirectoryMapper):
    """Test classification of files in tests/ directory."""
    category, subcategory = mapper.classify("python/tests/unit/memory/test_models.py")
    assert category == "tests"
    assert subcategory == "unit"


def test_classify_test_prefix(mapper: DirectoryMapper):
    """Test classification of files with test_ prefix."""
    category, subcategory = mapper.classify("src/test_utils.py")
    assert category == "tests"
    assert subcategory is None


def test_classify_test_suffix(mapper: DirectoryMapper):
    """Test classification of files with _test suffix."""
    category, subcategory = mapper.classify("src/utils_test.go")
    assert category == "tests"
    assert subcategory is None


# ============================================================================
# Pattern Matching Tests - Config Category
# ============================================================================


def test_classify_config_directory(mapper: DirectoryMapper):
    """Test classification of files in config/ directory."""
    category, subcategory = mapper.classify("python/mindflow_backend/config/settings.py")
    assert category == "config"
    assert subcategory is None


def test_classify_env_file(mapper: DirectoryMapper):
    """Test classification of .env files."""
    category, subcategory = mapper.classify(".env.local")
    assert category == "config"
    assert subcategory is None


def test_classify_settings_file(mapper: DirectoryMapper):
    """Test classification of settings files."""
    category, subcategory = mapper.classify("src/settings.json")
    assert category == "config"
    assert subcategory is None


# ============================================================================
# Pattern Matching Tests - Frontend Category
# ============================================================================


def test_classify_components(mapper: DirectoryMapper):
    """Test classification of files in components/ directory."""
    category, subcategory = mapper.classify("frontend/src/components/Button/index.tsx")
    assert category == "frontend"
    assert subcategory == "Button"


def test_classify_pages(mapper: DirectoryMapper):
    """Test classification of files in pages/ directory."""
    category, subcategory = mapper.classify("src/pages/home/index.vue")
    assert category == "frontend"
    assert subcategory == "home"


def test_classify_views(mapper: DirectoryMapper):
    """Test classification of files in views/ directory."""
    category, subcategory = mapper.classify("app/views/users/show.html.erb")
    assert category == "frontend"
    assert subcategory == "users"


# ============================================================================
# Pattern Matching Tests - Infrastructure Category
# ============================================================================


def test_classify_infra(mapper: DirectoryMapper):
    """Test classification of files in infra/ directory."""
    category, subcategory = mapper.classify("python/mindflow_backend/infra/database/connection.py")
    assert category == "infrastructure"
    assert subcategory == "database"


def test_classify_docker(mapper: DirectoryMapper):
    """Test classification of Docker files."""
    category, subcategory = mapper.classify("docker-compose.yml")
    assert category == "infrastructure"
    assert subcategory is None


def test_classify_deploy(mapper: DirectoryMapper):
    """Test classification of files in deploy/ directory."""
    category, subcategory = mapper.classify("deploy/kubernetes/deployment.yaml")
    assert category == "infrastructure"
    assert subcategory == "kubernetes"


# ============================================================================
# Pattern Matching Tests - Memory Category
# ============================================================================


def test_classify_memory(mapper: DirectoryMapper):
    """Test classification of files in memory/ directory."""
    category, subcategory = mapper.classify("python/mindflow_backend/memory/facade.py")
    assert category == "memory"
    assert subcategory is None


def test_classify_memory_subdirectory(mapper: DirectoryMapper):
    """Test classification of files in memory subdirectories."""
    category, subcategory = mapper.classify("python/mindflow_backend/memory/storage/models.py")
    assert category == "memory"
    assert subcategory == "storage"


# ============================================================================
# Pattern Matching Tests - Docs Category
# ============================================================================


def test_classify_docs_directory(mapper: DirectoryMapper):
    """Test classification of files in docs/ directory."""
    category, subcategory = mapper.classify("docs/architecture/memory-system.md")
    assert category == "docs"
    assert subcategory == "architecture"


def test_classify_markdown_file(mapper: DirectoryMapper):
    """Test classification of .md files."""
    category, subcategory = mapper.classify("README.md")
    assert category == "docs"
    assert subcategory is None


# ============================================================================
# Fallback Tests - Other Category
# ============================================================================


def test_classify_unmatched_path(mapper: DirectoryMapper):
    """Test that unmatched paths fall back to 'other' category."""
    category, subcategory = mapper.classify("random/unknown/file.txt")
    assert category == "other"
    assert subcategory is None


def test_classify_root_file(mapper: DirectoryMapper):
    """Test classification of root-level files."""
    category, subcategory = mapper.classify("main.py")
    assert category == "other"
    assert subcategory is None


# ============================================================================
# Custom Patterns Tests
# ============================================================================


def test_custom_patterns():
    """Test DirectoryMapper with custom patterns."""
    custom_mapper = DirectoryMapper(
        custom_patterns={
            "custom_category": ["**/custom/**"],
            "api": ["**/api_v2/**"],  # Override default api pattern
        }
    )

    # Custom pattern should work
    category, subcategory = custom_mapper.classify("src/custom/module.py")
    assert category == "custom_category"

    # Overridden pattern should work
    category, subcategory = custom_mapper.classify("src/api_v2/users.py")
    assert category == "api"

    # Original api pattern should still work (merged, not replaced)
    category, subcategory = custom_mapper.classify("src/api/users.py")
    assert category == "api"


# ============================================================================
# Path Normalization Tests
# ============================================================================


def test_classify_windows_path(mapper: DirectoryMapper):
    """Test that Windows-style paths are normalized correctly."""
    category, subcategory = mapper.classify("python\\mindflow_backend\\api\\v1\\chat.py")
    assert category == "api"
    assert subcategory == "v1"


def test_classify_mixed_separators(mapper: DirectoryMapper):
    """Test paths with mixed separators."""
    category, subcategory = mapper.classify("python/mindflow_backend\\api/v1\\chat.py")
    assert category == "api"
    assert subcategory == "v1"


# ============================================================================
# Async Database Tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_or_create_category(async_session: AsyncSession):
    """Test get_or_create_ids creates category."""
    mapper = DirectoryMapper()

    # Create project first
    project = ProjectMemory(project_name="TestProject", root_path="/test")
    async_session.add(project)
    await async_session.flush()

    # Get or create category
    category_id, subcategory_id = await mapper.get_or_create_ids(
        async_session, project_id=project.id, file_path="python/api/v1/chat.py"
    )

    assert category_id is not None
    assert subcategory_id is not None

    # Verify category was created
    result = await async_session.execute(
        select(MemoryCategory).where(MemoryCategory.id == category_id)
    )
    category = result.scalar_one()
    assert category.name == "api"
    assert category.project_id == project.id


@pytest.mark.asyncio
async def test_get_or_create_reuses_existing(async_session: AsyncSession):
    """Test that get_or_create_ids reuses existing categories."""
    mapper = DirectoryMapper()

    # Create project
    project = ProjectMemory(project_name="TestProject", root_path="/test")
    async_session.add(project)
    await async_session.flush()

    # First call creates category
    category_id_1, _ = await mapper.get_or_create_ids(
        async_session, project_id=project.id, file_path="python/api/v1/chat.py"
    )

    # Second call should reuse existing category
    category_id_2, _ = await mapper.get_or_create_ids(
        async_session, project_id=project.id, file_path="python/api/v2/users.py"
    )

    assert category_id_1 == category_id_2

    # Verify only one category was created
    result = await async_session.execute(
        select(MemoryCategory).where(MemoryCategory.project_id == project.id)
    )
    categories = result.scalars().all()
    assert len(categories) == 1


@pytest.mark.asyncio
async def test_get_or_create_subcategory(async_session: AsyncSession):
    """Test that subcategories are created correctly."""
    mapper = DirectoryMapper()

    # Create project
    project = ProjectMemory(project_name="TestProject", root_path="/test")
    async_session.add(project)
    await async_session.flush()

    # Create category with subcategory
    category_id, subcategory_id = await mapper.get_or_create_ids(
        async_session, project_id=project.id, file_path="python/api/middleware/auth.py"
    )

    assert category_id is not None
    assert subcategory_id is not None

    # Verify subcategory was created
    result = await async_session.execute(
        select(MemorySubCategory).where(MemorySubCategory.id == subcategory_id)
    )
    subcategory = result.scalar_one()
    assert subcategory.name == "middleware"
    assert subcategory.category_id == category_id


@pytest.mark.asyncio
async def test_get_or_create_without_subcategory(async_session: AsyncSession):
    """Test classification without subcategory."""
    mapper = DirectoryMapper()

    # Create project
    project = ProjectMemory(project_name="TestProject", root_path="/test")
    async_session.add(project)
    await async_session.flush()

    # Classify file without subcategory
    category_id, subcategory_id = await mapper.get_or_create_ids(
        async_session, project_id=project.id, file_path="python/models/user.py"
    )

    assert category_id is not None
    assert subcategory_id is None
