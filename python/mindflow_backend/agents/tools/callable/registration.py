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
from .browser import (
    BrowserSearchCallable,
    DeepPageScraperCallable,
    MultiTabSearchCallable,
)
from .llm import (
    LLMResearchSynthesisCallable,
    LLMQueryRefinementCallable,
)
from .planning import (
    TodoListReadCallable,
    TodoListWriteCallable,
    TodoListFocusCallable,
)
from .scratchpad import (
    ScratchpadReadCallable,
    ScratchpadWriteCallable,
)
from .memory import (
    StoreFactCallable,
    SearchFactsCallable,
    RetrieveTaskContextCallable,
    RecallSessionMemoryCallable,
)
from .orchestration import (
    AgentToolCallable,
    SendMessageCallable,
)

_logger = get_logger(__name__)


def _build_registration(tool, category: str) -> ToolRegistration:
    """Build registry metadata from a callable tool instance."""
    probe_input = tool.input_schema.model_construct() if getattr(tool, "input_schema", None) else None
    return ToolRegistration(
        name=tool.name,
        description=tool.description,
        schema=None,
        category=category,
        is_read_only=bool(tool.is_read_only(probe_input)) if probe_input is not None else False,
        is_concurrency_safe=bool(tool.is_concurrency_safe(probe_input))
        if probe_input is not None
        else False,
        is_destructive=bool(tool.is_destructive(probe_input)) if probe_input is not None else False,
        is_enabled=bool(tool.is_enabled()),
    )


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

    # Priority 6: Browser
    browser_tools = [
        (BrowserSearchCallable, "browser"),
        (WebScraperCallable, "browser"),
        (DeepPageScraperCallable, "browser"),
        (MultiTabSearchCallable, "browser"),
    ]

    # Priority 5: Planning + LLM
    planning_tools = [
        (TodoListReadCallable, "planning"),
        (TodoListWriteCallable, "planning"),
        (TodoListFocusCallable, "planning"),
        (LLMResearchSynthesisCallable, "llm"),
        (LLMQueryRefinementCallable, "llm"),
        (ScratchpadReadCallable, "planning"),
        (ScratchpadWriteCallable, "planning"),
    ]

    memory_tools = [
        (StoreFactCallable, "memory"),
        (SearchFactsCallable, "memory"),
        (RetrieveTaskContextCallable, "memory"),
        (RecallSessionMemoryCallable, "memory"),
    ]

    orchestration_tools = [
        (AgentToolCallable, "orchestration"),
        (SendMessageCallable, "orchestration"),
    ]

    # Combine all tools
    all_tools = (
        filesystem_readonly_tools
        + filesystem_write_tools
        + system_tools
        + web_tools
        + browser_tools
        + planning_tools
        + memory_tools
        + orchestration_tools
    )

    seen_names: set[str] = set()

    # Register each tool once, preserving the first category assignment.
    for tool, category in all_tools:
        if tool.name in seen_names:
            continue
        try:
            registration = _build_registration(tool, category)
            registry.register(registration)
            registered_count += 1
            seen_names.add(tool.name)
            _logger.debug(f"Registered callable tool: {tool.name} (category: {category})")
        except Exception as e:
            _logger.error(f"Failed to register tool {tool.name}: {e}")

    _logger.info(f"Registered {registered_count} callable tools across callable categories")
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
        "file_read", "list_dir", "file_finder", "grep_search", "glob_search",
        "write_file", "edit_file", "delete_file", "mkdir",
        # System
        "shell_execute", "system_info", "process_manager",
        # Web
        "http_client", "web_scraper", "api_client",
        # Browser
        "browser_search", "deep_page_scraper", "multi_tab_search",
        # Planning + LLM
        "read_todos", "write_todos", "focus_todos",
        "llm_research_synthesis", "llm_query_refinement",
        "read_scratchpad", "write_scratchpad",
        "store_fact", "search_facts", "retrieve_task_context", "recall_session_memory",
        "AgentTool", "SendMessage",
    ]

    for name in tool_names:
        try:
            registry.unregister(name)
            unregistered_count += 1
        except Exception as e:
            _logger.error(f"Failed to unregister tool {name}: {e}")

    _logger.info(f"Unregistered {unregistered_count} callable tools")
    return unregistered_count
