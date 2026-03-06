"""Enhanced gRPC client with monitoring and resilience.

Implements GrpcClient interface with actual gRPC communication,
comprehensive monitoring, circuit breaker, retry policies, and
proper connection management.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncGenerator
from typing import Any

import grpc
from grpc.aio import Channel, UnaryStreamCall

from omnimind_backend.grpc.interfaces.client import GrpcClient
from omnimind_backend.grpc.monitoring.metrics import GrpcMetricsCollector
from omnimind_backend.grpc.monitoring.interceptor import ClientMetricsInterceptor
from omnimind_backend.grpc.resilience.circuit_breaker import GrpcCircuitBreaker, CircuitBreakerConfig
from omnimind_backend.grpc.resilience.retry import AdvancedRetryPolicy, RetryConfig, RetryExhaustedError
from omnimind_backend.grpc.resilience.timeout import TimeoutManager, TimeoutConfig, TimeoutError
from omnimind_backend.grpc.services.agent_runtime_service import AgentRuntimeServiceImpl
from omnimind_backend.grpc.config import GrpcClientConfig
from omnimind_backend.infra.config import get_settings
from omnimind_backend.infra.logging import get_logger
from omnimind_backend.schemas.chat.agent import AgentChatRequest, StreamEvent
from omnimind_backend.schemas.core.common import LLMProvider

_logger = get_logger(__name__)


class EnhancedGrpcAgentClient(GrpcClient):
    """Enhanced gRPC client with monitoring, resilience, and advanced features."""
    
    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        secure: bool = False,
        config: GrpcClientConfig | None = None,
        enable_monitoring: bool = True,
        enable_circuit_breaker: bool = True,
        enable_retry: bool = True,
        enable_timeout_management: bool = True,
    ) -> None:
        settings = get_settings()
        
        # Configuration
        self.config = config or GrpcClientConfig.from_settings(settings)
        self.host = host or self.config.host
        self.port = port or self.config.port
        self.secure = secure or self.config.secure
        
        # Core components
        self._channel: Channel | None = None
        self._stub: Any = None
        self._connected = False
        self._connection_lock = asyncio.Lock()
        
        # Enhanced features
        self.enable_monitoring = enable_monitoring
        self.enable_circuit_breaker = enable_circuit_breaker
        self.enable_retry = enable_retry
        self.enable_timeout_management = enable_timeout_management
        
        # Initialize components
        if enable_monitoring:
            self.metrics_collector = GrpcMetricsCollector()
            self.metrics_interceptor = ClientMetricsInterceptor(self.metrics_collector)
        
        if enable_circuit_breaker:
            circuit_config = CircuitBreakerConfig(
                failure_threshold=5,
                recovery_timeout=60.0,
                success_threshold=3,
                timeout=self.config.request_timeout_seconds,
            )
            self.circuit_breaker = GrpcCircuitBreaker(f"grpc_client_{self.host}:{self.port}", circuit_config)
        
        if enable_retry:
            retry_config = RetryConfig(
                max_attempts=self.config.max_attempts,
                base_delay=0.1,
                max_delay=10.0,
                multiplier=2.0,
                jitter=True,
            )
            self.retry_policy = AdvancedRetryPolicy(retry_config)
        
        if enable_timeout_management:
            timeout_config = TimeoutConfig(
                default_timeout=self.config.request_timeout_seconds,
                enable_adaptive=True,
                enable_deadline_propagation=True,
            )
            self.timeout_manager = TimeoutManager(timeout_config)
        
        _logger.info(
            "enhanced_grpc_client_initialized",
            host=self.host,
            port=self.port,
            monitoring=enable_monitoring,
            circuit_breaker=enable_circuit_breaker,
            retry=enable_retry,
            timeout_management=enable_timeout_management
        )
    
    async def connect(self) -> None:
        """Establish connection to gRPC server with enhanced error handling."""
        async with self._connection_lock:
            if self._connected and self._channel:
                return
            
            connection_operation = self._create_connection_operation()
            
            try:
                if self.enable_circuit_breaker:
                    await self.circuit_breaker.call(connection_operation)
                else:
                    await connection_operation()
                
                self._connected = True
                _logger.info("grpc_client_connected", host=self.host, port=self.port)
                
            except Exception as exc:
                _logger.error(
                    "grpc_client_connection_failed",
                    host=self.host,
                    port=self.port,
                    error=str(exc),
                    attempts=self.config.max_attempts
                )
                raise ConnectionError(
                    f"Failed to connect to gRPC server at {self.host}:{self.port}: {str(exc)}"
                ) from exc
    
    async def _create_connection_operation(self):
        """Create the actual connection operation."""
        for attempt in range(self.config.max_attempts):
            try:
                # Create channel
                if self.secure:
                    # TODO: Implement TLS credentials
                    self._channel = grpc.aio.insecure_channel(f"{self.host}:{self.port}")
                else:
                    self._channel = grpc.aio.insecure_channel(f"{self.host}:{self.port}")
                
                # Test connection
                await self._test_connection()
                
                # Create stub with interceptors
                await self._create_stub()
                
                return
                
            except Exception as exc:
                _logger.warning(
                    "grpc_connection_attempt_failed",
                    attempt=attempt + 1,
                    max_attempts=self.config.max_attempts,
                    error=str(exc)
                )
                
                if attempt < self.config.max_attempts - 1:
                    # Exponential backoff with jitter
                    delay = min(2 ** attempt + 0.1, 5.0)
                    await asyncio.sleep(delay)
                else:
                    raise
    
    async def _create_stub(self):
        """Create gRPC stub with interceptors."""
        try:
            from omnimind_backend.grpc.generated import omnimind_backend_pb2_grpc as pb2_grpc
            
            interceptors = []
            if self.enable_monitoring:
                interceptors.append(self.metrics_interceptor)
            
            self._stub = pb2_grpc.AgentRuntimeServiceStub(self._channel, interceptors=interceptors)
            
        except Exception as exc:
            raise RuntimeError(
                "Missing generated gRPC bindings. Run: python/scripts/gen_proto.sh"
            ) from exc
    
    async def close(self) -> None:
        """Close gRPC connection and cleanup resources."""
        async with self._connection_lock:
            if self._channel:
                await self._channel.close()
                self._channel = None
                self._stub = None
                self._connected = False
                _logger.info("grpc_client_closed")
    
    async def _test_connection(self) -> None:
        """Test connection to server."""
        if not self._channel:
            raise ConnectionError("No channel established")
        
        try:
            grpc.channel_ready_future(self._channel).result(timeout=10)
        except Exception as exc:
            raise ConnectionError(f"Channel not ready: {exc}") from exc
    
    def is_connected(self) -> bool:
        """Check if client is connected to server."""
        return self._connected and self._channel is not None
    
    async def stream_chat(
        self,
        *,
        session_id: str,
        message: str,
        provider: LLMProvider | None = None,
        model: str | None = None,
        run_id: str | None = None,
        orchestrate: bool = False,
        agent_type: str | None = None,
        debug_steps: bool = False,
    ) -> AsyncGenerator[StreamEvent, None]:
        """Stream chat response from gRPC server with enhanced error handling."""
        if not self.is_connected():
            await self.connect()
        
        operation_name = "StreamChat"
        
        # Create the streaming operation
        async def streaming_operation():
            return self._execute_stream_chat(
                session_id, message, provider, model, run_id,
                orchestrate, agent_type, debug_steps
            )
        
        try:
            # Execute with timeout management
            if self.enable_timeout_management:
                timeout = self.timeout_manager.get_timeout_for_operation(operation_name)
                async with self.timeout_manager.timeout_context(operation_name, timeout):
                    if self.enable_retry:
                        async for event in self.retry_policy.execute_with_retry(streaming_operation):
                            yield event
                    else:
                        async for event in await streaming_operation():
                            yield event
            else:
                if self.enable_retry:
                    async for event in self.retry_policy.execute_with_retry(streaming_operation):
                        yield event
                else:
                    async for event in await streaming_operation():
                        yield event
                        
        except (TimeoutError, RetryExhaustedError, ConnectionError) as exc:
            _logger.error(
                "grpc_stream_chat_failed",
                operation=operation_name,
                session_id=session_id,
                error=str(exc),
                error_type=type(exc).__name__
            )
            raise
        except Exception as exc:
            _logger.error(
                "grpc_stream_chat_unexpected_error",
                operation=operation_name,
                session_id=session_id,
                error=str(exc),
                error_type=type(exc).__name__
            )
            raise
    
    async def _execute_stream_chat(self, session_id: str, message: str, provider: LLMProvider | None,
                                 model: str | None, run_id: str | None, orchestrate: bool,
                                 agent_type: str | None, debug_steps: bool) -> AsyncGenerator[StreamEvent, None]:
        """Execute the actual streaming chat operation."""
        # Import protobuf types
        from omnimind_backend.grpc.generated import omnimind_backend_pb2 as pb2
        
        # Create request
        request = pb2.ChatStreamRequest(
            session_id=session_id,
            message=message,
            provider=provider or "",
            model=model or "",
            run_id=run_id or "",
            orchestrate=orchestrate,
            agent_type=agent_type or "",
            debug_steps=debug_steps,
        )
        
        # Create gRPC options
        options = {}
        if self.enable_timeout_management:
            options.update(self.timeout_manager.create_grpc_options("StreamChat"))
        
        # Make streaming call
        call: UnaryStreamCall = self._stub.StreamChat(request, **options)
        
        # Process responses
        async for response in call:
            try:
                # Convert protobuf response to StreamEvent
                stream_event = StreamEvent(
                    id=response.id,
                    seq=response.seq,
                    type=response.type,
                    mode=response.mode,
                    data=response.data,
                    meta=self._parse_metadata(response.json_meta) if response.json_meta else None,
                )
                yield stream_event
                
            except Exception as exc:
                _logger.error("grpc_response_parsing_error", error=str(exc))
                continue
    
    def _parse_metadata(self, json_meta: str) -> dict[str, Any] | None:
        """Parse JSON metadata from protobuf string."""
        try:
            import json
            return json.loads(json_meta) if json_meta else None
        except Exception:
            return None
    
    async def health_check(self) -> dict[str, str]:
        """Check health of gRPC server with enhanced information."""
        if not self.is_connected():
            await self.connect()
        
        try:
            health_info = {
                "status": "healthy",
                "host": self.host,
                "port": str(self.port),
                "connected": "true",
                "secure": str(self.secure),
            }
            
            # Add circuit breaker status
            if self.enable_circuit_breaker:
                circuit_stats = self.circuit_breaker.get_statistics()
                health_info["circuit_breaker"] = {
                    "state": circuit_stats["state"],
                    "failure_count": circuit_stats["failure_count"],
                    "success_rate": f"{circuit_stats['success_rate_percent']:.1f}%"
                }
            
            # Add retry statistics
            if self.enable_retry:
                retry_stats = self.retry_policy.get_statistics()
                health_info["retry"] = {
                    "total_attempts": retry_stats["total_attempts"],
                    "success_rate": f"{retry_stats['success_rate']:.1f}%"
                }
            
            # Add metrics summary
            if self.enable_monitoring:
                metrics_summary = self.metrics_collector.get_connection_metrics()
                health_info["metrics"] = {
                    "total_connections": metrics_summary["total_active_connections"],
                    "connection_errors": metrics_summary["total_connection_errors"]
                }
            
            return health_info
            
        except Exception as exc:
            return {
                "status": "unhealthy",
                "error": str(exc),
                "host": self.host,
                "port": str(self.port),
            }
    
    def get_statistics(self) -> dict[str, Any]:
        """Get comprehensive client statistics."""
        stats = {
            "client_info": {
                "host": self.host,
                "port": self.port,
                "secure": self.secure,
                "connected": self._connected,
                "features": {
                    "monitoring": self.enable_monitoring,
                    "circuit_breaker": self.enable_circuit_breaker,
                    "retry": self.enable_retry,
                    "timeout_management": self.enable_timeout_management,
                }
            }
        }
        
        # Add component statistics
        if self.enable_monitoring:
            stats["metrics"] = self.metrics_collector.get_connection_metrics()
        
        if self.enable_circuit_breaker:
            stats["circuit_breaker"] = self.circuit_breaker.get_statistics()
        
        if self.enable_retry:
            stats["retry"] = self.retry_policy.get_statistics()
        
        if self.enable_timeout_management:
            stats["timeout"] = self.timeout_manager.get_statistics()
        
        return stats


# Maintain backward compatibility
GrpcAgentClient = EnhancedGrpcAgentClient


class LocalAgentClient:
    """Fallback client that calls service implementations directly (not real gRPC).
    
    DEPRECATED: This client is kept for backward compatibility during migration.
    Use EnhancedGrpcAgentClient for real gRPC communication.
    
    Calls AgentRuntimeServiceImpl methods in-process instead of over a real gRPC
    channel. This avoids the need for generated stubs and a running gRPC server
    during development and testing.
    """

    def __init__(self) -> None:
        self._service = AgentRuntimeServiceImpl()
        self.agent = self._service

    async def stream_chat(
        self,
        *,
        session_id: str,
        message: str,
        provider: LLMProvider | None = None,
        model: str | None = None,
        run_id: str | None = None,
        orchestrate: bool = False,
        agent_type: str | None = None,
    ) -> AsyncGenerator[StreamEvent, None]:
        payload = AgentChatRequest(
            message=message,
            provider=provider,
            model=model,
            orchestrate=orchestrate,
            agent_type=agent_type,
        )
        async for event in self._service.runtime.stream_chat(
            payload,
            session_id=session_id,
            run_id=run_id,
        ):
            yield event
