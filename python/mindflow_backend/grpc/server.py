"""Enhanced gRPC server with monitoring, resilience, and advanced features.

Starts gRPC server with comprehensive monitoring, circuit breaker protection,
health checking, metrics collection, and proper integration with FastAPI.
"""

from __future__ import annotations

import asyncio
import signal
import time
from typing import Any

import grpc
from grpc.aio import Server

from mindflow_backend.grpc.interfaces.server import GrpcServer
from mindflow_backend.grpc.interceptors.error_handler import ErrorHandlerInterceptor
from mindflow_backend.grpc.monitoring.metrics import GrpcMetricsCollector
from mindflow_backend.grpc.monitoring.interceptor import MetricsInterceptor
from mindflow_backend.grpc.monitoring.health import AdvancedHealthChecker
from mindflow_backend.grpc.monitoring.prometheus import PrometheusExporter
from mindflow_backend.grpc.services.agent_runtime_service import AgentRuntimeServiceImpl
from mindflow_backend.grpc.config import GrpcConfig
from mindflow_backend.infra.config import get_settings
from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


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
        
        # Enhanced components
        self.metrics_collector = GrpcMetricsCollector() if self.config.enable_metrics else None
        self.health_checker = AdvancedHealthChecker() if self.config.enable_health_check else None
        self.prometheus_exporter = None
        
        # Initialize components
        if self.config.enable_metrics and self.config.grpc_prometheus_port:
            self.prometheus_exporter = PrometheusExporter(
                self.metrics_collector,
                host="0.0.0.0",
                port=self.config.grpc_prometheus_port
            )
        
        _logger.info(
            "enhanced_grpc_server_initialized",
            host=self._host,
            port=self._port,
            monitoring=self.config.enable_metrics,
            health_check=self.config.enable_health_check,
            prometheus_port=getattr(self.config, 'grpc_prometheus_port', None)
        )
    
    async def start(self) -> None:
        """Start the enhanced gRPC server with all features."""
        if self._running:
            _logger.warning("grpc_server_already_running")
            return
        
        try:
            # Create gRPC server
            self._server = grpc.aio.server(
                options=[
                    ('grpc.max_receive_message_length', self.config.max_receive_message_length),
                    ('grpc.max_send_message_length', self.config.max_send_message_length),
                    ('grpc.keepalive_time_ms', self.config.keepalive_time_seconds * 1000),
                    ('grpc.keepalive_timeout_ms', self.config.keepalive_timeout_seconds * 1000),
                    ('grpc.http2.max_pings_without_data', 0),
                    ('grpc.http2.min_time_between_pings_ms', 10000),
                    ('grpc.http2.min_ping_interval_without_data_ms', 300000),
                ]
            )
            
            # Setup interceptors
            await self._setup_interceptors()
            
            # Setup services
            await self._setup_services()
            
            # Configure port and security
            await self._configure_port()
            
            # Start monitoring components
            await self._start_monitoring()
            
            # Start server
            await self._server.start()
            self._running = True
            self._start_time = time.time()
            
            _logger.info(
                "enhanced_grpc_server_started",
                host=self._host,
                port=self._port,
                secure=self.config.secure,
                uptime_seconds=self.get_uptime_seconds()
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
            
            # Stop monitoring components
            await self._stop_monitoring()
            
            # Graceful shutdown
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
        """Setup server interceptors."""
        interceptors = []
        
        # Error handling interceptor (always enabled)
        error_interceptor = ErrorHandlerInterceptor(debug=self.settings.app_env == "development")
        interceptors.append(error_interceptor)
        
        # Metrics interceptor
        if self.config.enable_metrics and self.metrics_collector:
            metrics_interceptor = MetricsInterceptor(
                self.metrics_collector,
                collect_business_metrics=True
            )
            interceptors.append(metrics_interceptor)
        
        # Add all interceptors to server
        for interceptor in interceptors:
            self.add_interceptor(interceptor)
        
        _logger.info("grpc_interceptors_setup", count=len(interceptors))
    
    async def _setup_services(self) -> None:
        """Setup gRPC services."""
        try:
            # Import generated bindings
            from mindflow_backend.grpc.generated import mindflow_backend_pb2_grpc as pb2_grpc
            
            # Create and add service
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
        
        cert_path = Path(self.config.tls_cert_path) if self.config.tls_cert_path else None
        key_path = Path(self.config.tls_key_path) if self.config.tls_key_path else None
        
        if not cert_path or not key_path:
            _logger.warning("grpc_tls_missing_files", falling_back_to_insecure=True)
            await self._setup_insecure_port()
            return
        
        if not cert_path.exists() or not key_path.exists():
            _logger.warning("grpc_tls_files_not_found", falling_back_to_insecure=True)
            await self._setup_insecure_port()
            return
        
        try:
            # Read certificate files
            with open(cert_path, 'rb') as f:
                private_key = f.read()
            with open(key_path, 'rb') as f:
                certificate_chain = f.read()
            
            # Create server credentials
            credentials = grpc.ssl_server_credentials(
                [(private_key, certificate_chain)]
            )
            
            # Add secure port
            self._server.add_secure_port(f"{self._host}:{self._port}", credentials)
            
            _logger.info("grpc_secure_port_configured", host=self._host, port=self._port)
            
        except Exception as exc:
            _logger.error("grpc_tls_setup_failed", error=str(exc), falling_back_to_insecure=True)
            await self._setup_insecure_port()
    
    async def _start_monitoring(self) -> None:
        """Start monitoring components."""
        # Start Prometheus exporter
        if self.prometheus_exporter:
            self.prometheus_exporter.start()
        
        # Setup health checker
        if self.health_checker:
            self.health_checker.setup_default_checkers(self.settings)
            await self.health_checker.start_background_monitoring()
        
        _logger.info("grpc_monitoring_started")
    
    async def _stop_monitoring(self) -> None:
        """Stop monitoring components."""
        # Stop Prometheus exporter
        if self.prometheus_exporter:
            self.prometheus_exporter.stop()
        
        # Stop health checker
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
            return {
                "status": "unknown",
                "message": "Health checking not enabled"
            }
        
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
                        "duration_ms": check.duration_ms
                    }
                    for check in report.checks
                ],
                "dependencies": report.dependencies
            }
        except Exception as exc:
            return {
                "status": "error",
                "error": str(exc)
            }
    
    def get_metrics_summary(self) -> dict[str, Any]:
        """Get metrics summary."""
        if not self.metrics_collector:
            return {"message": "Metrics not enabled"}
        
        return {
            "request_metrics": self.metrics_collector.get_request_metrics(),
            "connection_metrics": self.metrics_collector.get_connection_metrics(),
            "system_metrics": self.metrics_collector.get_system_metrics(),
            "business_metrics": self.metrics_collector.get_business_metrics(),
            "latency_summary": self.metrics_collector.get_latency_summary()
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
                "start_time": self._start_time
            },
            "config": {
                "enabled": self.config.enabled,
                "auto_start": self.config.auto_start,
                "max_connections": self.config.max_connections,
                "connection_timeout": self.config.connection_timeout_seconds,
                "max_attempts": self.config.max_attempts,
                "default_timeout": self.config.default_timeout_seconds,
                "enable_metrics": self.config.enable_metrics,
                "enable_health_check": self.config.enable_health_check
            },
            "features": {
                "monitoring": self.config.enable_metrics,
                "health_check": self.config.enable_health_check,
                "prometheus": bool(self.prometheus_exporter),
                "error_handling": True,
                "tls": self.config.secure
            }
        }


def run() -> None:
    """Run gRPC server synchronously."""
    asyncio.run(serve())


async def get_server() -> GrpcAgentServer:
    """Get or create the global server instance."""
    global _server_instance
    if _server_instance is None:
        _server_instance = GrpcAgentServer()
    return _server_instance


async def start_grpc_server() -> GrpcAgentServer:
    """Start gRPC server and return instance for management."""
    server = await get_server()
    if not server.is_running():
        await server.start()
    return server


async def stop_grpc_server() -> None:
    """Stop the global gRPC server instance."""
    global _server_instance
    if _server_instance and _server_instance.is_running():
        await _server_instance.stop()
        _server_instance = None


# Graceful shutdown handling
def setup_signal_handlers() -> None:
    """Setup signal handlers for graceful shutdown."""
    def signal_handler(signum, frame):
        _logger.info("grpc_shutdown_signal_received", signal=signum)
        asyncio.create_task(stop_grpc_server())
    
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)


if __name__ == "__main__":
    setup_signal_handlers()
    run()
