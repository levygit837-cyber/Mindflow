"""SystemInfoTool v3 compatibility wrapper.

Delegates execution to the canonical unsuffixed system info tool while
preserving the V3 input schema and flattened response contract.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from mindflow_backend.agents.tools.filesystem._legacy_adapter import (
    build_legacy_tool,
    flatten_legacy_result,
)
from mindflow_backend.agents.tools.system.system_info import SystemInfoTool
from mindflow_backend.schemas.tools import build_tool
from mindflow_backend.schemas.tools.context import ToolContext


class SystemInfoInput(BaseModel):
    """Input schema for SystemInfoTool v3."""

    info_type: str = Field(
        default="all",
        description="Type of information to collect: 'all', 'hardware', 'software', 'network', 'environment'",
    )
    include_sensitive: bool = Field(
        default=False,
        description="Include sensitive environment variables (masked)",
    )


async def system_info_execute(input: SystemInfoInput, context: ToolContext) -> dict[str, Any]:
    """Collect system information through the canonical V1 implementation."""
    tool = build_legacy_tool(SystemInfoTool, context)
    result = await tool.execute(
        info_type=input.info_type,
        include_sensitive=input.include_sensitive,
    )
    flattened = flatten_legacy_result(
        result,
        default_error_code="COLLECTION_ERROR",
    )
    if flattened.get("success"):
        flattened.setdefault("info_type", input.info_type)
    else:
        flattened.setdefault("info_type", input.info_type)
    return flattened


SystemInfoToolV3 = build_tool(
    name="system_info",
    description=(
        "Collect comprehensive system information including hardware (CPU, memory, disk), "
        "software (Python, OS), network (interfaces, connections), and environment variables. "
        "Supports filtering by info type and optional sensitive data masking."
    ),
    input_schema=SystemInfoInput,
    execute=system_info_execute,
    is_read_only=True,
    is_concurrency_safe=True,
    is_destructive=False,
)
