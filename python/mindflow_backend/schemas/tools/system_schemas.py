"""System tool schemas for MindFlow agents.

Provides standardized schemas for system-related tools including
process management, resource monitoring, sandbox execution, and system information.
"""

from __future__ import annotations

from mindflow_backend.schemas.tools.tool_config import ToolParameter, ToolSchema

# Process Manager Tool Schema
PROCESS_MANAGER_SCHEMA = ToolSchema(
    name="process_manager",
    description="System process management with security controls",
    category="system",
    parameters=[
        ToolParameter(
            name="action",
            type="string",
            description="Action to perform (list, kill, monitor)",
            required=True
        ),
        ToolParameter(
            name="pid",
            type="integer",
            description="Process ID (for kill action)",
            required=False
        ),
        ToolParameter(
            name="signal",
            type="string",
            description="Signal to send (SIGTERM, SIGKILL, etc.)",
            required=False,
            default="SIGTERM"
        ),
        ToolParameter(
            name="filter_name",
            type="string",
            description="Filter processes by name",
            required=False
        ),
        ToolParameter(
            name="filter_user",
            type="string",
            description="Filter processes by user",
            required=False
        )
    ],
    returns={
        "type": "object",
        "description": "Process management result",
        "properties": {
            "processes": {"type": "array", "description": "List of processes"},
            "action_result": {"type": "object", "description": "Result of action"},
            "timestamp": {"type": "string", "description": "Operation timestamp"}
        }
    }
)


# Resource Monitor Tool Schema
RESOURCE_MONITOR_SCHEMA = ToolSchema(
    name="resource_monitor",
    description="System resource monitoring with alerting",
    category="system",
    parameters=[
        ToolParameter(
            name="action",
            type="string",
            description="Action to perform (start, stop, get_current, get_history)",
            required=True
        ),
        ToolParameter(
            name="resources",
            type="array",
            description="Resources to monitor (cpu, memory, disk, network)",
            required=False,
            default=["cpu", "memory"]
        ),
        ToolParameter(
            name="duration",
            type="integer",
            description="Monitoring duration in seconds",
            required=False,
            default=60
        ),
        ToolParameter(
            name="interval",
            type="integer",
            description="Monitoring interval in seconds",
            required=False,
            default=5
        ),
        ToolParameter(
            name="alert_conditions",
            type="object",
            description="Alert conditions and thresholds",
            required=False,
            default={}
        )
    ],
    returns={
        "type": "object",
        "description": "Resource monitoring results",
        "properties": {
            "current": {"type": "object", "description": "Current resource usage"},
            "averages": {"type": "object", "description": "Average resource usage"},
            "peaks": {"type": "object", "description": "Peak resource usage"},
            "history": {"type": "object", "description": "Historical data"},
            "alerts": {"type": "array", "description": "Alert conditions"}
        }
    }
)


# Sandbox Tool Schema
SANDBOX_SCHEMA = ToolSchema(
    name="sandbox",
    description="Secure code execution sandbox with process isolation",
    category="system",
    parameters=[
        ToolParameter(
            name="code",
            type="string",
            description="Code to execute",
            required=True
        ),
        ToolParameter(
            name="language",
            type="string",
            description="Programming language",
            required=False,
            default="python"
        ),
        ToolParameter(
            name="timeout",
            type="integer",
            description="Execution timeout in seconds",
            required=False,
            default=30
        ),
        ToolParameter(
            name="working_directory",
            type="string",
            description="Working directory for execution",
            required=False
        ),
        ToolParameter(
            name="environment_vars",
            type="object",
            description="Environment variables",
            required=False,
            default={}
        )
    ],
    returns={
        "type": "object",
        "description": "Sandbox execution result",
        "properties": {
            "stdout": {"type": "string", "description": "Standard output"},
            "stderr": {"type": "string", "description": "Standard error"},
            "exit_code": {"type": "integer", "description": "Process exit code"},
            "execution_time": {"type": "float", "description": "Execution time in seconds"},
            "memory_used": {"type": "integer", "description": "Memory used in bytes"}
        }
    }
)


# Shell Executor Tool Schema
SHELL_EXECUTOR_SCHEMA = ToolSchema(
    name="shell_execute",
    description="Execute shell commands with security controls and monitoring",
    category="system",
    parameters=[
        ToolParameter(
            name="command",
            type="string",
            description="Shell command to execute",
            required=True
        ),
        ToolParameter(
            name="timeout",
            type="integer",
            description="Timeout in seconds",
            required=False,
            default=120
        ),
        ToolParameter(
            name="working_dir",
            type="string",
            description="Working directory",
            required=False,
            format="file-path"
        ),
        ToolParameter(
            name="environment",
            type="object",
            description="Environment variables",
            required=False
        ),
        ToolParameter(
            name="capture_output",
            type="boolean",
            description="Capture command output",
            required=False,
            default=True
        ),
        ToolParameter(
            name="shell",
            type="boolean",
            description="Use system shell",
            required=False,
            default=True
        ),
        ToolParameter(
            name="check_return_code",
            type="boolean",
            description="Check return code for success",
            required=False,
            default=False
        )
    ],
    returns={
        "type": "object",
        "description": "Command execution result",
        "properties": {
            "output": {"type": "string", "description": "Command output"},
            "stderr": {"type": "string", "description": "Standard error"},
            "return_code": {"type": "integer", "description": "Process return code"},
            "pid": {"type": "integer", "description": "Process ID"},
            "execution_time": {"type": "float", "description": "Execution time in seconds"},
            "timeout": {"type": "boolean", "description": "Whether command timed out"}
        }
    }
)


# System Info Tool Schema
SYSTEM_INFO_SCHEMA = ToolSchema(
    name="system_info",
    description="Collect comprehensive system information",
    category="system",
    parameters=[
        ToolParameter(
            name="info_type",
            type="string",
            description="Type of information to collect (all, hardware, software, network, environment)",
            required=False,
            default="all"
        ),
        ToolParameter(
            name="include_sensitive",
            type="boolean",
            description="Include potentially sensitive information",
            required=False,
            default=False
        )
    ],
    returns={
        "type": "object",
        "description": "System information results",
        "properties": {
            "hardware": {"type": "object", "description": "Hardware information"},
            "software": {"type": "object", "description": "Software information"},
            "network": {"type": "object", "description": "Network information"},
            "environment": {"type": "object", "description": "Environment variables"},
            "timestamp": {"type": "string", "description": "Collection timestamp"}
        }
    }
)


# Dictionary of all system tool schemas
SYSTEM_SCHEMAS = {
    "process_manager": PROCESS_MANAGER_SCHEMA,
    "resource_monitor": RESOURCE_MONITOR_SCHEMA,
    "sandbox": SANDBOX_SCHEMA,
    "shell_executor": SHELL_EXECUTOR_SCHEMA,
    "system_info": SYSTEM_INFO_SCHEMA
}


# Export schemas for easy import
__all__ = [
    "PROCESS_MANAGER_SCHEMA",
    "RESOURCE_MONITOR_SCHEMA",
    "SANDBOX_SCHEMA",
    "SHELL_EXECUTOR_SCHEMA",
    "SYSTEM_INFO_SCHEMA",
    "SYSTEM_SCHEMAS"
]
