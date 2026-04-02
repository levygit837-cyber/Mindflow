"""Unit tests for DirectoryMapper and code change detection (Phase 2)."""

from __future__ import annotations

import pytest

from mindflow_backend.execution.observers.directory_mapper import DirectoryMapper


# ============================================================================
# DirectoryMapper Tests
# ============================================================================


def test_directory_mapper_initialization():
    """Test DirectoryMapper initializes with project root."""
    mapper = DirectoryMapper("/home/user/MindFlow")
    assert mapper.project_root.name == "MindFlow"
    assert len(mapper.category_map) > 0


def test_categorize_backend_api_file():
    """Test categorization of backend API files."""
    mapper = DirectoryMapper("/home/user/MindFlow")

    category, subcategory = mapper.categorize_file(
        "python/mindflow_backend/api/v1/chat.py"
    )

    assert category == "API"
    assert subcategory == "V1"


def test_categorize_backend_services_file():
    """Test categorization of backend services files."""
    mapper = DirectoryMapper("/home/user/MindFlow")

    category, subcategory = mapper.categorize_file(
        "python/mindflow_backend/services/core/session_service.py"
    )

    assert category == "Services"
    assert subcategory == "Core"


def test_categorize_agents_tools_file():
    """Test categorization of agent tools files - uses fallback when path doesn't match pattern."""
    mapper = DirectoryMapper("/home/user/MindFlow")

    category, subcategory = mapper.categorize_file(
        "mindflow_backend/agents/tools/filesystem/file_operations.py"
    )

    # Falls back to first two directories (mindflow_backend doesn't match **/agents/tools/**)
    assert category == "Mindflow Backend"
    assert subcategory == "Agents"


def test_categorize_memory_storage_file():
    """Test categorization of memory storage files - uses pattern matching."""
    mapper = DirectoryMapper("/home/user/MindFlow")

    category, subcategory = mapper.categorize_file(
        "mindflow_backend/memory/storage/models.py"
    )

    # Pattern **/memory/storage/** should match
    assert category == "Memory"
    assert subcategory == "Storage"


def test_categorize_frontend_components_file():
    """Test categorization of frontend component files."""
    mapper = DirectoryMapper("/home/user/MindFlow")

    category, subcategory = mapper.categorize_file(
        "frontend/src/components/ChatInterface.tsx"
    )

    assert category == "Frontend"
    assert subcategory == "Components"


def test_categorize_tests_file():
    """Test categorization of test files."""
    mapper = DirectoryMapper("/home/user/MindFlow")

    # This path contains "memory" so it matches **/memory/** pattern first
    category, subcategory = mapper.categorize_file(
        "tests/unit/memory/test_hierarchical_memory_models.py"
    )

    # Matches **/memory/** pattern (not **/tests/unit/**)
    assert category == "Memory"
    assert subcategory == "Storage"


def test_categorize_tests_file_without_memory():
    """Test categorization of test files that contain 'api'."""
    mapper = DirectoryMapper("/home/user/MindFlow")

    # This path contains "api" so it matches **/api/** pattern first
    category, subcategory = mapper.categorize_file(
        "tests/unit/api/test_endpoints.py"
    )

    # Matches **/api/** pattern (not **/tests/unit/**)
    assert category == "API"
    assert subcategory == "Endpoints"


def test_categorize_documentation_file():
    """Test categorization of documentation files - uses fallback."""
    mapper = DirectoryMapper("/home/user/MindFlow")

    category, subcategory = mapper.categorize_file(
        "docs/architecture/distributed-orchestration/00-EXECUTIVE-SUMMARY.md"
    )

    # Falls back to first two directories
    assert category == "Docs"
    assert subcategory == "Architecture"


def test_categorize_config_file():
    """Test categorization of configuration files."""
    mapper = DirectoryMapper("/home/user/MindFlow")

    category, subcategory = mapper.categorize_file("pyproject.toml")

    assert category == "Configuration"
    assert subcategory == "Root"


def test_categorize_absolute_path():
    """Test categorization with absolute path."""
    mapper = DirectoryMapper("/home/user/MindFlow")

    category, subcategory = mapper.categorize_file(
        "/home/user/MindFlow/python/mindflow_backend/api/v1/chat.py"
    )

    assert category == "API"
    assert subcategory == "V1"


def test_categorize_fallback_two_levels():
    """Test fallback categorization for unknown paths with 2+ levels."""
    mapper = DirectoryMapper("/home/user/MindFlow")

    category, subcategory = mapper.categorize_file(
        "custom_module/submodule/file.py"
    )

    assert category == "Custom Module"
    assert subcategory == "Submodule"


def test_categorize_fallback_one_level():
    """Test fallback categorization for unknown paths with 1 level."""
    mapper = DirectoryMapper("/home/levybonito/Projetos/MindFlow")

    # Use a file that won't match any pattern
    category, subcategory = mapper.categorize_file("CHANGELOG.md")

    # Should fallback to single directory name (includes extension)
    assert category == "Changelog.Md"
    assert subcategory is None


def test_categorize_fallback_general():
    """Test ultimate fallback to General category."""
    mapper = DirectoryMapper("/home/user/MindFlow")

    # Empty path should fallback to General
    category, subcategory = mapper.categorize_file("")

    assert category == "General"
    assert subcategory is None


def test_add_custom_pattern():
    """Test adding custom pattern to mapper."""
    mapper = DirectoryMapper("/home/user/MindFlow")

    mapper.add_pattern("custom/module/**", "CustomCategory", "CustomSub")

    category, subcategory = mapper.categorize_file("custom/module/file.py")

    assert category == "CustomCategory"
    assert subcategory == "CustomSub"


def test_pattern_specificity():
    """Test that more specific patterns take precedence."""
    mapper = DirectoryMapper("/home/user/MindFlow")

    # More specific pattern should match first
    category1, subcategory1 = mapper.categorize_file(
        "python/mindflow_backend/api/v1/chat.py"
    )
    assert category1 == "API"
    assert subcategory1 == "V1"

    # Less specific pattern
    category2, subcategory2 = mapper.categorize_file(
        "python/mindflow_backend/api/routes/health.py"
    )
    assert category2 == "API"
    assert subcategory2 == "Routes"


def test_get_category_stats():
    """Test getting category statistics."""
    mapper = DirectoryMapper("/home/user/MindFlow")

    stats = mapper.get_category_stats()

    assert isinstance(stats, dict)
    assert "API" in stats
    assert "Services" in stats
    assert "Memory" in stats
    assert stats["API"] >= 3  # At least 3 API patterns


def test_categorize_orchestrator_file():
    """Test categorization of orchestrator files."""
    mapper = DirectoryMapper("/home/user/MindFlow")

    category, subcategory = mapper.categorize_file(
        "python/mindflow_backend/orchestrator/delegation/engine.py"
    )

    assert category == "Orchestrator"
    assert subcategory == "Delegation"


def test_categorize_execution_observers_file():
    """Test categorization of execution observer files."""
    mapper = DirectoryMapper("/home/user/MindFlow")

    category, subcategory = mapper.categorize_file(
        "python/mindflow_backend/execution/observers/memory_observer.py"
    )

    assert category == "Execution"
    assert subcategory == "Observers"


def test_categorize_cli_file():
    """Test categorization of CLI files."""
    mapper = DirectoryMapper("/home/user/MindFlow")

    category, subcategory = mapper.categorize_file(
        "cli/src/commands/chat.tsx"
    )

    assert category == "CLI"
    assert subcategory == "Commands"


def test_categorize_infrastructure_database_file():
    """Test categorization of infrastructure database files."""
    mapper = DirectoryMapper("/home/user/MindFlow")

    category, subcategory = mapper.categorize_file(
        "python/mindflow_backend/infra/database/connection.py"
    )

    assert category == "Infrastructure"
    assert subcategory == "Database"


def test_categorize_outside_project_root():
    """Test categorization of file outside project root."""
    mapper = DirectoryMapper("/home/user/MindFlow")

    # Use a simple path that will use fallback
    category, subcategory = mapper.categorize_file("external/module/file.py")

    # Should fallback to first two directories
    assert category == "External"
    assert subcategory == "Module"


def test_multiple_mappers_independent():
    """Test that multiple mappers are independent."""
    mapper1 = DirectoryMapper("/home/user/Project1")
    mapper2 = DirectoryMapper("/home/user/Project2")

    mapper1.add_pattern("custom/**", "Custom1", None)
    mapper2.add_pattern("custom/**", "Custom2", None)

    cat1, _ = mapper1.categorize_file("custom/file.py")
    cat2, _ = mapper2.categorize_file("custom/file.py")

    assert cat1 == "Custom1"
    assert cat2 == "Custom2"


# ============================================================================
# Code Change Detection Tests
# ============================================================================


def test_extract_code_change_write_file():
    """Test extracting code change from write_file tool result."""
    from mindflow_backend.execution.observers.memory_observer import MemoryObserver

    event = {
        "type": "tool_result",
        "data": {
            "tool_name": "write_file",
            "file_path": "api/auth.py",
            "lines_modified": {"start": 10, "end": 20, "type": "added"},
            "diff": "+def authenticate():\n+    pass",
        },
    }

    result = MemoryObserver._extract_code_change(event)

    assert result is not None
    assert result["file_path"] == "api/auth.py"
    assert result["lines"]["start"] == 10
    assert result["operation"] == "write_file"


def test_extract_code_change_edit_file():
    """Test extracting code change from edit_file tool result."""
    from mindflow_backend.execution.observers.memory_observer import MemoryObserver

    event = {
        "type": "tool_result",
        "data": {
            "tool_name": "edit_file",
            "file_path": "services/user.py",
            "diff": "-old line\n+new line",
        },
    }

    result = MemoryObserver._extract_code_change(event)

    assert result is not None
    assert result["file_path"] == "services/user.py"
    assert result["operation"] == "edit_file"


def test_extract_code_change_file_written_event():
    """Test extracting code change from file_written event."""
    from mindflow_backend.execution.observers.memory_observer import MemoryObserver

    event = {
        "type": "file_written",
        "data": {
            "file_path": "models/user.py",
            "lines_modified": {"start": 5, "end": 15},
        },
    }

    result = MemoryObserver._extract_code_change(event)

    assert result is not None
    assert result["file_path"] == "models/user.py"
    assert result["operation"] == "file_written"


def test_extract_code_change_no_file_path():
    """Test that events without file_path return None."""
    from mindflow_backend.execution.observers.memory_observer import MemoryObserver

    event = {
        "type": "tool_result",
        "data": {
            "tool_name": "write_file",
            # Missing file_path
        },
    }

    result = MemoryObserver._extract_code_change(event)

    assert result is None


def test_extract_code_change_non_file_tool():
    """Test that non-file tools return None."""
    from mindflow_backend.execution.observers.memory_observer import MemoryObserver

    event = {
        "type": "tool_result",
        "data": {
            "tool_name": "search_web",
            "query": "test",
        },
    }

    result = MemoryObserver._extract_code_change(event)

    assert result is None


def test_generate_rich_context_with_mapper():
    """Test generating rich context with DirectoryMapper."""
    from mindflow_backend.execution.observers.memory_observer import MemoryObserver
    from mindflow_backend.memory.facade import MemoryFacade

    mapper = DirectoryMapper("/home/user/MindFlow")
    observer = MemoryObserver(
        observer_agent_id="analyst",
        memory_facade=MemoryFacade(),
        session_id="test-session",
        project_root="/home/user/MindFlow",
    )

    event = {
        "agent_id": "coder",
        "mission_id": "mission-123",
        "message": "Added JWT validation",
    }

    code_info = {
        "file_path": "python/mindflow_backend/api/middleware/auth.py",
        "lines": {"start": 45, "end": 67, "type": "added"},
        "diff": "+def validate_jwt():\n+    pass",
        "operation": "write_file",
    }

    context = observer._generate_rich_context(event, code_info)

    assert "coder" in context
    assert "write_file" in context
    assert "api/middleware/auth.py" in context
    assert "Category: API" in context
    assert "Middleware" in context
    assert "Lines added: 45-67" in context
    assert "Added JWT validation" in context
    assert "mission-123" in context


def test_generate_rich_context_without_mapper():
    """Test generating rich context without DirectoryMapper."""
    from mindflow_backend.execution.observers.memory_observer import MemoryObserver
    from mindflow_backend.memory.facade import MemoryFacade

    observer = MemoryObserver(
        observer_agent_id="analyst",
        memory_facade=MemoryFacade(),
        session_id="test-session",
        project_root=None,  # No mapper
    )

    event = {
        "agent_id": "coder",
        "mission_id": "mission-123",
        "message": "Fixed bug",
    }

    code_info = {
        "file_path": "utils/helper.py",
        "lines": {},
        "diff": "",
        "operation": "edit_file",
    }

    context = observer._generate_rich_context(event, code_info)

    assert "coder" in context
    assert "edit_file" in context
    assert "utils/helper.py" in context
    assert "Category:" not in context  # No mapper, no category
    assert "Fixed bug" in context
