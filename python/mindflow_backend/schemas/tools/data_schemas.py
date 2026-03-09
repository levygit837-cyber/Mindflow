"""Data tool schemas for MindFlow agents.

Provides standardized schemas for data-related tools including
database operations, CSV processing, and data analysis.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from mindflow_backend.schemas.tools.tool_config import ToolParameter, ToolSchema


# Predefined schemas for Data tools
DATABASE_SCHEMA = ToolSchema(
    name="database_manager",
    description="Database operations and query management",
    category="data",
    parameters=[
        ToolParameter(
            name="action",
            type="string",
            description="Action to perform (connect, query, execute, list_tables, schema)",
            required=True
        ),
        ToolParameter(
            name="database_type",
            type="string",
            description="Database type (sqlite, postgresql, mysql)",
            required=False,
            default="sqlite"
        ),
        ToolParameter(
            name="connection_string",
            type="string",
            description="Database connection string",
            required=False
        ),
        ToolParameter(
            name="query",
            type="string",
            description="SQL query to execute",
            required=False
        ),
        ToolParameter(
            name="table_name",
            type="string",
            description="Table name for operations",
            required=False
        )
    ],
    returns={
        "type": "object",
        "description": "Database operation result",
        "properties": {
            "action": {"type": "string", "description": "Action performed"},
            "result": {"type": "object", "description": "Operation result"}
        }
    }
)


CSV_PROCESSOR_SCHEMA = ToolSchema(
    name="csv_processor",
    description="CSV file processing and analysis",
    category="data",
    parameters=[
        ToolParameter(
            name="action",
            type="string",
            description="Action to perform (read, write, analyze, transform, info)",
            required=True
        ),
        ToolParameter(
            name="file_path",
            type="string",
            description="CSV file path",
            required=False
        ),
        ToolParameter(
            name="data",
            type="array",
            description="Data to write to CSV",
            required=False
        ),
        ToolParameter(
            name="delimiter",
            type="string",
            description="CSV delimiter",
            required=False,
            default=","
        ),
        ToolParameter(
            name="encoding",
            type="string",
            description="File encoding",
            required=False,
            default="utf-8"
        ),
        ToolParameter(
            name="headers",
            type="boolean",
            description="Whether CSV has headers",
            required=False,
            default=True
        )
    ],
    returns={
        "type": "object",
        "description": "CSV operation result",
        "properties": {
            "action": {"type": "string", "description": "Action performed"},
            "result": {"type": "object", "description": "Operation result"}
        }
    }
)


# Dictionary of all data tool schemas
DATA_SCHEMAS = {
    "database_manager": DATABASE_SCHEMA,
    "csv_processor": CSV_PROCESSOR_SCHEMA
}


# Export schemas for easy import
__all__ = [
    "DATABASE_SCHEMA",
    "CSV_PROCESSOR_SCHEMA",
    "DATA_SCHEMAS"
]
