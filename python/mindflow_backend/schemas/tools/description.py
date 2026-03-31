"""Schema-to-LLM description bridge for MindFlow tools.

Mirrors Claude Code CLI pattern where each tool has:
1. An inputSchema (Zod/Pydantic) for API validation
2. A description(input, context) callback for the LLM

This module generates LLM-readable descriptions from Pydantic schemas,
eliminating the need for manual description strings that drift from the
actual schema.

Design principles:
- Auto-generate descriptions from Pydantic field metadata
- Support manual override for complex tools
- Include examples from schema annotations
- Format as SKILL.md-like markdown
"""

from __future__ import annotations

from typing import Any, TypeVar

from pydantic import BaseModel

from mindflow_backend.schemas.tools.progress import ToolProgressData
from mindflow_backend.schemas.tools.result import ToolResult


# ---------------------------------------------------------------------------
# Description Generator
# ---------------------------------------------------------------------------


def describe_field(name: str, field_info: Any, is_required: bool = True) -> str:
    """Generate a markdown line describing a single Pydantic field.

    Similar to how Claude Code's tool descriptions list parameters.
    """
    parts = [f"- **`{name}`**"]

    # Type info
    type_name = _get_type_name(field_info)
    if type_name:
        parts.append(f"({type_name})")

    # Description
    if field_info.description:
        parts.append(f"— {field_info.description}")

    # Default value
    from pydantic_core import PydanticUndefined
    if not is_required and field_info.default is not PydanticUndefined:
        default_repr = repr(field_info.default)
        if len(default_repr) > 50:
            default_repr = default_repr[:47] + "..."
        parts.append(f"*(default: {default_repr})*")

    # Required marker for optional-looking required fields
    if is_required:
        parts.append("*required*")

    return " ".join(parts)


def describe_model(schema_cls: type[BaseModel], tool_name: str) -> str:
    """Generate a full tool description from a Pydantic model.

    Format:
    ## ToolName

    Description from model docstring.

    ### Parameters
    - **`param1`** (string) — param description *required*
    - **`param2`** (integer) — param description *(default: 10)*

    ### Example
    ```
    { "param1": "value", "param2": 10 }
    ```
    """
    lines = [f"## {tool_name}\n"]

    # Docstring as description
    doc = (schema_cls.__doc__ or "").strip()
    if doc:
        lines.append(doc)
        lines.append("")

    # Parameters section
    fields = schema_cls.model_fields
    if fields:
        lines.append("### Parameters\n")
        required_fields = schema_cls.model_json_schema().get("required", [])
        for name, field in fields.items():
            is_required = name in required_fields
            lines.append(describe_field(name, field, is_required))
        lines.append("")

    # Example section (from example attribute)
    examples = getattr(schema_cls, "model_config", {}).get("json_schema_extra", {}).get("examples", [])
    if examples:
        import json
        lines.append("### Example\n")
        lines.append("```json")
        lines.append(json.dumps(examples[0], indent=2))
        lines.append("```\n")

    return "\n".join(lines)


def get_json_schema_description(schema_cls: type[BaseModel]) -> dict[str, Any]:
    """Get the JSON schema for a Pydantic model (for API tool definitions).

    Similar to Claude Code's JSON schema output for tool definitions.
    """
    return schema_cls.model_json_schema()


def generate_openai_tool_definition(
    name: str,
    schema_cls: type[BaseModel],
    description_override: str | None = None,
) -> dict[str, Any]:
    """Generate an OpenAI-compatible tool definition.

    Compatible with:
    - OpenAI function calling
    - Anthropic tool use
    - Any provider using JSON Schema tool definitions
    """
    schema = schema_cls.model_json_schema()

    # Use override or auto-generate from model
    if description_override:
        desc = description_override
    else:
        doc = (schema_cls.__doc__ or "").strip()
        if doc:
            desc = doc.split("\n")[0]  # First line as short description
        else:
            desc = f"Execute {name} with the provided parameters."

    return {
        "type": "function",
        "function": {
            "name": name,
            "description": desc,
            "parameters": {
                "type": "object",
                "properties": schema.get("properties", {}),
                "required": schema.get("required", []),
            },
        },
    }


def generate_anthropic_tool_definition(
    name: str,
    schema_cls: type[BaseModel],
    description_override: str | None = None,
) -> dict[str, Any]:
    """Generate an Anthropic-compatible tool definition."""
    schema = schema_cls.model_json_schema()

    if description_override:
        desc = description_override
    else:
        doc = (schema_cls.__doc__ or "").strip()
        if doc:
            desc = doc.split("\n")[0]
        else:
            desc = f"Execute {name} with the provided parameters."

    # Clean up schema for Anthropic (remove $defs if possible, keep it flat)
    input_schema = {
        "type": "object",
        "properties": schema.get("properties", {}),
        "required": schema.get("required", []),
    }

    return {
        "name": name,
        "description": desc,
        "input_schema": input_schema,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_type_name(field_info: Any) -> str:
    """Get a human-readable type name from a Pydantic field."""
    annotation = field_info.annotation
    if annotation is None:
        return "any"

    # Handle common types
    import typing
    origin = typing.get_origin(annotation)
    args = typing.get_args(annotation)

    if origin is list or origin is typing.List:
        inner = _get_type_name_from_annotation(args[0]) if args else "any"
        return f"array<{inner}>"
    elif origin is dict or origin is dict or origin is typing.Dict:
        return "object"
    elif origin is typing.Union:
        # Check for Optional (Union with None)
        non_none = [a for a in args if a is not type(None)]
        if len(non_none) == 1:
            return _get_type_name_from_annotation(non_none[0])
        return "union"
    elif origin is None:
        return _get_type_name_from_annotation(annotation)

    return "any"


def _get_type_name_from_annotation(annotation: Any) -> str:
    """Get a simple type name from a type annotation."""
    if annotation is str:
        return "string"
    elif annotation is int:
        return "integer"
    elif annotation is float:
        return "number"
    elif annotation is bool:
        return "boolean"
    elif annotation is list or annotation is dict:
        return annotation.__name__
    elif hasattr(annotation, "__name__"):
        return annotation.__name__
    return str(annotation)