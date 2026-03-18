"""Code analysis tool schemas for MindFlow agents.

Provides standardized schemas for GitNexus-backed code intelligence tools.
"""

from __future__ import annotations

from mindflow_backend.schemas.orchestration.orchestrator import AgentType
from mindflow_backend.schemas.tools.tool_config import ToolParameter, ToolSchema

_GITNEXUS_TAGS = ["gitnexus", "code_intelligence", "analysis"]
_SUPPORTED_AGENTS = [AgentType.ANALYST]


GITNEXUS_STATUS_SCHEMA = ToolSchema(
    name="gitnexus_status",
    description="Inspect GitNexus index status for the current workspace",
    category="code_analysis",
    parameters=[
        ToolParameter(
            name="workspace_path",
            type="string",
            description="Workspace path to inspect. Defaults to the agent root directory.",
            required=False,
            format="file-path",
        ),
    ],
    returns={
        "type": "object",
        "description": "GitNexus repository status",
        "properties": {
            "state": {"type": "string"},
            "repository_path": {"type": "string"},
            "indexed_commit": {"type": "string"},
            "current_commit": {"type": "string"},
            "stale": {"type": "boolean"},
        },
    },
    supported_agents=_SUPPORTED_AGENTS,
    tags=_GITNEXUS_TAGS,
)


GITNEXUS_QUERY_SCHEMA = ToolSchema(
    name="gitnexus_query",
    description="Search GitNexus execution flows related to a concept",
    category="code_analysis",
    parameters=[
        ToolParameter(
            name="query",
            type="string",
            description="Natural language or keyword query",
            required=True,
        ),
        ToolParameter(
            name="task_context",
            type="string",
            description="Task context used to improve ranking",
            required=False,
        ),
        ToolParameter(
            name="goal",
            type="string",
            description="What you want to find",
            required=False,
        ),
        ToolParameter(
            name="limit",
            type="integer",
            description="Maximum number of processes to return",
            required=False,
            default=5,
        ),
        ToolParameter(
            name="include_content",
            type="boolean",
            description="Include full symbol source code",
            required=False,
            default=False,
        ),
        ToolParameter(
            name="workspace_path",
            type="string",
            description="Workspace path to inspect. Defaults to the agent root directory.",
            required=False,
            format="file-path",
        ),
    ],
    returns={
        "type": "object",
        "description": "GitNexus query results",
    },
    supported_agents=_SUPPORTED_AGENTS,
    tags=_GITNEXUS_TAGS,
)


GITNEXUS_CONTEXT_SCHEMA = ToolSchema(
    name="gitnexus_context",
    description="Get a 360-degree GitNexus view of a code symbol",
    category="code_analysis",
    parameters=[
        ToolParameter(
            name="name",
            type="string",
            description="Symbol name to inspect",
            required=False,
        ),
        ToolParameter(
            name="uid",
            type="string",
            description="Direct symbol UID from prior GitNexus results",
            required=False,
        ),
        ToolParameter(
            name="file_path",
            type="string",
            description="File path used to disambiguate common symbol names",
            required=False,
            format="file-path",
        ),
        ToolParameter(
            name="include_content",
            type="boolean",
            description="Include full symbol source code",
            required=False,
            default=False,
        ),
        ToolParameter(
            name="workspace_path",
            type="string",
            description="Workspace path to inspect. Defaults to the agent root directory.",
            required=False,
            format="file-path",
        ),
    ],
    returns={
        "type": "object",
        "description": "GitNexus symbol context",
    },
    supported_agents=_SUPPORTED_AGENTS,
    tags=_GITNEXUS_TAGS,
)


GITNEXUS_IMPACT_SCHEMA = ToolSchema(
    name="gitnexus_impact",
    description="Analyze GitNexus blast radius for a symbol or file",
    category="code_analysis",
    parameters=[
        ToolParameter(
            name="target",
            type="string",
            description="Name of the function, class, or file to analyze",
            required=True,
        ),
        ToolParameter(
            name="direction",
            type="string",
            description="Impact direction: upstream (dependants) or downstream (dependencies)",
            required=False,
            default="upstream",
            enum=["upstream", "downstream"],
        ),
        ToolParameter(
            name="depth",
            type="integer",
            description="Maximum relationship depth",
            required=False,
            default=3,
        ),
        ToolParameter(
            name="include_tests",
            type="boolean",
            description="Include test files in the impact result",
            required=False,
            default=False,
        ),
        ToolParameter(
            name="workspace_path",
            type="string",
            description="Workspace path to inspect. Defaults to the agent root directory.",
            required=False,
            format="file-path",
        ),
    ],
    returns={
        "type": "object",
        "description": "GitNexus impact analysis",
    },
    supported_agents=_SUPPORTED_AGENTS,
    tags=_GITNEXUS_TAGS,
)


CODE_SCHEMAS = {
    "gitnexus_status": GITNEXUS_STATUS_SCHEMA,
    "gitnexus_query": GITNEXUS_QUERY_SCHEMA,
    "gitnexus_context": GITNEXUS_CONTEXT_SCHEMA,
    "gitnexus_impact": GITNEXUS_IMPACT_SCHEMA,
}


__all__ = [
    "GITNEXUS_STATUS_SCHEMA",
    "GITNEXUS_QUERY_SCHEMA",
    "GITNEXUS_CONTEXT_SCHEMA",
    "GITNEXUS_IMPACT_SCHEMA",
    "CODE_SCHEMAS",
]
