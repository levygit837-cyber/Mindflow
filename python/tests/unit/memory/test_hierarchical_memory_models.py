"""Unit tests for hierarchical memory models (Phase 1)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session

from mindflow_backend.memory.storage.models import (
    Base,
    HierarchicalAnnotation,
    MemoryCategory,
    MemorySubCategory,
    ProjectMemory,
)


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


@pytest.fixture
def db_session(in_memory_db):
    """Create a database session for testing."""
    with Session(in_memory_db) as session:
        yield session


# ============================================================================
# ProjectMemory Tests
# ============================================================================


def test_create_project_memory(db_session: Session):
    """Test creating a ProjectMemory record."""
    project = ProjectMemory(
        project_name="MindFlow",
        root_path="/home/user/Projetos/MindFlow",
        description="AI agent orchestration platform",
    )
    db_session.add(project)
    db_session.commit()

    assert project.id is not None
    assert project.project_name == "MindFlow"
    assert project.root_path == "/home/user/Projetos/MindFlow"
    assert project.created_at is not None
    assert project.updated_at is not None


def test_project_memory_timestamps(db_session: Session):
    """Test that timestamps are set correctly."""
    project = ProjectMemory(
        project_name="TestProject",
        root_path="/test/path",
    )
    db_session.add(project)
    db_session.commit()

    assert isinstance(project.created_at, datetime)
    assert isinstance(project.updated_at, datetime)
    assert project.created_at <= project.updated_at


def test_query_project_by_name(db_session: Session):
    """Test querying projects by name."""
    project1 = ProjectMemory(project_name="Project1", root_path="/path1")
    project2 = ProjectMemory(project_name="Project2", root_path="/path2")
    db_session.add_all([project1, project2])
    db_session.commit()

    result = db_session.execute(
        select(ProjectMemory).where(ProjectMemory.project_name == "Project1")
    ).scalar_one()

    assert result.id == project1.id
    assert result.project_name == "Project1"


# ============================================================================
# MemoryCategory Tests
# ============================================================================


def test_create_memory_category(db_session: Session):
    """Test creating a MemoryCategory with foreign key to ProjectMemory."""
    project = ProjectMemory(project_name="TestProject", root_path="/test")
    db_session.add(project)
    db_session.commit()

    category = MemoryCategory(
        project_id=project.id,
        name="API",
        path_pattern="python/mindflow_backend/api/**",
        description="API endpoints and routes",
    )
    db_session.add(category)
    db_session.commit()

    assert category.id is not None
    assert category.project_id == project.id
    assert category.name == "API"
    assert category.path_pattern == "python/mindflow_backend/api/**"


def test_category_unique_constraint(db_session: Session):
    """Test that project_id + name must be unique."""
    project = ProjectMemory(project_name="TestProject", root_path="/test")
    db_session.add(project)
    db_session.commit()

    category1 = MemoryCategory(project_id=project.id, name="API")
    db_session.add(category1)
    db_session.commit()

    # Attempting to create duplicate should fail
    category2 = MemoryCategory(project_id=project.id, name="API")
    db_session.add(category2)

    with pytest.raises(Exception):  # IntegrityError in real DB
        db_session.commit()

    db_session.rollback()  # Clean up after exception


def test_category_cascade_delete(db_session: Session):
    """Test that deleting a project cascades to categories."""
    project = ProjectMemory(project_name="TestProject", root_path="/test")
    db_session.add(project)
    db_session.commit()

    category = MemoryCategory(project_id=project.id, name="API")
    db_session.add(category)
    db_session.commit()

    category_id = category.id

    # Delete project
    db_session.delete(project)
    db_session.commit()

    # Category should be deleted
    result = db_session.execute(
        select(MemoryCategory).where(MemoryCategory.id == category_id)
    ).first()
    assert result is None


# ============================================================================
# MemorySubCategory Tests
# ============================================================================


def test_create_memory_subcategory(db_session: Session):
    """Test creating a MemorySubCategory with foreign key to MemoryCategory."""
    project = ProjectMemory(project_name="TestProject", root_path="/test")
    db_session.add(project)
    db_session.commit()

    category = MemoryCategory(project_id=project.id, name="API")
    db_session.add(category)
    db_session.commit()

    subcategory = MemorySubCategory(
        category_id=category.id,
        name="Controllers",
        path_pattern="api/controllers/**",
    )
    db_session.add(subcategory)
    db_session.commit()

    assert subcategory.id is not None
    assert subcategory.category_id == category.id
    assert subcategory.name == "Controllers"


def test_subcategory_unique_constraint(db_session: Session):
    """Test that category_id + name must be unique."""
    project = ProjectMemory(project_name="TestProject", root_path="/test")
    db_session.add(project)
    db_session.commit()

    category = MemoryCategory(project_id=project.id, name="API")
    db_session.add(category)
    db_session.commit()

    subcat1 = MemorySubCategory(category_id=category.id, name="Controllers")
    db_session.add(subcat1)
    db_session.commit()

    # Duplicate should fail
    subcat2 = MemorySubCategory(category_id=category.id, name="Controllers")
    db_session.add(subcat2)

    with pytest.raises(Exception):
        db_session.commit()

    db_session.rollback()  # Clean up after exception


def test_subcategory_cascade_delete(db_session: Session):
    """Test that deleting a category cascades to subcategories."""
    project = ProjectMemory(project_name="TestProject", root_path="/test")
    db_session.add(project)
    db_session.commit()

    category = MemoryCategory(project_id=project.id, name="API")
    db_session.add(category)
    db_session.commit()

    subcategory = MemorySubCategory(category_id=category.id, name="Controllers")
    db_session.add(subcategory)
    db_session.commit()

    subcategory_id = subcategory.id

    # Delete category
    db_session.delete(category)
    db_session.commit()

    # Subcategory should be deleted
    result = db_session.execute(
        select(MemorySubCategory).where(MemorySubCategory.id == subcategory_id)
    ).first()
    assert result is None


# ============================================================================
# HierarchicalAnnotation Tests
# ============================================================================


def test_create_hierarchical_annotation(db_session: Session):
    """Test creating a HierarchicalAnnotation with full hierarchy."""
    project = ProjectMemory(project_name="MindFlow", root_path="/home/user/MindFlow")
    db_session.add(project)
    db_session.commit()

    category = MemoryCategory(project_id=project.id, name="API")
    db_session.add(category)
    db_session.commit()

    subcategory = MemorySubCategory(category_id=category.id, name="Controllers")
    db_session.add(subcategory)
    db_session.commit()

    annotation = HierarchicalAnnotation(
        project_id=project.id,
        category_id=category.id,
        subcategory_id=subcategory.id,
        observer_agent_id="analyst",
        source_agent_id="coder",
        mission_id="mission-123",
        session_id="session-456",
        file_path="python/mindflow_backend/api/v1/chat.py",
        lines_modified={"start": 45, "end": 67, "type": "added"},
        diff_summary="Added JWT validation middleware",
        content="Coder modified auth middleware in api/v1/chat.py, lines 45-67, added JWT validation",
        annotation_type="code_change",
        importance=0.8,
        tags=["api", "authentication", "jwt"],
        raw_event_type="tool_result",
    )
    db_session.add(annotation)
    db_session.commit()

    assert annotation.id is not None
    assert annotation.project_id == project.id
    assert annotation.category_id == category.id
    assert annotation.subcategory_id == subcategory.id
    assert annotation.file_path == "python/mindflow_backend/api/v1/chat.py"
    assert annotation.importance == 0.8
    assert "jwt" in annotation.tags


def test_annotation_without_category(db_session: Session):
    """Test creating annotation without category/subcategory (nullable)."""
    project = ProjectMemory(project_name="TestProject", root_path="/test")
    db_session.add(project)
    db_session.commit()

    annotation = HierarchicalAnnotation(
        project_id=project.id,
        category_id=None,
        subcategory_id=None,
        observer_agent_id="analyst",
        source_agent_id="coder",
        mission_id="mission-123",
        session_id="session-456",
        content="Generic observation without categorization",
        annotation_type="observation",
        importance=0.5,
    )
    db_session.add(annotation)
    db_session.commit()

    assert annotation.id is not None
    assert annotation.category_id is None
    assert annotation.subcategory_id is None


def test_annotation_set_null_on_category_delete(db_session: Session):
    """Test that deleting category sets category_id to NULL (not cascade)."""
    project = ProjectMemory(project_name="TestProject", root_path="/test")
    db_session.add(project)
    db_session.commit()

    category = MemoryCategory(project_id=project.id, name="API")
    db_session.add(category)
    db_session.commit()

    annotation = HierarchicalAnnotation(
        project_id=project.id,
        category_id=category.id,
        observer_agent_id="analyst",
        source_agent_id="coder",
        mission_id="mission-123",
        session_id="session-456",
        content="Test annotation",
    )
    db_session.add(annotation)
    db_session.commit()

    annotation_id = annotation.id

    # Delete category
    db_session.delete(category)
    db_session.commit()

    # Annotation should still exist with category_id = NULL
    result = db_session.execute(
        select(HierarchicalAnnotation).where(HierarchicalAnnotation.id == annotation_id)
    ).scalar_one()

    assert result is not None
    assert result.category_id is None


def test_annotation_cascade_delete_on_project(db_session: Session):
    """Test that deleting project cascades to annotations."""
    project = ProjectMemory(project_name="TestProject", root_path="/test")
    db_session.add(project)
    db_session.commit()

    annotation = HierarchicalAnnotation(
        project_id=project.id,
        observer_agent_id="analyst",
        source_agent_id="coder",
        mission_id="mission-123",
        session_id="session-456",
        content="Test annotation",
    )
    db_session.add(annotation)
    db_session.commit()

    annotation_id = annotation.id

    # Delete project
    db_session.delete(project)
    db_session.commit()

    # Annotation should be deleted
    result = db_session.execute(
        select(HierarchicalAnnotation).where(HierarchicalAnnotation.id == annotation_id)
    ).first()
    assert result is None


def test_query_annotations_by_file_path(db_session: Session):
    """Test querying annotations by file path."""
    project = ProjectMemory(project_name="TestProject", root_path="/test")
    db_session.add(project)
    db_session.commit()

    ann1 = HierarchicalAnnotation(
        project_id=project.id,
        observer_agent_id="analyst",
        source_agent_id="coder",
        mission_id="m1",
        session_id="s1",
        file_path="api/auth.py",
        content="Auth change",
    )
    ann2 = HierarchicalAnnotation(
        project_id=project.id,
        observer_agent_id="analyst",
        source_agent_id="coder",
        mission_id="m2",
        session_id="s1",
        file_path="api/users.py",
        content="User change",
    )
    db_session.add_all([ann1, ann2])
    db_session.commit()

    results = db_session.execute(
        select(HierarchicalAnnotation).where(HierarchicalAnnotation.file_path == "api/auth.py")
    ).scalars().all()

    assert len(results) == 1
    assert results[0].content == "Auth change"


def test_query_annotations_by_importance(db_session: Session):
    """Test querying annotations by importance threshold."""
    project = ProjectMemory(project_name="TestProject", root_path="/test")
    db_session.add(project)
    db_session.commit()

    ann1 = HierarchicalAnnotation(
        project_id=project.id,
        observer_agent_id="analyst",
        source_agent_id="coder",
        mission_id="m1",
        session_id="s1",
        content="Low importance",
        importance=0.3,
    )
    ann2 = HierarchicalAnnotation(
        project_id=project.id,
        observer_agent_id="analyst",
        source_agent_id="coder",
        mission_id="m2",
        session_id="s1",
        content="High importance",
        importance=0.9,
    )
    db_session.add_all([ann1, ann2])
    db_session.commit()

    # Query annotations with importance >= 0.7
    results = db_session.execute(
        select(HierarchicalAnnotation).where(HierarchicalAnnotation.importance >= 0.7)
    ).scalars().all()

    assert len(results) == 1
    assert results[0].content == "High importance"


def test_annotation_json_fields(db_session: Session):
    """Test that JSON fields (tags, lines_modified, metadata) work correctly."""
    project = ProjectMemory(project_name="TestProject", root_path="/test")
    db_session.add(project)
    db_session.commit()

    annotation = HierarchicalAnnotation(
        project_id=project.id,
        observer_agent_id="analyst",
        source_agent_id="coder",
        mission_id="m1",
        session_id="s1",
        content="Test",
        tags=["api", "auth", "security"],
        lines_modified={"start": 10, "end": 20, "type": "modified"},
        metadata_json={"tool": "write_file", "duration_ms": 150},
    )
    db_session.add(annotation)
    db_session.commit()

    # Retrieve and verify JSON fields
    result = db_session.execute(
        select(HierarchicalAnnotation).where(HierarchicalAnnotation.id == annotation.id)
    ).scalar_one()

    assert result.tags == ["api", "auth", "security"]
    assert result.lines_modified["start"] == 10
    assert result.lines_modified["type"] == "modified"
    assert result.metadata_json["tool"] == "write_file"
    assert result.metadata_json["duration_ms"] == 150
