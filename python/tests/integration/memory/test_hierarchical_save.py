"""Integration tests for hierarchical memory save functionality (Phase 3)."""

from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from mindflow_backend.memory.facade import MemoryFacade
from mindflow_backend.memory.storage.models import (
    HierarchicalAnnotation,
    MemoryCategory,
    MemorySubCategory,
    ProjectMemory,
)
from mindflow_backend.schemas.memory.annotation import MemoryAnnotation


@pytest_asyncio.fixture
async def async_db_session():
    """Create async database session for testing."""
    # Use in-memory SQLite with async support
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(ProjectMemory.metadata.create_all)

    # Create session factory
    async_session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    # Yield session
    async with async_session_factory() as session:
        yield session

    # Cleanup
    await engine.dispose()


@pytest_asyncio.fixture
def memory_facade():
    """Create MemoryFacade instance."""
    return MemoryFacade()


@pytest_asyncio.fixture
def sample_annotation():
    """Create sample MemoryAnnotation for testing."""
    return MemoryAnnotation(
        observer_agent_id="test-observer",
        source_agent_id="test-agent",
        mission_id="test-mission",
        session_id="test-session",
        content="Test annotation content",
        raw_event_type="tool_result",
        importance=0.8,
        annotation_type="code_change",
        tags=["test", "integration"],
    )


# ============================================================================
# Project Creation and Reuse Tests
# ============================================================================


@pytest.mark.asyncio
async def test_save_creates_new_project(
    async_db_session: AsyncSession,
    memory_facade: MemoryFacade,
    sample_annotation: MemoryAnnotation,
):
    """Test that save_hierarchical_annotation creates a new project when it doesn't exist."""
    annotation_id = await memory_facade.save_hierarchical_annotation(
        async_db_session,
        annotation=sample_annotation,
        project_name="TestProject",
        project_root="/home/user/TestProject",
    )

    assert annotation_id > 0

    # Verify project was created
    result = await async_db_session.execute(
        select(ProjectMemory).where(ProjectMemory.project_name == "TestProject")
    )
    project = result.scalar_one_or_none()

    assert project is not None
    assert project.project_name == "TestProject"
    assert project.root_path == "/home/user/TestProject"


@pytest.mark.asyncio
async def test_save_reuses_existing_project(
    async_db_session: AsyncSession,
    memory_facade: MemoryFacade,
    sample_annotation: MemoryAnnotation,
):
    """Test that save_hierarchical_annotation reuses existing project."""
    # First save - creates project
    await memory_facade.save_hierarchical_annotation(
        async_db_session,
        annotation=sample_annotation,
        project_name="TestProject",
        project_root="/home/user/TestProject",
    )

    # Get project count
    result1 = await async_db_session.execute(select(ProjectMemory))
    projects_before = len(result1.scalars().all())

    # Second save - should reuse project
    await memory_facade.save_hierarchical_annotation(
        async_db_session,
        annotation=sample_annotation,
        project_name="TestProject",
        project_root="/home/user/TestProject",
    )

    # Verify project count didn't increase
    result2 = await async_db_session.execute(select(ProjectMemory))
    projects_after = len(result2.scalars().all())

    assert projects_after == projects_before == 1


# ============================================================================
# Category Creation and Reuse Tests
# ============================================================================


@pytest.mark.asyncio
async def test_save_creates_category(
    async_db_session: AsyncSession,
    memory_facade: MemoryFacade,
    sample_annotation: MemoryAnnotation,
):
    """Test that save_hierarchical_annotation creates category when provided."""
    await memory_facade.save_hierarchical_annotation(
        async_db_session,
        annotation=sample_annotation,
        project_name="TestProject",
        project_root="/home/user/TestProject",
        category_name="API",
    )

    # Verify category was created
    result = await async_db_session.execute(
        select(MemoryCategory).where(MemoryCategory.name == "API")
    )
    category = result.scalar_one_or_none()

    assert category is not None
    assert category.name == "API"


@pytest.mark.asyncio
async def test_save_reuses_existing_category(
    async_db_session: AsyncSession,
    memory_facade: MemoryFacade,
    sample_annotation: MemoryAnnotation,
):
    """Test that save_hierarchical_annotation reuses existing category."""
    # First save - creates category
    await memory_facade.save_hierarchical_annotation(
        async_db_session,
        annotation=sample_annotation,
        project_name="TestProject",
        project_root="/home/user/TestProject",
        category_name="API",
    )

    # Get category count
    result1 = await async_db_session.execute(select(MemoryCategory))
    categories_before = len(result1.scalars().all())

    # Second save - should reuse category
    await memory_facade.save_hierarchical_annotation(
        async_db_session,
        annotation=sample_annotation,
        project_name="TestProject",
        project_root="/home/user/TestProject",
        category_name="API",
    )

    # Verify category count didn't increase
    result2 = await async_db_session.execute(select(MemoryCategory))
    categories_after = len(result2.scalars().all())

    assert categories_after == categories_before == 1


# ============================================================================
# SubCategory Creation Tests
# ============================================================================


@pytest.mark.asyncio
async def test_save_creates_subcategory(
    async_db_session: AsyncSession,
    memory_facade: MemoryFacade,
    sample_annotation: MemoryAnnotation,
):
    """Test that save_hierarchical_annotation creates subcategory when provided."""
    await memory_facade.save_hierarchical_annotation(
        async_db_session,
        annotation=sample_annotation,
        project_name="TestProject",
        project_root="/home/user/TestProject",
        category_name="API",
        subcategory_name="V1",
    )

    # Verify subcategory was created
    result = await async_db_session.execute(
        select(MemorySubCategory).where(MemorySubCategory.name == "V1")
    )
    subcategory = result.scalar_one_or_none()

    assert subcategory is not None
    assert subcategory.name == "V1"


# ============================================================================
# Full Hierarchy Tests
# ============================================================================


@pytest.mark.asyncio
async def test_save_creates_full_hierarchy(
    async_db_session: AsyncSession,
    memory_facade: MemoryFacade,
    sample_annotation: MemoryAnnotation,
):
    """Test that save_hierarchical_annotation creates complete hierarchy."""
    annotation_id = await memory_facade.save_hierarchical_annotation(
        async_db_session,
        annotation=sample_annotation,
        project_name="TestProject",
        project_root="/home/user/TestProject",
        category_name="API",
        subcategory_name="V1",
        file_path="api/v1/chat.py",
        lines_modified={"start": 10, "end": 20, "type": "added"},
        diff_summary="+def new_function():\n+    pass",
    )

    # Verify annotation was created with all relationships
    result = await async_db_session.execute(
        select(HierarchicalAnnotation).where(HierarchicalAnnotation.id == annotation_id)
    )
    annotation = result.scalar_one_or_none()

    assert annotation is not None
    assert annotation.project_id is not None
    assert annotation.category_id is not None
    assert annotation.subcategory_id is not None
    assert annotation.file_path == "api/v1/chat.py"
    assert annotation.lines_modified == {"start": 10, "end": 20, "type": "added"}
    assert annotation.diff_summary == "+def new_function():\n+    pass"
    assert annotation.content == "Test annotation content"


@pytest.mark.asyncio
async def test_save_multiple_annotations_same_hierarchy(
    async_db_session: AsyncSession,
    memory_facade: MemoryFacade,
    sample_annotation: MemoryAnnotation,
):
    """Test that multiple annotations can be saved to the same hierarchy."""
    # Save first annotation
    id1 = await memory_facade.save_hierarchical_annotation(
        async_db_session,
        annotation=sample_annotation,
        project_name="TestProject",
        project_root="/home/user/TestProject",
        category_name="API",
        subcategory_name="V1",
    )

    # Save second annotation (same hierarchy)
    annotation2 = MemoryAnnotation(
        observer_agent_id="test-observer",
        source_agent_id="test-agent-2",
        mission_id="test-mission-2",
        session_id="test-session",
        content="Second annotation content",
        raw_event_type="tool_result",
        importance=0.9,
        annotation_type="code_change",
        tags=["test", "second"],
    )

    id2 = await memory_facade.save_hierarchical_annotation(
        async_db_session,
        annotation=annotation2,
        project_name="TestProject",
        project_root="/home/user/TestProject",
        category_name="API",
        subcategory_name="V1",
    )

    # Verify both annotations exist
    assert id1 != id2

    result = await async_db_session.execute(select(HierarchicalAnnotation))
    annotations = result.scalars().all()

    assert len(annotations) == 2

    # Verify they share the same project/category/subcategory
    assert annotations[0].project_id == annotations[1].project_id
    assert annotations[0].category_id == annotations[1].category_id
    assert annotations[0].subcategory_id == annotations[1].subcategory_id


# ============================================================================
# Edge Cases
# ============================================================================


@pytest.mark.asyncio
async def test_save_without_category(
    async_db_session: AsyncSession,
    memory_facade: MemoryFacade,
    sample_annotation: MemoryAnnotation,
):
    """Test that save works without category/subcategory."""
    annotation_id = await memory_facade.save_hierarchical_annotation(
        async_db_session,
        annotation=sample_annotation,
        project_name="TestProject",
        project_root="/home/user/TestProject",
    )

    # Verify annotation was created without category
    result = await async_db_session.execute(
        select(HierarchicalAnnotation).where(HierarchicalAnnotation.id == annotation_id)
    )
    annotation = result.scalar_one_or_none()

    assert annotation is not None
    assert annotation.project_id is not None
    assert annotation.category_id is None
    assert annotation.subcategory_id is None


@pytest.mark.asyncio
async def test_save_with_category_without_subcategory(
    async_db_session: AsyncSession,
    memory_facade: MemoryFacade,
    sample_annotation: MemoryAnnotation,
):
    """Test that save works with category but without subcategory."""
    annotation_id = await memory_facade.save_hierarchical_annotation(
        async_db_session,
        annotation=sample_annotation,
        project_name="TestProject",
        project_root="/home/user/TestProject",
        category_name="API",
    )

    # Verify annotation was created with category but no subcategory
    result = await async_db_session.execute(
        select(HierarchicalAnnotation).where(HierarchicalAnnotation.id == annotation_id)
    )
    annotation = result.scalar_one_or_none()

    assert annotation is not None
    assert annotation.project_id is not None
    assert annotation.category_id is not None
    assert annotation.subcategory_id is None
