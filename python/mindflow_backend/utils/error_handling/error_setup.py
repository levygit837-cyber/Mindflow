"""Error handling setup utilities for MindFlow.

Provides convenient functions to set up error handling for different
frameworks and services with consistent configuration.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI

from mindflow_backend.api.middleware.error_handler import ErrorHandlerMiddleware
from mindflow_backend.grpc_internal.interceptors.error_handler import ErrorHandlerInterceptor


def setup_fastapi_error_handling(
    app: FastAPI,
    *,
    debug: bool = False,
    cors_origins: list[str] | None = None,
    cors_allow_credentials: bool = True,
    cors_allow_methods: list[str] | None = None,
    cors_allow_headers: list[str] | None = None,
) -> None:
    """Set up comprehensive error handling for FastAPI application.
    
    Args:
        app: FastAPI application instance
        debug: Enable debug mode with stack traces
        cors_origins: List of allowed CORS origins (default: ["*"] for development)
        cors_allow_credentials: Allow credentials in CORS
        cors_allow_methods: List of allowed HTTP methods (default: ["*"])
        cors_allow_headers: List of allowed headers (default: ["*"])
    """
    # Add error handling middleware
    app.add_middleware(ErrorHandlerMiddleware, debug=debug)
    
    # Add CORS middleware if requested
    if cors_origins is None:
        cors_origins = ["*"]  # Development default
    if cors_allow_methods is None:
        cors_allow_methods = ["*"]
    if cors_allow_headers is None:
        cors_allow_headers = ["*"]
    
    try:
        from fastapi.middleware.cors import CORSMiddleware
        app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_credentials=cors_allow_credentials,
            allow_methods=cors_allow_methods,
            allow_headers=cors_allow_headers,
        )
    except ImportError:
        # CORS middleware not available, skip
        pass


def setup_grpc_error_handling(
    server: Any,
    *,
    debug: bool = False,
    port: int = 50051,
    host: str = "[::]:",
) -> None:
    """Set up comprehensive error handling for gRPC server.
    
    Args:
        server: gRPC server instance
        debug: Enable debug mode with stack traces
        port: Port to bind the server to
        host: Host to bind the server to
    """
    # Add error handling interceptor
    error_interceptor = ErrorHandlerInterceptor(debug=debug)
    server.add_interceptor(error_interceptor)
    
    # Add insecure port
    server.add_insecure_port(f"{host}{port}")


def setup_comprehensive_error_handling(
    fastapi_app: FastAPI | None = None,
    grpc_server: Any | None = None,
    *,
    debug: bool = False,
    fastapi_cors_origins: list[str] | None = None,
    grpc_port: int = 50051,
    grpc_host: str = "[::]:",
) -> dict[str, Any]:
    """Set up error handling for both FastAPI and gRPC services.
    
    Args:
        fastapi_app: FastAPI application instance (optional)
        grpc_server: gRPC server instance (optional)
        debug: Enable debug mode with stack traces
        fastapi_cors_origins: CORS origins for FastAPI
        grpc_port: Port for gRPC server
        grpc_host: Host for gRPC server
        
    Returns:
        Dictionary with setup status and configuration
    """
    setup_status = {
        "fastapi_setup": False,
        "grpc_setup": False,
        "debug_enabled": debug,
        "configuration": {
            "fastapi_cors_origins": fastapi_cors_origins or ["*"],
            "grpc_port": grpc_port,
            "grpc_host": grpc_host,
        },
    }
    
    if fastapi_app is not None:
        setup_fastapi_error_handling(
            fastapi_app,
            debug=debug,
            cors_origins=fastapi_cors_origins,
        )
        setup_status["fastapi_setup"] = True
    
    if grpc_server is not None:
        setup_grpc_error_handling(
            grpc_server,
            debug=debug,
            port=grpc_port,
            host=grpc_host,
        )
        setup_status["grpc_setup"] = True
    
    return setup_status


def create_error_handling_config(
    *,
    debug: bool = False,
    log_level: str = "INFO",
    enable_metrics: bool = False,
    enable_tracing: bool = False,
) -> dict[str, Any]:
    """Create standardized error handling configuration.
    
    Args:
        debug: Enable debug mode
        log_level: Logging level
        enable_metrics: Enable error metrics collection
        enable_tracing: Enable distributed tracing
        
    Returns:
        Configuration dictionary
    """
    return {
        "debug": debug,
        "log_level": log_level,
        "enable_metrics": enable_metrics,
        "enable_tracing": enable_tracing,
        "middleware_config": {
            "fastapi": {"debug": debug},
            "grpc": {"debug": debug},
        },
        "logging_config": {
            "structured": True,
            "include_context": True,
            "include_stack_trace": debug,
        },
    }
