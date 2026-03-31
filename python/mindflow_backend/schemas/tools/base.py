"""
Tool schema definitions for MindFlow agents. Provides standardized schema
structures for tool parameters, validation, and configuration.
"""

from __future__ import annotations

import builtins
from dataclasses import dataclass
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ParameterType(str, Enum):
    """Parameter type enumeration."""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"
    FILE = "file"


@dataclass
class ToolParameter:
    """Tool parameter definition."""
    name: str = Field(..., description="Parameter name")
    type: ParameterType = Field(..., description="Parameter data type")
    description: str = Field(..., description="Parameter description")
    required: bool = Field(default=False, description="Whether parameter is required")
    default: Any | None = Field(default=None, description="Default value")
    enum: list[Any] | None = Field(default=None, description="Allowed values")
    min_value: int | float | None = Field(default=None, description="Minimum value")
    max_value: int | float | None = Field(default=None, description="Maximum value")
    min_length: int | None = Field(default=None, description="Minimum length")
    max_length: int | None = Field(default=None, description="Maximum length")
    pattern: str | None = Field(default=None, description="Regex pattern")


@dataclass
class ToolSchema:
    """Tool schema definition."""
    name: str = Field(..., description="Tool name")
    description: str = Field(..., description="Tool description")
    category: str = Field(default="general", description="Tool category")
    version: str = Field(default="1.0.0", description="Tool version")
    parameters: list[ToolParameter] = Field(default_factory=list, description="Tool parameters")
    returns: builtins.dict[str, Any] = Field(default_factory=dict, description="Return value schema")
    examples: list[builtins.dict[str, Any]] = Field(default_factory=list, description="Usage examples")
    
    def dict(self) -> builtins.dict[str, Any]:
        """Convert schema to dictionary."""
        from dataclasses import asdict
        result = asdict(self)
        # Convert parameters to proper format
        result['parameters'] = [
            {
                'name': param.name,
                'type': param.type.value,
                'description': param.description,
                'required': param.required,
                'default': param.default,
                'enum': param.enum,
                'min_value': param.min_value,
                'max_value': param.max_value,
                'min_length': param.min_length,
                'max_length': param.max_length,
                'pattern': param.pattern
            }
            for param in self.parameters
        ]
        return result


class ToolResult(BaseModel):
    """Standard tool result format."""
    success: bool = Field(..., description="Whether execution was successful")
    result: Any | None = Field(default=None, description="Execution result")
    error: str | None = Field(default=None, description="Error message")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    timestamp: str = Field(..., description="Execution timestamp")


def create_tool_schema(
    name: str,
    description: str,
    category: str = "general",
    parameters: list[dict[str, Any]] | None = None,
    returns: dict[str, Any] | None = None,
    version: str = "1.0.0"
) -> ToolSchema:
    """
    Create a tool schema from parameters.
    Args:
        name: Tool name
        description: Tool description
        category: Tool category
        parameters: List of parameter dictionaries
        returns: Return value schema
        version: Tool version
    Returns:
        ToolSchema instance
    """
    tool_parameters = []
    
    if parameters:
        for param in parameters:
            tool_param = ToolParameter(
                name=param.get("name", ""),
                type=ParameterType(param.get("type", "string")),
                description=param.get("description", ""),
                required=param.get("required", False),
                default=param.get("default"),
                enum=param.get("enum"),
                min_value=param.get("min_value"),
                max_value=param.get("max_value"),
                min_length=param.get("min_length"),
                max_length=param.get("max_length"),
                pattern=param.get("pattern")
            )
            tool_parameters.append(tool_param)

    return ToolSchema(
        name=name,
        description=description,
        category=category,
        parameters=tool_parameters,
        returns=returns or {},
        version=version
    )


def create_parameter(
    name: str,
    param_type: ParameterType,
    description: str,
    required: bool = False,
    default: Any | None = None,
    enum: list[Any] | None = None,
    min_value: int | float | None = None,
    max_value: int | float | None = None,
    min_length: int | None = None,
    max_length: int | None = None,
    pattern: str | None = None
) -> ToolParameter:
    """
    Create a tool parameter.
    Args:
        name: Parameter name
        param_type: Parameter type
        description: Parameter description
        required: Whether parameter is required
        default: Default value
        enum: Allowed values
        min_value: Minimum value
        max_value: Maximum value
        min_length: Minimum length
        max_length: Maximum length
        pattern: Regex pattern
    Returns:
        ToolParameter instance
    """
    return ToolParameter(
        name=name,
        type=param_type,
        description=description,
        required=required,
        default=default,
        enum=enum,
        min_value=min_value,
        max_value=max_value,
        min_length=min_length,
        max_length=max_length,
        pattern=pattern
    )


def validate_tool_parameters(
    parameters: dict[str, Any],
    schema: ToolSchema
) -> dict[str, Any]:
    """
    Validate parameters against a tool schema.
    Args:
        parameters: Parameters to validate
        schema: Tool schema to validate against
    Returns:
        Dictionary with validation result
    """
    errors = []
    validated_params = {}

    for param_schema in schema.parameters:
        param_name = param_schema.name
        param_value = parameters.get(param_name)

        # Check required parameters
        if param_schema.required and param_value is None:
            errors.append(f"Required parameter '{param_name}' is missing")
            continue

        # Skip validation if parameter not provided and not required
        if param_value is None and not param_schema.required:
            continue

        # Type validation
        if param_schema.type == ParameterType.STRING:
            if not isinstance(param_value, str):
                errors.append(f"Parameter '{param_name}' must be a string")
            else:
                # Length validation
                if param_schema.min_length and len(param_value) < param_schema.min_length:
                    errors.append(f"Parameter '{param_name}' must be at least {param_schema.min_length} characters")
                if param_schema.max_length and len(param_value) > param_schema.max_length:
                    errors.append(f"Parameter '{param_name}' must be at most {param_schema.max_length} characters")
                
                # Pattern validation
                if param_schema.pattern:
                    import re
                    if not re.match(param_schema.pattern, param_value):
                        errors.append(f"Parameter '{param_name}' does not match required pattern")

        elif param_schema.type == ParameterType.INTEGER:
            if not isinstance(param_value, int):
                errors.append(f"Parameter '{param_name}' must be an integer")
            else:
                # Range validation
                if param_schema.min_value is not None and param_value < param_schema.min_value:
                    errors.append(f"Parameter '{param_name}' must be at least {param_schema.min_value}")
                if param_schema.max_value is not None and param_value > param_schema.max_value:
                    errors.append(f"Parameter '{param_name}' must be at most {param_schema.max_value}")

        elif param_schema.type == ParameterType.FLOAT:
            if not isinstance(param_value, (int, float)):
                errors.append(f"Parameter '{param_name}' must be a number")
            else:
                # Range validation
                if param_schema.min_value is not None and param_value < param_schema.min_value:
                    errors.append(f"Parameter '{param_name}' must be at least {param_schema.min_value}")
                if param_schema.max_value is not None and param_value > param_schema.max_value:
                    errors.append(f"Parameter '{param_name}' must be at most {param_schema.max_value}")

        elif param_schema.type == ParameterType.BOOLEAN:
            if not isinstance(param_value, bool):
                errors.append(f"Parameter '{param_name}' must be a boolean")

        elif param_schema.type == ParameterType.ARRAY:
            if not isinstance(param_value, list):
                errors.append(f"Parameter '{param_name}' must be an array")

        elif param_schema.type == ParameterType.OBJECT:
            if not isinstance(param_value, dict):
                errors.append(f"Parameter '{param_name}' must be an object")

        # Enum validation
        if param_schema.enum and param_value not in param_schema.enum:
            errors.append(f"Parameter '{param_name}' must be one of: {param_schema.enum}")

        validated_params[param_name] = param_value

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "parameters": validated_params
    }
