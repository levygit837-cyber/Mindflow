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
]
