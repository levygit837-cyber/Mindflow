"""LangChain adapter for MindFlow tools.

Converts MindFlow ``AsyncToolInterface`` / ``ToolInterface`` instances to proper
LangChain ``StructuredTool`` objects that can be passed to ``llm.bind_tools()``.

The MindFlow schema format (ToolSchema / ToolParameter) is translated to a
dynamically-built Pydantic model so LangChain can generate the correct JSON Schema
for function calling.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, List, Optional

from pydantic import Field, create_model

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)

# Map MindFlow type strings → Python types used in Pydantic field definitions.
# array → List[str]: Vertex AI requires items to be defined for every array property.
# Using List[str] makes Pydantic emit {"type":"array","items":{"type":"string"}}.
_JSON_TYPE_MAP: dict[str, type] = {
    "string": str,
    "integer": int,
    "number": float,
    "boolean": bool,
    "array": List[str],  # type: ignore[valid-type]
    "object": Dict[str, Any],  # type: ignore[valid-type]
}


def _sanitize_vertex_schema(schema: dict) -> dict:
    """Recursively ensure every 'array' property has an 'items' field.

    Vertex AI (Gemini) rejects function declarations where an array-type property
    is missing 'items'. This walks the schema and injects a default
    ``{"type": "string"}`` items definition wherever it is absent.
    """
    if not isinstance(schema, dict):
        return schema

    if schema.get("type") == "array" and "items" not in schema:
        schema["items"] = {"type": "string"}

    for key, value in schema.items():
        if isinstance(value, dict):
            schema[key] = _sanitize_vertex_schema(value)
        elif isinstance(value, list):
            schema[key] = [
                _sanitize_vertex_schema(v) if isinstance(v, dict) else v
                for v in value
            ]

    return schema


def _build_args_schema(schema_dict: dict):
    """Build a Pydantic model from a MindFlow ToolSchema dict.

    Expects ``schema_dict`` to contain a ``parameters`` key with a list of
    ``ToolParameter``-like objects (dicts or dataclass-style objects with
    ``name``, ``type``, ``description``, ``required``, ``default`` attrs).

    Returns a Pydantic ``BaseModel`` class or ``None`` if no parameters found.
    """
    try:
        parameters = schema_dict.get("parameters", [])
        if not parameters:
            return None

        field_definitions: dict[str, Any] = {}

        for param in parameters:
            # Support both dict and object (ToolParameter) representations
            if isinstance(param, dict):
                name = param.get("name", "")
                type_str = param.get("type", "string")
                description = param.get("description", "")
                required = param.get("required", False)
                default = param.get("default", None)
            else:
                name = getattr(param, "name", "")
                type_str = getattr(param, "type", "string")
                description = getattr(param, "description", "")
                required = getattr(param, "required", False)
                default = getattr(param, "default", None)

            if not name:
                continue

            python_type = _JSON_TYPE_MAP.get(type_str, str)

            if required:
                field_definitions[name] = (python_type, Field(description=description))
            else:
                field_definitions[name] = (
                    Optional[python_type],
                    Field(default=default, description=description),
                )

        if not field_definitions:
            return None

        return create_model("ToolArgs", **field_definitions)

    except Exception as exc:
        _logger.warning(f"Failed to build Pydantic schema for tool: {exc}")
        return None


def to_langchain_tool(mindflow_tool: Any):
    """Convert a single MindFlow tool to a LangChain ``StructuredTool``.

    Returns a ``StructuredTool`` instance or ``None`` if conversion fails.
    """
    try:
        from langchain_core.tools import StructuredTool
    except ImportError:
        _logger.error("langchain_core not installed — cannot convert tools")
        return None

    try:
        # Resolve schema
        schema_dict: dict = {}
        if hasattr(mindflow_tool, "get_schema"):
            raw = mindflow_tool.get_schema()
            if hasattr(raw, "dict"):
                schema_dict = raw.dict()
            elif isinstance(raw, dict):
                schema_dict = raw

        args_schema = _build_args_schema(schema_dict)

        # Keep a stable reference to avoid closure capture issues in loops
        _tool = mindflow_tool

        async def _arun(**kwargs: Any) -> str:
            try:
                result = await _tool.execute(**kwargs)
                if isinstance(result, dict):
                    return json.dumps(result, ensure_ascii=False, default=str)
                return str(result)
            except Exception as exc:
                return json.dumps({"success": False, "error": str(exc)})

        def _run(**kwargs: Any) -> str:
            """Sync fallback — runs the async execute in a new event loop."""
            try:
                result = asyncio.run(_tool.execute(**kwargs))
                if isinstance(result, dict):
                    return json.dumps(result, ensure_ascii=False, default=str)
                return str(result)
            except Exception as exc:
                return json.dumps({"success": False, "error": str(exc)})

        lc_tool = StructuredTool.from_function(
            func=_run,
            coroutine=_arun,
            name=mindflow_tool.name,
            description=mindflow_tool.description,
            args_schema=args_schema,
            handle_tool_error=True,
        )

        # Patch the generated JSON schema in-place so Vertex AI accepts it.
        # Pydantic may still produce bare {"type":"array"} in edge cases;
        # _sanitize_vertex_schema adds "items" wherever it is missing.
        if args_schema is not None and hasattr(args_schema, "model_json_schema"):
            try:
                raw_schema = args_schema.model_json_schema()
                sanitized = _sanitize_vertex_schema(raw_schema)
                if sanitized != raw_schema:
                    _logger.debug(
                        f"Schema patched for Vertex AI on tool '{mindflow_tool.name}'"
                    )
            except Exception:
                pass  # non-critical — tool still usable

        _logger.debug(f"Converted tool '{mindflow_tool.name}' → LangChain StructuredTool")
        return lc_tool

    except Exception as exc:
        tool_name = getattr(mindflow_tool, "name", repr(mindflow_tool))
        _logger.warning(f"Failed to convert tool '{tool_name}' to LangChain: {exc}")
        return None


def to_langchain_tools(mindflow_tools: list[Any]) -> list[Any]:
    """Convert a list of MindFlow tools to LangChain ``StructuredTool`` objects.

    Deduplicates tools by name (first occurrence wins) and silently skips tools
    that fail conversion.
    """
    result = []
    seen_names: set[str] = set()
    for tool in mindflow_tools:
        tool_name = getattr(tool, "name", None)
        if tool_name and tool_name in seen_names:
            _logger.debug(f"Skipping duplicate tool '{tool_name}'")
            continue
        lc_tool = to_langchain_tool(tool)
        if lc_tool is not None:
            result.append(lc_tool)
            if tool_name:
                seen_names.add(tool_name)

    _logger.info(
        f"Tool conversion: {len(result)}/{len(mindflow_tools)} tools converted to LangChain format"
    )
    return result
