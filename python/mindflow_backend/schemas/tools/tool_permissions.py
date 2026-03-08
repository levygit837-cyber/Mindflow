"""Tool permission schemas for MindFlow backend.

Provides schemas for tool access control, security constraints,
and permission management.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set
from pydantic import BaseModel, Field, validator

from mindflow_backend.schemas.orchestration.orchestrator import AgentType


class ToolPermission(BaseModel):
    """Permission definition for tool access control."""
    
    tool_name: str = Field(..., description="Tool name this permission applies to")
    required_level: str = Field(default="basic", description="Required permission level")
    allowed_agents: List[AgentType] = Field(default_factory=lambda: list(AgentType), description="Allowed agent types")
    restricted_agents: List[AgentType] = Field(default_factory=list, description="Restricted agent types")
    resource_requirements: Dict[str, Any] = Field(default_factory=dict, description="Resource requirements")
    security_constraints: Optional[Dict[str, Any]] = Field(default=None, description="Security constraints")
    time_restrictions: Optional[Dict[str, Any]] = Field(default=None, description="Time-based restrictions")
    rate_limits: Optional[Dict[str, Any]] = Field(default=None, description="Rate limiting constraints")
    
    class Config:
        use_enum_values = True


class SecurityConstraint(BaseModel):
    """Security constraint for tool execution."""
    
    constraint_type: str = Field(..., description="Type of constraint")
    parameters: Dict[str, Any] = Field(..., description="Constraint parameters")
    enforcement_level: str = Field(default="strict", description="Enforcement level")
    description: Optional[str] = Field(default=None, description="Constraint description")
    
    class Config:
        use_enum_values = True


class PathSecurityConstraint(SecurityConstraint):
    """Path-based security constraint."""
    
    allowed_paths: List[str] = Field(default_factory=list, description="Allowed file paths")
    forbidden_paths: List[str] = Field(default_factory=list, description="Forbidden file paths")
    path_patterns: List[str] = Field(default_factory=list, description="Path patterns (regex)")
    max_file_size_mb: Optional[int] = Field(default=None, description="Maximum file size in MB")
    read_only: bool = Field(default=False, description="Read-only access")
    require_confirmation: bool = Field(default=False, description="Require user confirmation")
    
    def __init__(self, **data):
        data.setdefault("constraint_type", "path_security")
        super().__init__(**data)


class NetworkSecurityConstraint(SecurityConstraint):
    """Network-based security constraint."""
    
    allowed_domains: List[str] = Field(default_factory=list, description="Allowed domains")
    forbidden_domains: List[str] = Field(default_factory=list, description="Forbidden domains")
    allowed_ports: List[int] = Field(default_factory=list, description="Allowed ports")
    max_request_size_mb: Optional[int] = Field(default=None, description="Maximum request size in MB")
    require_https: bool = Field(default=True, description="Require HTTPS")
    timeout_seconds: Optional[int] = Field(default=None, description="Request timeout")
    
    def __init__(self, **data):
        data.setdefault("constraint_type", "network_security")
        super().__init__(**data)


class ResourceConstraint(BaseModel):
    """Resource usage constraint."""
    
    resource_type: str = Field(..., description="Type of resource (cpu, memory, disk, network)")
    max_amount: Optional[float] = Field(default=None, description="Maximum amount allowed")
    time_window_seconds: Optional[int] = Field(default=None, description="Time window for limit")
    per_agent: bool = Field(default=True, description="Apply limit per agent")
    per_session: bool = Field(default=False, description="Apply limit per session")
    burst_allowed: bool = Field(default=False, description="Allow burst usage")
    
    class Config:
        use_enum_values = True


class RateLimit(BaseModel):
    """Rate limiting constraint."""
    
    max_requests: int = Field(..., description="Maximum number of requests")
    time_window_seconds: int = Field(..., description="Time window in seconds")
    per_agent: bool = Field(default=True, description="Apply per agent")
    per_tool: bool = Field(default=False, description="Apply per tool")
    per_user: bool = Field(default=False, description="Apply per user")
    burst_size: Optional[int] = Field(default=None, description="Burst size")
    
    class Config:
        use_enum_values = True


class TimeRestriction(BaseModel):
    """Time-based access restriction."""
    
    allowed_hours: Optional[List[int]] = Field(default=None, description="Allowed hours (0-23)")
    allowed_days: Optional[List[int]] = Field(default=None, description="Allowed days (0-6, 0=Monday)")
    timezone: str = Field(default="UTC", description="Timezone for restrictions")
    start_date: Optional[str] = Field(default=None, description="Start date (ISO format)")
    end_date: Optional[str] = Field(default=None, description="End date (ISO format)")
    holidays_excluded: bool = Field(default=False, description="Exclude holidays")
    
    class Config:
        use_enum_values = True


class ToolPermissionSet(BaseModel):
    """Set of permissions for a tool."""
    
    tool_name: str = Field(..., description="Tool name")
    permissions: List[ToolPermission] = Field(..., description="Permission rules")
    default_permission: str = Field(default="deny", description="Default permission")
    priority: int = Field(default=0, description="Priority for conflict resolution")
    
    class Config:
        use_enum_values = True


class PermissionAuditLog(BaseModel):
    """Audit log entry for permission checks."""
    
    timestamp: str = Field(..., description="Timestamp of permission check")
    tool_name: str = Field(..., description="Tool name")
    agent_type: AgentType = Field(..., description="Agent type")
    user_id: Optional[str] = Field(default=None, description="User identifier")
    session_id: Optional[str] = Field(default=None, description="Session identifier")
    action: str = Field(..., description="Action attempted")
    granted: bool = Field(..., description="Whether permission was granted")
    reason: Optional[str] = Field(default=None, description="Reason for decision")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Action parameters")
    execution_time_ms: int = Field(default=0, description="Permission check time")
    
    class Config:
        use_enum_values = True


def create_basic_permission(
    tool_name: str,
    allowed_agents: Optional[List[AgentType]] = None,
    **kwargs
) -> ToolPermission:
    """Create a basic tool permission.
    
    Args:
        tool_name: Tool name
        allowed_agents: List of allowed agent types
        **kwargs: Additional permission properties
        
    Returns:
        ToolPermission instance
    """
    return ToolPermission(
        tool_name=tool_name,
        allowed_agents=allowed_agents or list(AgentType),
        **kwargs
    )


def create_restricted_permission(
    tool_name: str,
    allowed_agents: List[AgentType],
    security_constraints: Optional[Dict[str, Any]] = None,
    **kwargs
) -> ToolPermission:
    """Create a restricted tool permission.
    
    Args:
        tool_name: Tool name
        allowed_agents: List of allowed agent types
        security_constraints: Security constraints
        **kwargs: Additional permission properties
        
    Returns:
        ToolPermission instance
    """
    return ToolPermission(
        tool_name=tool_name,
        allowed_agents=allowed_agents,
        required_level="restricted",
        security_constraints=security_constraints,
        **kwargs
    )


def create_path_constraint(
    allowed_paths: Optional[List[str]] = None,
    forbidden_paths: Optional[List[str]] = None,
    **kwargs
) -> PathSecurityConstraint:
    """Create a path security constraint.
    
    Args:
        allowed_paths: List of allowed paths
        forbidden_paths: List of forbidden paths
        **kwargs: Additional constraint properties
        
    Returns:
        PathSecurityConstraint instance
    """
    return PathSecurityConstraint(
        allowed_paths=allowed_paths or [],
        forbidden_paths=forbidden_paths or [],
        **kwargs
    )


def create_rate_limit(
    max_requests: int,
    time_window_seconds: int,
    **kwargs
) -> RateLimit:
    """Create a rate limit constraint.
    
    Args:
        max_requests: Maximum number of requests
        time_window_seconds: Time window in seconds
        **kwargs: Additional rate limit properties
        
    Returns:
        RateLimit instance
    """
    return RateLimit(
        max_requests=max_requests,
        time_window_seconds=time_window_seconds,
        **kwargs
    )
