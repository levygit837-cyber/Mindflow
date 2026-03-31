"""Message compression for gRPC performance optimization.

Provides compression strategies and utilities for reducing
bandwidth usage and improving transfer speeds.
"""

from .compressor import CompressionAlgorithm, CompressionConfig, GrpcMessageCompressor

__all__ = [
    "GrpcMessageCompressor",
    "CompressionConfig", 
    "CompressionAlgorithm",
]
