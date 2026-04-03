"""Unit tests for MemoryFacade.save_hierarchical_annotation() (Phase 1)."""

from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from mindflow_backend.memory.facade import MemoryFacade
from mindflow_backend.memory.storage.models import (
    Base,
    HierarchicalAnnotation,
    MemoryCategory,
    MemorySubCategory,
    ProjectMemory,
)
from mindflow_backend.schemas.memory.annotation import MemoryAnnotation


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


@pytest_asyncio.fixture
async def memory_facade():
    """Create a MemoryFacade instance."""
    return MemoryFacade()


# ============================================================================
# Basic Save Tests
# ============================================================================


@pytest.mark.asyncio
async def test_save_hierarchical_annotation_creates_project(
    async_session: AsyncSession,
    memory_facade: MemoryFacade,
):
    """Test that save_hierarchical_annotation creates ProjectMemory if not exists."""
    annotation = MemoryAnnotation(
        observer_agent_id="observer-1",
        source_agent_id="coder",
        mission_id="mission-123",
        session_id="session-456",
        content="Test annotation content",
        annotation_type="code_change",
        importance=0.8,
    )

    annotation_id = await memory_facade.save_hierarchical_annotation(
        async_session,
        annotation=annotation,
        project_name="TestProject",
        project_root="/test/path",
    )

    assert annotation_id is not None

    # Verify ProjectMemory was created
    result = await async_session.execute(select(ProjectMemory))
    projects = result.scalars().all()
    assert len(projects) == 1
    assert projects[0].project_name == "TestProject"
    assert projects[0].root_path == "/test/path"


@pytest.mark.asyncio
async def test_save_hierarchical_annotation_reuses_existing_project(
    async_session: AsyncSession,
    memory_facade: MemoryFacade,
):
    """Test that save_hierarchical_annotation reuses existing ProjectMemory."""
    # Create project first
    project = ProjectMemory(project_name="TestProject", root_path="/test/path")
    async_session.add(project)
    await async_session.commit()

    annotation = MemoryAnnotation(
        observer_agent_id="observer-1",
        source_agent_id="coder",
        mission_id="mission-123",
        session_id="session-456",
        content="Test annotation",
        annotation_type="observation",
        importance=0.5,
    )

    await memory_facade.save_hierarchical_annotation(
        async_session,
        annotation=annotation,
        project_name="TestProject",
        project_root="/test/path",
    )

    # Verify only one project exists
    result = await async_session.execute(select(ProjectMemory))
    projects = result.scalars().all()
    assert len(projects) == 1


@pytest.mark.asyncio
async def test_save_hierarchical_annotation_with_category(
    async_session: AsyncSession,
    memory_facade: MemoryFacade,
):
    """Test saving annotation with category."""
    annotation = MemoryAnnotation(
        observer_agent_id="observer-1",
        source_agent_id="coder",
        mission_id="mission-123",
        session_id="session-456",
        content="Modified API endpoint",
        annotation_type="code_change",
        importance=0.8,
    )

    annotation_id = await memory_facade.save_hierarchical_annotation(
        async_session,
        annotation=annotation,
        project_name="TestProject",
        project_root="/test/path",
        category_name="api",
        file_path="python/api/v1/chat.py",
    )

    # Verify category was created
    result = await async_session.execute(select(MemoryCategory))
    categories = result.scalars().all()
    assert len(categories) == 1
    assert categories[0].name == "api"

    # Verify annotation has category_id
    ann_result = await async_session.execute(
        select(HierarchicalAnnotation).where(HierarchicalAnnotation.id == annotation_id)
    )
    saved_annotation = ann_result.scalar_one()
    assert saved_annotation.category_id == categories[0].id
    assert saved_annotation.file_path == "python/api/v1/chat.py"


@pytest.mark.asyncio
async def test_save_hierarchical_annotation_with_subcategory(
    async_session: AsyncSession,
    memory_facade: MemoryFacade,
):
    """Test saving annotation with category and subcategory."""
    annotation = MemoryAnnotation(
        observer_agent_id="observer-1",
        source_agent_id="coder",
        mission_id="mission-123",
        session_id="session-456",
        content="Modified middleware",
        annotation_type="code_change",
        importance=0.8,
    )

    annotation_id = await memory_facade.save_hierarchical_annotation(
        async_session,
        annotation=annotation,
        project_name="TestProject",
        project_root="/test/path",
        category_name="api",
        subcategory_name="middleware",
        file_path="python/api/middleware/auth.py",
        lines_modified={"start": 45, "end": 67, "count": 22},
        diff_summary="Added JWT validation",
    )

    # Verify subcategory was created
    result = await async_session.execute(select(MemorySubCategory))
    subcategories = result.scalars().all()
    assert len(subcategories) == 1
    assert subcategories[0].name == "middleware"

    # Verify annotation has all fields
    ann_result = await async_session.execute(
        select(HierarchicalAnnotation).where(HierarchicalAnnotation.id == annotation_id)
    )
    saved_annotation = ann_result.scalar_one()
    assert saved_annotation.subcategory_id == subcategories[0].id
    assert saved_annotation.file_path == "python/api/middleware/auth.py"
    assert saved_annotation.lines_modified == {"start": 45, "end": 67, "count": 22}
    assert saved_annotation.diff_summary == "Added JWT validation"


@pytest.mark.asyncio
async def test_save_hierarchical_annotation_without_category(
    async_session: AsyncSession,
    memory_facade: MemoryFacade,
):
    """Test saving annotation without category (category_id should be None)."""
    annotation = MemoryAnnotation(
        observer_agent_id="observer-1",
        source_agent_id="analyst",
        mission_id="mission-123",
        session_id="session-456",
        content="General observation",
        annotation_type="observation",
        importance=0.5,
    )

    annotation_id = await memory_facade.save_hierarchical_annotation(
        async_session,
        annotation=annotation,
        project_name="TestProject",
        project_root="/test/path",
    )

    # Verify annotation has no category
    ann_result = await async_session.execute(
        select(HierarchicalAnnotation).where(HierarchicalAnnotation.id == annotation_id)
    )
    saved_annotation = ann_result.scalar_one()
    assert saved_annotation.category_id is None
    assert saved_annotation.subcategory_id is None


# ============================================================================
# Reuse Existing Categories Tests
# ============================================================================


@pytest.mark.asyncio
async def test_save_hierarchical_annotation_reuses_category(
    async_session: AsyncSession,
    memory_facade: MemoryFacade,
):
    """Test that existing categories are reused."""
    # Create project and category first
    project = ProjectMemory(project_name="TestProject", root_path="/test/path")
    async_session.add(project)
    await async_session.flush()

    category = MemoryCategory(project_id=project.id, name="api")
    async_session.add(category)
    await async_session.commit()

    annotation = MemoryAnnotation(
        observer_agent_id="observer-1",
        source_agent_id="coder",
        mission_id="mission-123",
        session_id="session-456",
        content="Test",
        annotation_type="code_change",
        importance=0.8,
    )

    await memory_facade.save_hierarchical_annotation(
        async_session,
        annotation=annotation,
        project_name="TestProject",
        project_root="/test/path",
        category_name="api",
    )

    # Verify only one category exists
    result = await async_session.execute(select(MemoryCategory))
    categories = result.scalars().all()
    assert len(categories) == 1


@pytest.mark.asyncio
async def test_save_hierarchical_annotation_reuses_subcategory(
    async_session: AsyncSession,
    memory_facade: MemoryFacade,
):
    """Test that existing subcategories are reused."""
    # Create project, category, and subcategory first
    project = ProjectMemory(project_name="TestProject", root_path="/test/path")
    async_session.add(project)
    await async_session.flush()

    category = MemoryCategory(project_id=project.id, name="api")
    async_session.add(category)
    await async_session.flush()

    subcategory = MemorySubCategory(category_id=category.id, name="middleware")
    async_session.add(subcategory)
    await async_session.commit()

    annotation = MemoryAnnotation(
        observer_agent_id="observer-1",
        source_agent_id="coder",
        mission_id="mission-123",
        session_id="session-456",
        content="Test",
        annotation_type="code_change",
        importance=0.8,
    )

    await memory_facade.save_hierarchical_annotation(
        async_session,
        annotation=annotation,
        project_name="TestProject",
        project_root="/test/path",
        category_name="api",
        subcategory_name="middleware",
    )

    # Verify only one subcategory exists
    result = await async_session.execute(select(MemorySubCategory))
    subcategories = result.scalars().all()
    assert len(subcategories) == 1


# ============================================================================
# Multiple Annotations Tests
# ============================================================================


@pytest.mark.asyncio
async def test_save_multiple_hierarchical_annotations(
    async_session: AsyncSession,
    memory_facade: MemoryFacade,
):
    """Test saving multiple annotations to the same project."""
    annotations = [
        MemoryAnnotation(
            observer_agent_id="observer-1",
            source_agent_id="coder",
            mission_id="mission-123",
            session_id="session-456",
            content=f"Annotation {i}",
            annotation_type="code_change",
            importance=0.8,
        )
        for i in range(3)
    ]

    for ann in annotations:
        await memory_facade.save_hierarchical_annotation(
            async_session,
            annotation=ann,
            project_name="TestProject",
            project_root="/test/path",
            category_name="api",
        )

    # Verify all annotations were saved
    result = await async_session.execute(select(HierarchicalAnnotation))
    saved_annotations = result.scalars().all()
    assert len(saved_annotations) == 3

    # Verify only one project and one category
    project_result = await async_session.execute(select(ProjectMemory))
    projects = project_result.scalars().all()
    assert len(projects) == 1

    category_result = await async_session.execute(select(MemoryCategory))
    categories = category_result.scalars().all()
    assert len(categories) == 1


# ============================================================================
# Field Preservation Tests
# ============================================================================


@pytest.mark.asyncio
async def test_save_hierarchical_annotation_preserves_all_fields(
    async_session: AsyncSession,
    memory_facade: MemoryFacade,
):
    """Test that all annotation fields are preserved."""
    annotation = MemoryAnnotation(
        observer_agent_id="observer-1",
        source_agent_id="coder",
        mission_id="mission-123",
        session_id="session-456",
        content="Detailed annotation content",
        annotation_type="code_change",
        importance=0.9,
        tags=["api", "auth", "security"],
        raw_event_type="tool_result",
    )

    annotation_id = await memory_facade.save_hierarchical_annotation(
        async_session,
        annotation=annotation,
        project_name="TestProject",
        project_root="/test/path",
        category_name="api",
        subcategory_name="middleware",
        file_path="python/api/middleware/auth.py",
        lines_modified={"start": 10, "end": 20, "type": "modified"},
        diff_summary="Added JWT validation middleware",
    )

    # Verify all fields
    result = await async_session.execute(
        select(HierarchicalAnnotation).where(HierarchicalAnnotation.id == annotation_id)
    )
    saved = result.scalar_one()

    assert saved.observer_agent_id == "observer-1"
    assert saved.source_agent_id == "coder"
    assert saved.mission_id == "mission-123"
    assert saved.session_id == "session-456"
    assert saved.content == "Detailed annotation content"
    assert saved.annotation_type == "code_change"
    assert saved.importance == 0.9
    assert saved.tags == ["api", "auth", "security"]
    assert saved.raw_event_type == "tool_result"
    assert saved.file_path == "python/api/middleware/auth.py"
    assert saved.lines_modified == {"start": 10, "end": 20, "type": "modified"}
    assert saved.diff_summary == "Added JWT validation middleware"
