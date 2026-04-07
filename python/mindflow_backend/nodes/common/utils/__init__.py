"""Utility functions for common nodes.

This module contains reusable utility functions with fine-grained
granularity that can be used across different nodes.
"""

from __future__ import annotations

import time
from typing import Any

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


async def setup_tools_from_policy(
    agent_id: str,
    session_id: str | None = None,
) -> dict[str, Any]:
    """Setup tools based on AgentRuntimePolicy.

    Args:
        agent_id: Agent identifier
        session_id: Optional session identifier

    Returns:
        Dictionary with enabled tools and their configurations
    """
    from mindflow_backend.agents.specialists.runtime_policy import (
        get_agent_runtime_policy,
    )
    from mindflow_backend.agents.tools.base.tool_registry import get_tool_registry

    try:
        policy = get_agent_runtime_policy(agent_id=agent_id, session_id=session_id)
        registry = get_tool_registry()

        enabled_tools = {}
        for tool_scope in policy.tools:
            tools_in_scope = registry.list_tools(category=tool_scope.value)
            enabled_tools[tool_scope.value] = tools_in_scope

        _logger.info(
            "tools_setup_from_policy",
            agent_id=agent_id,
            tool_scopes=[t.value for t in policy.tools],
            enabled_tools_count=len(enabled_tools),
        )

        return {
            "enabled_tools": enabled_tools,
            "tool_scopes": [t.value for t in policy.tools],
            "sandbox_mode": policy.sandbox.value,
        }

    except Exception as e:
        _logger.error("tools_setup_failed", agent_id=agent_id, error=str(e))
        return {
            "enabled_tools": {},
            "tool_scopes": [],
            "error": str(e),
        }


async def configure_memory_scope(
    agent_id: str,
    mission_type: str,
    session_id: str,
) -> dict[str, Any]:
    """Configure memory scope for the mission.

    Args:
        agent_id: Agent identifier
        mission_type: Type of mission
        session_id: Session identifier

    Returns:
        Dictionary with memory scope configuration
    """
    # Configure memory scope based on mission type
    scope_config = {
        "agent_id": agent_id,
        "mission_type": mission_type,
        "session_id": session_id,
        "read_scope": "project",  # Default: read from project memory
        "write_scope": "mission",  # Default: write to mission-specific memory
    }

    # Adjust scope based on mission type
    if mission_type in ["security_audit", "vulnerability_scan"]:
        scope_config["write_scope"] = "universal"  # Security findings go to universal memory
    elif mission_type in ["analysis", "deep_investigation"]:
        scope_config["read_scope"] = "universal"  # Analysis can read universal memory

    _logger.info(
        "memory_scope_configured",
        agent_id=agent_id,
        mission_type=mission_type,
        scope_config=scope_config,
    )

    return scope_config


def initialize_metrics(
    max_iterations: int = 500,
    max_duration_seconds: float = 300.0,
) -> dict[str, Any]:
    """Initialize execution metrics.

    Args:
        max_iterations: Maximum number of iterations
        max_duration_seconds: Maximum execution duration

    Returns:
        Dictionary with initial metrics
    """
    return {
        "started_at": time.time(),
        "iteration": 0,
        "confidence": 0.0,
        "max_iterations": max_iterations,
        "max_duration_seconds": max_duration_seconds,
        "nodes_executed": 0,
        "nodes_failed": 0,
        "total_tokens_used": 0,
        "annotations": [],
        "errors": [],
    }


async def scan_filesystem(working_directory: str = ".") -> dict[str, Any]:
    """Scan filesystem to identify files and directories.

    Args:
        working_directory: Root directory to scan

    Returns:
        Dictionary with files and directories structure
    """
    from pathlib import Path

    root_path = Path(working_directory)
    files = []
    directories = []

    try:
        # Scan directory structure
        for item in root_path.rglob("*"):
            if item.is_file():
                # Filter common non-code files
                if not any(
                    pattern in item.name
                    for pattern in [
                        ".pyc",
                        "__pycache__",
                        ".git",
                        "node_modules",
                        ".pytest_cache",
                    ]
                ):
                    files.append(
                        {
                            "path": str(item.relative_to(root_path)),
                            "size": item.stat().st_size,
                            "extension": item.suffix,
                        }
                    )
            elif item.is_dir():
                directories.append(str(item.relative_to(root_path)))

        _logger.info(
            "filesystem_scan_complete",
            working_directory=working_directory,
            files_count=len(files),
            directories_count=len(directories),
        )

        return {
            "root": str(root_path),
            "files": files,
            "directories": directories,
        }

    except Exception as e:
        _logger.error("filesystem_scan_failed", working_directory=working_directory, error=str(e))
        return {
            "root": str(root_path),
            "files": [],
            "directories": [],
            "error": str(e),
        }


def map_project_structure(filesystem_scan: dict[str, Any]) -> dict[str, Any]:
    """Map project structure based on filesystem scan.

    Args:
        filesystem_scan: Result from scan_filesystem

    Returns:
        Dictionary with mapped project structure
    """
    files = filesystem_scan.get("files", [])

    # Group files by extension
    by_extension = {}
    for file_info in files:
        ext = file_info.get("extension", "unknown")
        if ext not in by_extension:
            by_extension[ext] = []
        by_extension[ext].append(file_info["path"])

    # Identify project type
    project_type = "unknown"
    if ".py" in by_extension:
        project_type = "python"
    elif ".ts" in by_extension or ".tsx" in by_extension:
        project_type = "typescript"
    elif ".js" in by_extension:
        project_type = "javascript"
    elif ".go" in by_extension:
        project_type = "go"
    elif ".rs" in by_extension:
        project_type = "rust"

    return {
        "project_type": project_type,
        "by_extension": by_extension,
        "total_files": len(files),
    }


def identify_relevant_files(
    structure_map: dict[str, Any],
    mission_type: str,
    working_directory: str,
) -> list[str]:
    """Identify relevant files based on mission type.

    Args:
        structure_map: Mapped project structure
        mission_type: Type of mission
        working_directory: Root directory

    Returns:
        List of relevant file paths
    """
    by_extension = structure_map.get("by_extension", {})
    relevant_files = []

    # Determine relevant extensions based on mission type
    if mission_type in ["analysis", "deep_investigation", "code_review"]:
        # Analysis missions: focus on code files
        relevant_extensions = [".py", ".ts", ".tsx", ".js", ".go", ".rs", ".java"]
    elif mission_type in ["security_audit", "vulnerability_scan"]:
        # Security missions: focus on auth, config, and API files
        relevant_extensions = [".py", ".ts", ".js", ".json", ".yaml", ".yml", ".env"]
    elif mission_type in ["web_research", "documentation_lookup"]:
        # Research missions: focus on docs and readme
        relevant_extensions = [".md", ".rst", ".txt"]
    else:
        # Default: all files
        relevant_extensions = list(by_extension.keys())

    # Collect relevant files
    for ext in relevant_extensions:
        if ext in by_extension:
            relevant_files.extend(by_extension[ext])

    _logger.info(
        "relevant_files_identified",
        mission_type=mission_type,
        relevant_files_count=len(relevant_files),
    )

    return relevant_files


def format_final_result(state: dict[str, Any]) -> dict[str, Any]:
    """Format final result for the mission.

    Args:
        state: Current graph state

    Returns:
        Dictionary with formatted result
    """
    mission_type = state.get("mission_type", "unknown")
    iteration = state.get("iteration", 0)
    confidence = state.get("confidence", 0.0)
    annotations = state.get("annotations", [])

    # Base result structure
    result = {
        "mission_type": mission_type,
        "iterations": iteration,
        "confidence": confidence,
        "annotations_count": len(annotations),
        "status": "completed",
    }

    # Add mission-specific result data
    if mission_type in ["analysis", "deep_investigation"]:
        result["findings"] = annotations
        result["analyzed_files"] = state.get("analyzed_files", {})
    elif mission_type in ["security_audit", "vulnerability_scan"]:
        result["vulnerabilities"] = annotations
        result["security_score"] = confidence
    elif mission_type in ["code_review"]:
        result["review_points"] = annotations
        result["quality_score"] = confidence

    return result


def compile_metrics(state: dict[str, Any]) -> dict[str, Any]:
    """Compile execution metrics.

    Args:
        state: Current graph state

    Returns:
        Dictionary with compiled metrics
    """
    started_at = state.get("started_at", time.time())
    metrics = state.get("metrics", {})

    compiled = {
        "duration_seconds": time.time() - started_at,
        "nodes_executed": metrics.get("nodes_executed", 0),
        "nodes_failed": metrics.get("nodes_failed", 0),
        "total_tokens_used": metrics.get("total_tokens_used", 0),
        "iteration": state.get("iteration", 0),
        "confidence": state.get("confidence", 0.0),
    }

    # Add error details if any
    if state.get("error"):
        compiled["error"] = state["error"]

    return compiled


async def generate_memory_annotations(
    state: dict[str, Any],
    agent_id: str,
    mission_type: str,
    session_id: str,
) -> list[dict[str, Any]]:
    """Generate memory annotations from mission results.

    Args:
        state: Current graph state
        agent_id: Agent identifier
        mission_type: Type of mission
        session_id: Session identifier

    Returns:
        List of memory annotations
    """
    annotations = state.get("annotations", [])
    confidence = state.get("confidence", 0.0)

    # Filter annotations based on confidence threshold
    high_confidence_annotations = [
        ann for ann in annotations if isinstance(ann, dict) and ann.get("confidence", 0.0) >= 0.7
    ]

    # Add metadata to annotations
    formatted_annotations = []
    for ann in high_confidence_annotations:
        formatted_annotations.append(
            {
                "content": ann.get("content", str(ann)),
                "agent_id": agent_id,
                "mission_type": mission_type,
                "session_id": session_id,
                "confidence": ann.get("confidence", confidence),
                "timestamp": time.time(),
            }
        )

    _logger.info(
        "memory_annotations_generated",
        agent_id=agent_id,
        mission_type=mission_type,
        annotations_count=len(formatted_annotations),
    )

    return formatted_annotations
