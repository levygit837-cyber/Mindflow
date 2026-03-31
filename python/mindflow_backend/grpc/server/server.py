"""Enhanced gRPC server with monitoring, resilience, and advanced features.

Starts gRPC server with comprehensive monitoring, circuit breaker protection,
health checking, metrics collection, and proper integration with FastAPI.
"""

from __future__ import annotations

import asyncio
import signal
import time
from typing import Any

from grpc.aio import Server

import grpc
from mindflow_backend.grpc.config import GrpcConfig
from mindflow_backend.grpc.interceptors.error_handler import ErrorHandlerInterceptor
from mindflow_backend.grpc.interfaces.server import GrpcServer
from mindflow_backend.grpc.monitoring.health import AdvancedHealthChecker
from mindflow_backend.grpc.monitoring.interceptor import MetricsInterceptor
from mindflow_backend.grpc.monitoring.metrics import GrpcMetricsCollector
from mindflow_backend.grpc.services.agent_runtime_service import AgentRuntimeServiceImpl
from mindflow_backend.infra.config import get_settings
from mindflow_backend.infra.logging import get_logger

from .components import (
    initialize_monitoring_components,
    initialize_performance_components,
    initialize_resilience_components,
)

_logger = get_logger(__name__)

# Global singleton — created lazily by get_server().
_server_instance: EnhancedGrpcAgentServer | None = None


class EnhancedGrpcAgentServer(GrpcServer):
    """Enhanced gRPC server with monitoring, resilience, and advanced features."""

    def __init__(self, config: GrpcConfig | None = None):
        self.settings = get_settings()
        self.config = config or GrpcConfig.from_settings()

        # Server state
        self._server: Server | None = None
        self._running = False
        self._start_time: float | None = None
        self._host: str = self.config.host
        self._port: int = self.config.port

        # Enhanced monitoring components
        self.metrics_collector = (
            GrpcMetricsCollector() if self.config.enable_metrics else None
        )
        self.health_checker = (
            AdvancedHealthChecker() if self.config.enable_health_check else None
        )
        self.prometheus_exporter = None
        self.alert_manager = None

        # Enhanced resilience components
        self.circuit_breaker = None
        self.retry_policy = None
        self.bulkhead = None
        self.fallback_manager = None

        # Enhanced performance components
        self.connection_pool_manager = None
        self.message_compressor = None
        self.response_cache = None
        self.profiler = None
        self.optimizer = None

        # Initialize enhanced components
        self._initialize_enhanced_components()

        _logger.info(
            "enhanced_grpc_server_initialized",
            host=self._host,
            port=self._port,
            monitoring=self.config.enable_metrics,
            health_check=self.config.enable_health_check,
            prometheus_port=getattr(self.config, "grpc_prometheus_port", None),
        )

    def _initialize_enhanced_components(self) -> None:
        """Initialize all enhanced resilience and performance components."""
        # Initialize monitoring components
        self.prometheus_exporter, self.alert_manager = initialize_monitoring_components(
            self.config,
            self.metrics_collector,
        )

        # Initialize resilience components
        resilience = initialize_resilience_components(self.config)
        self.circuit_breaker = resilience["circuit_breaker"]
        self.retry_policy = resilience["retry_policy"]
        self.bulkhead = resilience["bulkhead"]
        self.fallback_manager = resilience["fallback_manager"]

        # Initialize performance components
        performance = initialize_performance_components(self.config)
        self.connection_pool_manager = performance["connection_pool_manager"]
        self.message_compressor = performance["message_compressor"]
        self.response_cache = performance["response_cache"]
        self.profiler = performance["profiler"]
        self.optimizer = performance["optimizer"]

        _logger.info(
            "enhanced_components_initialized",
            resilience_components=len(
                [
                    c
                    for c in [
                        self.circuit_breaker,
                        self.retry_policy,
                        self.bulkhead,
                        self.fallback_manager,
                    ]
                    if c
                ]
            ),
            performance_components=len(
                [
                    c
                    for c in [
                        self.connection_pool_manager,
                        self.message_compressor,
                        self.response_cache,
                        self.profiler,
                        self.optimizer,
                    ]
                    if c
                ]
            ),
            monitoring_components=len(
                [
                    c
                    for c in [
                        self.metrics_collector,
                        self.health_checker,
                        self.alert_manager,
                    ]
                    if c
                ]
            ),
        )

    def _build_server_interceptors(self) -> list[Any]:
        """Build the list of interceptors to pass to grpc.aio.server() at creation."""
        interceptors: list[Any] = [
            ErrorHandlerInterceptor(debug=self.settings.app_env == "development")
        ]
        if self.config.enable_metrics and self.metrics_collector:
            interceptors.append(
                MetricsInterceptor(
                    self.metrics_collector,
                    collect_business_metrics=True,
                )
            )
        return interceptors

    async def start(self) -> None:
        """Start the enhanced gRPC server with all features."""
        if self._running:
            _logger.warning("grpc_server_already_running")
            return

        try:
            interceptors = self._build_server_interceptors()

            self._server = grpc.aio.server(
                interceptors=interceptors,
                options=[
                    (
                        "grpc.max_receive_message_length",
                        self.config.max_receive_message_length,
                    ),
                    (
                        "grpc.max_send_message_length",
                        self.config.max_send_message_length,
                    ),
                    (
                        "grpc.keepalive_time_ms",
                        self.config.keepalive_time_seconds * 1000,
                    ),
                    (
                        "grpc.keepalive_timeout_ms",
                        self.config.keepalive_timeout_seconds * 1000,
                    ),
                    ("grpc.http2.max_pings_without_data", 0),
                    ("grpc.http2.min_time_between_pings_ms", 10000),
                    ("grpc.http2.min_ping_interval_without_data_ms", 300000),
                ],
            )

            await self._setup_services()
            await self._configure_port()
            await self._start_monitoring()

            await self._server.start()
            self._running = True
            self._start_time = time.time()

            _logger.info(
                "enhanced_grpc_server_started",
                host=self._host,
                port=self._port,
                secure=self.config.secure,
                uptime_seconds=self.get_uptime_seconds(),
            )

        except Exception as exc:
            _logger.error("grpc_server_start_failed", error=str(exc))
            raise

    async def stop(self, grace_period_seconds: float = 30.0) -> None:
        """Stop the enhanced gRPC server with graceful shutdown."""
        if not self._running:
            _logger.warning("grpc_server_not_running")
            return

        try:
            _logger.info("grpc_server_stopping", grace_period=grace_period_seconds)

            await self._stop_monitoring()

            if self._server:
                await self._server.stop(grace_period_seconds)
                self._server = None

            self._running = False
            self._start_time = None

            _logger.info("grpc_server_stopped")

        except Exception as exc:
            _logger.error("grpc_server_stop_failed", error=str(exc))
            raise

    def is_running(self) -> bool:
        """Check if server is currently running."""
        return self._running

    def get_port(self) -> int:
        """Get the port the server is listening on."""
        return self._port

    def get_host(self) -> str:
        """Get the host the server is bound to."""
        return self._host

    async def wait_for_termination(self) -> None:
        """Wait for server termination."""
        if self._server:
            await self._server.wait_for_termination()

    def add_interceptor(self, interceptor) -> None:
        """Add a server interceptor."""
        if self._server:
            self._server.add_interceptor(interceptor)
            _logger.info("grpc_interceptor_added", type=type(interceptor).__name__)
        else:
            _logger.warning("grpc_server_not_initialized", action="add_interceptor")

    def add_service(self, service) -> None:
        """Add a service to the server."""
        if self._server:
            self._server.add_service(service)
            _logger.info("grpc_service_added", type=type(service).__name__)
        else:
            _logger.warning("grpc_server_not_initialized", action="add_service")

    async def _setup_interceptors(self) -> None:
        """Deprecated: kept for test compatibility."""
        _logger.debug("grpc_setup_interceptors_deprecated_noop")

    async def _setup_services(self) -> None:
        """Setup gRPC services."""
        try:
            from mindflow_backend.grpc.generated import (
                mindflow_backend_pb2_grpc as pb2_grpc,
            )

            service = AgentRuntimeServiceImpl()
            pb2_grpc.add_AgentRuntimeServiceServicer_to_server(service, self._server)

            _logger.info("grpc_services_setup")

        except ImportError as exc:
            raise RuntimeError(
                "Missing generated gRPC bindings. Run: python/scripts/gen_proto.sh"
            ) from exc

    async def _configure_port(self) -> None:
        """Configure server port and security."""
        if self.config.secure:
            await self._setup_secure_port()
        else:
            await self._setup_insecure_port()

    async def _setup_insecure_port(self) -> None:
        """Setup insecure port."""
        self._server.add_insecure_port(f"{self._host}:{self._port}")
        _logger.info("grpc_insecure_port_configured", host=self._host, port=self._port)

    async def _setup_secure_port(self) -> None:
        """Setup secure port with TLS."""
        from pathlib import Path

        cert_path = (
            Path(self.config.tls_cert_path) if self.config.tls_cert_path else None
        )
        key_path = (
            Path(self.config.tls_key_path) if self.config.tls_key_path else None
        )

        if not cert_path or not key_path:
            _logger.warning(
                "grpc_tls_missing_files",
                falling_back_to_insecure=True,
            )
            await self._setup_insecure_port()
            return

        if not cert_path.exists() or not key_path.exists():
            _logger.warning(
                "grpc_tls_files_not_found",
                falling_back_to_insecure=True,
            )
            await self._setup_insecure_port()
            return

        try:
            with open(cert_path, "rb") as f:
                private_key = f.read()
            with open(key_path, "rb") as f:
                certificate_chain = f.read()

            credentials = grpc.ssl_server_credentials([(private_key, certificate_chain)])
            self._server.add_secure_port(f"{self._host}:{self._port}", credentials)

            _logger.info("grpc_secure_port_configured", host=self._host, port=self._port)

        except Exception as exc:
            _logger.error(
                "grpc_tls_setup_failed",
                error=str(exc),
                falling_back_to_insecure=True,
            )
            await self._setup_insecure_port()

    async def _start_monitoring(self) -> None:
        """Start monitoring components."""
        if self.prometheus_exporter:
            self.prometheus_exporter.start()

        if self.health_checker:
            self.health_checker.setup_default_checkers(self.settings)
            await self.health_checker.start_background_monitoring()

        _logger.info("grpc_monitoring_started")

    async def _stop_monitoring(self) -> None:
        """Stop monitoring components."""
        if self.prometheus_exporter:
            self.prometheus_exporter.stop()

        if self.health_checker:
            await self.health_checker.stop_background_monitoring()

        _logger.info("grpc_monitoring_stopped")

    def get_uptime_seconds(self) -> float:
        """Get server uptime in seconds."""
        if self._start_time:
            return time.time() - self._start_time
        return 0.0

    async def get_health_report(self) -> dict[str, Any]:
        """Get comprehensive health report."""
        if not self.health_checker:
            return {"status": "unknown", "message": "Health checking not enabled"}

        try:
            report = await self.health_checker.check_health()
            return {
                "status": report.status.value,
                "uptime_seconds": report.uptime_seconds,
                "version": report.version,
                "timestamp": report.timestamp,
                "checks": [
                    {
                        "name": check.name,
                        "status": check.status.value,
                        "message": check.message,
                        "duration_ms": check.duration_ms,
                    }
                    for check in report.checks
                ],
                "dependencies": report.dependencies,
            }
        except Exception as exc:
            return {"status": "error", "error": str(exc)}

    def get_metrics_summary(self) -> dict[str, Any]:
        """Get metrics summary."""
        if not self.metrics_collector:
            return {"message": "Metrics not enabled"}

        return {
            "request_metrics": self.metrics_collector.get_request_metrics(),
            "connection_metrics": self.metrics_collector.get_connection_metrics(),
            "system_metrics": self.metrics_collector.get_system_metrics(),
            "business_metrics": self.metrics_collector.get_business_metrics(),
            "latency_summary": self.metrics_collector.get_latency_summary(),
        }

    def get_server_info(self) -> dict[str, Any]:
        """Get comprehensive server information."""
        return {
            "server": {
                "host": self.get_host(),
                "port": self.get_port(),
                "running": self.is_running(),
                "uptime_seconds": self.get_uptime_seconds(),
                "secure": self.config.secure,
                "start_time": self._start_time,
            },
            "config": {
                "enabled": self.config.enabled,
                "auto_start": self.config.auto_start,
                "max_connections": self.config.max_connections,
                "connection_timeout": self.config.connection_timeout_seconds,
                "max_attempts": self.config.max_attempts,
                "default_timeout": self.config.default_timeout_seconds,
                "enable_metrics": self.config.enable_metrics,
                "enable_health_check": self.config.enable_health_check,
            },
            "features": {
                "monitoring": self.config.enable_metrics,
                "health_check": self.config.enable_health_check,
                "prometheus": bool(self.prometheus_exporter),
                "error_handling": True,
                "tls": self.config.secure,
            },
        }

    def get_enhanced_status(self) -> dict[str, Any]:
        """Get comprehensive status of all enhanced components."""
        status = self.get_server_info()

        status["resilience"] = {}
        if self.circuit_breaker:
            status["resilience"]["circuit_breaker"] = (
                self.circuit_breaker.get_enhanced_metrics()
            )
        if self.retry_policy:
            status["resilience"]["retry_policy"] = (
                self.retry_policy.get_advanced_metrics()
            )
        if self.bulkhead:
            status["resilience"]["bulkhead"] = self.bulkhead.get_status()
        if self.fallback_manager:
            status["resilience"]["fallback_manager"] = (
                self.fallback_manager.get_metrics()
            )

        status["performance"] = {}
        if self.connection_pool_manager:
            status["performance"]["connection_pool_manager"] = (
                self.connection_pool_manager.get_status()
            )
        if self.message_compressor:
            status["performance"]["message_compressor"] = (
                self.message_compressor.get_compression_stats()
            )
        if self.response_cache:
            status["performance"]["response_cache"] = self.response_cache.get_stats()
        if self.profiler:
            status["performance"]["profiler"] = self.profiler.get_summary()
        if self.optimizer:
            status["performance"]["optimizer"] = self.optimizer.get_status()

        status["alerting"] = {}
        if self.alert_manager:
            status["alerting"]["alert_manager"] = self.alert_manager.get_alert_metrics()
            status["alerting"]["active_alerts"] = len(
                self.alert_manager.get_active_alerts()
            )

        return status


# ── Public compatibility aliases ─────────────────────────────────────────────

GrpcAgentServer = EnhancedGrpcAgentServer


def run() -> None:
    """Run gRPC server synchronously."""
    asyncio.run(serve())


async def get_server() -> EnhancedGrpcAgentServer:
    """Get or create the global server instance."""
    global _server_instance
    if _server_instance is None:
        _server_instance = EnhancedGrpcAgentServer()
    return _server_instance


async def start_grpc_server(
    config: GrpcConfig | None = None,
) -> EnhancedGrpcAgentServer:
    """Start gRPC server and return instance for management."""
    server = await get_server()

    if config:
        server.config = config
        server._host = config.host
        server._port = config.port

    if not server.is_running():
        await server.start()
    return server


async def stop_grpc_server() -> None:
    """Stop the global gRPC server instance."""
    global _server_instance
    if _server_instance and _server_instance.is_running():
        await _server_instance.stop()
        _server_instance = None


def setup_signal_handlers() -> None:
    """Setup signal handlers for graceful shutdown."""
    def signal_handler(signum, frame):
        _logger.info("grpc_shutdown_signal_received", signal=signum)
        asyncio.create_task(stop_grpc_server())

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)


async def get_grpc_server() -> EnhancedGrpcAgentServer:
    """Awaitable alias for get_server() — use this in FastAPI endpoints."""
    return await get_server()


async def serve() -> None:
    """Start gRPC server and block until termination (standalone use)."""
    server = GrpcAgentServer()
    setup_signal_handlers()
    await server.start()
    await server.wait_for_termination()


if __name__ == "__main__":
    setup_signal_handlers()
    run()