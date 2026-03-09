"""Filesystem tool schemas for MindFlow agents.

Provides standardized schemas for filesystem-related tools including
file operations, directory listing, search tools, and file manipulation.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from mindflow_backend.schemas.tools.tool_config import ToolParameter, ToolSchema


# File Read Tool Schema
READ_FILE_SCHEMA = ToolSchema(
    name="read_file",
    description="Read file contents with security controls",
    category="filesystem",
    parameters=[
        ToolParameter(
            name="file_path",
            type="string",
            description="Path to file to read",
            required=True
        ),
        ToolParameter(
            name="encoding",
            type="string",
            description="File encoding",
            required=False,
            default="utf-8"
        ),
        ToolParameter(
            name="max_lines",
            type="integer",
            description="Maximum number of lines to read",
            required=False
        )
    ],
    returns={
        "type": "object",
        "description": "File read operation result",
        "properties": {
            "content": {"type": "string", "description": "File content"},
            "line_count": {"type": "integer", "description": "Number of lines read"},
            "file_size": {"type": "integer", "description": "File size in bytes"},
            "encoding": {"type": "string", "description": "File encoding used"}
        }
    }
)


# File Write Tool Schema
WRITE_FILE_SCHEMA = ToolSchema(
    name="write_file",
    description="Write content to files with security controls",
    category="filesystem",
    parameters=[
        ToolParameter(
            name="file_path",
            type="string",
            description="Path to file to write",
            required=True
        ),
        ToolParameter(
            name="content",
            type="string",
            description="Content to write to file",
            required=True
        ),
        ToolParameter(
            name="encoding",
            type="string",
            description="File encoding",
            required=False,
            default="utf-8"
        ),
        ToolParameter(
            name="create_dirs",
            type="boolean",
            description="Create parent directories if they don't exist",
            required=False,
            default=True
        )
    ],
    returns={
        "type": "object",
        "description": "File write operation result",
        "properties": {
            "bytes_written": {"type": "integer", "description": "Number of bytes written"},
            "file_path": {"type": "string", "description": "Full path to written file"},
            "encoding": {"type": "string", "description": "Encoding used"}
        }
    }
)


# File Edit Tool Schema
EDIT_FILE_SCHEMA = ToolSchema(
    name="edit_file",
    description="Edit a file by replacing a substring (single occurrence)",
    category="filesystem",
    parameters=[
        ToolParameter(
            name="file_path",
            type="string",
            description="Path to file",
            required=True
        ),
        ToolParameter(
            name="old_string",
            type="string",
            description="Text to replace",
            required=True
        ),
        ToolParameter(
            name="new_string",
            type="string",
            description="Replacement text",
            required=True
        ),
        ToolParameter(
            name="count",
            type="integer",
            description="Max replacements",
            required=False,
            default=1
        ),
        ToolParameter(
            name="encoding",
            type="string",
            description="Encoding",
            required=False,
            default="utf-8"
        )
    ],
    returns={
        "type": "object",
        "description": "Edit result",
        "properties": {
            "success": {"type": "boolean"},
            "replacements": {"type": "integer"},
        }
    }
)


# File Delete Tool Schema
DELETE_FILE_SCHEMA = ToolSchema(
    name="delete_file",
    description="Delete files with security controls",
    category="filesystem",
    parameters=[
        ToolParameter(
            name="file_path",
            type="string",
            description="Path to file or directory to delete",
            required=True
        ),
        ToolParameter(
            name="recursive",
            type="boolean",
            description="Delete directories recursively",
            required=False,
            default=False
        ),
        ToolParameter(
            name="force",
            type="boolean",
            description="Force deletion without confirmation",
            required=False,
            default=False
        )
    ],
    returns={
        "type": "object",
        "description": "File deletion result",
        "properties": {
            "deleted": {"type": "boolean", "description": "Whether file was deleted"},
            "file_path": {"type": "string", "description": "Path that was deleted"}
        }
    }
)


# Directory List Tool Schema
LIST_DIRECTORY_SCHEMA = ToolSchema(
    name="list_directory",
    description="List directory contents with security controls",
    category="filesystem",
    parameters=[
        ToolParameter(
            name="directory_path",
            type="string",
            description="Path to directory to list",
            required=True
        ),
        ToolParameter(
            name="show_hidden",
            type="boolean",
            description="Include hidden files and directories",
            required=False,
            default=False
        ),
        ToolParameter(
            name="recursive",
            type="boolean",
            description="List directories recursively",
            required=False,
            default=False
        ),
        ToolParameter(
            name="pattern",
            type="string",
            description="Pattern to filter files (glob pattern)",
            required=False
        )
    ],
    returns={
        "type": "object",
        "description": "Directory listing result",
        "properties": {
            "files": {"type": "array", "description": "List of files"},
            "directories": {"type": "array", "description": "List of directories"},
            "total_count": {"type": "integer", "description": "Total items found"}
        }
    }
)


# Grep Search Tool Schema
GREP_SEARCH_SCHEMA = ToolSchema(
    name="grep_search",
    description="Search file contents with pattern matching",
    category="filesystem",
    parameters=[
        ToolParameter(
            name="pattern",
            type="string",
            description="Search pattern (regex or string)",
            required=True
        ),
        ToolParameter(
            name="directory",
            type="string",
            description="Directory to search in",
            required=False,
            default="."
        ),
        ToolParameter(
            name="file_pattern",
            type="string",
            description="File pattern to match (glob)",
            required=False,
            default="*"
        ),
        ToolParameter(
            name="recursive",
            type="boolean",
            description="Search recursively",
            required=False,
            default=True
        ),
        ToolParameter(
            name="case_sensitive",
            type="boolean",
            description="Case sensitive search",
            required=False,
            default=False
        ),
        ToolParameter(
            name="max_results",
            type="integer",
            description="Maximum number of results",
            required=False,
            default=100
        )
    ],
    returns={
        "type": "object",
        "description": "Search results",
        "properties": {
            "matches": {"type": "array", "description": "Found matches"},
            "total_files": {"type": "integer", "description": "Total files searched"},
            "total_matches": {"type": "integer", "description": "Total matches found"}
        }
    }
)


# Glob Search Tool Schema
GLOB_SEARCH_SCHEMA = ToolSchema(
    name="glob_search",
    description="Find files matching a glob pattern",
    category="filesystem",
    parameters=[
        ToolParameter(
            name="pattern",
            type="string",
            description="Glob pattern (e.g. **/*.py)",
            required=True
        ),
        ToolParameter(
            name="directory",
            type="string",
            description="Directory to search in",
            required=False,
            default="."
        ),
        ToolParameter(
            name="max_results",
            type="integer",
            description="Maximum number of results",
            required=False,
            default=200
        )
    ],
    returns={
        "type": "object",
        "description": "Glob results",
        "properties": {
            "files": {"type": "array"},
            "total_count": {"type": "integer"},
        }
    }
)


# File Finder Tool Schema
FILE_FINDER_SCHEMA = ToolSchema(
    name="file_finder",
    description="Find files by name, size, date, and other criteria",
    category="filesystem",
    parameters=[
        ToolParameter(
            name="pattern",
            type="string",
            description="File name pattern (glob)",
            required=True
        ),
        ToolParameter(
            name="directory",
            type="string",
            description="Directory to search in",
            required=False,
            default="."
        ),
        ToolParameter(
            name="min_size",
            type="integer",
            description="Minimum file size in bytes",
            required=False
        ),
        ToolParameter(
            name="max_size",
            type="integer",
            description="Maximum file size in bytes",
            required=False
        ),
        ToolParameter(
            name="min_date",
            type="string",
            description="Minimum modification date (YYYY-MM-DD)",
            required=False
        ),
        ToolParameter(
            name="max_date",
            type="string",
            description="Maximum modification date (YYYY-MM-DD)",
            required=False
        ),
        ToolParameter(
            name="max_results",
            type="integer",
            description="Maximum number of results",
            required=False,
            default=100
        )
    ],
    returns={
        "type": "object",
        "description": "File finder results",
        "properties": {
            "files": {"type": "array", "description": "Found files"},
            "total_count": {"type": "integer", "description": "Total files found"}
        }
    }
)


# Dictionary of all filesystem tool schemas
FILESYSTEM_SCHEMAS = {
    "read_file": READ_FILE_SCHEMA,
    "write_file": WRITE_FILE_SCHEMA,
    "edit_file": EDIT_FILE_SCHEMA,
    "delete_file": DELETE_FILE_SCHEMA,
    "list_directory": LIST_DIRECTORY_SCHEMA,
    "grep_search": GREP_SEARCH_SCHEMA,
    "glob_search": GLOB_SEARCH_SCHEMA,
    "file_finder": FILE_FINDER_SCHEMA
}


# Export schemas for easy import
__all__ = [
    "READ_FILE_SCHEMA",
    "WRITE_FILE_SCHEMA",
    "EDIT_FILE_SCHEMA",
    "DELETE_FILE_SCHEMA",
    "LIST_DIRECTORY_SCHEMA",
    "GREP_SEARCH_SCHEMA",
    "GLOB_SEARCH_SCHEMA",
    "FILE_FINDER_SCHEMA",
    "FILESYSTEM_SCHEMAS"
]
