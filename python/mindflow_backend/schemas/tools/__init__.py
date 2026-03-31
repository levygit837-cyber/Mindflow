"""Schemas for tool management in MindFlow backend.

Provides standardized schemas for tool configuration,
execution, permissions, and model management.
"""

from __future__ import annotations

from .code_schemas import (
    CODE_SCHEMAS,
    GITNEXUS_CONTEXT_SCHEMA,
    GITNEXUS_IMPACT_SCHEMA,
    GITNEXUS_QUERY_SCHEMA,
    GITNEXUS_STATUS_SCHEMA,
)
from .data_schemas import CSV_PROCESSOR_SCHEMA, DATA_SCHEMAS, DATABASE_SCHEMA
from .filesystem_schemas import (
    DELETE_FILE_SCHEMA,
    EDIT_FILE_SCHEMA,
    FILE_FINDER_SCHEMA,
    FILESYSTEM_SCHEMAS,
    GLOB_SEARCH_SCHEMA,
    GREP_SEARCH_SCHEMA,
    LIST_DIRECTORY_SCHEMA,
    READ_FILE_SCHEMA,
    WRITE_FILE_SCHEMA,
)
from .integration_schemas import DOCKER_SCHEMA, GIT_SCHEMA, INTEGRATION_SCHEMAS

# Model configuration schemas
from .model_config import (
    ModelConfig,
    ModelInfo,
    ModelLoadConfig,
    ModelPerformanceMetrics,
    ModelRecommendation,
    ModelRequirement,
    SystemInfo,
    create_model_config,
    create_model_info,
    create_recommendation,
)
from .pinchtab_schemas import (
    PINCHTAB_BROWSER_SCHEMA,
    PINCHTAB_FLEET_SCHEMA,
    PINCHTAB_SCHEMAS,
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
    PinchTabBrowserProfile,
    ReconcileFleetResponse,
)
from .planning import (
    FOCUS_TODOS_SCHEMA,
    READ_TODOS_SCHEMA,
    WRITE_TODOS_SCHEMA,
    TodoItemContract,
    TodoItemStatus,
    TodoListContract,
    TodoListFocusResponse,
    TodoListReadResponse,
    TodoListSummary,
    TodoListWriteRequest,
)
from .shell_tabs import (
    SHELL_TAB_CLOSE_SCHEMA,
    SHELL_TAB_EXEC_SCHEMA,
    SHELL_TAB_LIST_SCHEMA,
    SHELL_TAB_OPEN_SCHEMA,
    SHELL_TAB_READ_SCHEMA,
    SHELL_TAB_STATUS_SCHEMA,
    ShellTabContract,
    ShellTabCreateRequest,
    ShellTabExecRequest,
    ShellTabSnapshot,
    ShellTabState,
    ShellTabStatusResponse,
)
from .system_schemas import (
    PROCESS_MANAGER_SCHEMA,
    RESOURCE_MONITOR_SCHEMA,
    SANDBOX_SCHEMA,
    SHELL_EXECUTOR_SCHEMA,
    SYSTEM_INFO_SCHEMA,
    SYSTEM_SCHEMAS,
)

# Tool configuration schemas
from .tool_config import (
    ToolCategoryConfig,
    ToolConfig,
    ToolParameter,
    ToolRegistrySchema,
    ToolSchema,
    create_tool_schema,
)

# Tool execution schemas
from .tool_execution import (
    ToolCacheEntry,
    ToolExecutionBatch,
    ToolExecutionBatchResult,
    ToolExecutionContext,
    ToolExecutionRequest,
    ToolExecutionResult,
    ToolExecutionStats,
    create_execution_context,
    create_execution_result,
)

# Tool permission schemas
from .tool_permissions import (
    NetworkSecurityConstraint,
    PathSecurityConstraint,
    PermissionAuditLog,
    RateLimit,
    ResourceConstraint,
    SecurityConstraint,
    TimeRestriction,
    ToolPermission,
    ToolPermissionSet,
    create_basic_permission,
    create_path_constraint,
    create_rate_limit,
    create_restricted_permission,
)

# Category-specific schemas
from .web_schemas import (
    API_CLIENT_SCHEMA,
    BROWSER_SEARCH_SCHEMA,
    HTTP_CLIENT_SCHEMA,
    WEB_SCHEMAS,
    WEB_SCRAPER_SCHEMA,
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
