"""End-to-end integration tests for Phase 1: Observer → DirectoryMapper → Facade → Database."""

from __future__ import annotations

import asyncio

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from mindflow_backend.execution.observers.memory_observer import MemoryObserver
from mindflow_backend.memory.facade import MemoryFacade
from mindflow_backend.memory.storage.models import (
    Base,
    HierarchicalAnnotation,
    MemoryCategory,
    MemorySubCategory,
    ProjectMemory,
)


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
    async with AsyncSession(async_db, expire_on_commit=False) as session:
        yield session


@pytest_asyncio.fixture
async def memory_facade():
    """Create a MemoryFacade instance."""
    return MemoryFacade()


@pytest_asyncio.fixture
async def memory_observer(memory_facade):
    """Create a MemoryObserver with real DirectoryMapper."""
    observer = MemoryObserver(
        observer_agent_id="test-observer",
        memory_facade=memory_facade,
        session_id="test-session-e2e",
        project_root="/home/user/TestProject",
        project_name="TestProject",
    )
    return observer


# ============================================================================
# End-to-End: Code Change → Hierarchical Annotation
# ============================================================================


@pytest.mark.asyncio
async def test_e2e_code_change_creates_hierarchical_annotation(
    async_session: AsyncSession,
    memory_facade: MemoryFacade,
):
    """Test complete flow: code change event → hierarchical annotation in DB."""
    from mindflow_backend.schemas.memory.annotation import MemoryAnnotation

    # Simulate a code change annotation
    annotation = MemoryAnnotation(
        observer_agent_id="observer-1",
        source_agent_id="coder",
        mission_id="mission-e2e-1",
        session_id="session-e2e-1",
        content="Coder modified API endpoint in chat.py, lines 45-67. Added JWT validation.",
        annotation_type="code_change",
        importance=0.8,
        tags=["api", "auth", "security"],
        raw_event_type="tool_result",
    )

    # Save hierarchical annotation
    annotation_id = await memory_facade.save_hierarchical_annotation(
        async_session,
        annotation=annotation,
        project_name="TestProject",
        project_root="/home/user/TestProject",
        category_name="api",
        subcategory_name="v1",
        file_path="python/api/v1/chat.py",
        lines_modified={"start": 45, "end": 67, "count": 22},
        diff_summary="Added JWT validation middleware",
    )

    await async_session.commit()

    # Verify ProjectMemory was created
    project_result = await async_session.execute(select(ProjectMemory))
    projects = project_result.scalars().all()
    assert len(projects) == 1
    assert projects[0].project_name == "TestProject"

    # Verify MemoryCategory was created
    category_result = await async_session.execute(select(MemoryCategory))
    categories = category_result.scalars().all()
    assert len(categories) == 1
    assert categories[0].name == "api"

    # Verify MemorySubCategory was created
    subcategory_result = await async_session.execute(select(MemorySubCategory))
    subcategories = subcategory_result.scalars().all()
    assert len(subcategories) == 1
    assert subcategories[0].name == "v1"

    # Verify HierarchicalAnnotation was created with all fields
    annotation_result = await async_session.execute(
        select(HierarchicalAnnotation).where(HierarchicalAnnotation.id == annotation_id)
    )
    saved_annotation = annotation_result.scalar_one()

    assert saved_annotation.project_id == projects[0].id
    assert saved_annotation.category_id == categories[0].id
    assert saved_annotation.subcategory_id == subcategories[0].id
    assert saved_annotation.observer_agent_id == "observer-1"
    assert saved_annotation.source_agent_id == "coder"
    assert saved_annotation.file_path == "python/api/v1/chat.py"
    assert saved_annotation.lines_modified == {"start": 45, "end": 67, "count": 22}
    assert saved_annotation.diff_summary == "Added JWT validation middleware"
    assert saved_annotation.importance == 0.8
    assert "api" in saved_annotation.tags


@pytest.mark.asyncio
async def test_e2e_multiple_code_changes_same_category(
    async_session: AsyncSession,
    memory_facade: MemoryFacade,
):
    """Test multiple code changes in same category reuse existing category."""
    from mindflow_backend.schemas.memory.annotation import MemoryAnnotation

    # First annotation
    ann1 = MemoryAnnotation(
        observer_agent_id="observer-1",
        source_agent_id="coder",
        mission_id="mission-1",
        session_id="session-1",
        content="Modified chat.py",
        annotation_type="code_change",
        importance=0.8,
    )

    await memory_facade.save_hierarchical_annotation(
        async_session,
        annotation=ann1,
        project_name="TestProject",
        project_root="/test",
        category_name="api",
        subcategory_name="v1",
        file_path="api/v1/chat.py",
    )

    # Second annotation - same category
    ann2 = MemoryAnnotation(
        observer_agent_id="observer-1",
        source_agent_id="coder",
        mission_id="mission-1",
        session_id="session-1",
        content="Modified users.py",
        annotation_type="code_change",
        importance=0.7,
    )

    await memory_facade.save_hierarchical_annotation(
        async_session,
        annotation=ann2,
        project_name="TestProject",
        project_root="/test",
        category_name="api",
        subcategory_name="v2",
        file_path="api/v2/users.py",
    )

    await async_session.commit()

    # Verify only ONE project and ONE category
    project_result = await async_session.execute(select(ProjectMemory))
    projects = project_result.scalars().all()
    assert len(projects) == 1

    category_result = await async_session.execute(select(MemoryCategory))
    categories = category_result.scalars().all()
    assert len(categories) == 1

    # Verify TWO subcategories (v1 and v2)
    subcategory_result = await async_session.execute(select(MemorySubCategory))
    subcategories = subcategory_result.scalars().all()
    assert len(subcategories) == 2
    subcategory_names = {sub.name for sub in subcategories}
    assert subcategory_names == {"v1", "v2"}

    # Verify TWO annotations
    annotation_result = await async_session.execute(select(HierarchicalAnnotation))
    annotations = annotation_result.scalars().all()
    assert len(annotations) == 2


@pytest.mark.asyncio
async def test_e2e_different_categories_in_same_project(
    async_session: AsyncSession,
    memory_facade: MemoryFacade,
):
    """Test annotations in different categories within same project."""
    from mindflow_backend.schemas.memory.annotation import MemoryAnnotation

    # API category
    ann_api = MemoryAnnotation(
        observer_agent_id="observer-1",
        source_agent_id="coder",
        mission_id="mission-1",
        session_id="session-1",
        content="Modified API",
        annotation_type="code_change",
        importance=0.8,
    )

    await memory_facade.save_hierarchical_annotation(
        async_session,
        annotation=ann_api,
        project_name="TestProject",
        project_root="/test",
        category_name="api",
        file_path="api/chat.py",
    )

    # Services category
    ann_service = MemoryAnnotation(
        observer_agent_id="observer-1",
        source_agent_id="coder",
        mission_id="mission-1",
        session_id="session-1",
        content="Modified service",
        annotation_type="code_change",
        importance=0.7,
    )

    await memory_facade.save_hierarchical_annotation(
        async_session,
        annotation=ann_service,
        project_name="TestProject",
        project_root="/test",
        category_name="services",
        subcategory_name="auth",
        file_path="services/auth/jwt.py",
    )

    # Tests category
    ann_test = MemoryAnnotation(
        observer_agent_id="observer-1",
        source_agent_id="coder",
        mission_id="mission-1",
        session_id="session-1",
        content="Added test",
        annotation_type="code_change",
        importance=0.6,
    )

    await memory_facade.save_hierarchical_annotation(
        async_session,
        annotation=ann_test,
        project_name="TestProject",
        project_root="/test",
        category_name="tests",
        file_path="tests/test_auth.py",
    )

    await async_session.commit()

    # Verify ONE project
    project_result = await async_session.execute(select(ProjectMemory))
    projects = project_result.scalars().all()
    assert len(projects) == 1

    # Verify THREE categories
    category_result = await async_session.execute(select(MemoryCategory))
    categories = category_result.scalars().all()
    assert len(categories) == 3
    category_names = {cat.name for cat in categories}
    assert category_names == {"api", "services", "tests"}

    # Verify THREE annotations
    annotation_result = await async_session.execute(select(HierarchicalAnnotation))
    annotations = annotation_result.scalars().all()
    assert len(annotations) == 3


# ============================================================================
# End-to-End: Query Hierarchical Annotations
# ============================================================================


@pytest.mark.asyncio
async def test_e2e_query_annotations_by_category(
    async_session: AsyncSession,
    memory_facade: MemoryFacade,
):
    """Test querying annotations by category."""
    from mindflow_backend.schemas.memory.annotation import MemoryAnnotation

    # Create annotations in different categories
    for category in ["api", "services", "tests"]:
        ann = MemoryAnnotation(
            observer_agent_id="observer-1",
            source_agent_id="coder",
            mission_id="mission-1",
            session_id="session-1",
            content=f"Modified {category}",
            annotation_type="code_change",
            importance=0.7,
        )

        await memory_facade.save_hierarchical_annotation(
            async_session,
            annotation=ann,
            project_name="TestProject",
            project_root="/test",
            category_name=category,
            file_path=f"{category}/file.py",
        )

    await async_session.commit()

    # Query annotations in "api" category
    category_result = await async_session.execute(
        select(MemoryCategory).where(MemoryCategory.name == "api")
    )
    api_category = category_result.scalar_one()

    annotation_result = await async_session.execute(
        select(HierarchicalAnnotation).where(
            HierarchicalAnnotation.category_id == api_category.id
        )
    )
    api_annotations = annotation_result.scalars().all()

    assert len(api_annotations) == 1
    assert "Modified api" in api_annotations[0].content


@pytest.mark.asyncio
async def test_e2e_query_annotations_by_file_path(
    async_session: AsyncSession,
    memory_facade: MemoryFacade,
):
    """Test querying annotations by file path."""
    from mindflow_backend.schemas.memory.annotation import MemoryAnnotation

    # Create annotations for different files
    files = [
        "python/api/v1/chat.py",
        "python/api/v1/users.py",
        "python/services/auth.py",
    ]

    for file_path in files:
        ann = MemoryAnnotation(
            observer_agent_id="observer-1",
            source_agent_id="coder",
            mission_id="mission-1",
            session_id="session-1",
            content=f"Modified {file_path}",
            annotation_type="code_change",
            importance=0.7,
        )

        await memory_facade.save_hierarchical_annotation(
            async_session,
            annotation=ann,
            project_name="TestProject",
            project_root="/test",
            category_name="api",
            file_path=file_path,
        )

    await async_session.commit()

    # Query annotations for specific file
    annotation_result = await async_session.execute(
        select(HierarchicalAnnotation).where(
            HierarchicalAnnotation.file_path == "python/api/v1/chat.py"
        )
    )
    chat_annotations = annotation_result.scalars().all()

    assert len(chat_annotations) == 1
    assert chat_annotations[0].file_path == "python/api/v1/chat.py"


@pytest.mark.asyncio
async def test_e2e_query_annotations_by_importance(
    async_session: AsyncSession,
    memory_facade: MemoryFacade,
):
    """Test querying annotations by importance threshold."""
    from mindflow_backend.schemas.memory.annotation import MemoryAnnotation

    # Create annotations with different importance levels
    importances = [0.3, 0.5, 0.7, 0.9]

    for importance in importances:
        ann = MemoryAnnotation(
            observer_agent_id="observer-1",
            source_agent_id="coder",
            mission_id="mission-1",
            session_id="session-1",
            content=f"Importance {importance}",
            annotation_type="code_change",
            importance=importance,
        )

        await memory_facade.save_hierarchical_annotation(
            async_session,
            annotation=ann,
            project_name="TestProject",
            project_root="/test",
            category_name="api",
            file_path="test.py",
        )

    await async_session.commit()

    # Query high-importance annotations (>= 0.7)
    annotation_result = await async_session.execute(
        select(HierarchicalAnnotation).where(HierarchicalAnnotation.importance >= 0.7)
    )
    high_importance = annotation_result.scalars().all()

    assert len(high_importance) == 2
    assert all(ann.importance >= 0.7 for ann in high_importance)


# ============================================================================
# End-to-End: Cross-Agent Memory Bridge
# ============================================================================


@pytest.mark.asyncio
async def test_e2e_cross_agent_memory_bridge(
    async_session: AsyncSession,
    memory_facade: MemoryFacade,
):
    """Test that Agent B can query annotations created by Agent A."""
    from mindflow_backend.schemas.memory.annotation import MemoryAnnotation

    # Agent A (coder) creates annotation
    ann_agent_a = MemoryAnnotation(
        observer_agent_id="observer-1",
        source_agent_id="agent-a-coder",
        mission_id="mission-a",
        session_id="session-1",
        content="Agent A implemented JWT authentication",
        annotation_type="code_change",
        importance=0.9,
        tags=["agent:agent-a-coder", "auth", "jwt"],
    )

    await memory_facade.save_hierarchical_annotation(
        async_session,
        annotation=ann_agent_a,
        project_name="TestProject",
        project_root="/test",
        category_name="api",
        subcategory_name="middleware",
        file_path="api/middleware/auth.py",
    )

    await async_session.commit()

    # Agent B queries for auth-related annotations
    annotation_result = await async_session.execute(
        select(HierarchicalAnnotation).where(
            HierarchicalAnnotation.content.contains("authentication")
        )
    )
    auth_annotations = annotation_result.scalars().all()

    assert len(auth_annotations) == 1
    assert auth_annotations[0].source_agent_id == "agent-a-coder"
    assert "jwt" in auth_annotations[0].tags

    # Agent B can also query by category
    category_result = await async_session.execute(
        select(MemoryCategory).where(MemoryCategory.name == "api")
    )
    api_category = category_result.scalar_one()

    category_annotations = await async_session.execute(
        select(HierarchicalAnnotation).where(
            HierarchicalAnnotation.category_id == api_category.id
        )
    )
    api_anns = category_annotations.scalars().all()

    assert len(api_anns) == 1
    assert api_anns[0].source_agent_id == "agent-a-coder"


# ============================================================================
# End-to-End: Annotation Without Category (Fallback)
# ============================================================================


@pytest.mark.asyncio
async def test_e2e_annotation_without_category_fallback(
    async_session: AsyncSession,
    memory_facade: MemoryFacade,
):
    """Test that annotations without category still work (backward compat)."""
    from mindflow_backend.schemas.memory.annotation import MemoryAnnotation

    ann = MemoryAnnotation(
        observer_agent_id="observer-1",
        source_agent_id="analyst",
        mission_id="mission-1",
        session_id="session-1",
        content="General observation without file context",
        annotation_type="observation",
        importance=0.5,
    )

    annotation_id = await memory_facade.save_hierarchical_annotation(
        async_session,
        annotation=ann,
        project_name="TestProject",
        project_root="/test",
        # No category_name, subcategory_name, or file_path
    )

    await async_session.commit()

    # Verify annotation was created
    annotation_result = await async_session.execute(
        select(HierarchicalAnnotation).where(HierarchicalAnnotation.id == annotation_id)
    )
    saved_ann = annotation_result.scalar_one()

    assert saved_ann.category_id is None
    assert saved_ann.subcategory_id is None
    assert saved_ann.file_path is None
    assert saved_ann.content == "General observation without file context"
