"""gRPC connection pool for efficient connection management.

Provides connection pooling with health checking, dynamic sizing,
and performance monitoring for high-throughput gRPC operations.
"""

from __future__ import annotations

import asyncio
import time
from typing import Optional, Set, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
import grpc
from grpc.aio import Channel

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


class ConnectionState(Enum):
    """Connection states."""
    CREATED = "created"
    READY = "ready"
    BUSY = "busy"
    UNHEALTHY = "unhealthy"
    CLOSED = "closed"


@dataclass
class PoolStatistics:
    """Statistics for connection pool."""
    total_connections: int = 0
    active_connections: int = 0
    available_connections: int = 0
    unhealthy_connections: int = 0
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    average_response_time: float = 0.0
    connection_creation_time: float = 0.0
    last_health_check: float = 0.0
    
    def get_success_rate(self) -> float:
        """Get request success rate."""
        if self.total_requests == 0:
            return 0.0
        return self.successful_requests / self.total_requests
    
    def get_utilization_rate(self) -> float:
        """Get pool utilization rate."""
        if self.total_connections == 0:
            return 0.0
        return self.active_connections / self.total_connections


@dataclass
class GrpcConnection:
    """Wrapper for gRPC connection with metadata."""
    channel: Channel
    created_at: float
    last_used: float = field(default_factory=time.time)
    state: ConnectionState = ConnectionState.CREATED
    request_count: int = 0
    error_count: int = 0
    last_health_check: float = 0.0
    is_healthy: bool = True
    
    def record_request(self, success: bool, response_time: float):
        """Record request statistics."""
        self.last_used = time.time()
        self.request_count += 1
        if not success:
            self.error_count += 1
    
    def update_health(self, healthy: bool):
        """Update connection health status."""
        self.is_healthy = healthy
        self.last_health_check = time.time()
        self.state = ConnectionState.READY if healthy else ConnectionState.UNHEALTHY


@dataclass
class PoolConfig:
    """Configuration for connection pool."""
    host: str
    port: int
    secure: bool = False
    min_pool_size: int = 5
    max_pool_size: int = 50
    connection_timeout: float = 30.0
    keepalive_time_ms: int = 30000
    keepalive_timeout_ms: int = 5000
    max_message_size: int = 4 * 1024 * 1024  # 4MB
    health_check_interval: float = 60.0
    health_check_timeout: float = 5.0
    max_idle_time: float = 300.0  # 5 minutes
    enable_metrics: bool = True


class ConnectionPoolExhaustedError(Exception):
    """Raised when no connections are available in the pool."""
    pass


class ConnectionPoolTimeoutError(Exception):
    """Raised when connection acquisition times out."""
    pass


class GrpcConnectionPool:
    """gRPC connection pool with health checking and dynamic sizing."""
    
    def __init__(self, config: PoolConfig, pool_id: str):
        self.config = config
        self.pool_id = pool_id
        
        # Connection management
        self.available_connections: asyncio.Queue[GrpcConnection] = asyncio.Queue()
        self.active_connections: Set[GrpcConnection] = set()
        self.all_connections: Set[GrpcConnection] = set()
        
        # Pool state
        self._lock = asyncio.Lock()
        self._closed = False
        self._creation_in_progress = False
        
        # Statistics
        self.stats = PoolStatistics()
        self._response_times: list[float] = []
        self._max_response_times = 1000  # Keep last 1000 response times
        
        # Background tasks
        self._health_check_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        
        _logger.info("grpc_connection_pool_created", 
                    pool_id=pool_id, 
                    host=config.host, 
                    port=config.port,
                    min_size=config.min_pool_size,
                    max_size=config.max_pool_size)
    
    async def initialize(self) -> bool:
        """Initialize the connection pool with minimum connections."""
        try:
            async with self._lock:
                if self._closed:
                    return False
                
                # Create initial connections
                await self._create_initial_connections()
                
                # Start background tasks
                self._health_check_task = asyncio.create_task(self._health_check_loop())
                self._cleanup_task = asyncio.create_task(self._cleanup_loop())
                
                _logger.info("grpc_connection_pool_initialized", 
                            pool_id=self.pool_id,
                            initial_connections=len(self.all_connections))
                
                return True
                
        except Exception as exc:
            _logger.error("grpc_connection_pool_initialization_failed", 
                        pool_id=self.pool_id, 
                        error=str(exc))
            return False
    
    async def get_connection(self, timeout: float = 5.0) -> GrpcConnection:
        """Get connection from pool with timeout and auto-scaling."""
        if self._closed:
            raise RuntimeError("Connection pool is closed")
        
        start_time = time.time()
        
        try:
            # Try to get available connection
            connection = await self._get_available_connection(timeout)
            
            # Validate connection health
            if not await self._is_connection_healthy(connection):
                await self._remove_connection(connection)
                # Try again with a new connection
                connection = await self._create_and_get_connection(timeout - (time.time() - start_time))
            
            # Mark as active
            async with self._lock:
                self.active_connections.add(connection)
                connection.state = ConnectionState.BUSY
                self.stats.active_connections = len(self.active_connections)
            
            self.stats.total_requests += 1
            
            return connection
            
        except asyncio.TimeoutError:
            self.stats.failed_requests += 1
            raise ConnectionPoolTimeoutError(f"Connection timeout after {timeout}s")
        except Exception as exc:
            self.stats.failed_requests += 1
            _logger.error("get_connection_failed", pool_id=self.pool_id, error=str(exc))
            raise
    
    async def return_connection(self, connection: GrpcConnection, success: bool = True, response_time: float = 0.0):
        """Return connection to pool after use."""
        if self._closed or connection not in self.all_connections:
            return
        
        # Record request statistics
        connection.record_request(success, response_time)
        self._record_response_time(response_time)
        
        if success:
            self.stats.successful_requests += 1
        else:
            self.stats.failed_requests += 1
        
        async with self._lock:
            # Remove from active connections
            self.active_connections.discard(connection)
            
            # Check connection health
            if await self._is_connection_healthy(connection):
                connection.state = ConnectionState.READY
                await self.available_connections.put(connection)
                self.stats.available_connections = self.available_connections.qsize()
            else:
                await self._remove_connection(connection)
            
            self.stats.active_connections = len(self.active_connections)
    
    async def close(self):
        """Close all connections and cleanup resources."""
        if self._closed:
            return
        
        self._closed = True
        
        # Cancel background tasks
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Close all connections
        async with self._lock:
            for connection in list(self.all_connections):
                await self._close_connection(connection)
            
            self.all_connections.clear()
            self.active_connections.clear()
            
            # Clear available connections queue
            while not self.available_connections.empty():
                try:
                    self.available_connections.get_nowait()
                except asyncio.QueueEmpty:
                    break
        
        _logger.info("grpc_connection_pool_closed", pool_id=self.pool_id)
    
    async def get_statistics(self) -> PoolStatistics:
        """Get current pool statistics."""
        async with self._lock:
            self.stats.total_connections = len(self.all_connections)
            self.stats.active_connections = len(self.active_connections)
            self.stats.available_connections = self.available_connections.qsize()
            self.stats.unhealthy_connections = len([
                conn for conn in self.all_connections 
                if not conn.is_healthy
            ])
            
            # Calculate average response time
            if self._response_times:
                self.stats.average_response_time = sum(self._response_times) / len(self._response_times)
            
            return self.stats
    
    async def _create_initial_connections(self):
        """Create initial connections up to min_pool_size."""
        for _ in range(self.config.min_pool_size):
            try:
                connection = await self._create_connection()
                self.all_connections.add(connection)
                await self.available_connections.put(connection)
            except Exception as exc:
                _logger.warning("initial_connection_creation_failed", 
                              pool_id=self.pool_id, 
                              error=str(exc))
    
    async def _get_available_connection(self, timeout: float) -> GrpcConnection:
        """Get available connection with timeout and auto-scaling."""
        try:
            # Try to get existing connection
            connection = self.available_connections.get_nowait()
            return connection
        except asyncio.QueueEmpty:
            pass
        
        # Try to create new connection if under limit
        async with self._lock:
            if len(self.all_connections) < self.config.max_pool_size and not self._creation_in_progress:
                self._creation_in_progress = True
                try:
                    connection = await self._create_connection()
                    self.all_connections.add(connection)
                    return connection
                finally:
                    self._creation_in_progress = False
        
        # Wait for available connection
        try:
            connection = await asyncio.wait_for(
                self.available_connections.get(),
                timeout=timeout
            )
            return connection
        except asyncio.TimeoutError:
            raise ConnectionPoolExhaustedError("No connections available and pool is at maximum size")
    
    async def _create_and_get_connection(self, timeout: float) -> GrpcConnection:
        """Create new connection and return it."""
        async with self._lock:
            if len(self.all_connections) >= self.config.max_pool_size:
                raise ConnectionPoolExhaustedError("Pool is at maximum size")
            
            if self._creation_in_progress:
                # Wait for ongoing creation
                await asyncio.sleep(0.1)
                return await self._get_available_connection(timeout)
            
            self._creation_in_progress = True
            try:
                connection = await self._create_connection()
                self.all_connections.add(connection)
                return connection
            finally:
                self._creation_in_progress = False
    
    async def _create_connection(self) -> GrpcConnection:
        """Create new gRPC connection with optimized settings."""
        start_time = time.time()
        
        try:
            # Build channel options
            channel_options = [
                ('grpc.keepalive_time_ms', self.config.keepalive_time_ms),
                ('grpc.keepalive_timeout_ms', self.config.keepalive_timeout_ms),
                ('grpc.http2.max_pings_without_data', 0),
                ('grpc.http2.min_time_between_pings_ms', 10000),
                ('grpc.http2.min_ping_interval_without_data_ms', 300000),
                ('grpc.max_receive_message_length', self.config.max_message_size),
                ('grpc.max_send_message_length', self.config.max_message_size),
                ('grpc.http2.min_recv_ping_interval_without_data_ms', 300000),
                ('grpc.http2.max_ping_strikes', 2),
            ]
            
            # Create channel
            if self.config.secure:
                channel = grpc.aio.secure_channel(
                    f"{self.config.host}:{self.config.port}",
                    grpc.ssl_channel_credentials(),
                    options=channel_options
                )
            else:
                channel = grpc.aio.insecure_channel(
                    f"{self.config.host}:{self.config.port}",
                    options=channel_options
                )
            
            # Wait for channel to be ready
            await grpc.channel_ready_future(channel).result(timeout=self.config.connection_timeout)
            
            connection = GrpcConnection(
                channel=channel,
                created_at=time.time(),
                state=ConnectionState.READY
            )
            
            # Update statistics
            creation_time = time.time() - start_time
            self.stats.connection_creation_time = creation_time
            
            _logger.debug("grpc_connection_created", 
                        pool_id=self.pool_id,
                        creation_time=creation_time)
            
            return connection
            
        except Exception as exc:
            _logger.error("grpc_connection_creation_failed", 
                        pool_id=self.pool_id, 
                        error=str(exc))
            raise
    
    async def _is_connection_healthy(self, connection: GrpcConnection) -> bool:
        """Check if connection is healthy."""
        if not connection.is_healthy:
            return False
        
        # Check if connection is too old
        if time.time() - connection.created_at > self.config.max_idle_time:
            return False
        
        # Check error rate
        if connection.request_count > 0:
            error_rate = connection.error_count / connection.request_count
            if error_rate > 0.1:  # 10% error rate threshold
                return False
        
        return True
    
    async def _remove_connection(self, connection: GrpcConnection):
        """Remove connection from pool."""
        async with self._lock:
            self.all_connections.discard(connection)
            self.active_connections.discard(connection)
            
            # Remove from available queue if present
            # Note: This is a simplified approach, in production you might want
            # to maintain a more sophisticated tracking mechanism
            
            await self._close_connection(connection)
    
    async def _close_connection(self, connection: GrpcConnection):
        """Close gRPC connection."""
        try:
            await connection.channel.close()
            connection.state = ConnectionState.CLOSED
        except Exception as exc:
            _logger.warning("grpc_connection_close_failed", 
                          pool_id=self.pool_id, 
                          error=str(exc))
    
    async def _health_check_loop(self):
        """Background health checking loop."""
        while not self._closed:
            try:
                await self._perform_health_check()
                await asyncio.sleep(self.config.health_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                _logger.error("health_check_loop_error", 
                            pool_id=self.pool_id, 
                            error=str(exc))
                await asyncio.sleep(self.config.health_check_interval)
    
    async def _cleanup_loop(self):
        """Background cleanup loop for idle connections."""
        while not self._closed:
            try:
                await self._cleanup_idle_connections()
                await asyncio.sleep(self.config.health_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                _logger.error("cleanup_loop_error", 
                            pool_id=self.pool_id, 
                            error=str(exc))
                await asyncio.sleep(self.config.health_check_interval)
    
    async def _perform_health_check(self):
        """Perform health check on all connections."""
        unhealthy_connections = []
        
        async with self._lock:
            for connection in list(self.all_connections):
                if not await self._is_connection_healthy(connection):
                    unhealthy_connections.append(connection)
        
        # Remove unhealthy connections
        for connection in unhealthy_connections:
            await self._remove_connection(connection)
        
        # Update statistics
        self.stats.last_health_check = time.time()
        
        if unhealthy_connections:
            _logger.info("unhealthy_connections_removed", 
                        pool_id=self.pool_id,
                        count=len(unhealthy_connections))
    
    async def _cleanup_idle_connections(self):
        """Clean up idle connections to maintain pool size."""
        current_time = time.time()
        idle_connections = []
        
        async with self._lock:
            # Find idle connections (not in active use and not used recently)
            for connection in list(self.all_connections):
                if (connection not in self.active_connections and 
                    current_time - connection.last_used > self.config.max_idle_time and
                    len(self.all_connections) > self.config.min_pool_size):
                    idle_connections.append(connection)
        
        # Remove idle connections
        for connection in idle_connections:
            await self._remove_connection(connection)
        
        if idle_connections:
            _logger.info("idle_connections_cleaned_up", 
                        pool_id=self.pool_id,
                        count=len(idle_connections))
    
    def _record_response_time(self, response_time: float):
        """Record response time for statistics."""
        self._response_times.append(response_time)
        
        # Keep only recent response times
        if len(self._response_times) > self._max_response_times:
            self._response_times = self._response_times[-self._max_response_times:]
