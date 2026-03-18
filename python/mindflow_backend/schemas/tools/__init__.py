"""Schemas for tool management in MindFlow backend.

Provides standardized schemas for tool configuration,
execution, permissions, and model management.
"""

from __future__ import annotations

# Tool configuration schemas
from .tool_config import (
    ToolParameter,
    ToolSchema,
    ToolRegistrySchema,
    ToolConfig,
    ToolCategoryConfig,
    create_tool_schema,
)

# Tool execution schemas
from .tool_execution import (
    ToolExecutionContext,
    ToolExecutionResult,
    ToolExecutionStats,
    ToolExecutionRequest,
    ToolExecutionBatch,
    ToolExecutionBatchResult,
    ToolCacheEntry,
    create_execution_context,
    create_execution_result,
)

# Tool permission schemas
from .tool_permissions import (
    ToolPermission,
    SecurityConstraint,
    PathSecurityConstraint,
    NetworkSecurityConstraint,
    ResourceConstraint,
    RateLimit,
    TimeRestriction,
    ToolPermissionSet,
    PermissionAuditLog,
    create_basic_permission,
    create_restricted_permission,
    create_path_constraint,
    create_rate_limit,
)

# Model configuration schemas
from .model_config import (
    ModelInfo,
    SystemInfo,
    ModelRequirement,
    ModelConfig,
    ModelRecommendation,
    ModelPerformanceMetrics,
    ModelLoadConfig,
    create_model_info,
    create_model_config,
    create_recommendation,
)

# Category-specific schemas
from .web_schemas import (
    API_CLIENT_SCHEMA,
    HTTP_CLIENT_SCHEMA,
    WEB_SCRAPER_SCHEMA,
    BROWSER_SEARCH_SCHEMA,
    WEB_SCHEMAS
)
from .system_schemas import (
    PROCESS_MANAGER_SCHEMA,
    RESOURCE_MONITOR_SCHEMA,
    SANDBOX_SCHEMA,
    SHELL_EXECUTOR_SCHEMA,
    SYSTEM_INFO_SCHEMA,
    SYSTEM_SCHEMAS
)
from .filesystem_schemas import (
    READ_FILE_SCHEMA,
    WRITE_FILE_SCHEMA,
    EDIT_FILE_SCHEMA,
    DELETE_FILE_SCHEMA,
    LIST_DIRECTORY_SCHEMA,
    GREP_SEARCH_SCHEMA,
    GLOB_SEARCH_SCHEMA,
    FILE_FINDER_SCHEMA,
    FILESYSTEM_SCHEMAS
)
from .integration_schemas import (
    GIT_SCHEMA,
    DOCKER_SCHEMA,
    INTEGRATION_SCHEMAS
)
from .data_schemas import (
    DATABASE_SCHEMA,
    CSV_PROCESSOR_SCHEMA,
    DATA_SCHEMAS
)
from .code_schemas import (
    GITNEXUS_STATUS_SCHEMA,
    GITNEXUS_QUERY_SCHEMA,
    GITNEXUS_CONTEXT_SCHEMA,
    GITNEXUS_IMPACT_SCHEMA,
    CODE_SCHEMAS,
)
from .shell_tabs import (
    ShellTabState,
    ShellTabContract,
    ShellTabSnapshot,
    ShellTabStatusResponse,
    ShellTabCreateRequest,
    ShellTabExecRequest,
    SHELL_TAB_OPEN_SCHEMA,
    SHELL_TAB_LIST_SCHEMA,
    SHELL_TAB_STATUS_SCHEMA,
    SHELL_TAB_EXEC_SCHEMA,
    SHELL_TAB_READ_SCHEMA,
    SHELL_TAB_CLOSE_SCHEMA,
)
from .planning import (
    TodoItemStatus,
    TodoItemContract,
    TodoListContract,
    TodoListSummary,
    TodoListWriteRequest,
    TodoListReadResponse,
    TodoListFocusResponse,
    WRITE_TODOS_SCHEMA,
    READ_TODOS_SCHEMA,
    FOCUS_TODOS_SCHEMA,
)
from .pinchtab_schemas import (
    BrowserCommandAction,
    BrowserCommandRequest,
    BrowserCommandResponse,
    BrowserEconomyMode,
    BrowserInstanceState,
    BrowserOwnershipScope,
    BrowserRuntimeState,
    CreateBrowserRequest,
    CreateBrowserResponse,
    ListBrowsersRequest,
    ListBrowsersResponse,
    PINCHTAB_BROWSER_SCHEMA,
    PINCHTAB_FLEET_SCHEMA,
    PINCHTAB_SCHEMAS,
    PinchTabBrowserProfile,
    ReconcileFleetResponse,
)

__all__ = [
    # Tool configuration
    "ToolParameter",
    "ToolSchema",
    "ToolRegistrySchema", 
    "ToolConfig",
    "ToolCategoryConfig",
    "create_tool_schema",
    
    # Tool execution
    "ToolExecutionContext",
    "ToolExecutionResult",
    "ToolExecutionStats",
    "ToolExecutionRequest",
    "ToolExecutionBatch",
    "ToolExecutionBatchResult",
    "ToolCacheEntry",
    "create_execution_context",
    "create_execution_result",
    
    # Tool permissions
    "ToolPermission",
    "SecurityConstraint",
    "PathSecurityConstraint",
    "NetworkSecurityConstraint", 
    "ResourceConstraint",
    "RateLimit",
    "TimeRestriction",
    "ToolPermissionSet",
    "PermissionAuditLog",
    "create_basic_permission",
    "create_restricted_permission",
    "create_path_constraint",
    "create_rate_limit",
    
    # Model configuration
    "ModelInfo",
    "SystemInfo",
    "ModelRequirement",
    "ModelConfig",
    "ModelRecommendation",
    "ModelPerformanceMetrics",
    "ModelLoadConfig",
    "create_model_info",
    "create_model_config",
    "create_recommendation",
    
    # Category-specific schemas
    "API_CLIENT_SCHEMA",
    "HTTP_CLIENT_SCHEMA",
    "WEB_SCRAPER_SCHEMA",
    "BROWSER_SEARCH_SCHEMA",
    "WEB_SCHEMAS",
    "PROCESS_MANAGER_SCHEMA",
    "RESOURCE_MONITOR_SCHEMA",
    "SANDBOX_SCHEMA",
    "SHELL_EXECUTOR_SCHEMA",
    "SYSTEM_INFO_SCHEMA",
    "SYSTEM_SCHEMAS",
    "READ_FILE_SCHEMA",
    "WRITE_FILE_SCHEMA",
    "EDIT_FILE_SCHEMA",
    "DELETE_FILE_SCHEMA",
    "LIST_DIRECTORY_SCHEMA",
    "GREP_SEARCH_SCHEMA",
    "GLOB_SEARCH_SCHEMA",
    "FILE_FINDER_SCHEMA",
    "FILESYSTEM_SCHEMAS",
    "GIT_SCHEMA",
    "DOCKER_SCHEMA",
    "INTEGRATION_SCHEMAS",
    "DATABASE_SCHEMA",
    "CSV_PROCESSOR_SCHEMA",
    "DATA_SCHEMAS",
    "GITNEXUS_STATUS_SCHEMA",
    "GITNEXUS_QUERY_SCHEMA",
    "GITNEXUS_CONTEXT_SCHEMA",
    "GITNEXUS_IMPACT_SCHEMA",
    "CODE_SCHEMAS",
    "ShellTabState",
    "ShellTabContract",
    "ShellTabSnapshot",
    "ShellTabStatusResponse",
    "ShellTabCreateRequest",
    "ShellTabExecRequest",
    "SHELL_TAB_OPEN_SCHEMA",
    "SHELL_TAB_LIST_SCHEMA",
    "SHELL_TAB_STATUS_SCHEMA",
    "SHELL_TAB_EXEC_SCHEMA",
    "SHELL_TAB_READ_SCHEMA",
    "SHELL_TAB_CLOSE_SCHEMA",
    "TodoItemStatus",
    "TodoItemContract",
    "TodoListContract",
    "TodoListSummary",
    "TodoListWriteRequest",
    "TodoListReadResponse",
    "TodoListFocusResponse",
    "WRITE_TODOS_SCHEMA",
    "READ_TODOS_SCHEMA",
    "FOCUS_TODOS_SCHEMA",
    "BrowserCommandAction",
    "BrowserCommandRequest",
    "BrowserCommandResponse",
    "BrowserEconomyMode",
    "BrowserInstanceState",
    "BrowserOwnershipScope",
    "BrowserRuntimeState",
    "CreateBrowserRequest",
    "CreateBrowserResponse",
    "ListBrowsersRequest",
    "ListBrowsersResponse",
    "PINCHTAB_BROWSER_SCHEMA",
    "PINCHTAB_FLEET_SCHEMA",
    "PINCHTAB_SCHEMAS",
    "PinchTabBrowserProfile",
    "ReconcileFleetResponse",
]
