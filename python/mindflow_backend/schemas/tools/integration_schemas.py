"""Integration tool schemas for MindFlow agents.

Provides standardized schemas for integration-related tools including
Git operations, Docker management, and cloud services.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from mindflow_backend.schemas.tools.tool_config import ToolParameter, ToolSchema


# Predefined schemas for Integration tools
GIT_SCHEMA = ToolSchema(
    name="git_manager",
    description="Git repository management and operations",
    category="integration",
    parameters=[
        ToolParameter(
            name="action",
            type="string",
            description="Git action to perform (status, add, commit, push, pull, clone, log, branch, merge, diff)",
            required=True
        ),
        ToolParameter(
            name="repository_path",
            type="string",
            description="Repository path or URL",
            required=False
        ),
        ToolParameter(
            name="files",
            type="array",
            description="Files to add",
            required=False
        ),
        ToolParameter(
            name="message",
            type="string",
            description="Commit message",
            required=False
        ),
        ToolParameter(
            name="branch",
            type="string",
            description="Branch name",
            required=False
        ),
        ToolParameter(
            name="remote",
            type="string",
            description="Remote name",
            required=False,
            default="origin"
        ),
        ToolParameter(
            name="options",
            type="object",
            description="Additional options",
            required=False,
            default={}
        )
    ],
    returns={
        "type": "object",
        "description": "Git operation result",
        "properties": {
            "action": {"type": "string", "description": "Action performed"},
            "result": {"type": "object", "description": "Operation result"},
            "success": {"type": "boolean", "description": "Operation success"}
        }
    }
)


DOCKER_SCHEMA = ToolSchema(
    name="docker_manager",
    description="Docker container and image management",
    category="integration",
    parameters=[
        ToolParameter(
            name="action",
            type="string",
            description="Docker action to perform (list_containers, list_images, run, stop, remove, build, logs, exec)",
            required=True
        ),
        ToolParameter(
            name="container_name",
            type="string",
            description="Container name or ID",
            required=False
        ),
        ToolParameter(
            name="image_name",
            type="string",
            description="Image name",
            required=False
        ),
        ToolParameter(
            name="command",
            type="string",
            description="Container command",
            required=False
        ),
        ToolParameter(
            name="ports",
            type="array",
            description="Port mappings",
            required=False
        ),
        ToolParameter(
            name="volumes",
            type="array",
            description="Volume mappings",
            required=False
        ),
        ToolParameter(
            name="environment",
            type="object",
            description="Environment variables",
            required=False
        ),
        ToolParameter(
            name="detach",
            type="boolean",
            description="Run in detached mode",
            required=False,
            default=True
        ),
        ToolParameter(
            name="dockerfile_path",
            type="string",
            description="Dockerfile path for build",
            required=False
        ),
        ToolParameter(
            name="tag",
            type="string",
            description="Image tag",
            required=False
        )
    ],
    returns={
        "type": "object",
        "description": "Docker operation result",
        "properties": {
            "action": {"type": "string", "description": "Action performed"},
            "result": {"type": "object", "description": "Operation result"}
        }
    }
)


# Dictionary of all integration tool schemas
INTEGRATION_SCHEMAS = {
    "git_tool": GIT_SCHEMA,
    "docker_tool": DOCKER_SCHEMA
}


# Export schemas for easy import
__all__ = [
    "GIT_SCHEMA",
    "DOCKER_SCHEMA",
    "INTEGRATION_SCHEMAS"
]
