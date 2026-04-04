"""Scratchpad Tools - Blank board for Agents to maintain notes.

Provides read and write access to agent-specific markdown scratchpads
stored persistently during a session.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from mindflow_backend.schemas.tools import build_tool
from mindflow_backend.schemas.tools.context import ToolContext
from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Input Schemas
# ---------------------------------------------------------------------------

class ScratchpadReadInput(BaseModel):
    """Input schema for ScratchpadReadTool."""

    agent_type: str = Field(
        description="The type or name of the agent whose scratchpad you want to read (e.g., 'coder', 'analyst', 'orchestrator')"
    )


class ScratchpadWriteInput(BaseModel):
    """Input schema for ScratchpadWriteTool."""

    agent_type: str = Field(
        description="The type or name of the agent whose scratchpad you want to write to. Usually your own agent type."
    )
    content: str = Field(
        description="The content to write to the scratchpad. Format as Markdown."
    )
    append: bool = Field(
        default=False,
        description="If true, appends the content to the existing file. If false, overwrites the entire file."
    )


# ---------------------------------------------------------------------------
# Core Logic
# ---------------------------------------------------------------------------

def _get_scratchpad_path(context: ToolContext, agent_type: str) -> Path:
    """Helper to resolve the scratchpad path for a given session and agent."""
    root = context.root_dir or os.getcwd()
    session_id = context.session_id or "default_session"
    
    # Clean the agent_type string to be safe for filenames
    safe_agent_type = "".join(c if c.isalnum() else "_" for c in agent_type).lower()
    
    scratchpads_dir = Path(root) / ".mindflow" / "scratchpads" / session_id
    scratchpads_dir.mkdir(parents=True, exist_ok=True)
    
    return scratchpads_dir / f"{safe_agent_type}_scratchpad.md"


# ---------------------------------------------------------------------------
# Execute Functions
# ---------------------------------------------------------------------------

async def scratchpad_read_execute(input: ScratchpadReadInput, context: ToolContext) -> dict[str, Any]:
    """Read the contents of an agent's scratchpad.

    Args:
        input: Validated input (Pydantic model)
        context: Tool execution context

    Returns:
        Dictionary with scratchpad content or error
    """
    try:
        file_path = _get_scratchpad_path(context, input.agent_type)
        
        if not file_path.exists():
            return {
                "success": True,
                "content": "(Scratchpad is empty/does not exist yet.)",
                "agent_type": input.agent_type
            }
            
        content = file_path.read_text(encoding="utf-8")
        
        return {
            "success": True,
            "content": content,
            "agent_type": input.agent_type
        }

    except Exception as e:
        _logger.exception("Failed to read scratchpad")
        return {
            "success": False,
            "error": f"Failed to read scratchpad: {e}",
            "error_code": "SCRATCHPAD_READ_ERROR"
        }


async def scratchpad_write_execute(input: ScratchpadWriteInput, context: ToolContext) -> dict[str, Any]:
    """Write or append to an agent's scratchpad.

    Args:
        input: Validated input
        context: Tool execution context

    Returns:
        Dictionary with status
    """
    try:
        file_path = _get_scratchpad_path(context, input.agent_type)
        mode = "a" if input.append else "w"
        
        with open(file_path, mode, encoding="utf-8") as f:
            if input.append and file_path.exists() and file_path.stat().st_size > 0:
                f.write("\n\n")  # Ensure spacing when appending
            f.write(input.content)
            
        return {
            "success": True,
            "message": f"Successfully {'appended to' if input.append else 'wrote to'} {input.agent_type}'s scratchpad.",
            "file_path": str(file_path)
        }
        
    except Exception as e:
        _logger.exception("Failed to write to scratchpad")
        return {
            "success": False,
            "error": f"Failed to write to scratchpad: {e}",
            "error_code": "SCRATCHPAD_WRITE_ERROR"
        }


# ---------------------------------------------------------------------------
# Build Tools
# ---------------------------------------------------------------------------

ScratchpadReadTool = build_tool(
    name="read_scratchpad",
    description=(
        "Read an agent's scratchpad file. This contains blank board notes, thoughts, "
        "and progress written by that agent during the session."
    ),
    input_schema=ScratchpadReadInput,
    execute=scratchpad_read_execute,
    is_read_only=True,
    is_concurrency_safe=True,
    is_destructive=False,
)

ScratchpadWriteTool = build_tool(
    name="write_scratchpad",
    description=(
        "Write or append notes, plans, and checklist info to an agent's scratchpad (usually your own). "
        "Useful to maintain context, organize complex thoughts, and collaborate asynchronously. "
        "Uses Markdown."
    ),
    input_schema=ScratchpadWriteInput,
    execute=scratchpad_write_execute,
    is_read_only=False,
    is_concurrency_safe=False,
    is_destructive=True,
)
