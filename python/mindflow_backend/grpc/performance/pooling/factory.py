"""Factory for creating gRPC connections with optimized settings.

Provides standardized connection creation with performance
optimizations and error handling.
"""

from __future__ import annotations

import time
from typing import Dict, Any, Optional
import grpc
from grpc.aio import Channel

from .pool import PoolConfig, GrpcConnection
from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


class GrpcConnectionFactory:
    """Factory for creating optimized gRPC connections."""
    
    def __init__(self):
        self._default_options = self._get_default_options()
        self._creation_stats = {
            "total_created": 0,
            "successful_creations": 0,
            "failed_creations": 0,
            "average_creation_time": 0.0,
        }
        self._creation_times = []
        self._max_creation_times = 1000
    
    async def create_connection(self, config: PoolConfig) -> GrpcConnection:
        """Create a new gRPC connection with optimized settings."""
        start_time = time.time()
        
        try:
            # Build channel options
            channel_options = self._build_channel_options(config)
            
            # Create channel
            channel = await self._create_channel(config, channel_options)
            
            # Wait for channel to be ready
            await grpc.channel_ready_future(channel).result(timeout=config.connection_timeout)
            
            # Create connection wrapper
            connection = GrpcConnection(
                channel=channel,
                created_at=time.time(),
            )
            
            # Update statistics
            creation_time = time.time() - start_time
            self._update_creation_stats(creation_time, True)
            
            _logger.debug("grpc_connection_factory_created",
                        host=config.host,
                        port=config.port,
                        creation_time=creation_time)
            
            return connection
            
        except Exception as exc:
            creation_time = time.time() - start_time
            self._update_creation_stats(creation_time, False)
            
            _logger.error("grpc_connection_factory_failed",
                        host=config.host,
                        port=config.port,
                        creation_time=creation_time,
                        error=str(exc))
            raise
    
    def _build_channel_options(self, config: PoolConfig) -> list[tuple[str, Any]]:
        """Build channel options for optimal performance."""
        options = self._default_options.copy()
        
        # Add configuration-specific options
        options.extend([
            ('grpc.keepalive_time_ms', config.keepalive_time_ms),
            ('grpc.keepalive_timeout_ms', config.keepalive_timeout_ms),
            ('grpc.max_receive_message_length', config.max_message_size),
            ('grpc.max_send_message_length', config.max_message_size),
            ('grpc.http2.max_pings_without_data', 0),
            ('grpc.http2.min_time_between_pings_ms', 10000),
            ('grpc.http2.min_ping_interval_without_data_ms', 300000),
            ('grpc.http2.max_ping_strikes', 2),
            ('grpc.http2.keepalive_time_ms', config.keepalive_time_ms),
            ('grpc.http2.keepalive_timeout_ms', config.keepalive_timeout_ms),
            ('grpc.http2.permit_keepalive_without_calls', True),
            ('grpc.http2.bdp_probe', True),
            ('grpc.http2.min_ping_interval_without_data_ms', 300000),
            ('grpc.http2.max_ping_strikes', 2),
        ])
        
        # Performance optimizations
        options.extend([
            ('grpc.max_receive_message_length', config.max_message_size),
            ('grpc.max_send_message_length', config.max_message_size),
            ('grpc.default_authority', f"{config.host}:{config.port}"),
        ])
        
        return options
    
    async def _create_channel(self, config: PoolConfig, options: list[tuple[str, Any]]) -> Channel:
        """Create gRPC channel with specified options."""
        target = f"{config.host}:{config.port}"
        
        if config.secure:
            # Create secure channel
            credentials = grpc.ssl_channel_credentials()
            return grpc.aio.secure_channel(target, credentials, options=options)
        else:
            # Create insecure channel
            return grpc.aio.insecure_channel(target, options=options)
    
    def _get_default_options(self) -> list[tuple[str, Any]]:
        """Get default channel options for optimal performance."""
        return [
            # Flow control
            ('grpc.http2.initial_window_size', 64 * 1024 * 1024),  # 64MB
            ('grpc.http2.max_concurrent_streams', 1000),
            
            # Timeouts
            ('grpc.connect_timeout_ms', 30000),  # 30 seconds
            ('grpc.idle_timeout_ms', 300000),    # 5 minutes
            
            # Performance
            ('grpc.enable_retries', True),
            ('grpc.max_retry_buffer_size', 64 * 1024 * 1024),  # 64MB
            ('grpc.per_message_compression_algorithm', 'gzip'),
            
            # HTTP/2 settings
            ('grpc.http2.write_buffer_size', 64 * 1024),  # 64KB
            ('grpc.http2.read_buffer_size', 64 * 1024),   # 64KB
            ('grpc.http2.max_frame_size', 16 * 1024 * 1024),  # 16MB
            
            # Keepalive settings
            ('grpc.keepalive_permit_without_calls', True),
            ('grpc.keepalive_time_ms', 30000),      # 30 seconds
            ('grpc.keepalive_timeout_ms', 5000),     # 5 seconds
            ('grpc.http2.min_time_between_pings_ms', 10000),  # 10 seconds
            ('grpc.http2.min_ping_interval_without_data_ms', 300000),  # 5 minutes
            ('grpc.http2.max_pings_without_data', 0),
            ('grpc.http2.max_ping_strikes', 2),
            
            # BDP probing
            ('grpc.http2.bdp_probe', True),
            ('grpc.http2.min_time_between_bdp_probes_ms', 300000),  # 5 minutes
            
            # Compression
            ('grpc.default_compression_algorithm', 'gzip'),
            ('grpc.per_message_compression_algorithm', 'gzip'),
        ]
    
    def _update_creation_stats(self, creation_time: float, success: bool):
        """Update connection creation statistics."""
        self._creation_stats["total_created"] += 1
        
        if success:
            self._creation_stats["successful_creations"] += 1
        else:
            self._creation_stats["failed_creations"] += 1
        
        # Track creation times
        self._creation_times.append(creation_time)
        
        # Keep only recent creation times
        if len(self._creation_times) > self._max_creation_times:
            self._creation_times = self._creation_times[-self._max_creation_times:]
        
        # Update average creation time
        if self._creation_times:
            self._creation_stats["average_creation_time"] = sum(self._creation_times) / len(self._creation_times)
    
    def get_creation_statistics(self) -> Dict[str, Any]:
        """Get connection creation statistics."""
        total = self._creation_stats["total_created"]
        
        return {
            **self._creation_stats,
            "success_rate": self._creation_stats["successful_creations"] / max(total, 1),
            "failure_rate": self._creation_stats["failed_creations"] / max(total, 1),
            "recent_creation_times": self._creation_times[-10:],  # Last 10
        }
    
    def reset_statistics(self):
        """Reset creation statistics."""
        self._creation_stats = {
            "total_created": 0,
            "successful_creations": 0,
            "failed_creations": 0,
            "average_creation_time": 0.0,
        }
        self._creation_times.clear()
    
    async def test_connection(self, config: PoolConfig) -> bool:
        """Test connection to target without creating a persistent connection."""
        try:
            # Create temporary connection
            connection = await self.create_connection(config)
            
            # Test with a simple health check
            # Note: In a real implementation, you might want to perform
            # an actual gRPC call here
            await asyncio.sleep(0.1)  # Simulate health check
            
            # Close connection
            await connection.channel.close()
            
            return True
            
        except Exception as exc:
            _logger.debug("connection_test_failed",
                         host=config.host,
                         port=config.port,
                         error=str(exc))
            return False
    
    def validate_config(self, config: PoolConfig) -> list[str]:
        """Validate pool configuration."""
        issues = []
        
        # Host validation
        if not config.host or not config.host.strip():
            issues.append("Host cannot be empty")
        
        # Port validation
        if not (1 <= config.port <= 65535):
            issues.append("Port must be between 1 and 65535")
        
        # Pool size validation
        if config.min_pool_size < 1:
            issues.append("Minimum pool size must be at least 1")
        
        if config.max_pool_size < config.min_pool_size:
            issues.append("Maximum pool size must be >= minimum pool size")
        
        if config.max_pool_size > 1000:
            issues.append("Maximum pool size > 1000 may cause resource issues")
        
        # Timeout validation
        if config.connection_timeout <= 0:
            issues.append("Connection timeout must be positive")
        
        if config.connection_timeout > 300:
            issues.append("Connection timeout > 5 minutes may be too long")
        
        # Message size validation
        if config.max_message_size <= 0:
            issues.append("Max message size must be positive")
        
        if config.max_message_size > 100 * 1024 * 1024:  # 100MB
            issues.append("Max message size > 100MB may cause memory issues")
        
        # Keepalive validation
        if config.keepalive_time_ms <= 0:
            issues.append("Keepalive time must be positive")
        
        if config.keepalive_timeout_ms <= 0:
            issues.append("Keepalive timeout must be positive")
        
        if config.keepalive_timeout_ms >= config.keepalive_time_ms:
            issues.append("Keepalive timeout should be < keepalive time")
        
        # Health check validation
        if config.health_check_interval <= 0:
            issues.append("Health check interval must be positive")
        
        if config.health_check_timeout <= 0:
            issues.append("Health check timeout must be positive")
        
        if config.health_check_timeout >= config.health_check_interval:
            issues.append("Health check timeout should be < health check interval")
        
        return issues
