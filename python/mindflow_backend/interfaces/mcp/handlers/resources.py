"""
MCP Resource Handlers

Handlers for processing MCP resource-related operations including
resource discovery, access, and management.
"""

import asyncio
import logging
from pathlib import Path
from typing import Any, Optional

from mindflow_backend.interfaces.mcp.handlers.message import RequestHandler
from mindflow_backend.schemas.mcp.resources import (
    MCPResourceAccess,
    MCPResourceDefinition,
    MCPResourceResult,
    MCPResourceType,
)


class ResourceAccessor:
    """
    Base class for resource accessors.
    
    Resource accessors are responsible for actually accessing resources
    and returning their contents or metadata.
    """
    
    def __init__(self):
        """Initialize the resource accessor."""
        self.logger = logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}")
    
    async def read_resource(self, resource_uri: str, options: dict[str, Any]) -> MCPResourceResult:
        """
        Read a resource by URI.
        
        Args:
            resource_uri: URI of the resource to read
            options: Additional options for reading
            
        Returns:
            MCPResourceResult: Resource read result
        """
        try:
            # Get resource implementation
            read_func = getattr(self, f"read_{self._get_resource_type(resource_uri)}", None)
            if not read_func:
                return MCPResourceResult.error_result(
                    error=f"Resource type not supported for URI: {resource_uri}",
                    error_code="UNSUPPORTED_RESOURCE_TYPE"
                )
            
            # Execute the read operation
            start_time = asyncio.get_event_loop().time()
            result = await read_func(resource_uri, options)
            execution_time = (asyncio.get_event_loop().time() - start_time) * 1000
            
            return MCPResourceResult.success_result(
                data=result,
                execution_time=execution_time
            )
            
        except Exception as e:
            self.logger.error(f"Error reading resource '{resource_uri}': {e}")
            return MCPResourceResult.error_result(
                error=str(e),
                error_code="READ_ERROR"
            )
    
    def _get_resource_type(self, resource_uri: str) -> str:
        """
        Extract resource type from URI.
        
        Args:
            resource_uri: Resource URI
            
        Returns:
            str: Resource type
        """
        if resource_uri.startswith("file://"):
            return "file"
        elif resource_uri.startswith("http://") or resource_uri.startswith("https://"):
            return "http"
        elif resource_uri.startswith("memory://"):
            return "memory"
        else:
            return "unknown"
    
    async def get_resource_definition(self, resource_uri: str) -> MCPResourceDefinition | None:
        """
        Get the definition for a resource.
        
        Args:
            resource_uri: URI of the resource
            
        Returns:
            Optional[MCPResourceDefinition]: Resource definition if found
        """
        # This should be implemented by subclasses
        return None


class FileSystemResourceAccessor(ResourceAccessor):
    """
    Resource accessor for file system resources.
    
    This accessor provides access to local files and directories
    through file:// URIs.
    """
    
    def __init__(self, base_path: str | None = None):
        """
        Initialize file system resource accessor.
        
        Args:
            base_path: Base path for relative file URIs
        """
        super().__init__()
        self.base_path = Path(base_path) if base_path else None
    
    async def read_file(self, resource_uri: str, options: dict[str, Any]) -> Any:
        """
        Read a file resource.
        
        Args:
            resource_uri: File URI
            options: Read options
            
        Returns:
            Any: File contents
        """
        # Extract file path from URI
        if resource_uri.startswith("file://"):
            file_path = resource_uri[7:]  # Remove "file://" prefix
        else:
            file_path = resource_uri
        
        # Resolve relative to base path if provided
        if self.base_path and not Path(file_path).is_absolute():
            file_path = self.base_path / file_path
        
        file_path = Path(file_path)
        
        # Check if file exists
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Check if it's a file
        if not file_path.is_file():
            raise ValueError(f"Path is not a file: {file_path}")
        
        # Read file based on options
        encoding = options.get("encoding", "utf-8")
        binary = options.get("binary", False)
        
        if binary:
            with open(file_path, "rb") as f:
                return f.read()
        else:
            with open(file_path, encoding=encoding) as f:
                return f.read()
    
    async def get_resource_definition(self, resource_uri: str) -> MCPResourceDefinition | None:
        """
        Get the definition for a file resource.
        
        Args:
            resource_uri: File URI
            
        Returns:
            Optional[MCPResourceDefinition]: Resource definition
        """
        try:
            # Extract file path from URI
            if resource_uri.startswith("file://"):
                file_path = resource_uri[7:]
            else:
                file_path = resource_uri
            
            # Resolve relative to base path if provided
            if self.base_path and not Path(file_path).is_absolute():
                file_path = self.base_path / file_path
            
            file_path = Path(file_path)
            
            if not file_path.exists():
                return None
            
            # Determine MIME type
            mime_type = self._get_mime_type(file_path)
            
            return MCPResourceDefinition(
                name=file_path.name,
                description=f"File resource: {file_path}",
                resource_type=MCPResourceType.FILE,
                uri=resource_uri,
                mime_type=mime_type,
                access=[MCPResourceAccess.READ],
                metadata={
                    "size": file_path.stat().st_size if file_path.is_file() else 0,
                    "modified": file_path.stat().st_mtime if file_path.is_file() else None,
                    "is_directory": file_path.is_dir(),
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error getting resource definition for '{resource_uri}': {e}")
            return None
    
    def _get_mime_type(self, file_path: Path) -> str:
        """
        Get MIME type for a file.
        
        Args:
            file_path: File path
            
        Returns:
            str: MIME type
        """
        import mimetypes
        
        mime_type, _ = mimetypes.guess_type(str(file_path))
        return mime_type or "application/octet-stream"


class MemoryResourceAccessor(ResourceAccessor):
    """
    Resource accessor for in-memory resources.
    
    This accessor provides access to in-memory data structures
    through memory:// URIs.
    """
    
    def __init__(self):
        """Initialize memory resource accessor."""
        super().__init__()
        self._resources: dict[str, Any] = {}
    
    def store_resource(self, uri: str, data: Any, metadata: dict[str, Any] | None = None) -> None:
        """
        Store a resource in memory.
        
        Args:
            uri: Resource URI
            data: Resource data
            metadata: Optional metadata
        """
        self._resources[uri] = {
            "data": data,
            "metadata": metadata or {},
            "created_at": asyncio.get_event_loop().time()
        }
    
    async def read_memory(self, resource_uri: str, options: dict[str, Any]) -> Any:
        """
        Read a memory resource.
        
        Args:
            resource_uri: Memory URI
            options: Read options
            
        Returns:
            Any: Resource data
        """
        # Extract key from URI
        if resource_uri.startswith("memory://"):
            key = resource_uri[9:]  # Remove "memory://" prefix
        else:
            key = resource_uri
        
        if key not in self._resources:
            raise KeyError(f"Memory resource not found: {key}")
        
        return self._resources[key]["data"]
    
    async def get_resource_definition(self, resource_uri: str) -> MCPResourceDefinition | None:
        """
        Get the definition for a memory resource.
        
        Args:
            resource_uri: Memory URI
            
        Returns:
            Optional[MCPResourceDefinition]: Resource definition
        """
        try:
            # Extract key from URI
            if resource_uri.startswith("memory://"):
                key = resource_uri[9:]
            else:
                key = resource_uri
            
            if key not in self._resources:
                return None
            
            resource = self._resources[key]
            
            return MCPResourceDefinition(
                name=key,
                description=f"Memory resource: {key}",
                resource_type=MCPResourceType.CUSTOM,
                uri=resource_uri,
                access=[MCPResourceAccess.READ],
                metadata=resource["metadata"]
            )
            
        except Exception as e:
            self.logger.error(f"Error getting resource definition for '{resource_uri}': {e}")
            return None


class MCPResourceHandler(RequestHandler):
    """
    Handler for MCP resource-related requests.
    
    This handler processes resource discovery and access requests
    according to the MCP specification.
    """
    
    def __init__(self, resource_accessor: ResourceAccessor):
        """
        Initialize resource handler.
        
        Args:
            resource_accessor: Resource accessor instance
        """
        super().__init__(supported_methods=["resources/list", "resources/read"])
        self.resource_accessor = resource_accessor
    
    async def handle_request(self, message) -> Optional["MCPResponse"]:
        """
        Handle resource-related requests.
        
        Args:
            message: The request message
            
        Returns:
            Optional[MCPResponse]: Response message
        """
        from mindflow_backend.schemas.mcp.base import MCPError, MCPErrorCode, MCPResponse
        
        if message.method == "resources/list":
            return await self._handle_list_resources(message)
        elif message.method == "resources/read":
            return await self._handle_read_resource(message)
        else:
            return MCPResponse(
                id=message.id,
                error=MCPError(
                    code=MCPErrorCode.METHOD_NOT_FOUND,
                    message=f"Unknown method: {message.method}"
                )
            )
    
    async def _handle_list_resources(self, message) -> "MCPResponse":
        """
        Handle resources/list request.
        
        Args:
            message: The resources/list request
            
        Returns:
            MCPResponse: Resources list response
        """
        from mindflow_backend.schemas.mcp.base import MCPResponse
        
        try:
            resources = await self._get_available_resources()
            
            return MCPResponse(
                id=message.id,
                result={
                    "resources": [resource.model_dump() for resource in resources]
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error listing resources: {e}")
            return MCPResponse(
                id=message.id,
                error=MCPError(
                    code=MCPErrorCode.INTERNAL_ERROR,
                    message=f"Failed to list resources: {e}"
                )
            )
    
    async def _handle_read_resource(self, message) -> "MCPResponse":
        """
        Handle resources/read request.
        
        Args:
            message: The resources/read request
            
        Returns:
            MCPResponse: Resource read response
        """
        from mindflow_backend.schemas.mcp.base import MCPError, MCPErrorCode, MCPResponse
        
        try:
            params = message.params or {}
            resource_uri = params.get("uri")
            options = params.get("options", {})
            
            if not resource_uri:
                return MCPResponse(
                    id=message.id,
                    error=MCPError(
                        code=MCPErrorCode.INVALID_PARAMS,
                        message="Resource URI is required"
                    )
                )
            
            # Read the resource
            result = await self.resource_accessor.read_resource(resource_uri, options)
            
            if result.success:
                return MCPResponse(
                    id=message.id,
                    result={
                        "contents": result.data,
                        "metadata": result.metadata
                    }
                )
            else:
                return MCPResponse(
                    id=message.id,
                    error=MCPError(
                        code=MCPErrorCode.INTERNAL_ERROR,
                        message=result.error or "Resource read failed"
                    )
                )
                
        except Exception as e:
            self.logger.error(f"Error reading resource: {e}")
            return MCPResponse(
                id=message.id,
                error=MCPError(
                    code=MCPErrorCode.INTERNAL_ERROR,
                    message=f"Failed to read resource: {e}"
                )
            )
    
    async def _get_available_resources(self) -> list[MCPResourceDefinition]:
        """
        Get list of available resources.
        
        Returns:
            List[MCPResourceDefinition]: Available resources
        """
        # This should be implemented by subclasses or configured
        # For now, return empty list
        return []


class CompositeResourceAccessor(ResourceAccessor):
    """
    Composite resource accessor that delegates to multiple accessors.
    
    This accessor can handle different types of resources by delegating
    to the appropriate accessor based on URI scheme.
    """
    
    def __init__(self):
        """Initialize composite resource accessor."""
        super().__init__()
        self._accessors: dict[str, ResourceAccessor] = {}
    
    def register_accessor(self, scheme: str, accessor: ResourceAccessor) -> None:
        """
        Register a resource accessor for a URI scheme.
        
        Args:
            scheme: URI scheme (e.g., "file", "http", "memory")
            accessor: Resource accessor instance
        """
        self._accessors[scheme] = accessor
        self.logger.info(f"Registered accessor for scheme: {scheme}")
    
    async def read_resource(self, resource_uri: str, options: dict[str, Any]) -> MCPResourceResult:
        """
        Read a resource by delegating to the appropriate accessor.
        
        Args:
            resource_uri: URI of the resource to read
            options: Additional options for reading
            
        Returns:
            MCPResourceResult: Resource read result
        """
        scheme = resource_uri.split("://")[0] if "://" in resource_uri else "file"
        
        if scheme not in self._accessors:
            return MCPResourceResult.error_result(
                error=f"No accessor registered for scheme: {scheme}",
                error_code="UNSUPPORTED_SCHEME"
            )
        
        accessor = self._accessors[scheme]
        return await accessor.read_resource(resource_uri, options)
    
    async def get_resource_definition(self, resource_uri: str) -> MCPResourceDefinition | None:
        """
        Get the definition for a resource by delegating to the appropriate accessor.
        
        Args:
            resource_uri: URI of the resource
            
        Returns:
            Optional[MCPResourceDefinition]: Resource definition if found
        """
        scheme = resource_uri.split("://")[0] if "://" in resource_uri else "file"
        
        if scheme not in self._accessors:
            return None
        
        accessor = self._accessors[scheme]
        return await accessor.get_resource_definition(resource_uri)
