"""
MCP Service Module

Service layer for MCP (Model Context Protocol) operations.
Provides high-level services for managing MCP connections, tools, and resources.
"""

import logging
from collections.abc import Callable
from datetime import datetime
from typing import Any

from mindflow_backend.config.mcp import get_mcp_settings
from mindflow_backend.interfaces.mcp.client import MCPClient, MCPClientConfig
from mindflow_backend.interfaces.mcp.handlers.resources import CompositeResourceAccessor
from mindflow_backend.interfaces.mcp.handlers.tools import SimpleToolExecutor
from mindflow_backend.interfaces.mcp.server import MCPServer, MCPServerConfig
from mindflow_backend.schemas.mcp.base import MCPCapability
from mindflow_backend.schemas.mcp.resources import MCPResourceDefinition, MCPResourceResult
from mindflow_backend.schemas.mcp.tools import MCPToolDefinition, MCPToolResult


class MCPServiceError(Exception):
    """Base exception for MCP service errors."""
    pass


class MCPConnectionManager:
    """
    Manager for MCP client connections.
    
    This service manages multiple MCP client connections,
    handles connection lifecycle, and provides connection pooling.
    """
    
    def __init__(self):
        """Initialize connection manager."""
        self.logger = logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}")
        self._clients: dict[str, MCPClient] = {}
        self._client_configs: dict[str, MCPClientConfig] = {}
        self._connection_stats: dict[str, dict[str, Any]] = {}
    
    async def create_client(
        self,
        name: str,
        transport_config,
        client_info: dict[str, Any] | None = None,
        capabilities: list[MCPCapability] | None = None
    ) -> MCPClient:
        """
        Create and configure an MCP client.
        
        Args:
            name: Unique client name
            transport_config: Transport configuration
            client_info: Client information
            capabilities: Client capabilities
            
        Returns:
            MCPClient: Created client
            
        Raises:
            MCPServiceError: If client creation fails
        """
        if name in self._clients:
            raise MCPServiceError(f"Client '{name}' already exists")
        
        try:
            # Create client config
            client_config = MCPClientConfig(
                transport_config=transport_config,
                client_info=client_info,
                capabilities=capabilities or []
            )
            
            # Create client
            client = MCPClient(client_config)
            
            # Store client
            self._clients[name] = client
            self._client_configs[name] = client_config
            self._connection_stats[name] = {
                "created_at": datetime.utcnow().isoformat(),
                "connected_at": None,
                "connection_count": 0,
                "last_connected": None,
                "last_disconnected": None,
            }
            
            self.logger.info(f"Created MCP client: {name}")
            return client
            
        except Exception as e:
            raise MCPServiceError(f"Failed to create client '{name}': {e}")
    
    async def connect_client(self, name: str) -> None:
        """
        Connect an MCP client.
        
        Args:
            name: Client name
            
        Raises:
            MCPServiceError: If connection fails
        """
        if name not in self._clients:
            raise MCPServiceError(f"Client '{name}' not found")
        
        try:
            client = self._clients[name]
            await client.connect()
            
            # Update stats
            self._connection_stats[name]["connected_at"] = datetime.utcnow().isoformat()
            self._connection_stats[name]["connection_count"] += 1
            self._connection_stats[name]["last_connected"] = datetime.utcnow().isoformat()
            
            self.logger.info(f"Connected MCP client: {name}")
            
        except Exception as e:
            raise MCPServiceError(f"Failed to connect client '{name}': {e}")
    
    async def disconnect_client(self, name: str) -> None:
        """
        Disconnect an MCP client.
        
        Args:
            name: Client name
        """
        if name not in self._clients:
            return
        
        try:
            client = self._clients[name]
            await client.disconnect()
            
            # Update stats
            self._connection_stats[name]["last_disconnected"] = datetime.utcnow().isoformat()
            
            self.logger.info(f"Disconnected MCP client: {name}")
            
        except Exception as e:
            self.logger.error(f"Error disconnecting client '{name}': {e}")
    
    def get_client(self, name: str) -> MCPClient | None:
        """
        Get an MCP client by name.
        
        Args:
            name: Client name
            
        Returns:
            Optional[MCPClient]: Client if found
        """
        return self._clients.get(name)
    
    def list_clients(self) -> list[str]:
        """
        Get list of client names.
        
        Returns:
            List[str]: Client names
        """
        return list(self._clients.keys())
    
    def get_connection_stats(self, name: str) -> dict[str, Any] | None:
        """
        Get connection statistics for a client.
        
        Args:
            name: Client name
            
        Returns:
            Optional[Dict[str, Any]]: Connection stats
        """
        stats = self._connection_stats.get(name, {}).copy()
        if name in self._clients:
            client = self._clients[name]
            stats["is_connected"] = client.is_connected
            stats["is_initialized"] = client.is_initialized
            stats["available_tools"] = len(client.available_tools)
            stats["available_resources"] = len(client.available_resources)
        return stats
    
    async def remove_client(self, name: str) -> None:
        """
        Remove an MCP client.
        
        Args:
            name: Client name
        """
        if name not in self._clients:
            return
        
        # Disconnect if connected
        await self.disconnect_client(name)
        
        # Remove from storage
        del self._clients[name]
        del self._client_configs[name]
        del self._connection_stats[name]
        
        self.logger.info(f"Removed MCP client: {name}")


class MCPServerManager:
    """
    Manager for MCP server instances.
    
    This service manages multiple MCP server instances,
    handles server lifecycle, and provides server monitoring.
    """
    
    def __init__(self):
        """Initialize server manager."""
        self.logger = logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}")
        self._servers: dict[str, MCPServer] = {}
        self._server_configs: dict[str, MCPServerConfig] = {}
        self._server_stats: dict[str, dict[str, Any]] = {}
    
    async def create_server(
        self,
        name: str,
        transport_configs: list,
        server_info: dict[str, Any] | None = None,
        capabilities: list[MCPCapability] | None = None
    ) -> MCPServer:
        """
        Create and configure an MCP server.
        
        Args:
            name: Unique server name
            transport_configs: List of transport configurations
            server_info: Server information
            capabilities: Server capabilities
            
        Returns:
            MCPServer: Created server
            
        Raises:
            MCPServiceError: If server creation fails
        """
        if name in self._servers:
            raise MCPServiceError(f"Server '{name}' already exists")
        
        try:
            # Create server config
            server_config = MCPServerConfig(
                transport_configs=transport_configs,
                server_info=server_info,
                capabilities=capabilities or []
            )
            
            # Create server
            server = MCPServer(server_config)
            
            # Store server
            self._servers[name] = server
            self._server_configs[name] = server_config
            self._server_stats[name] = {
                "created_at": datetime.utcnow().isoformat(),
                "started_at": None,
                "connection_count": 0,
                "last_started": None,
                "last_stopped": None,
            }
            
            self.logger.info(f"Created MCP server: {name}")
            return server
            
        except Exception as e:
            raise MCPServiceError(f"Failed to create server '{name}': {e}")
    
    async def start_server(self, name: str) -> None:
        """
        Start an MCP server.
        
        Args:
            name: Server name
            
        Raises:
            MCPServiceError: If server start fails
        """
        if name not in self._servers:
            raise MCPServiceError(f"Server '{name}' not found")
        
        try:
            server = self._servers[name]
            await server.start()
            
            # Update stats
            self._server_stats[name]["started_at"] = datetime.utcnow().isoformat()
            self._server_stats[name]["last_started"] = datetime.utcnow().isoformat()
            
            self.logger.info(f"Started MCP server: {name}")
            
        except Exception as e:
            raise MCPServiceError(f"Failed to start server '{name}': {e}")
    
    async def stop_server(self, name: str) -> None:
        """
        Stop an MCP server.
        
        Args:
            name: Server name
        """
        if name not in self._servers:
            return
        
        try:
            server = self._servers[name]
            await server.stop()
            
            # Update stats
            self._server_stats[name]["last_stopped"] = datetime.utcnow().isoformat()
            
            self.logger.info(f"Stopped MCP server: {name}")
            
        except Exception as e:
            self.logger.error(f"Error stopping server '{name}': {e}")
    
    def get_server(self, name: str) -> MCPServer | None:
        """
        Get an MCP server by name.
        
        Args:
            name: Server name
            
        Returns:
            Optional[MCPServer]: Server if found
        """
        return self._servers.get(name)
    
    def list_servers(self) -> list[str]:
        """
        Get list of server names.
        
        Returns:
            List[str]: Server names
        """
        return list(self._servers.keys())
    
    def get_server_stats(self, name: str) -> dict[str, Any] | None:
        """
        Get statistics for a server.
        
        Args:
            name: Server name
            
        Returns:
            Optional[Dict[str, Any]]: Server stats
        """
        stats = self._server_stats.get(name, {}).copy()
        if name in self._servers:
            server = self._servers[name]
            stats["is_running"] = server.is_running
            stats["connection_count"] = server.connection_count
            stats["available_tools"] = len(server.available_tools)
            stats["available_resources"] = len(server.available_resources)
        return stats
    
    async def remove_server(self, name: str) -> None:
        """
        Remove an MCP server.
        
        Args:
            name: Server name
        """
        if name not in self._servers:
            return
        
        # Stop if running
        await self.stop_server(name)
        
        # Remove from storage
        del self._servers[name]
        del self._server_configs[name]
        del self._server_stats[name]
        
        self.logger.info(f"Removed MCP server: {name}")


class MCPToolService:
    """
    Service for managing MCP tools.
    
    This service provides tool registration, discovery, and execution
    capabilities across multiple MCP connections.
    """
    
    def __init__(self):
        """Initialize tool service."""
        self.logger = logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}")
        self._tool_executors: dict[str, SimpleToolExecutor] = {}
        self._registered_tools: dict[str, MCPToolDefinition] = {}
    
    def register_tool_executor(self, name: str, executor: SimpleToolExecutor) -> None:
        """
        Register a tool executor.
        
        Args:
            name: Executor name
            executor: Tool executor instance
        """
        self._tool_executors[name] = executor
        self.logger.info(f"Registered tool executor: {name}")
    
    def register_tool(self, executor_name: str, tool_def: MCPToolDefinition, func: Callable) -> None:
        """
        Register a tool with an executor.
        
        Args:
            executor_name: Name of the executor
            tool_def: Tool definition
            func: Tool function
        """
        if executor_name not in self._tool_executors:
            raise MCPServiceError(f"Tool executor '{executor_name}' not found")
        
        executor = self._tool_executors[executor_name]
        executor.register_tool(tool_def.name, func, tool_def)
        self._registered_tools[tool_def.name] = tool_def
        
        self.logger.info(f"Registered tool: {tool_def.name}")
    
    async def execute_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        executor_name: str | None = None
    ) -> MCPToolResult:
        """
        Execute a tool.
        
        Args:
            tool_name: Name of the tool to execute
            arguments: Tool arguments
            executor_name: Specific executor to use (optional)
            
        Returns:
            MCPToolResult: Execution result
        """
        # Try specific executor first
        if executor_name and executor_name in self._tool_executors:
            executor = self._tool_executors[executor_name]
            return await executor.execute(tool_name, arguments)
        
        # Try all executors
        for executor in self._tool_executors.values():
            if tool_name in executor._tool_definitions:
                return await executor.execute(tool_name, arguments)
        
        return MCPToolResult.error_result(
            error=f"Tool '{tool_name}' not found",
            error_code="TOOL_NOT_FOUND"
        )
    
    def list_tools(self) -> list[MCPToolDefinition]:
        """
        Get list of all registered tools.
        
        Returns:
            List[MCPToolDefinition]: Registered tools
        """
        return list(self._registered_tools.values())
    
    def get_tool_definition(self, tool_name: str) -> MCPToolDefinition | None:
        """
        Get tool definition by name.
        
        Args:
            tool_name: Tool name
            
        Returns:
            Optional[MCPToolDefinition]: Tool definition if found
        """
        return self._registered_tools.get(tool_name)


class MCPResourceService:
    """
    Service for managing MCP resources.
    
    This service provides resource registration, discovery, and access
    capabilities across multiple MCP connections.
    """
    
    def __init__(self):
        """Initialize resource service."""
        self.logger = logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}")
        self._resource_accessor = CompositeResourceAccessor()
        self._registered_resources: dict[str, MCPResourceDefinition] = {}
    
    def register_resource_accessor(self, scheme: str, accessor) -> None:
        """
        Register a resource accessor for a URI scheme.
        
        Args:
            scheme: URI scheme (e.g., "file", "http", "memory")
            accessor: Resource accessor instance
        """
        self._resource_accessor.register_accessor(scheme, accessor)
        self.logger.info(f"Registered resource accessor for scheme: {scheme}")
    
    def register_resource(self, resource_def: MCPResourceDefinition) -> None:
        """
        Register a resource definition.
        
        Args:
            resource_def: Resource definition
        """
        self._registered_resources[resource_def.uri] = resource_def
        self.logger.info(f"Registered resource: {resource_def.uri}")
    
    async def read_resource(self, resource_uri: str, options: dict[str, Any] | None = None) -> MCPResourceResult:
        """
        Read a resource.
        
        Args:
            resource_uri: URI of the resource to read
            options: Additional options for reading
            
        Returns:
            MCPResourceResult: Resource read result
        """
        return await self._resource_accessor.read_resource(resource_uri, options or {})
    
    def list_resources(self) -> list[MCPResourceDefinition]:
        """
        Get list of all registered resources.
        
        Returns:
            List[MCPResourceDefinition]: Registered resources
        """
        return list(self._registered_resources.values())
    
    def get_resource_definition(self, resource_uri: str) -> MCPResourceDefinition | None:
        """
        Get resource definition by URI.
        
        Args:
            resource_uri: Resource URI
            
        Returns:
            Optional[MCPResourceDefinition]: Resource definition if found
        """
        return self._registered_resources.get(resource_uri)


class MCPService:
    """
    Main MCP service that coordinates all MCP operations.
    
    This service provides a unified interface for managing MCP clients,
    servers, tools, and resources in the MindFlow system.
    """
    
    def __init__(self):
        """Initialize MCP service."""
        self.logger = logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}")
        self.settings = get_mcp_settings()
        
        # Initialize sub-services
        self.connection_manager = MCPConnectionManager()
        self.server_manager = MCPServerManager()
        self.tool_service = MCPToolService()
        self.resource_service = MCPResourceService()
        
        self._initialized = False
    
    async def initialize(self) -> None:
        """
        Initialize the MCP service.
        
        Raises:
            MCPServiceError: If initialization fails
        """
        if self._initialized:
            return
        
        try:
            if not self.settings.enabled:
                self.logger.info("MCP service is disabled")
                return
            
            self.logger.info("Initializing MCP service")
            
            # Initialize default tool executor
            default_executor = SimpleToolExecutor()
            self.tool_service.register_tool_executor("default", default_executor)
            
            # Initialize default resource accessor
            from mindflow_backend.interfaces.mcp.handlers.resources import (
                FileSystemResourceAccessor,
                MemoryResourceAccessor,
            )
            fs_accessor = FileSystemResourceAccessor()
            mem_accessor = MemoryResourceAccessor()
            self.resource_service.register_resource_accessor("file", fs_accessor)
            self.resource_service.register_resource_accessor("memory", mem_accessor)
            
            self._initialized = True
            self.logger.info("MCP service initialized successfully")
            
        except Exception as e:
            raise MCPServiceError(f"Failed to initialize MCP service: {e}")
    
    async def shutdown(self) -> None:
        """Shutdown the MCP service."""
        if not self._initialized:
            return
        
        self.logger.info("Shutting down MCP service")
        
        # Stop all servers
        for server_name in self.server_manager.list_servers():
            await self.server_manager.stop_server(server_name)
        
        # Disconnect all clients
        for client_name in self.connection_manager.list_clients():
            await self.connection_manager.disconnect_client(client_name)
        
        self._initialized = False
        self.logger.info("MCP service shutdown complete")
    
    def get_status(self) -> dict[str, Any]:
        """
        Get service status.
        
        Returns:
            Dict[str, Any]: Service status
        """
        return {
            "initialized": self._initialized,
            "enabled": self.settings.enabled,
            "clients": {
                name: self.connection_manager.get_connection_stats(name)
                for name in self.connection_manager.list_clients()
            },
            "servers": {
                name: self.server_manager.get_server_stats(name)
                for name in self.server_manager.list_servers()
            },
            "tools": len(self.tool_service.list_tools()),
            "resources": len(self.resource_service.list_resources())
        }


# Global service instance
_service: MCPService | None = None


def get_mcp_service() -> MCPService:
    """
    Get the global MCP service instance.
    
    Returns:
        MCPService: MCP service instance
    """
    global _service
    
    if _service is None:
        _service = MCPService()
    
    return _service


async def initialize_mcp_service() -> None:
    """Initialize the global MCP service."""
    await get_mcp_service().initialize()


async def shutdown_mcp_service() -> None:
    """Shutdown the global MCP service."""
    await get_mcp_service().shutdown()
