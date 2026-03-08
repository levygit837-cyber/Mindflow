"""Message compression for gRPC performance optimization.

Provides compression strategies and utilities for reducing
bandwidth usage and improving transfer speeds.
"""

from .compressor import GrpcMessageCompressor, CompressionConfig, CompressionAlgorithm

__all__ = [
    "GrpcMessageCompressor",
    "CompressionConfig", 
    "CompressionAlgorithm",
]
