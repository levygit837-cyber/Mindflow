"""Filesystem tool interfaces for MindFlow backend.

Provides contracts for filesystem operations including file access,
search capabilities, and directory management with proper validation
and security controls.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class FileReadTool(Protocol):
    """Interface for reading file contents."""
    
    async def read_file(
        self,
        file_path: str,
        encoding: str = "utf-8",
        offset: int = 0,
        limit: int | None = None
    ) -> dict[str, Any]:
        """Read file contents with optional offset and limit.
        
        Args:
            file_path: Path to file to read
            encoding: File encoding
            offset: Starting position in bytes
            limit: Maximum bytes to read
            
        Returns:
            Dictionary with file content and metadata
        """
        ...


@runtime_checkable
class FileWriteTool(Protocol):
    """Interface for writing file contents."""
    
    async def write_file(
        self,
        file_path: str,
        content: str,
        encoding: str = "utf-8",
        create_dirs: bool = True,
        backup: bool = False
    ) -> dict[str, Any]:
        """Write content to file with optional directory creation.
        
        Args:
            file_path: Path to file to write
            content: Content to write
            encoding: File encoding
            create_dirs: Create parent directories if needed
            backup: Create backup of existing file
            
        Returns:
            Dictionary with operation result
        """
        ...


@runtime_checkable
class FileEditTool(Protocol):
    """Interface for editing existing files."""
    
    async def edit_file(
        self,
        file_path: str,
        old_content: str,
        new_content: str,
        encoding: str = "utf-8",
        backup: bool = True
    ) -> dict[str, Any]:
        """Edit file by replacing specific content.
        
        Args:
            file_path: Path to file to edit
            old_content: Content to replace
            new_content: New content
            encoding: File encoding
            backup: Create backup before editing
            
        Returns:
            Dictionary with edit result
        """
        ...


@runtime_checkable
class DirectoryListTool(Protocol):
    """Interface for listing directory contents."""
    
    async def list_directory(
        self,
        directory_path: str,
        recursive: bool = False,
        show_hidden: bool = False,
        pattern: str | None = None
    ) -> dict[str, Any]:
        """List directory contents with filtering options.
        
        Args:
            directory_path: Path to directory
            recursive: List subdirectories recursively
            show_hidden: Include hidden files
            pattern: Filter by glob pattern
            
        Returns:
            Dictionary with directory listing
        """
        ...


@runtime_checkable
class FileDeleteTool(Protocol):
    """Interface for deleting files and directories."""
    
    async def delete_file(
        self,
        file_path: str,
        recursive: bool = False,
        force: bool = False,
        backup: bool = True
    ) -> dict[str, Any]:
        """Delete file or directory with safety options.
        
        Args:
            file_path: Path to delete
            recursive: Delete directories recursively
            force: Force deletion without confirmation
            backup: Create backup before deletion
            
        Returns:
            Dictionary with deletion result
        """
        ...


@runtime_checkable
class DirectoryCreateTool(Protocol):
    """Interface for creating directories."""
    
    async def create_directory(
        self,
        directory_path: str,
        parents: bool = True,
        exist_ok: bool = True
    ) -> dict[str, Any]:
        """Create directory with parent creation options.
        
        Args:
            directory_path: Path to create
            parents: Create parent directories
            exist_ok: Don't error if directory exists
            
        Returns:
            Dictionary with creation result
        """
        ...


@runtime_checkable
class GrepSearchTool(Protocol):
    """Interface for searching text patterns in files."""
    
    async def search_in_files(
        self,
        pattern: str,
        search_path: str,
        file_pattern: str = "*",
        case_sensitive: bool = True,
        regex: bool = True,
        max_results: int = 100,
        context_lines: int = 2
    ) -> dict[str, Any]:
        """Search for text patterns in files.
        
        Args:
            pattern: Text pattern to search for
            search_path: Directory to search in
            file_pattern: File pattern filter
            case_sensitive: Case-sensitive search
            regex: Use regex pattern matching
            max_results: Maximum results to return
            context_lines: Lines of context around matches
            
        Returns:
            Dictionary with search results
        """
        ...


@runtime_checkable
class GlobSearchTool(Protocol):
    """Interface for glob pattern file searching."""
    
    async def glob_search(
        self,
        pattern: str,
        search_path: str = ".",
        recursive: bool = True,
        max_results: int = 100
    ) -> dict[str, Any]:
        """Search files using glob patterns.
        
        Args:
            pattern: Glob pattern to match
            search_path: Directory to search
            recursive: Recursive search
            max_results: Maximum results to return
            
        Returns:
            Dictionary with matching files
        """
        ...


@runtime_checkable
class FindFilesTool(Protocol):
    """Interface for advanced file finding."""
    
    async def find_files(
        self,
        search_path: str = ".",
        name_pattern: str | None = None,
        size_min: int | None = None,
        size_max: int | None = None,
        modified_after: str | None = None,
        modified_before: str | None = None,
        file_type: str | None = None,
        max_depth: int | None = None,
        max_results: int = 100
    ) -> dict[str, Any]:
        """Find files with advanced filtering criteria.
        
        Args:
            search_path: Directory to search
            name_pattern: File name pattern
            size_min: Minimum file size in bytes
            size_max: Maximum file size in bytes
            modified_after: Modified after date (ISO format)
            modified_before: Modified before date (ISO format)
            file_type: File type filter
            max_depth: Maximum directory depth
            max_results: Maximum results to return
            
        Returns:
            Dictionary with found files
        """
        ...
