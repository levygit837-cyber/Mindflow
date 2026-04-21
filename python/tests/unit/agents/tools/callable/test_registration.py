"""Tests for callable tool registration.

Validates that all Phase 2 callable tools register correctly with the central registry.
"""

import pytest

from mindflow_backend.agents.tools.callable import (
    register_all_callable_tools,
    unregister_all_callable_tools,
)
from mindflow_backend.schemas.tools.registry import get_registry, reset_registry


@pytest.fixture(autouse=True)
def clean_registry():
    """Reset registry before and after each test."""
    reset_registry()
    yield
    reset_registry()


def test_register_all_callable_tools():
    """Test that the callable registry exposes the full unique tool set."""
    registry = get_registry()

    # Initially empty
    assert len(registry.tools) == 0

    # Register all tools
    count = register_all_callable_tools()

    assert count == 31
    assert len(registry.tools) == 31


def test_registered_tool_names():
    """Test that all expected tool names are registered."""
    register_all_callable_tools()
    registry = get_registry()

    expected_names = {
        # Filesystem (9 tools) - using actual names from implementation
        "file_read", "list_dir", "file_finder", "grep_search", "glob_search",
        "write_file", "edit_file", "delete_file", "mkdir",
        # System (3 tools)
        "shell_execute", "system_info", "process_manager",
        # Web (3 tools)
        "http_client", "web_scraper", "api_client",
        # Browser
        "browser_search", "deep_page_scraper", "multi_tab_search",
        # Planning
        "read_todos", "write_todos", "focus_todos",
        # Scratchpad + LLM
        "read_scratchpad", "write_scratchpad",
        "llm_research_synthesis", "llm_query_refinement",
        # Memory
        "store_fact", "search_facts", "retrieve_task_context", "recall_session_memory",
        # Orchestration
        "AgentTool", "SendMessage",
    }

    registered_names = set(registry.tool_names)
    assert registered_names == expected_names


def test_registered_tool_categories():
    """Test that tools are registered with correct categories."""
    register_all_callable_tools()
    registry = get_registry()

    # Check filesystem category
    filesystem_tools = registry.filter_by_category("filesystem")
    assert len(filesystem_tools) == 9

    # Check system category
    system_tools = registry.filter_by_category("system")
    assert len(system_tools) == 3

    # Check web category
    web_tools = registry.filter_by_category("web")
    assert len(web_tools) == 3

    # Check browser category
    browser_tools = registry.filter_by_category("browser")
    assert len(browser_tools) == 3

    # Check planning category
    planning_tools = registry.filter_by_category("planning")
    assert len(planning_tools) == 5

    llm_tools = registry.filter_by_category("llm")
    assert len(llm_tools) == 2

    memory_tools = registry.filter_by_category("memory")
    assert len(memory_tools) == 4

    orchestration_tools = registry.filter_by_category("orchestration")
    assert len(orchestration_tools) == 2


def test_registered_tool_metadata():
    """Test that tools have correct metadata flags."""
    register_all_callable_tools()
    registry = get_registry()

    # Check read-only tools
    file_read = next(t for t in registry.tools if t.name == "file_read")
    assert file_read.is_read_only is True
    assert file_read.is_concurrency_safe is True
    assert file_read.is_destructive is False

    # Check write tools (write_file uses build_destructive_tool, so is_destructive=True)
    write_file = next(t for t in registry.tools if t.name == "write_file")
    assert write_file.is_read_only is False
    assert write_file.is_concurrency_safe is False
    assert write_file.is_destructive is True  # FileWriteCallable uses build_destructive_tool

    # Check destructive tools
    delete_file = next(t for t in registry.tools if t.name == "delete_file")
    assert delete_file.is_read_only is False
    assert delete_file.is_concurrency_safe is False
    assert delete_file.is_destructive is True


def test_unregister_all_callable_tools():
    """Test that unregistration removes all tools."""
    register_all_callable_tools()
    registry = get_registry()

    assert len(registry.tools) == 31

    # Unregister all
    count = unregister_all_callable_tools()
    assert count == 31

    # Should be empty
    assert len(registry.tools) == 0


def test_double_registration_is_safe():
    """Test that registering twice doesn't duplicate tools."""
    registry = get_registry()

    # Register once
    count1 = register_all_callable_tools()
    assert count1 == 31
    assert len(registry.tools) == 31

    # Register again - registry.register() will overwrite existing tools with same name
    count2 = register_all_callable_tools()
    assert count2 == 31
    assert len(registry.tools) == 31


def test_get_enabled_tools():
    """Test that all registered tools are enabled by default."""
    register_all_callable_tools()
    registry = get_registry()

    enabled_tools = registry.get_enabled_tools()
    assert len(enabled_tools) == 31

    # All tools should be enabled
    for tool in enabled_tools:
        assert tool.is_enabled is True


def test_filter_by_pattern():
    """Test pattern-based tool filtering."""
    register_all_callable_tools()
    registry = get_registry()

    # Find all file-related tools (file_read, file_finder, but NOT list_dir)
    file_tools = registry.filter_by_pattern("file_*")
    assert len(file_tools) == 2  # file_read, file_finder

    # Find all *_search tools
    search_tools = registry.filter_by_pattern("*_search")
    assert len(search_tools) == 4  # grep_search, glob_search, browser_search, multi_tab_search

    # Find all *_todos tools
    todo_tools = registry.filter_by_pattern("*_todos")
    assert len(todo_tools) == 3  # read_todos, write_todos, focus_todos


def test_tool_schemas_are_present():
    """Test that callable tools don't require ToolSchema (they use Pydantic directly)."""
    register_all_callable_tools()
    registry = get_registry()

    # Callable tools use Pydantic models directly, so schema can be None
    for tool in registry.tools:
        # Schema is optional for callable tools
        assert tool.schema is None or isinstance(tool.schema, dict)
