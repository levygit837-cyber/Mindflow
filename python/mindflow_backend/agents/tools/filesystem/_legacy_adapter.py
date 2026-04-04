"""Compatibility helpers for filesystem wrappers.

These adapters let V3/new-tool wrappers delegate execution to the
canonical unsuffixed filesystem tool implementations while preserving
their response contracts.
"""

from __future__ import annotations

from typing import Any

from mindflow_backend.schemas.tools.context import ToolContext
from mindflow_backend.schemas.tools.permission import PermissionBehavior


def get_context_root_dir(context: ToolContext) -> str | None:
    """Resolve the effective root dir carried by tool context."""
    return context.root_dir or context.metadata.get("root_dir")


def build_legacy_tool(tool_cls: type, context: ToolContext):
    """Instantiate a canonical legacy tool configured from ToolContext."""
    tool = tool_cls()
    root_dir = get_context_root_dir(context)
    if root_dir:
        tool.root_dir = root_dir
    tool.sandbox_mode = context.sandbox_mode
    return tool


async def deny_if_permission_blocked(
    context: ToolContext,
    *,
    tool_name: str,
    input_data: dict[str, Any],
    tool_content: str,
    content_key: str,
) -> dict[str, Any] | None:
    """Return a V3-style permission denial payload when applicable."""
    if not context.permission_manager:
        return None

    perm_result = await context.check_permission_async(
        tool_name=tool_name,
        input=input_data,
        tool_content=tool_content,
    )
    if perm_result.behavior != PermissionBehavior.DENY:
        return None

    error = getattr(perm_result, "reason", None) or getattr(perm_result, "message", None) or "Permission denied"
    return {
        "success": False,
        "error": error,
        "error_code": "PERMISSION_DENIED",
        content_key: tool_content,
    }


def flatten_legacy_result(
    result: dict[str, Any],
    *,
    error_map: dict[str, str] | None = None,
    default_error_code: str,
) -> dict[str, Any]:
    """Flatten AsyncToolInterface results into the V3 response shape."""
    if result.get("success"):
        payload = result.get("result")
        if isinstance(payload, dict):
            return {"success": True, **payload}
        return {"success": True, "result": payload}

    error = result.get("error") or "Unknown error"
    error_code = default_error_code
    if error_map:
        lowered = error.lower()
        for fragment, mapped_code in error_map.items():
            if fragment in lowered:
                error_code = mapped_code
                break

    return {
        "success": False,
        "error": error,
        "error_code": error_code,
    }
