"""LangChain adapter for MindFlow tools.

Converts MindFlow tools to LangChain ``StructuredTool`` objects that can be
passed to ``llm.bind_tools()``.

Supports THREE tool systems:
1. **CALLABLE**: CallableTool (from schemas/tools/callable.py) - Phase 2 pattern
2. **NEW**: Tool (from schemas/tools/tool.py) - uses build_tool() factory
3. **LEGACY**: AsyncToolInterface (from agents/tools/base/tool_interface.py)

The adapter automatically detects which type and converts appropriately.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, Optional

from pydantic import Field, create_model

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)

# Import new Tool type for isinstance check
try:
    from mindflow_backend.schemas.tools.tool import Tool as NewTool
    from mindflow_backend.schemas.tools.context import ToolContext
    _NEW_TOOL_AVAILABLE = True
except ImportError:
    _NEW_TOOL_AVAILABLE = False
    _logger.warning("New Tool system not available - only legacy tools supported")

# Import CallableTool type for isinstance check (Phase 2)
try:
    from mindflow_backend.schemas.tools.callable import CallableTool
    from mindflow_backend.schemas.tools.callable_adapter import callable_to_langchain
    _CALLABLE_TOOL_AVAILABLE = True
except ImportError:
    _CALLABLE_TOOL_AVAILABLE = False
    _logger.warning("CallableTool system not available - using legacy/new tools only")

# Map MindFlow type strings → Python types used in Pydantic field definitions.
# array → List[str]: Vertex AI requires items to be defined for every array property.
# Using List[str] makes Pydantic emit {"type":"array","items":{"type":"string"}}.
_JSON_TYPE_MAP: dict[str, type] = {
    "string": str,
    "integer": int,
    "number": float,
    "boolean": bool,
    "array": list[str],  # type: ignore[valid-type]
    "object": dict[str, Any],  # type: ignore[valid-type]
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

    Supports two formats:

    1. **List format** — ``parameters`` is a list of ``ToolParameter``-like
       objects (dicts or dataclass-style) with ``name``, ``type``,
       ``description``, ``required``, ``default`` attrs.

    2. **JSON Schema format** — ``parameters`` is a JSON Schema object with
       ``properties`` (and optionally ``required``). This is the format used
       by tools that define their schema inline with ``get_schema()``.

    Returns a Pydantic ``BaseModel`` class or ``None`` if no parameters found.
    """
    try:
        parameters = schema_dict.get("parameters", [])
        if not parameters:
            return None

        field_definitions: dict[str, Any] = {}

        # ── JSON Schema format: {"type": "object", "properties": {...}, "required": [...]} ──
        if isinstance(parameters, dict):
            properties: dict = parameters.get("properties") or {}
            required_fields: list = parameters.get("required") or []

            for name, prop in properties.items():
                if not name:
                    continue
                type_str = prop.get("type", "string")
                description = prop.get("description", "")
                default = prop.get("default", None)
                is_required = name in required_fields

                python_type = _JSON_TYPE_MAP.get(type_str, str)

                if is_required:
                    field_definitions[name] = (python_type, Field(description=description))
                else:
                    field_definitions[name] = (
                        Optional[python_type],
                        Field(default=default, description=description),
                    )

        # ── List format: [{name, type, description, required, default}, ...] ──
        else:
            for param in parameters:
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


def _is_callable_tool(tool: Any) -> bool:
    """Detect if tool is CallableTool (Phase 2 callable pattern)."""
    if not _CALLABLE_TOOL_AVAILABLE:
        return False
    return isinstance(tool, CallableTool)


def _is_new_tool(tool: Any) -> bool:
    """Detect if tool is new Tool (schemas/tools) or legacy AsyncToolInterface."""
    if not _NEW_TOOL_AVAILABLE:
        return False
    return isinstance(tool, NewTool)


def _convert_new_tool(tool: Any):
    """Convert Tool (new system) → LangChain StructuredTool.

    New tools use:
    - input_schema (Pydantic model) instead of get_schema()
    - execute(input, context) instead of execute(**kwargs)
    - Explicit permission metadata (is_read_only, is_destructive)
    """
    try:
        from langchain_core.tools import StructuredTool
    except ImportError:
        _logger.error("langchain_core not installed")
        return None

    try:
        # Extract input schema (already a Pydantic model)
        input_model = tool.input_schema

        # Build metadata
        tool_metadata = {
            "tool_name": tool.name,
            "tool_type": "new",
            "is_read_only": tool.is_read_only,
            "is_destructive": tool.is_destructive,
            "is_concurrency_safe": tool.is_concurrency_safe,
            "execution_mode": str(tool.execution_mode),
        }

        # Keep stable reference
        _tool = tool

        async def _arun(**kwargs: Any) -> str:
            """Async execution wrapper that injects ToolContext."""
            try:
                # Try to get permission context from runtime if available
                permission_context = None
                try:
                    # Try to get from session or runtime context
                    from mindflow_backend.services.permission import get_permission_manager
                    
                    perm_manager = get_permission_manager()
                    if perm_manager:
                        permission_context = await perm_manager.get_context_for_tool(_tool.name)
                except ImportError:
                    pass  # Permission system not available
                except Exception:
                    pass  # Silently fall back to None
                
                context = ToolContext(
                    permission_context=permission_context,
                    metadata={
                        "tool_name": _tool.name,
                        "tool_input": kwargs,
                    }
                )

                # Validate input with Pydantic
                try:
                    validated_input = input_model(**kwargs)
                except Exception as e:
                    return json.dumps({
                        "success": False,
                        "error": f"Invalid input: {e}",
                        "error_code": "VALIDATION_ERROR"
                    })

                # Execute tool
                result = await _tool.execute(validated_input, context)

                if isinstance(result, dict):
                    return json.dumps(result, ensure_ascii=False, default=str)
                return str(result)

            except Exception as exc:
                return json.dumps({
                    "success": False,
                    "error": str(exc),
                    "error_code": "EXECUTION_ERROR"
                })

        def _run(**kwargs: Any) -> str:
            """Sync fallback."""
            try:
                return asyncio.run(_arun(**kwargs))
            except Exception as exc:
                return json.dumps({"success": False, "error": str(exc)})

        lc_tool = StructuredTool.from_function(
            func=_run,
            coroutine=_arun,
            name=_tool.name,
            description=_tool.description,
            args_schema=input_model,
            handle_tool_error=True,
            metadata=tool_metadata,
        )

        _logger.debug(f"Converted NEW tool '{_tool.name}' → LangChain StructuredTool")
        return lc_tool

    except Exception as exc:
        tool_name = getattr(tool, "name", repr(tool))
        _logger.warning(f"Failed to convert new tool '{tool_name}': {exc}")
        return None


def _convert_legacy_tool(mindflow_tool: Any):
    """Convert AsyncToolInterface (legacy) → LangChain StructuredTool.

    This is the original conversion logic for legacy tools.
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
        category = schema_dict.get("category") or getattr(mindflow_tool, "category", "tool")
        family = getattr(mindflow_tool, "tool_family", category or "tool")
        notifier_kind = getattr(mindflow_tool, "notifier_kind", getattr(mindflow_tool, "name", None))
        tool_metadata = {
            key: value
            for key, value in {
                "tool_name": getattr(mindflow_tool, "name", None),
                "category": category,
                "family": family,
                "notifier_kind": notifier_kind,
                "version": getattr(mindflow_tool, "version", None),
            }.items()
            if value is not None
        }
        tool_tags = list(schema_dict.get("tags") or [])
        for extra_tag in (category, family):
            if isinstance(extra_tag, str) and extra_tag and extra_tag not in tool_tags:
                tool_tags.append(extra_tag)

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
            metadata=tool_metadata,
            tags=tool_tags or None,
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

        _logger.debug(f"Converted LEGACY tool '{mindflow_tool.name}' → LangChain StructuredTool")
        return lc_tool

    except Exception as exc:
        tool_name = getattr(mindflow_tool, "name", repr(mindflow_tool))
        _logger.warning(f"Failed to convert legacy tool '{tool_name}': {exc}")
        return None


def to_langchain_tool(mindflow_tool: Any):
    """Convert a MindFlow tool to a LangChain ``StructuredTool``.

    Supports THREE types (checked in priority order):
    1. CallableTool (Phase 2 callable pattern from schemas/tools/callable.py)
    2. Tool (new system from schemas/tools/tool.py)
    3. AsyncToolInterface (legacy from agents/tools/base/tool_interface.py)

    Returns a ``StructuredTool`` instance or ``None`` if conversion fails.
    """
    # Priority 1: Check for CallableTool (Phase 2)
    if _is_callable_tool(mindflow_tool):
        _logger.debug(f"Detected CALLABLE tool: {getattr(mindflow_tool, 'name', 'unknown')}")
        try:
            return callable_to_langchain(mindflow_tool)
        except Exception as exc:
            tool_name = getattr(mindflow_tool, "name", repr(mindflow_tool))
            _logger.warning(f"Failed to convert callable tool '{tool_name}': {exc}")
            return None

    # Priority 2: Check for new Tool
    if _is_new_tool(mindflow_tool):
        _logger.debug(f"Detected NEW tool: {getattr(mindflow_tool, 'name', 'unknown')}")
        return _convert_new_tool(mindflow_tool)

    # Priority 3: Legacy AsyncToolInterface
    _logger.debug(f"Detected LEGACY tool: {getattr(mindflow_tool, 'name', 'unknown')}")
    return _convert_legacy_tool(mindflow_tool)


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
