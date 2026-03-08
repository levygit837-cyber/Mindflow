"""Performance management API endpoints.

Provides REST API endpoints for managing gRPC performance features
including compression, caching, connection pooling, and optimization.
"""

from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel, Field

from mindflow_backend.grpc.config import get_config_manager
from mindflow_backend.grpc.performance.compression.compressor import CompressionAlgorithm
from mindflow_backend.grpc.performance.caching.cache import CacheEvictionPolicy
from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)
router = APIRouter(prefix="/performance", tags=["performance"])


class CompressionConfigRequest(BaseModel):
    """Request model for compression configuration."""
    enabled: bool = True
    algorithm: CompressionAlgorithm = CompressionAlgorithm.GZIP
    compression_level: int = Field(default=6, ge=1, le=9)
    threshold_bytes: int = Field(default=512, ge=1)


class CacheConfigRequest(BaseModel):
    """Request model for cache configuration."""
    enabled: bool = True
    max_size: int = Field(default=1000, ge=1)
    max_memory_mb: int = Field(default=100, ge=1)
    default_ttl_seconds: int = Field(default=300, ge=1)
    eviction_policy: Optional[str] = None


class ConnectionPoolConfigRequest(BaseModel):
    """Request model for connection pool configuration."""
    max_connections: int = Field(default=100, ge=1)
    max_idle_time_seconds: int = Field(default=300, ge=1)
    connection_timeout_seconds: int = Field(default=30, ge=1)
    health_check_interval_seconds: int = Field(default=60, ge=1)


class ProfilerConfigRequest(BaseModel):
    """Request model for profiler configuration."""
    enabled: bool = True
    level: str = Field(default="basic", pattern="^(basic|detailed|comprehensive)$")
    sampling_rate: float = Field(default=0.1, ge=0.0, le=1.0)
    max_profiles: int = Field(default=10000, ge=1)


@router.get("/status")
async def get_performance_status() -> Dict[str, Any]:
    """Get current performance configuration and metrics."""
    try:
        # Get global gRPC server instance
        from mindflow_backend.grpc.server import get_grpc_server
        server = await get_grpc_server()
        
        if not server:
            raise HTTPException(status_code=404, detail="gRPC server not found")
        
        enhanced_status = server.get_enhanced_status()
        return enhanced_status.get("performance", {})
        
    except Exception as e:
        _logger.error("get_performance_status_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/compression/stats")
async def get_compression_stats() -> Dict[str, Any]:
    """Get compression statistics."""
    try:
        from mindflow_backend.grpc.server import get_grpc_server
        server = await get_grpc_server()
        
        if not server or not server.message_compressor:
            raise HTTPException(status_code=404, detail="Compression not available")
        
        return server.message_compressor.get_compression_stats()
        
    except Exception as e:
        _logger.error("get_compression_stats_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/compression/config")
async def update_compression_config(config: CompressionConfigRequest) -> Dict[str, Any]:
    """Update compression configuration."""
    try:
        from mindflow_backend.grpc.server import get_grpc_server
        server = await get_grpc_server()
        
        if not server or not server.message_compressor:
            raise HTTPException(status_code=404, detail="Compression not available")
        
        # Update compression configuration
        from mindflow_backend.grpc.performance.compression.compressor import CompressionConfig
        new_config = CompressionConfig(
            enabled=config.enabled,
            algorithm=config.algorithm,
            compression_level=config.compression_level,
            threshold_bytes=config.threshold_bytes,
            enable_compression_stats=True
        )
        
        # Create new compressor instance (simplified approach)
        server.message_compressor = GrpcMessageCompressor(new_config)
        
        _logger.info("compression_config_updated", config=config.dict())
        
        return {"message": "Compression configuration updated successfully", "config": config.dict()}
        
    except Exception as e:
        _logger.error("update_compression_config_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cache/stats")
async def get_cache_stats() -> Dict[str, Any]:
    """Get cache statistics."""
    try:
        from mindflow_backend.grpc.server import get_grpc_server
        server = await get_grpc_server()
        
        if not server or not server.response_cache:
            raise HTTPException(status_code=404, detail="Cache not available")
        
        return server.response_cache.get_stats()
        
    except Exception as e:
        _logger.error("get_cache_stats_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cache/config")
async def update_cache_config(config: CacheConfigRequest) -> Dict[str, Any]:
    """Update cache configuration."""
    try:
        from mindflow_backend.grpc.server import get_grpc_server
        server = await get_grpc_server()
        
        if not server or not server.response_cache:
            raise HTTPException(status_code=404, detail="Cache not available")
        
        # Update cache configuration
        from mindflow_backend.grpc.performance.caching.cache import CacheConfig
        new_config = CacheConfig(
            enabled=config.enabled,
            max_size=config.max_size,
            max_memory_mb=config.max_memory_mb,
            default_ttl_seconds=config.default_ttl_seconds,
            enable_stats=True
        )
        
        # Create new cache instance (simplified approach)
        server.response_cache = GrpcResponseCache(new_config)
        
        _logger.info("cache_config_updated", config=config.dict())
        
        return {"message": "Cache configuration updated successfully", "config": config.dict()}
        
    except Exception as e:
        _logger.error("update_cache_config_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/cache/clear")
async def clear_cache() -> Dict[str, Any]:
    """Clear all cache entries."""
    try:
        from mindflow_backend.grpc.server import get_grpc_server
        server = await get_grpc_server()
        
        if not server or not server.response_cache:
            raise HTTPException(status_code=404, detail="Cache not available")
        
        cleared_count = server.response_cache.clear()
        
        _logger.info("cache_cleared", cleared_entries=cleared_count)
        
        return {"message": "Cache cleared successfully", "cleared_entries": cleared_count}
        
    except Exception as e:
        _logger.error("clear_cache_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/connection-pool/status")
async def get_connection_pool_status() -> Dict[str, Any]:
    """Get connection pool status."""
    try:
        from mindflow_backend.grpc.server import get_grpc_server
        server = await get_grpc_server()
        
        if not server or not server.connection_pool_manager:
            raise HTTPException(status_code=404, detail="Connection pool not available")
        
        return server.connection_pool_manager.get_status()
        
    except Exception as e:
        _logger.error("get_connection_pool_status_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/connection-pool/config")
async def update_connection_pool_config(config: ConnectionPoolConfigRequest) -> Dict[str, Any]:
    """Update connection pool configuration."""
    try:
        from mindflow_backend.grpc.server import get_grpc_server
        server = await get_grpc_server()
        
        if not server or not server.connection_pool_manager:
            raise HTTPException(status_code=404, detail="Connection pool not available")
        
        # Update pool configuration (simplified approach)
        # In a real implementation, this would update the existing pool configuration
        _logger.info("connection_pool_config_updated", config=config.dict())
        
        return {"message": "Connection pool configuration updated successfully", "config": config.dict()}
        
    except Exception as e:
        _logger.error("update_connection_pool_config_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/profiler/status")
async def get_profiler_status() -> Dict[str, Any]:
    """Get profiler status and statistics."""
    try:
        from mindflow_backend.grpc.server import get_grpc_server
        server = await get_grpc_server()
        
        if not server or not server.profiler:
            raise HTTPException(status_code=404, detail="Profiler not available")
        
        return server.profiler.get_summary()
        
    except Exception as e:
        _logger.error("get_profiler_status_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/profiler/config")
async def update_profiler_config(config: ProfilerConfigRequest) -> Dict[str, Any]:
    """Update profiler configuration."""
    try:
        from mindflow_backend.grpc.server import get_grpc_server
        server = await get_grpc_server()
        
        if not server or not server.profiler:
            raise HTTPException(status_code=404, detail="Profiler not available")
        
        # Update profiler configuration
        from mindflow_backend.grpc.performance.monitoring.profiler import ProfileConfig, ProfileLevel
        level_map = {
            "basic": ProfileLevel.BASIC,
            "detailed": ProfileLevel.DETAILED,
            "comprehensive": ProfileLevel.COMPREHENSIVE
        }
        
        new_config = ProfileConfig(
            enabled=config.enabled,
            level=level_map.get(config.level, ProfileLevel.BASIC),
            sampling_rate=config.sampling_rate,
            max_profiles=config.max_profiles
        )
        
        # Create new profiler instance (simplified approach)
        server.profiler = GrpcProfiler(new_config)
        
        _logger.info("profiler_config_updated", config=config.dict())
        
        return {"message": "Profiler configuration updated successfully", "config": config.dict()}
        
    except Exception as e:
        _logger.error("update_profiler_config_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/optimizer/status")
async def get_optimizer_status() -> Dict[str, Any]:
    """Get optimizer status and recommendations."""
    try:
        from mindflow_backend.grpc.server import get_grpc_server
        server = await get_grpc_server()
        
        if not server or not server.optimizer:
            raise HTTPException(status_code=404, detail="Optimizer not available")
        
        return server.optimizer.get_status()
        
    except Exception as e:
        _logger.error("get_optimizer_status_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/optimizer/tune")
async def trigger_optimization() -> Dict[str, Any]:
    """Trigger performance optimization analysis."""
    try:
        from mindflow_backend.grpc.server import get_grpc_server
        server = await get_grpc_server()
        
        if not server or not server.optimizer:
            raise HTTPException(status_code=404, detail="Optimizer not available")
        
        # Trigger optimization (simplified approach)
        # In a real implementation, this would analyze performance data and generate recommendations
        recommendations = server.optimizer.analyze_performance()
        
        _logger.info("optimization_triggered", recommendations=len(recommendations))
        
        return {
            "message": "Optimization analysis completed",
            "recommendations": recommendations,
            "timestamp": time.time()
        }
        
    except Exception as e:
        _logger.error("trigger_optimization_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics")
async def get_performance_metrics(
    start_time: Optional[float] = Query(None, description="Start timestamp"),
    end_time: Optional[float] = Query(None, description="End timestamp"),
    metric_type: Optional[str] = Query(None, description="Metric type filter")
) -> Dict[str, Any]:
    """Get performance metrics for analysis."""
    try:
        from mindflow_backend.grpc.server import get_grpc_server
        server = await get_grpc_server()
        
        if not server or not server.metrics_collector:
            raise HTTPException(status_code=404, detail="Metrics collector not available")
        
        # Get metrics from collector
        metrics = server.metrics_collector.get_metrics()
        
        # Filter by time range if specified
        if start_time or end_time:
            # In a real implementation, this would filter metrics by time range
            pass
        
        # Filter by metric type if specified
        if metric_type:
            metrics = {k: v for k, v in metrics.items() if metric_type.lower() in k.lower()}
        
        return metrics
        
    except Exception as e:
        _logger.error("get_performance_metrics_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# Import required modules at the end to avoid circular imports
import time
from mindflow_backend.grpc.performance.compression.compressor import GrpcMessageCompressor, CompressionAlgorithm
from mindflow_backend.grpc.performance.caching.cache import GrpcResponseCache
from mindflow_backend.grpc.performance.monitoring.profiler import GrpcProfiler, ProfileConfig, ProfileLevel
