"""
Pydantic schemas 
for tool validation and metadata. Provides standardized schemas 
for tool parameters, results, and capabilities validation across the tool ecosystem. 
"""
 
from __future__ 
import annotations 
from typing 
import Any, Dict, List, Optional, Union 
from pydantic 
import BaseModel, Field 
from enum 
import Enum 
from mindflow_backend.schemas.orchestration.orchestrator 
import AgentType 
class ParameterType(str, Enum): 
"""
Supported parameter types 
for tools.
"""
 STRING = "string" INTEGER = "integer" FLOAT = "float" BOOLEAN = "boolean" ARRAY = "array" OBJECT = "object" FILE = "file" DIRECTORY = "directory" 
class ToolParameter(BaseModel): 
"""
Schema definition 
for a tool parameter.
"""
 name: str = Field(..., description="Parameter name") type: ParameterType = Field(..., description="Parameter data type") description: str = Field(..., description="Parameter description") required: bool = Field(default=False, description="Whether parameter is required") default: Optional[Any] = Field(default=None, description="Default value") enum: Optional[List[Any]] = Field(default=None, description="Allowed values") min_value: Optional[Union[int, float]] = Field(default=None, description="Minimum value") max_value: Optional[Union[int, float]] = Field(default=None, description="Maximum value") min_length: Optional[int] = Field(default=None, description="Minimum length") max_length: Optional[int] = Field(default=None, description="Maximum length") pattern: Optional[str] = Field(default=None, description="Regex pattern 
for validation") 
class Config: use_enum_values = True 
class ToolResult(BaseModel): 
"""
Standardized result format 
for tool execution.
"""
 success: bool = Field(..., description="Whether execution was successful") result: Optional[Any] = Field(default=None, description="Main result data") error: Optional[str] = Field(default=None, description="Error message 
if failed") metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata") tool_name: str = Field(..., description="Name of the tool that generated result") timestamp: str = Field(..., description="Execution timestamp") execution_time_ms: Optional[int] = Field(default=None, description="Execution time in milliseconds") 
class Config: json_encoders = { 
# Add custom encoders 
if needed } 
class ToolCapability(BaseModel): 
"""
Definition of a tool capability or requirement.
"""
 name: str = Field(..., description="Capability name") description: str = Field(..., description="Capability description") required: bool = Field(default=False, description="Whether this capability is required") version: Optional[str] = Field(default=None, description="Capability version") 
class ToolSchema(BaseModel): 
"""
Complete schema definition 
for a tool.
"""
 name: str = Field(..., description="Tool name") description: str = Field(..., description="Tool description") version: str = Field(default="1.0.0", description="Tool version") category: str = Field(..., description="Tool category (filesystem, web, code, etc.)") parameters: List[ToolParameter] = Field(default_factory=list, description="Tool parameters") returns: ToolResult = Field(..., description="Tool 
return schema") capabilities: List[ToolCapability] = Field(default_factory=list, description="Tool capabilities") 
# Requirements requires_backend: bool = Field(default=False, description="Requires backend integration") requires_sandbox: bool = Field(default=False, description="Requires sandbox execution") requires_internet: bool = Field(default=False, description="Requires internet access") 
# Agent permissions supported_agents: List[AgentType] = Field(default_factory=lambda: list(AgentType), description="Supported agent types") restricted_agents: List[AgentType] = Field(default_factory=list, description="Restricted agent types") 
# Performance characteristics async_execution: bool = Field(default=True, description="Supports async execution") stateful: bool = Field(default=False, description="Maintains state between calls") 
# Resource requirements memory_mb: Optional[int] = Field(default=None, description="Memory requirement in MB") timeout_seconds: Optional[int] = Field(default=None, description="Default timeout in seconds") 
# Security security_level: str = Field(default="medium", description="Security level (low, medium, high)") 
class Config: use_enum_values = True schema_extra = { "example": { "name": "file_reader", "description": "Read file contents", "parameters": [ { "name": "file_path", "type": "string", "description": "Path to file to read", "required": True } ], "returns": { "success": True, "result": "file contents", "tool_name": "file_reader", "timestamp": "2024-01-01T00:00:00" } } } 
class ToolRegistrySchema(BaseModel): 
"""
Schema 
for tool registry configuration.
"""
 name: str = Field(..., description="Registry name") version: str = Field(default="1.0.0", description="Registry version") 
# Tool storage tools: Dict[str, ToolSchema] = Field(default_factory=dict, description="Registered tools") tool_classes: Dict[str, str] = Field(default_factory=dict, description="Tool 
class paths") 
# Permissions default_permissions: List[AgentType] = Field( default_factory=lambda: list(AgentType), description="Default agent permissions" ) 
# Configuration auto_discovery: bool = Field(default=True, description="Enable auto-discovery of tools") validation_enabled: bool = Field(default=True, description="Enable schema validation") caching_enabled: bool = Field(default=True, description="Enable tool result caching") 
# Performance cache_ttl_seconds: int = Field(default=300, description="Cache TTL in seconds") max_concurrent_executions: int = Field(default=10, description="Max concurrent executions") 
class Config: use_enum_values = True 
class ToolExecutionContext(BaseModel): 
"""
Context information 
for tool execution.
"""
 tool_name: str = Field(..., description="Name of executing tool") agent_type: AgentType = Field(..., description="Type of agent executing tool") session_id: Optional[str] = Field(default=None, description="Session identifier") parameters: Dict[str, Any] = Field(default_factory=dict, description="Execution parameters") 
# Execution metadata request_id: Optional[str] = Field(default=None, description="Request identifier") parent_request_id: Optional[str] = Field(default=None, description="Parent request ID") 
# Security context sandbox_mode: Optional[str] = Field(default=None, description="Sandbox mode") permissions: List[str] = Field(default_factory=list, description="Granted permissions") 
# Performance tracking start_time: Optional[str] = Field(default=None, description="Execution start time") timeout_seconds: Optional[int] = Field(default=None, description="Execution timeout") 
class Config: use_enum_values = True 
class ToolValidationError(BaseModel): 
"""
Schema 
for tool validation errors.
"""
 tool_name: str = Field(..., description="Name of the tool") parameter_name: str = Field(..., description="Name of invalid parameter") error_type: str = Field(..., description="Type of validation error") error_message: str = Field(..., description="Detailed error message") provided_value: Any = Field(..., description="Value that caused validation error") expected_type: Optional[str] = Field(default=None, description="Expected type") 
class Config: use_enum_values = True 
# Utility functions 
for schema validation 
def create_parameter( name: str, param_type: ParameterType, description: str, required: bool = False, **kwargs ) -> ToolParameter: 
"""
Create a ToolParameter 
with common defaults. Args: name: Parameter name param_type: Parameter type description: Parameter description required: Whether parameter is required **kwargs: Additional parameter properties Returns: ToolParameter instance 
"""
 
return ToolParameter( name=name, type=param_type, description=description, required=required, **kwargs ) 
def create_tool_schema( name: str, description: str, category: str, parameters: List[ToolParameter], **kwargs ) -> ToolSchema: 
"""
Create a ToolSchema 
with common defaults. Args: name: Tool name description: Tool description category: Tool category parameters: List of tool parameters **kwargs: Additional schema properties Returns: ToolSchema instance 
"""
 
return ToolSchema( name=name, description=description, category=category, parameters=parameters, **kwargs )