import logging
import signal
import sys
import time
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from mindflow_backend.agents._registry import register_all_specialists
from mindflow_backend.api.router import router
from mindflow_backend.api.docs import custom_openapi, setup_documentation_routes, add_operation_examples
from mindflow_backend.grpc.server import start_grpc_server, stop_grpc_server, setup_signal_handlers
from mindflow_backend.grpc.config.dynamic.manager import DynamicConfigManager, get_config_manager
from mindflow_backend.grpc.config.profiles import get_environment_loader
from mindflow_backend.grpc.config.features import get_feature_toggles
from mindflow_backend.grpc.config.config import GrpcConfig
from mindflow_backend.infra.config import get_settings
from mindflow_backend.infra.logging import configure_logging, get_logger
from mindflow_backend.infra.middleware.rate_limiter import RateLimiterMiddleware
from mindflow_backend.infra.middleware.request_context import RequestContextMiddleware
from mindflow_backend.infra.middleware.security_headers import SecurityHeadersMiddleware
from mindflow_backend.api.middleware.validation import ValidationMiddleware
from mindflow_backend.api.middleware.performance import PerformanceMiddleware
from mindflow_backend.api.middleware.caching import AdvancedCacheMiddleware, MemoryCacheBackend
from mindflow_backend.storage import Base

settings = get_settings()
configure_logging(logging.DEBUG if settings.app_env == "development" else logging.INFO)
_logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager with gRPC and dynamic configuration integration."""
    # Convenience bootstrap for local environments.
    # Base.metadata.create_all(bind=engine)
    # Phase 2: Boot agent registry.
    register_all_specialists()

    # Initialize database
    from mindflow_backend.infra.database.connection import initialize_database
    try:
        await initialize_database()
        _logger.info("database_initialized")
    except Exception as exc:
        _logger.error("database_initialization_failed", error=str(exc))

    # Initialize dynamic configuration system
    config_manager = await get_config_manager()
    await config_manager.initialize()
    app.state.config_manager = config_manager

    # Start gRPC server only if explicitly enabled in settings
    if settings.grpc_enabled and settings.grpc_auto_start:
        try:
            from mindflow_backend.grpc.config import GrpcConfig
            grpc_config = await GrpcConfig.load_dynamic()
            app.state.grpc_config = grpc_config
            grpc_server = await start_grpc_server(grpc_config)
            app.state.grpc_server = grpc_server
            _logger.info("grpc_server_started_in_lifespan", port=grpc_server.get_port())
        except Exception as exc:
            _logger.error("grpc_server_startup_failed", error=str(exc))
    else:
        _logger.info("grpc_server_disabled")
    
    yield
    
    # Shutdown gRPC server
    if hasattr(app.state, 'grpc_server'):
        try:
            await stop_grpc_server()
            _logger.info("grpc_server_stopped_in_lifespan")
        except Exception as exc:
            _logger.error("grpc_server_shutdown_failed", error=str(exc))


app = FastAPI(
    title="MindFlow API",
    description="Advanced AI agent orchestration and management platform",
    version="2.0.0",
    lifespan=lifespan,
    docs_url=None,  # We'll set up custom docs
    redoc_url=None,  # We'll set up custom docs
    openapi_url="/openapi.json"
)

# Set up custom OpenAPI schema
app.openapi = lambda: custom_openapi(app)

# Set up documentation routes
setup_documentation_routes(app)

# Add operation examples
add_operation_examples(app)

# Set up rate limiting
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


def _parse_csv(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


cors_allow_origins = _parse_csv(settings.cors_allow_origins)
cors_allow_credentials = settings.cors_allow_credentials and "*" not in cors_allow_origins
cors_expose_headers = _parse_csv(settings.cors_expose_headers)

# Production CORS hardening: restrict methods and headers.
if settings.app_env == "production":
    cors_allow_methods = _parse_csv(settings.cors_allow_methods) or ["GET", "POST", "OPTIONS"]
    cors_allow_headers = _parse_csv(settings.cors_allow_headers) or [
        "Authorization", "Content-Type", "X-Request-ID",
    ]
    cors_expose_headers = cors_expose_headers or ["X-Request-ID"]
else:
    cors_allow_methods = _parse_csv(settings.cors_allow_methods) or ["*"]
    cors_allow_headers = _parse_csv(settings.cors_allow_headers) or ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_allow_origins,
    allow_credentials=cors_allow_credentials,
    allow_methods=cors_allow_methods,
    allow_headers=cors_allow_headers,
    expose_headers=cors_expose_headers,
)

app.include_router(router)

# Add SlowAPI middleware for rate limiting (add first)
app.add_middleware(SlowAPIMiddleware)

# Performance middleware (AdvancedCacheMiddleware disabled: body unreadable in BaseHTTPMiddleware)
app.add_middleware(PerformanceMiddleware, cache_ttl=300, max_cache_size=1000)

# Security and validation middleware
app.add_middleware(ValidationMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimiterMiddleware)
app.add_middleware(RequestContextMiddleware)


@app.get("/health")
async def health() -> dict[str, str | dict]:
    """Health check endpoint that includes gRPC status with dynamic configuration."""
    grpc_status = {
        "enabled": False,
        "status": "not_running",
    }
    
    # Check if we have dynamic configuration
    if hasattr(app.state, 'grpc_config'):
        grpc_config = app.state.grpc_config
        grpc_status.update({
            "enabled": grpc_config.enabled,
            "profile": grpc_config.profile,
            "auto_reload": grpc_config.auto_reload,
        })
        
        if grpc_config.enabled:
            try:
                from mindflow_backend.grpc.server import get_server
                server = get_server()
                if server and server.is_running():
                    grpc_status.update({
                        "status": "running",
                        "host": server.get_host(),
                        "port": server.get_port(),
                        "uptime_seconds": server.get_uptime_seconds(),
                    })
                    
                    # Add enhanced health info if available
                    if hasattr(server, 'get_health_report'):
                        health_report = await server.get_health_report()
                        grpc_status["health_details"] = health_report
                        
            except Exception as exc:
                grpc_status["status"] = "error"
                grpc_status["error"] = str(exc)
    
    return {
        "status": "ok",
        "app_name": settings.app_name,
        "environment": settings.app_env,
        "grpc": grpc_status,
    }


@app.get("/api-info")
def api_info():
    """Get comprehensive API information."""
    from mindflow_backend.api.docs import create_api_info
    return create_api_info()


@app.get("/test-rate-limit")
@limiter.limit("5/minute")
async def test_rate_limit(request: Request):
    """Test endpoint for rate limiting."""
    return {"message": "Rate limiting test successful", "timestamp": time.time()}


def run() -> None:
    """Run the application with gRPC integration."""
    # Setup signal handlers for graceful shutdown
    setup_signal_handlers()
    
    uvicorn.run(
        "mindflow_backend.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_env == "development",
    )


if __name__ == "__main__":
    print(f"FastAPI Backend starting on {settings.app_host}:{settings.app_port}...", flush=True)
    if settings.grpc_enabled:
        print(f"gRPC Server will start on {settings.grpc_host}:{settings.grpc_port}", flush=True)
    run()
