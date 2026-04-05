"""gRPC message compressor with multiple compression strategies.

Provides intelligent compression based on message size, type,
and network conditions to optimize bandwidth usage.
"""

from __future__ import annotations

import gzip
import zlib
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


class CompressionAlgorithm(Enum):
    """Supported compression algorithms."""
    NONE = "none"
    GZIP = "gzip"
    DEFLATE = "deflate"
    AUTO = "auto"


@dataclass
class CompressionConfig:
    """Configuration for message compression."""
    
    # Algorithm settings
    algorithm: CompressionAlgorithm = CompressionAlgorithm.AUTO
    compression_level: int = 6  # 1-9 for gzip/deflate
    threshold_bytes: int = 1024  # Only compress messages larger than this
    
    # Auto selection settings
    auto_gzip_threshold: int = 1024
    auto_deflate_threshold: int = 2048
    auto_max_size: int = 10 * 1024 * 1024  # 10MB max for compression
    
    # Performance settings
    enable_compression_stats: bool = True
    max_compression_time_ms: float = 50.0  # Skip if compression takes too long
    
    # Content type settings
    compress_content_types: list[str] = field(default_factory=lambda: [
        "application/json",
        "application/x-protobuf", 
        "text/plain",
        "text/html"
    ])
    
    def should_compress(self, message_size: int, content_type: str = "") -> bool:
        """Determine if message should be compressed."""
        if message_size < self.threshold_bytes:
            return False
        
        if message_size > self.auto_max_size:
            return False
            
        if content_type and content_type not in self.compress_content_types:
            return False
            
        return True
    
    def select_algorithm(self, message_size: int) -> CompressionAlgorithm:
        """Select best algorithm based on message size."""
        if self.algorithm != CompressionAlgorithm.AUTO:
            return self.algorithm
        
        if message_size < self.auto_gzip_threshold:
            return CompressionAlgorithm.NONE
        elif message_size < self.auto_deflate_threshold:
            return CompressionAlgorithm.GZIP
        else:
            return CompressionAlgorithm.DEFLATE


@dataclass
class CompressionResult:
    """Result of compression operation."""
    
    original_size: int
    compressed_size: int
    algorithm: CompressionAlgorithm
    compression_ratio: float
    compression_time_ms: float
    success: bool
    error_message: str | None = None
    
    @property
    def bandwidth_saved(self) -> int:
        """Bytes saved by compression."""
        return self.original_size - self.compressed_size
    
    @property
    def bandwidth_saved_percent(self) -> float:
        """Percentage of bandwidth saved."""
        if self.original_size == 0:
            return 0.0
        return (self.bandwidth_saved / self.original_size) * 100


class CompressionStrategy:
    """Base class for compression strategies."""
    
    def __init__(self, config: CompressionConfig):
        self.config = config
    
    def compress(self, data: bytes) -> CompressionResult:
        """Compress data using this strategy."""
        raise NotImplementedError
    
    def decompress(self, compressed_data: bytes) -> bytes:
        """Decompress data using this strategy."""
        raise NotImplementedError
    
    def get_name(self) -> str:
        """Get strategy name."""
        raise NotImplementedError


class NoCompressionStrategy(CompressionStrategy):
    """No compression strategy."""
    
    def compress(self, data: bytes) -> CompressionResult:
        """Return data unchanged."""
        return CompressionResult(
            original_size=len(data),
            compressed_size=len(data),
            algorithm=CompressionAlgorithm.NONE,
            compression_ratio=1.0,
            compression_time_ms=0.0,
            success=True
        )
    
    def decompress(self, compressed_data: bytes) -> bytes:
        """Return data unchanged."""
        return compressed_data
    
    def get_name(self) -> str:
        return "none"


class GzipCompressionStrategy(CompressionStrategy):
    """GZIP compression strategy."""
    
    def compress(self, data: bytes) -> CompressionResult:
        """Compress data using GZIP."""
        import time
        start_time = time.time()
        
        try:
            compressed_data = gzip.compress(
                data, 
                compresslevel=self.config.compression_level
            )
            
            compression_time = (time.time() - start_time) * 1000
            
            # Check if compression took too long
            if compression_time > self.config.max_compression_time_ms:
                _logger.warning(
                    "compression_too_slow",
                    algorithm="gzip",
                    time_ms=compression_time,
                    max_time_ms=self.config.max_compression_time_ms
                )
                return CompressionResult(
                    original_size=len(data),
                    compressed_size=len(data),
                    algorithm=CompressionAlgorithm.NONE,
                    compression_ratio=1.0,
                    compression_time_ms=compression_time,
                    success=False,
                    error_message="Compression too slow"
                )
            
            compression_ratio = len(compressed_data) / len(data) if data else 1.0
            
            return CompressionResult(
                original_size=len(data),
                compressed_size=len(compressed_data),
                algorithm=CompressionAlgorithm.GZIP,
                compression_ratio=compression_ratio,
                compression_time_ms=compression_time,
                success=True
            )
            
        except Exception as e:
            _logger.error("gzip_compression_failed", error=str(e))
            return CompressionResult(
                original_size=len(data),
                compressed_size=len(data),
                algorithm=CompressionAlgorithm.GZIP,
                compression_ratio=1.0,
                compression_time_ms=(time.time() - start_time) * 1000,
                success=False,
                error_message=str(e)
            )
    
    def decompress(self, compressed_data: bytes) -> bytes:
        """Decompress GZIP data."""
        try:
            return gzip.decompress(compressed_data)
        except Exception as e:
            _logger.error("gzip_decompression_failed", error=str(e))
            raise
    
    def get_name(self) -> str:
        return "gzip"


class DeflateCompressionStrategy(CompressionStrategy):
    """Deflate compression strategy."""
    
    def compress(self, data: bytes) -> CompressionResult:
        """Compress data using Deflate."""
        import time
        start_time = time.time()
        
        try:
            compressed_data = zlib.compress(
                data,
                level=self.config.compression_level
            )
            
            compression_time = (time.time() - start_time) * 1000
            
            # Check if compression took too long
            if compression_time > self.config.max_compression_time_ms:
                _logger.warning(
                    "compression_too_slow",
                    algorithm="deflate",
                    time_ms=compression_time,
                    max_time_ms=self.config.max_compression_time_ms
                )
                return CompressionResult(
                    original_size=len(data),
                    compressed_size=len(data),
                    algorithm=CompressionAlgorithm.NONE,
                    compression_ratio=1.0,
                    compression_time_ms=compression_time,
                    success=False,
                    error_message="Compression too slow"
                )
            
            compression_ratio = len(compressed_data) / len(data) if data else 1.0
            
            return CompressionResult(
                original_size=len(data),
                compressed_size=len(compressed_data),
                algorithm=CompressionAlgorithm.DEFLATE,
                compression_ratio=compression_ratio,
                compression_time_ms=compression_time,
                success=True
            )
            
        except Exception as e:
            _logger.error("deflate_compression_failed", error=str(e))
            return CompressionResult(
                original_size=len(data),
                compressed_size=len(data),
                algorithm=CompressionAlgorithm.DEFLATE,
                compression_ratio=1.0,
                compression_time_ms=(time.time() - start_time) * 1000,
                success=False,
                error_message=str(e)
            )
    
    def decompress(self, compressed_data: bytes) -> bytes:
        """Decompress Deflate data."""
        try:
            return zlib.decompress(compressed_data)
        except Exception as e:
            _logger.error("deflate_decompression_failed", error=str(e))
            raise
    
    def get_name(self) -> str:
        return "deflate"


class GrpcMessageCompressor:
    """Main gRPC message compressor with strategy selection."""
    
    def __init__(self, config: CompressionConfig | None = None):
        self.config = config or CompressionConfig()
        self._strategies: dict[CompressionAlgorithm, CompressionStrategy] = {
            CompressionAlgorithm.NONE: NoCompressionStrategy(self.config),
            CompressionAlgorithm.GZIP: GzipCompressionStrategy(self.config),
            CompressionAlgorithm.DEFLATE: DeflateCompressionStrategy(self.config),
        }
        
        # Statistics tracking
        self._compression_stats = {
            'total_compressions': 0,
            'successful_compressions': 0,
            'total_original_bytes': 0,
            'total_compressed_bytes': 0,
            'total_compression_time_ms': 0.0,
            'algorithm_usage': {
                CompressionAlgorithm.NONE.value: 0,
                CompressionAlgorithm.GZIP.value: 0,
                CompressionAlgorithm.DEFLATE.value: 0,
            },
            'average_compression_ratio': 0.0,
            'bandwidth_saved_bytes': 0,
        }
        
        _logger.info(
            "grpc_compressor_initialized",
            algorithm=self.config.algorithm.value,
            threshold=self.config.threshold_bytes,
            compression_level=self.config.compression_level
        )
    
    def compress_message(
        self, 
        data: bytes, 
        content_type: str = "",
        force_algorithm: CompressionAlgorithm | None = None
    ) -> tuple[bytes, CompressionResult]:
        """Compress a gRPC message."""
        message_size = len(data)
        
        # Check if we should compress
        if not force_algorithm and not self.config.should_compress(message_size, content_type):
            strategy = self._strategies[CompressionAlgorithm.NONE]
        else:
            # Select algorithm
            algorithm = force_algorithm or self.config.select_algorithm(message_size)
            strategy = self._strategies[algorithm]
        
        # Compress the data
        result = strategy.compress(data)
        
        # Update statistics
        if self.config.enable_compression_stats:
            self._update_compression_stats(result)
        
        # Return compressed data and result
        if result.success:
            if result.algorithm != CompressionAlgorithm.NONE:
                # For successful compression, we need to get the actual compressed data
                if result.algorithm == CompressionAlgorithm.GZIP:
                    compressed_data = gzip.compress(data, compresslevel=self.config.compression_level)
                elif result.algorithm == CompressionAlgorithm.DEFLATE:
                    compressed_data = zlib.compress(data, level=self.config.compression_level)
                else:
                    compressed_data = data
            else:
                compressed_data = data
        else:
            # Fallback to uncompressed data
            compressed_data = data
        
        return compressed_data, result
    
    def decompress_message(
        self, 
        compressed_data: bytes, 
        algorithm: CompressionAlgorithm
    ) -> bytes:
        """Decompress a gRPC message."""
        if algorithm == CompressionAlgorithm.NONE:
            return compressed_data
        
        strategy = self._strategies[algorithm]
        return strategy.decompress(compressed_data)
    
    def get_compression_stats(self) -> dict[str, Any]:
        """Get compression statistics."""
        stats = self._compression_stats.copy()
        
        # Calculate derived metrics
        if stats['total_compressions'] > 0:
            stats['success_rate'] = (
                stats['successful_compressions'] / stats['total_compressions']
            ) * 100
            stats['average_compression_time_ms'] = (
                stats['total_compression_time_ms'] / stats['total_compressions']
            )
        else:
            stats['success_rate'] = 0.0
            stats['average_compression_time_ms'] = 0.0
        
        if stats['total_original_bytes'] > 0:
            stats['overall_compression_ratio'] = (
                stats['total_compressed_bytes'] / stats['total_original_bytes']
            )
            stats['bandwidth_saved_percent'] = (
                stats['bandwidth_saved_bytes'] / stats['total_original_bytes']
            ) * 100
        else:
            stats['overall_compression_ratio'] = 1.0
            stats['bandwidth_saved_percent'] = 0.0
        
        return stats
    
    def reset_stats(self) -> None:
        """Reset compression statistics."""
        self._compression_stats = {
            'total_compressions': 0,
            'successful_compressions': 0,
            'total_original_bytes': 0,
            'total_compressed_bytes': 0,
            'total_compression_time_ms': 0.0,
            'algorithm_usage': {
                CompressionAlgorithm.NONE.value: 0,
                CompressionAlgorithm.GZIP.value: 0,
                CompressionAlgorithm.DEFLATE.value: 0,
            },
            'average_compression_ratio': 0.0,
            'bandwidth_saved_bytes': 0,
        }
        
        _logger.info("compression_stats_reset")
    
    def _update_compression_stats(self, result: CompressionResult) -> None:
        """Update compression statistics."""
        self._compression_stats['total_compressions'] += 1
        
        if result.success:
            self._compression_stats['successful_compressions'] += 1
            self._compression_stats['total_original_bytes'] += result.original_size
            self._compression_stats['total_compressed_bytes'] += result.compressed_size
            self._compression_stats['total_compression_time_ms'] += result.compression_time_ms
            self._compression_stats['bandwidth_saved_bytes'] += result.bandwidth_saved
        
        # Update algorithm usage
        algorithm_key = result.algorithm.value
        self._compression_stats['algorithm_usage'][algorithm_key] += 1
    
    def update_config(self, new_config: CompressionConfig) -> None:
        """Update compression configuration."""
        self.config = new_config
        
        # Reinitialize strategies with new config
        self._strategies = {
            CompressionAlgorithm.NONE: NoCompressionStrategy(self.config),
            CompressionAlgorithm.GZIP: GzipCompressionStrategy(self.config),
            CompressionAlgorithm.DEFLATE: DeflateCompressionStrategy(self.config),
        }
        
        _logger.info("compression_config_updated", algorithm=self.config.algorithm.value)
    
    def get_optimal_algorithm(self, message_size: int) -> CompressionAlgorithm:
        """Get optimal algorithm for message size based on historical data."""
        stats = self._compression_stats
        
        # If we don't have enough data, use default selection
        if stats['total_compressions'] < 10:
            return self.config.select_algorithm(message_size)
        
        # Analyze historical performance for each algorithm
        algorithm_performance = {}
        
        for algorithm in [CompressionAlgorithm.GZIP, CompressionAlgorithm.DEFLATE]:
            usage_count = stats['algorithm_usage'][algorithm.value]
            if usage_count > 0:
                # Simple heuristic: prefer algorithm with better compression ratio
                # In a real implementation, you'd track per-algorithm stats
                algorithm_performance[algorithm] = {
                    'usage': usage_count,
                    'preferred_for_size': message_size > 2048  # Simple heuristic
                }
        
        # Select best performing algorithm
        if algorithm_performance:
            best_algorithm = max(algorithm_performance.keys(), 
                                key=lambda x: algorithm_performance[x]['usage'])
            return best_algorithm
        
        return self.config.select_algorithm(message_size)
