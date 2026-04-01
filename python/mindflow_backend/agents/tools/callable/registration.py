"""Registration module for callable tools.

Registers all Phase 2 callable tools with the central tool registry.
This module should be imported during application startup to populate
the registry with all available callable tools.
"""

from __future__ import annotations

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.schemas.tools.registry import ToolRegistration, get_registry

# Import all callable tools
from .filesystem import (
    FileReadCallable,
    DirectoryListCallable,
    FileFinderCallable,
    GrepSearchCallable,
    GlobSearchCallable,
    FileWriteCallable,
    FileEditCallable,
    FileDeleteCallable,
    DirectoryCreateCallable,
)
from .shell import (
    ShellExecutorCallable,
    SystemInfoCallable,
    ProcessManagerCallable,
)
from .web import (
    HttpClientCallable,
    WebScraperCallable,
    ApiClientCallable,
)
from .planning import (
    TodoListReadCallable,
    TodoListWriteCallable,
    TodoListFocusCallable,
)

_logger = get_logger(__name__)


def register_all_callable_tools() -> int:
    """Register all callable tools with the central registry.

    Returns:
        Number of tools registered
    """
    registry = get_registry()
    registered_count = 0

    # Priority 1: Filesystem (Read-Only)
    filesystem_readonly_tools = [
        (FileReadCallable, "filesystem"),
        (DirectoryListCallable, "filesystem"),
        (FileFinderCallable, "filesystem"),
        (GrepSearchCallable, "filesystem"),
        (GlobSearchCallable, "filesystem"),
    ]

    # Priority 2: Filesystem (Write)
    filesystem_write_tools = [
        (FileWriteCallable, "filesystem"),
        (FileEditCallable, "filesystem"),
        (FileDeleteCallable, "filesystem"),
        (DirectoryCreateCallable, "filesystem"),
    ]

    # Priority 3: System
    system_tools = [
        (ShellExecutorCallable, "system"),
        (SystemInfoCallable, "system"),
        (ProcessManagerCallable, "system"),
    ]

    # Priority 4: Web
    web_tools = [
        (HttpClientCallable, "web"),
        (WebScraperCallable, "web"),
        (ApiClientCallable, "web"),
    ]

    # Priority 5: Planning
    planning_tools = [
        (TodoListReadCallable, "planning"),
        (TodoListWriteCallable, "planning"),
        (TodoListFocusCallable, "planning"),
    ]

    # Combine all tools
    all_tools = (
        filesystem_readonly_tools
        + filesystem_write_tools
        + system_tools
        + web_tools
        + planning_tools
    )

    # Register each tool
    for tool, category in all_tools:
        try:
            registration = ToolRegistration(
                name=tool.name,
                description=tool.description,
                schema=tool.input_schema.model_json_schema() if tool.input_schema else None,
                category=category,
                is_read_only=tool.is_read_only,
                is_concurrency_safe=tool.is_concurrency_safe,
                is_destructive=tool.is_destructive,
                is_enabled=tool.is_enabled,
            )
            registry.register(registration)
            registered_count += 1
            _logger.debug(f"Registered callable tool: {tool.name} (category: {category})")
        except Exception as e:
            _logger.error(f"Failed to register tool {tool.name}: {e}")

    _logger.info(f"Registered {registered_count} callable tools across 5 categories")
    return registered_count


def unregister_all_callable_tools() -> int:
    """Unregister all callable tools from the registry.

    Useful for testing or cleanup.

    Returns:
        Number of tools unregistered
    """
    registry = get_registry()
    unregistered_count = 0

    tool_names = [
        # Filesystem
        "file_read", "directory_list", "file_finder", "grep_search", "glob_search",
        "file_write", "file_edit", "file_delete", "directory_create",
        # System
        "shell_executor", "system_info", "process_manager",
        # Web
        "http_client", "web_scraper", "api_client",
        # Planning
        "read_todos", "write_todos", "focus_todos",
    ]

    for name in tool_names:
        try:
            registry.unregister(name)
            unregistered_count += 1
        except Exception as e:
            _logger.error(f"Failed to unregister tool {name}: {e}")

    _logger.info(f"Unregistered {unregistered_count} callable tools")
    return unregistered_count
