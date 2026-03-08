"""Compression strategies for different algorithms and use cases.

"""

from __future__ import annotations

import time
import heapq
from typing import Dict, Any, Optional, List
from collections import defaultdict, OrderedDict
from abc import ABC, abstractmethod

from .compressor import CompressionStrategy, CompressionResult, CompressionConfig, CompressionAlgorithm
from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


class AdaptiveCompressionStrategy(CompressionStrategy):
    """Adaptive compression that adjusts based on performance feedback."""
    
    def __init__(self, config: CompressionConfig):
        super().__init__(config)
        self._performance_history: Dict[str, float] = {}
        self._adaptive_enabled = True
        self._min_samples = 5
    
    def compress(self, data: bytes) -> CompressionResult:
        """Compress with adaptive algorithm selection."""
        import time
        start_time = time.time()
        
        # Select best algorithm based on historical performance
        algorithm = self._select_adaptive_algorithm(len(data))
        
        try:
            if algorithm == CompressionAlgorithm.GZIP:
                compressed_data = gzip.compress(data, compresslevel=self.config.compression_level)
            elif algorithm == CompressionAlgorithm.DEFLATE:
                compressed_data = zlib.compress(data, level=self.config.compression_level)
            else:
                compressed_data = data
            
            compression_time = (time.time() - start_time) * 1000
            compression_ratio = len(compressed_data) / len(data) if data else 1.0
            
            # Update performance history
            if self._adaptive_enabled:
                self._update_performance_history(algorithm, compression_time, compression_ratio)
            
            return CompressionResult(
                original_size=len(data),
                compressed_size=len(compressed_data),
                algorithm=algorithm,
                compression_ratio=compression_ratio,
                compression_time_ms=compression_time,
                success=True
            )
            
        except Exception as e:
            _logger.error("adaptive_compression_failed", error=str(e))
            return CompressionResult(
                original_size=len(data),
                compressed_size=len(data),
                algorithm=algorithm,
                compression_ratio=1.0,
                compression_time_ms=(time.time() - start_time) * 1000,
                success=False,
                error_message=str(e)
            )
    
    def decompress(self, compressed_data: bytes) -> bytes:
        """Decompress based on algorithm."""
        # This would need to know the algorithm used
        # For now, try both
        try:
            return gzip.decompress(compressed_data)
        except:
            try:
                return zlib.decompress(compressed_data)
            except:
                return compressed_data
    
    def get_name(self) -> str:
        return "adaptive"
    
    def _select_adaptive_algorithm(self, message_size: int) -> CompressionAlgorithm:
        """Select algorithm based on historical performance."""
        if not self._adaptive_enabled or len(self._performance_history) < self._min_samples:
            return self.config.select_algorithm(message_size)
        
        # Analyze performance history
        gzip_performance = self._performance_history.get('gzip_time', float('inf'))
        deflate_performance = self._performance_history.get('deflate_time', float('inf'))
        
        # Choose faster algorithm
        if gzip_performance < deflate_performance:
            return CompressionAlgorithm.GZIP
        else:
            return CompressionAlgorithm.DEFLATE
    
    def _update_performance_history(self, algorithm: CompressionAlgorithm, 
                                 time_ms: float, ratio: float) -> None:
        """Update performance history for algorithm."""
        key = f"{algorithm.value}_time"
        
        if key not in self._performance_history:
            self._performance_history[key] = time_ms
        else:
            # Exponential moving average
            alpha = 0.3
            self._performance_history[key] = (
                alpha * time_ms + (1 - alpha) * self._performance_history[key]
            )


class FastCompressionStrategy(CompressionStrategy):
    """Fast compression optimized for speed over ratio."""
    
    def compress(self, data: bytes) -> CompressionResult:
        """Compress with maximum speed."""
        import time
        start_time = time.time()
        
        try:
            # Use lowest compression level for speed
            compressed_data = gzip.compress(data, compresslevel=1)
            compression_time = (time.time() - start_time) * 1000
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
            _logger.error("fast_compression_failed", error=str(e))
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
        """Decompress data."""
        try:
            return gzip.decompress(compressed_data)
        except Exception as e:
            _logger.error("fast_decompression_failed", error=str(e))
            raise
    
    def get_name(self) -> str:
        return "fast"


class HighCompressionStrategy(CompressionStrategy):
    """High compression optimized for ratio over speed."""
    
    def compress(self, data: bytes) -> CompressionResult:
        """Compress with maximum ratio."""
        import time
        start_time = time.time()
        
        try:
            # Use highest compression level for ratio
            compressed_data = gzip.compress(data, compresslevel=9)
            compression_time = (time.time() - start_time) * 1000
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
            _logger.error("high_compression_failed", error=str(e))
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
        """Decompress data."""
        try:
            return gzip.decompress(compressed_data)
        except Exception as e:
            _logger.error("high_decompression_failed", error=str(e))
            raise
    
    def get_name(self) -> str:
        return "high"


class LZ4CompressionStrategy(CompressionStrategy):
    """LZ4 compression strategy (if available)."""
    
    def __init__(self, config: CompressionConfig):
        super().__init__(config)
        self._lz4_available = self._check_lz4_availability()
        if not self._lz4_available:
            _logger.warning("lz4_not_available", fallback="gzip")
    
    def _check_lz4_availability(self) -> bool:
        """Check if LZ4 is available."""
        try:
            import lz4.frame
            return True
        except ImportError:
            return False
    
    def compress(self, data: bytes) -> CompressionResult:
        """Compress using LZ4 if available, otherwise gzip."""
        import time
        start_time = time.time()
        
        try:
            if self._lz4_available:
                import lz4.frame
                compressed_data = lz4.frame.compress(data)
                algorithm = CompressionAlgorithm.GZIP  # Use GZIP enum for consistency
            else:
                # Fallback to gzip
                compressed_data = gzip.compress(data, compresslevel=self.config.compression_level)
                algorithm = CompressionAlgorithm.GZIP
            
            compression_time = (time.time() - start_time) * 1000
            compression_ratio = len(compressed_data) / len(data) if data else 1.0
            
            return CompressionResult(
                original_size=len(data),
                compressed_size=len(compressed_data),
                algorithm=algorithm,
                compression_ratio=compression_ratio,
                compression_time_ms=compression_time,
                success=True
            )
            
        except Exception as e:
            _logger.error("lz4_compression_failed", error=str(e))
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
        """Decompress LZ4 or gzip data."""
        try:
            if self._lz4_available:
                import lz4.frame
                return lz4.frame.decompress(compressed_data)
            else:
                return gzip.decompress(compressed_data)
        except Exception as e:
            _logger.error("lz4_decompression_failed", error=str(e))
            raise
    
    def get_name(self) -> str:
        return "lz4"


class ContentAwareCompressionStrategy(CompressionStrategy):
    """Compression strategy that adapts based on content type."""
    
    def __init__(self, config: CompressionConfig):
        super().__init__(config)
        self._content_strategies = {
            'application/json': self._compress_json,
            'text/plain': self._compress_text,
            'application/x-protobuf': self._compress_protobuf,
            'text/html': self._compress_html,
        }
    
    def compress(self, data: bytes) -> CompressionResult:
        """Compress based on content analysis."""
        import time
        start_time = time.time()
        
        try:
            # Simple content detection
            content_type = self._detect_content_type(data)
            
            # Use content-specific strategy
            if content_type in self._content_strategies:
                compressed_data, algorithm = self._content_strategies[content_type](data)
            else:
                # Default compression
                compressed_data = gzip.compress(data, compresslevel=self.config.compression_level)
                algorithm = CompressionAlgorithm.GZIP
            
            compression_time = (time.time() - start_time) * 1000
            compression_ratio = len(compressed_data) / len(data) if data else 1.0
            
            return CompressionResult(
                original_size=len(data),
                compressed_size=len(compressed_data),
                algorithm=algorithm,
                compression_ratio=compression_ratio,
                compression_time_ms=compression_time,
                success=True
            )
            
        except Exception as e:
            _logger.error("content_aware_compression_failed", error=str(e))
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
        """Decompress data."""
        try:
            return gzip.decompress(compressed_data)
        except Exception as e:
            _logger.error("content_aware_decompression_failed", error=str(e))
            raise
    
    def get_name(self) -> str:
        return "content_aware"
    
    def _detect_content_type(self, data: bytes) -> str:
        """Simple content type detection."""
        try:
            text = data[:100].decode('utf-8', errors='ignore')
            
            if text.startswith('{') or text.startswith('['):
                return 'application/json'
            elif '<html>' in text.lower():
                return 'text/html'
            elif text.strip().startswith('proto'):
                return 'application/x-protobuf'
            else:
                return 'text/plain'
        except:
            return 'application/octet-stream'
    
    def _compress_json(self, data: bytes) -> tuple[bytes, CompressionAlgorithm]:
        """Compress JSON data."""
        # JSON compresses well with gzip
        compressed = gzip.compress(data, compresslevel=6)
        return compressed, CompressionAlgorithm.GZIP
    
    def _compress_text(self, data: bytes) -> tuple[bytes, CompressionAlgorithm]:
        """Compress text data."""
        # Text compresses well with deflate
        compressed = zlib.compress(data, level=6)
        return compressed, CompressionAlgorithm.DEFLATE
    
    def _compress_protobuf(self, data: bytes) -> tuple[bytes, CompressionAlgorithm]:
        """Compress protobuf data."""
        # Protobuf is already binary, use light compression
        compressed = gzip.compress(data, compresslevel=3)
        return compressed, CompressionAlgorithm.GZIP
    
    def _compress_html(self, data: bytes) -> tuple[bytes, CompressionAlgorithm]:
        """Compress HTML data."""
        # HTML compresses well with gzip
        compressed = gzip.compress(data, compresslevel=6)
        return compressed, CompressionAlgorithm.GZIP


# Strategy factory
def create_compression_strategy(strategy_name: str, config: CompressionConfig) -> CompressionStrategy:
    """Create a compression strategy by name."""
    strategies = {
        'none': NoCompressionStrategy,
        'gzip': GzipCompressionStrategy,
        'deflate': DeflateCompressionStrategy,
        'adaptive': AdaptiveCompressionStrategy,
        'fast': FastCompressionStrategy,
        'high': HighCompressionStrategy,
        'lz4': LZ4CompressionStrategy,
        'content_aware': ContentAwareCompressionStrategy,
    }
    
    if strategy_name not in strategies:
        raise ValueError(f"Unknown compression strategy: {strategy_name}")
    
    return strategies[strategy_name](config)
