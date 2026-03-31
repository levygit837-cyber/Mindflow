"""Tool schema definitions for MindFlow agents.

Refactored to follow Claude Code CLI patterns:
- Pure Pydantic BaseModel (no @dataclass mixing)
- Automatic validation via model_validate()
- ToolSchema generates JSON schema for LLM tool definitions
- Helper functions for quick schema building

Previously: mixed @dataclass + Pydantic, manual validation loop.
Now: All Pydantic, automatic validation, proper schema generation.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ParameterType(StrEnum):
    """Parameter type enumeration — maps to JSON Schema types."""

    STRING = "string"
    INTEGER = "integer"
    FLOAT = "number"    # JSON Schema uses "number" for floats
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"
    FILE = "string"     # Files are path strings in schemas


# ---------------------------------------------------------------------------
# Tool Parameter Schema
# ---------------------------------------------------------------------------


class ToolParameterSchema(BaseModel):
    """A single parameter definition for a tool.

    Uses Pydantic for automatic validation and JSON Schema generation.
    """

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    name: str = Field(..., description="Parameter name")
    type: ParameterType = Field(..., description="Parameter data type")
    description: str = Field(default="", description="Parameter description")
    required: bool = Field(default=False, description="Whether parameter is required")
    default: Any | None = Field(default=None, description="Default value")
    enum: list[Any] | None = Field(default=None, description="Allowed values")
    min_value: float | None = Field(default=None, description="Minimum value (numbers)")
    max_value: float | None = Field(default=None, description="Maximum value (numbers)")
    min_length: int | None = Field(default=None, description="Minimum length (strings/arrays)")
    max_length: int | None = Field(default=None, description="Maximum length (strings/arrays)")
    pattern: str | None = Field(default=None, description="Regex pattern (strings)")

    def to_json_schema_property(self) -> dict[str, Any]:
        """Convert to a JSON Schema property definition."""
        prop: dict[str, Any] = {
            "type": self.type.value,
        }

        if self.description:
            prop["description"] = self.description

        if self.enum is not None:
            prop["enum"] = self.enum

        # Numeric constraints
        if self.min_value is not None:
            prop["minimum"] = self.min_value
        if self.max_value is not None:
            prop["maximum"] = self.max_value

        # String/array constraints
        if self.min_length is not None:
            prop["minLength"] = self.min_length
        if self.max_length is not None:
            prop["maxLength"] = self.max_length

        # Pattern (strings only)
        if self.pattern:
            prop["pattern"] = self.pattern

        return prop


# ---------------------------------------------------------------------------
# Tool Schema
# ---------------------------------------------------------------------------


class ToolSchema(BaseModel):
    """Tool input schema with parameter definitions.

    Mirrors Claude Code's inputSchema pattern — defines what parameters
    a tool accepts, with validation rules. Use generate_json_schema()
    to produce a JSON Schema for LLM tool definitions.
    """

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    name: str = Field(..., description="Tool name")
    description: str = Field(..., description="Tool description")
    category: str = Field(default="general", description="Tool category")
    version: str = Field(default="1.0.0", description="Tool version")
    parameters: list[ToolParameterSchema] = Field(
        default_factory=list,
        description="Tool parameters",
    )
    return_description: str = Field(
        default="",
        description="Description of what the tool returns",
    )
    examples: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Usage examples",
    )

    def generate_json_schema(self) -> dict[str, Any]:
        """Generate a JSON Schema from parameters.

        Compatible with OpenAI function calling and Anthropic tool use.
        """
        properties: dict[str, Any] = {}
        required: list[str] = []

        for param in self.parameters:
            properties[param.name] = param.to_json_schema_property()
            if param.required:
                required.append(param.name)

        schema: dict[str, Any] = {
            "type": "object",
            "properties": properties,
        }
        if required:
            schema["required"] = required

        return schema

    def validate_parameters(self, values: dict[str, Any]) -> dict[str, Any]:
        """Validate a dict of parameters against this schema.

        Replaces the old validate_tool_parameters() procedural approach.
        Returns a dict with validated params or raises ValueError.
        """
        errors: list[str] = []
        validated: dict[str, Any] = {}
        required_names = {p.name for p in self.parameters if p.required}
        param_map = {p.name: p for p in self.parameters}

        # Check required parameters
        for name in required_names:
            if name not in values or values[name] is None:
                errors.append(f"Required parameter '{name}' is missing")

        # Validate provided values
        for name, value in values.items():
            if name not in param_map:
                validated[name] = value  # Pass through extra params
                continue

            param = param_map[name]

            # Skip None for non-required
            if value is None and not param.required:
                continue

            # Type validation
            if param.type == ParameterType.STRING:
                if not isinstance(value, str):
                    errors.append(f"Parameter '{name}' must be a string")
                else:
                    if param.min_length and len(value) < param.min_length:
                        errors.append(
                            f"Parameter '{name}' must be at least {param.min_length} characters"
                        )
                    if param.max_length and len(value) > param.max_length:
                        errors.append(
                            f"Parameter '{name}' must be at most {param.max_length} characters"
                        )
                    if param.pattern:
                        import re
                        if not re.match(param.pattern, value):
                            errors.append(
                                f"Parameter '{name}' does not match required pattern"
                            )

            elif param.type == ParameterType.INTEGER:
                if not isinstance(value, int) or isinstance(value, bool):
                    errors.append(f"Parameter '{name}' must be an integer")
                else:
                    if param.min_value is not None and value < param.min_value:
                        errors.append(f"Parameter '{name}' must be at least {param.min_value}")
                    if param.max_value is not None and value > param.max_value:
                        errors.append(f"Parameter '{name}' must be at most {param.max_value}")

            elif param.type == ParameterType.FLOAT:
                if not isinstance(value, (int, float)) or isinstance(value, bool):
                    errors.append(f"Parameter '{name}' must be a number")
                else:
                    if param.min_value is not None and value < param.min_value:
                        errors.append(f"Parameter '{name}' must be at least {param.min_value}")
                    if param.max_value is not None and value > param.max_value:
                        errors.append(f"Parameter '{name}' must be at most {param.max_value}")

            elif param.type == ParameterType.BOOLEAN:
                if not isinstance(value, bool):
                    errors.append(f"Parameter '{name}' must be a boolean")

            elif param.type in (ParameterType.ARRAY,):
                if not isinstance(value, list):
                    errors.append(f"Parameter '{name}' must be an array")

            elif param.type == ParameterType.OBJECT:
                if not isinstance(value, dict):
                    errors.append(f"Parameter '{name}' must be an object")

            # Enum validation
            if param.enum and value not in param.enum:
                errors.append(f"Parameter '{name}' must be one of: {param.enum}")

            validated[name] = value

        if errors:
            raise ValueError("\n".join(errors))

        return validated


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


def make_parameter(
    name: str,
    param_type: ParameterType,
    description: str = "",
    required: bool = False,
    default: Any | None = None,
    enum: list[Any] | None = None,
    min_value: float | None = None,
    max_value: float | None = None,
    min_length: int | None = None,
    max_length: int | None = None,
    pattern: str | None = None,
) -> ToolParameterSchema:
    """Create a tool parameter with validation."""
    return ToolParameterSchema(
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
        pattern=pattern,
    )


def make_tool_schema(
    name: str,
    description: str,
    parameters: list[ToolParameterSchema] | None = None,
    category: str = "general",
    version: str = "1.0.0",
    return_description: str = "",
    examples: list[dict[str, Any]] | None = None,
) -> ToolSchema:
    """Create a tool schema from parameters."""
    return ToolSchema(
        name=name,
        description=description,
        category=category,
        parameters=parameters or [],
        version=version,
        return_description=return_description,
        examples=examples or [],
    )