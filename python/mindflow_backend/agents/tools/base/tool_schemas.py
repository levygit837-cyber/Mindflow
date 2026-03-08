"""
Tool schema definitions for MindFlow agents. Provides standardized schema
structures for tool parameters, validation, and configuration.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, Union, Literal
from enum import Enum
from dataclasses import dataclass, field
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
    default: Optional[Any] = Field(default=None, description="Default value")
    enum: Optional[List[Any]] = Field(default=None, description="Allowed values")
    min_value: Optional[Union[int, float]] = Field(default=None, description="Minimum value")
    max_value: Optional[Union[int, float]] = Field(default=None, description="Maximum value")
    min_length: Optional[int] = Field(default=None, description="Minimum length")
    max_length: Optional[int] = Field(default=None, description="Maximum length")
    pattern: Optional[str] = Field(default=None, description="Regex pattern")


@dataclass
class ToolSchema:
    """Tool schema definition."""
    name: str = Field(..., description="Tool name")
    description: str = Field(..., description="Tool description")
    category: str = Field(default="general", description="Tool category")
    version: str = Field(default="1.0.0", description="Tool version")
    parameters: List[ToolParameter] = Field(default_factory=list, description="Tool parameters")
    returns: Dict[str, Any] = Field(default_factory=dict, description="Return value schema")
    examples: List[Dict[str, Any]] = Field(default_factory=list, description="Usage examples")
    
    def dict(self) -> Dict[str, Any]:
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
    result: Optional[Any] = Field(default=None, description="Execution result")
    error: Optional[str] = Field(default=None, description="Error message")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    timestamp: str = Field(..., description="Execution timestamp")


def create_tool_schema(
    name: str,
    description: str,
    category: str = "general",
    parameters: Optional[List[Dict[str, Any]]] = None,
    returns: Optional[Dict[str, Any]] = None,
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
    default: Optional[Any] = None,
    enum: Optional[List[Any]] = None,
    min_value: Optional[Union[int, float]] = None,
    max_value: Optional[Union[int, float]] = None,
    min_length: Optional[int] = None,
    max_length: Optional[int] = None,
    pattern: Optional[str] = None
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
    parameters: Dict[str, Any],
    schema: ToolSchema
) -> Dict[str, Any]:
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
