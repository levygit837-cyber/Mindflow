"""gRPC service for managing communication and streaming.

This service provides comprehensive gRPC capabilities including
server management, connection handling, and streaming operations.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, AsyncGenerator
from datetime import datetime, UTC
import asyncio
import uuid

from omnimind_backend.infra.logging import get_logger
from omnimind_backend.services.interfaces.base_interfaces import BaseAbstractService
from omnimind_backend.services.interfaces.communication_interfaces import GrpcServiceInterface


class GrpcService(BaseAbstractService, GrpcServiceInterface):
    """Service for gRPC communication and streaming.
    
    This service provides comprehensive gRPC capabilities including
    server management, connection handling, and performance monitoring.
    """
    
    def __init__(self) -> None:
        """Initialize gRPC service with configuration."""
        super().__init__()
        
        # Server state
        self._server = None
        self._host = "localhost"
        self._port = 50051
        self._is_running = False
        
        # Connection management
        self._active_connections: Dict[str, Dict[str, Any]] = {}
        self._connection_metrics = {
            "total_connections": 0,
            "active_connections": 0,
            "failed_connections": 0
        }
        
        # Service registry
        self._registered_services: Dict[str, Any] = {}
        self._interceptors: List[Any] = []
        
        # Performance metrics
        self._request_metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "avg_response_time_ms": 0.0
        }
    
    def _get_logger(self) -> Any:
        """Get logger instance for this service."""
        return get_logger(__name__)
    
    async def start_server(self, host: str = "localhost", port: int = 50051) -> Dict[str, Any]:
        """Start gRPC server.
        
        Args:
            host: Server host
            port: Server port
            
        Returns:
            Dictionary containing server start result
        """
        self.log_operation("start_server", host=host, port=port)
        
        try:
            if self._is_running:
                return {
                    "status": "already_running",
                    "host": self._host,
                    "port": self._port,
                    "started_at": self._started_at
                }
            
            # Update server configuration
            self._host = host
            self._port = port
            
            # Create gRPC server (placeholder implementation)
            # In a real implementation, this would use grpc.aio.server()
            self._server = self._create_grpc_server()
            
            # Start server
            await self._server.start()
            
            self._is_running = True
            self._started_at = datetime.now(UTC).isoformat()
            
            return {
                "status": "started",
                "host": host,
                "port": port,
                "started_at": self._started_at,
                "registered_services": list(self._registered_services.keys()),
                "interceptors_count": len(self._interceptors)
            }
            
        except Exception as exc:
            self._logger.error(f"Error starting gRPC server: {str(exc)}")
            
            return {
                "status": "failed",
                "host": host,
                "port": port,
                "error": str(exc),
                "error_type": type(exc).__name__
            }
    
    async def stop_server(self) -> Dict[str, Any]:
        """Stop gRPC server.
        
        Returns:
            Dictionary containing server stop result
        """
        self.log_operation("stop_server")
        
        try:
            if not self._is_running:
                return {
                    "status": "not_running",
                    "message": "Server is not currently running"
                }
            
            # Stop server
            if self._server:
                await self._server.stop(0)  # Graceful stop
                self._server = None
            
            # Close all active connections
            for connection_id, connection in self._active_connections.items():
                await self._close_connection(connection_id, "server_shutdown")
            
            self._is_running = False
            stopped_at = datetime.now(UTC).isoformat()
            
            return {
                "status": "stopped",
                "stopped_at": stopped_at,
                "connections_closed": len(self._active_connections),
                "final_metrics": self._request_metrics.copy()
            }
            
        except Exception as exc:
            self._logger.error(f"Error stopping gRPC server: {str(exc)}")
            
            return {
                "status": "failed",
                "error": str(exc),
                "error_type": type(exc).__name__
            }
    
    async def handle_stream_chat(
        self,
        request: Dict[str, Any]
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Handle streaming chat requests.
        
        Args:
            request: Chat request dictionary
            
        Yields:
            Streaming response events
        """
        self.log_operation(
            "handle_stream_chat",
            session_id=request.get("session_id"),
            agent_type=request.get("agent_type")
        )
        
        try:
            # Generate connection ID
            connection_id = f"conn-{uuid.uuid4()}"
            
            # Create connection record
            connection = {
                "id": connection_id,
                "type": "stream_chat",
                "session_id": request.get("session_id"),
                "agent_type": request.get("agent_type"),
                "created_at": datetime.now(UTC).isoformat(),
                "status": "active"
            }
            
            self._active_connections[connection_id] = connection
            self._connection_metrics["active_connections"] += 1
            self._connection_metrics["total_connections"] += 1
            
            try:
                # Send initial response
                yield {
                    "type": "start",
                    "connection_id": connection_id,
                    "timestamp": datetime.now(UTC).isoformat(),
                    "status": "connected"
                }
                
                # Process the actual request
                async for event in self._process_chat_request(request, connection_id):
                    yield event
                
                # Send completion event
                yield {
                    "type": "end",
                    "connection_id": connection_id,
                    "timestamp": datetime.now(UTC).isoformat(),
                    "status": "completed"
                }
                
            finally:
                # Clean up connection
                await self._close_connection(connection_id, "completed")
                
        except Exception as exc:
            self._logger.error(f"Error handling stream chat: {str(exc)}")
            
            # Send error event
            yield {
                "type": "error",
                "connection_id": connection_id,
                "timestamp": datetime.now(UTC).isoformat(),
                "error": str(exc),
                "error_type": type(exc).__name__
            }
    
    async def get_server_status(self) -> Dict[str, Any]:
        """Get gRPC server status.
        
        Returns:
            Dictionary containing server status information
        """
        self.log_operation("get_server_status")
        
        try:
            return {
                "is_running": self._is_running,
                "host": self._host,
                "port": self._port,
                "started_at": getattr(self, '_started_at', None),
                "uptime_seconds": self._calculate_uptime(),
                "connections": {
                    "active": self._connection_metrics["active_connections"],
                    "total": self._connection_metrics["total_connections"],
                    "failed": self._connection_metrics["failed_connections"]
                },
                "services": {
                    "registered": list(self._registered_services.keys()),
                    "count": len(self._registered_services)
                },
                "metrics": self._request_metrics.copy(),
                "status": "healthy" if self._is_running else "stopped"
            }
            
        except Exception as exc:
            self._logger.error(f"Error getting server status: {str(exc)}")
            
            return {
                "status": "error",
                "error": str(exc),
                "error_type": type(exc).__name__
            }
    
    async def register_service(
        self,
        service_name: str,
        service_implementation: Any
    ) -> Dict[str, Any]:
        """Register a gRPC service.
        
        Args:
            service_name: Name of the service
            service_implementation: Service implementation
            
        Returns:
            Dictionary containing registration result
        """
        self.log_operation("register_service", service_name=service_name)
        
        try:
            # Validate service implementation
            if not service_implementation:
                raise ValueError("Service implementation cannot be None")
            
            # Register service
            self._registered_services[service_name] = {
                "implementation": service_implementation,
                "registered_at": datetime.now(UTC).isoformat(),
                "status": "active"
            }
            
            # Add to server if running
            if self._server and self._is_running:
                await self._add_service_to_server(service_name, service_implementation)
            
            return {
                "service_name": service_name,
                "status": "registered",
                "registered_at": self._registered_services[service_name]["registered_at"],
                "server_running": self._is_running
            }
            
        except Exception as exc:
            self._logger.error(f"Error registering service {service_name}: {str(exc)}")
            
            return {
                "service_name": service_name,
                "status": "failed",
                "error": str(exc),
                "error_type": type(exc).__name__
            }
    
    async def get_connection_metrics(self) -> Dict[str, Any]:
        """Get connection metrics and statistics.
        
        Returns:
            Dictionary containing connection metrics
        """
        self.log_operation("get_connection_metrics")
        
        try:
            # Calculate connection statistics
            active_connections = list(self._active_connections.values())
            
            # Connection duration statistics
            if active_connections:
                now = datetime.now(UTC)
                durations = []
                for conn in active_connections:
                    created_at = datetime.fromisoformat(conn["created_at"])
                    duration = (now - created_at).total_seconds()
                    durations.append(duration)
                
                avg_duration = sum(durations) / len(durations) if durations else 0
                max_duration = max(durations) if durations else 0
                min_duration = min(durations) if durations else 0
            else:
                avg_duration = max_duration = min_duration = 0
            
            return {
                "total_connections": self._connection_metrics["total_connections"],
                "active_connections": self._connection_metrics["active_connections"],
                "failed_connections": self._connection_metrics["failed_connections"],
                "connection_statistics": {
                    "average_duration_seconds": round(avg_duration, 2),
                    "max_duration_seconds": round(max_duration, 2),
                    "min_duration_seconds": round(min_duration, 2)
                },
                "active_connections_detail": [
                    {
                        "id": conn["id"],
                        "type": conn["type"],
                        "session_id": conn.get("session_id"),
                        "created_at": conn["created_at"],
                        "duration_seconds": (datetime.now(UTC) - datetime.fromisoformat(conn["created_at"])).total_seconds()
                    }
                    for conn in active_connections
                ],
                "generated_at": datetime.now(UTC).isoformat()
            }
            
        except Exception as exc:
            self._logger.error(f"Error getting connection metrics: {str(exc)}")
            raise
    
    async def configure_interceptors(
        self,
        interceptors: List[Any]
    ) -> Dict[str, Any]:
        """Configure gRPC interceptors.
        
        Args:
            interceptors: List of interceptor instances
            
        Returns:
            Dictionary containing configuration result
        """
        self.log_operation("configure_interceptors", interceptor_count=len(interceptors))
        
        try:
            # Validate interceptors
            for interceptor in interceptors:
                if not hasattr(interceptor, 'intercept'):
                    raise ValueError("Interceptor must have 'intercept' method")
            
            # Store interceptors
            self._interceptors = interceptors.copy()
            
            # Apply to server if running
            if self._server and self._is_running:
                await self._apply_interceptors_to_server(interceptors)
            
            return {
                "status": "configured",
                "interceptor_count": len(interceptors),
                "interceptor_types": [type(i).__name__ for i in interceptors],
                "configured_at": datetime.now(UTC).isoformat()
            }
            
        except Exception as exc:
            self._logger.error(f"Error configuring interceptors: {str(exc)}")
            
            return {
                "status": "failed",
                "error": str(exc),
                "error_type": type(exc).__name__
            }
    
    async def test_connection(self, endpoint: str) -> Dict[str, Any]:
        """Test gRPC connection to an endpoint.
        
        Args:
            endpoint: gRPC endpoint to test
            
        Returns:
            Dictionary containing connection test result
        """
        self.log_operation("test_connection", endpoint=endpoint)
        
        try:
            # Parse endpoint
            if ":" not in endpoint:
                raise ValueError("Invalid endpoint format. Expected host:port")
            
            host, port_str = endpoint.rsplit(":", 1)
            port = int(port_str)
            
            # Test connection (placeholder implementation)
            start_time = datetime.now(UTC)
            
            # In a real implementation, this would use grpc.aio.insecure_channel()
            # For now, we'll simulate the connection test
            await asyncio.sleep(0.1)  # Simulate connection time
            
            end_time = datetime.now(UTC)
            latency_ms = int((end_time - start_time).total_seconds() * 1000)
            
            return {
                "endpoint": endpoint,
                "status": "connected",
                "latency_ms": latency_ms,
                "tested_at": end_time.isoformat(),
                "host": host,
                "port": port
            }
            
        except Exception as exc:
            return {
                "endpoint": endpoint,
                "status": "failed",
                "error": str(exc),
                "error_type": type(exc).__name__,
                "tested_at": datetime.now(UTC).isoformat()
            }
    
    # Helper methods
    
    def _create_grpc_server(self) -> Any:
        """Create gRPC server instance."""
        # Placeholder implementation
        # In a real implementation, this would create a grpc.aio.server()
        # and register all services
        
        class MockServer:
            def __init__(self):
                self.services = {}
                self.interceptors = []
                self.running = False
            
            async def start(self):
                self.running = True
            
            async def stop(self, grace):
                self.running = False
            
            async def add_service(self, name, service):
                self.services[name] = service
            
            async def add_interceptors(self, interceptors):
                self.interceptors = interceptors
        
        return MockServer()
    
    async def _add_service_to_server(self, service_name: str, service_implementation: Any) -> None:
        """Add service to running server."""
        if self._server and hasattr(self._server, 'add_service'):
            await self._server.add_service(service_name, service_implementation)
    
    async def _apply_interceptors_to_server(self, interceptors: List[Any]) -> None:
        """Apply interceptors to running server."""
        if self._server and hasattr(self._server, 'add_interceptors'):
            await self._server.add_interceptors(interceptors)
    
    async def _process_chat_request(self, request: Dict[str, Any], connection_id: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Process chat request and yield response events."""
        try:
            # Update request metrics
            self._request_metrics["total_requests"] += 1
            
            # Send processing event
            yield {
                "type": "processing",
                "connection_id": connection_id,
                "timestamp": datetime.now(UTC).isoformat(),
                "message": "Processing your request..."
            }
            
            # Get agent service to handle request
            from omnimind_backend.services import get_agent_service
            agent_service = get_agent_service()
            
            # Process the request
            result = await agent_service.process_agent_request(
                message=request.get("message", ""),
                agent_type=request.get("agent_type"),
                provider=request.get("provider"),
                model=request.get("model"),
                session_id=request.get("session_id"),
                orchestrate=request.get("orchestrate", False)
            )
            
            # Send response events
            if result.get("status") == "success":
                self._request_metrics["successful_requests"] += 1
                
                yield {
                    "type": "response",
                    "connection_id": connection_id,
                    "timestamp": datetime.now(UTC).isoformat(),
                    "data": result.get("response", ""),
                    "metadata": {
                        "agent_type": result.get("agent_type"),
                        "provider": result.get("provider"),
                        "model": result.get("model")
                    }
                }
            else:
                self._request_metrics["failed_requests"] += 1
                
                yield {
                    "type": "error",
                    "connection_id": connection_id,
                    "timestamp": datetime.now(UTC).isoformat(),
                    "error": result.get("error", "Unknown error"),
                    "error_type": "processing_error"
                }
            
        except Exception as exc:
            self._request_metrics["failed_requests"] += 1
            self._logger.error(f"Error processing chat request: {str(exc)}")
            
            yield {
                "type": "error",
                "connection_id": connection_id,
                "timestamp": datetime.now(UTC).isoformat(),
                "error": str(exc),
                "error_type": "system_error"
            }
    
    async def _close_connection(self, connection_id: str, reason: str) -> None:
        """Close a connection and update metrics."""
        if connection_id in self._active_connections:
            connection = self._active_connections[connection_id]
            connection["status"] = "closed"
            connection["closed_at"] = datetime.now(UTC).isoformat()
            connection["close_reason"] = reason
            
            del self._active_connections[connection_id]
            self._connection_metrics["active_connections"] -= 1
    
    def _calculate_uptime(self) -> int:
        """Calculate server uptime in seconds."""
        if not self._is_running or not hasattr(self, '_started_at'):
            return 0
        
        started_at = datetime.fromisoformat(self._started_at)
        uptime = datetime.now(UTC) - started_at
        return int(uptime.total_seconds())
