"""Advanced Prometheus metrics exporter for gRPC services.

Provides HTTP endpoint for Prometheus scraping, Grafana dashboard generation,
and alert rule configuration. Includes browser metrics for LightPanda integration.
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler
from typing import Any

import uvicorn
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.services.browser import BrowserMetricsCollector

_logger = get_logger(__name__)


class PrometheusMetricsHandler(BaseHTTPRequestHandler):
    """HTTP request handler for Prometheus metrics endpoint."""
    
    def __init__(self, metrics_collector: GrpcMetricsCollector, browser_metrics_collector: BrowserMetricsCollector | None = None, *args, **kwargs):
        self.metrics_collector = metrics_collector
        self.browser_metrics_collector = browser_metrics_collector
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """Handle GET requests for metrics."""
        if self.path == '/metrics':
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; version=0.0.4')
            self.end_headers()
            
            metrics_text = self._generate_metrics_text()
            self.wfile.write(metrics_text.encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        """Override to prevent default logging."""
        pass
    
    def _generate_metrics_text(self) -> str:
        """Generate Prometheus metrics text format."""
        lines = []
        
        # Request metrics
        request_metrics = self.metrics_collector.get_request_metrics()
        for method, metrics in request_metrics.items():
            method_safe = method.replace('/', '_').replace('.', '_')
            
            # Request count
            lines.append(f'grpc_requests_total{{method="{method}"}} {metrics["request_count"]}')
            
            # Error count
            lines.append(f'grpc_errors_total{{method="{method}"}} {metrics["error_count"]}')
            
            # Success rate
            lines.append(f'grpc_success_rate{{method="{method}"}} {metrics["success_rate"]}')
            
            # Average duration
            lines.append(f'grpc_request_duration_seconds{{method="{method}"}} {metrics["average_duration"]}')
            
            # Active connections
            lines.append(f'grpc_active_connections{{method="{method}"}} {metrics["active_connections"]}')
        
        # Connection metrics
        connection_metrics = self.metrics_collector.get_connection_metrics()
        lines.append(f'grpc_total_active_connections {connection_metrics["total_active_connections"]}')
        lines.append(f'grpc_total_connection_errors {connection_metrics["total_connection_errors"]}')
        
        # Average connection duration per endpoint
        for endpoint, avg_duration in connection_metrics["average_connection_duration"].items():
            endpoint_safe = endpoint.replace(':', '_').replace('.', '_')
            lines.append(f'grpc_connection_duration_seconds{{endpoint="{endpoint}"}} {avg_duration}')
        
        # System metrics
        system_metrics = self.metrics_collector.get_system_metrics()
        lines.append(f'grpc_system_cpu_usage_percent {system_metrics["cpu_usage_percent"]}')
        lines.append(f'grpc_system_memory_usage_mb {system_metrics["memory_usage_mb"]}')
        
        # Business metrics
        business_metrics = self.metrics_collector.get_business_metrics()
        lines.append(f'grpc_chat_requests_per_second {business_metrics["chat_requests_per_second"]}')
        lines.append(f'grpc_average_session_duration_seconds {business_metrics["average_session_duration_seconds"]}')
        
        # Agent performance metrics
        for agent_type, performance in business_metrics["agent_performance"].items():
            agent_safe = agent_type.replace('-', '_').replace('.', '_')
            lines.append(f'grpc_agent_duration_seconds{{agent_type="{agent_type}"}} {performance["average_duration"]}')
            lines.append(f'grpc_agent_requests_total{{agent_type="{agent_type}"}} {performance["count"]}')
        
        # Latency histogram
        latency_summary = self.metrics_collector.get_latency_summary()
        if latency_summary:
            lines.append(f'grpc_request_duration_seconds_count {latency_summary["count"]}')
            lines.append(f'grpc_request_duration_seconds_sum {latency_summary["count"] * latency_summary["average"]}')
            
            # Percentiles
            for percentile, value in latency_summary["percentiles"].items():
                lines.append(f'grpc_request_duration_seconds{{quantile="{percentile}"}} {value}')
            
            # Histogram buckets
            for bucket, count in latency_summary["buckets"].items():
                lines.append(f'grpc_request_duration_seconds_bucket{{{bucket}}} {count}')
        
        # Uptime metric
        uptime = time.time() - (self.metrics_collector._collection_thread.start_time if hasattr(self.metrics_collector._collection_thread, 'start_time') else time.time())
        lines.append(f'grpc_uptime_seconds {uptime}')
        
        # Browser metrics (LightPanda)
        if self.browser_metrics_collector:
            try:
                browser_metrics_text = asyncio.run(self.browser_metrics_collector.get_prometheus_metrics())
                lines.append(browser_metrics_text)
            except Exception as exc:
                _logger.warning("browser_metrics_collection_failed", error=str(exc))
        
        return '\n'.join(lines) + '\n'


class PrometheusExporter:
    """Prometheus metrics exporter for gRPC services."""
    
    def __init__(
        self,
        metrics_collector: GrpcMetricsCollector,
        browser_metrics_collector: BrowserMetricsCollector | None = None,
        host: str = '0.0.0.0',
        port: int = 9090
    ):
        self.metrics_collector = metrics_collector
        self.browser_metrics_collector = browser_metrics_collector
        self.host = host
        self.port = port
        self.server: HTTPServer | None = None
        self.server_thread: Thread | None = None
    
    def start(self):
        """Start the Prometheus metrics server."""
        if self.server and self.server_thread:
            _logger.warning("prometheus_exporter_already_running")
            return
        
        try:
            # Create handler with metrics collector
            def handler_factory(*args, **kwargs):
                return PrometheusMetricsHandler(
                    self.metrics_collector,
                    self.browser_metrics_collector,
                    *args,
                    **kwargs
                )
            
            # Create HTTP server
            self.server = HTTPServer((self.host, self.port), handler_factory)
            
            # Start server in background thread
            self.server_thread = Thread(target=self.server.serve_forever, daemon=True)
            self.server_thread.start()
            
            _logger.info(
                "prometheus_exporter_started",
                host=self.host,
                port=self.port,
                url=f"http://{self.host}:{self.port}/metrics"
            )
            
        except Exception as exc:
            _logger.error("prometheus_exporter_start_failed", error=str(exc))
            raise
    
    def stop(self):
        """Stop the Prometheus metrics server."""
        if not self.server:
            _logger.warning("prometheus_exporter_not_running")
            return
        
        try:
            self.server.shutdown()
            self.server.server_close()
            
            if self.server_thread:
                self.server_thread.join(timeout=5)
            
            _logger.info("prometheus_exporter_stopped")
            
        except Exception as exc:
            _logger.error("prometheus_exporter_stop_failed", error=str(exc))
        finally:
            self.server = None
            self.server_thread = None
    
    def is_running(self) -> bool:
        """Check if the exporter is running."""
        return self.server is not None and self.server_thread is not None
    
    def get_metrics_url(self) -> str:
        """Get the metrics endpoint URL."""
        return f"http://{self.host}:{self.port}/metrics"


class GrafanaDashboardConfig:
    """Generate Grafana dashboard configuration for gRPC metrics."""
    
    @staticmethod
    def generate_dashboard_config(datasource_name: str = 'Prometheus') -> dict:
        """Generate Grafana dashboard JSON configuration."""
        dashboard = {
            "dashboard": {
                "id": None,
                "title": "MindFlow gRPC Metrics",
                "tags": ["mindflow", "grpc"],
                "timezone": "browser",
                "panels": [
                    # Request Rate Panel
                    {
                        "id": 1,
                        "title": "gRPC Request Rate",
                        "type": "graph",
                        "targets": [
                            {
                                "expr": 'rate(grpc_requests_total[5m])',
                                "legendFormat": "{{method}}"
                            }
                        ],
                        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0},
                        "yAxes": [
                            {"label": "Requests/sec"}
                        ]
                    },
                    
                    # Request Duration Panel
                    {
                        "id": 2,
                        "title": "gRPC Request Duration",
                        "type": "graph",
                        "targets": [
                            {
                                "expr": 'histogram_quantile(0.50, grpc_request_duration_seconds_bucket)',
                                "legendFormat": "P50"
                            },
                            {
                                "expr": 'histogram_quantile(0.95, grpc_request_duration_seconds_bucket)',
                                "legendFormat": "P95"
                            },
                            {
                                "expr": 'histogram_quantile(0.99, grpc_request_duration_seconds_bucket)',
                                "legendFormat": "P99"
                            }
                        ],
                        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0},
                        "yAxes": [
                            {"label": "Duration (seconds)"}
                        ]
                    },
                    
                    # Error Rate Panel
                    {
                        "id": 3,
                        "title": "gRPC Error Rate",
                        "type": "graph",
                        "targets": [
                            {
                                "expr": 'rate(grpc_errors_total[5m]) / rate(grpc_requests_total[5m])',
                                "legendFormat": "{{method}}"
                            }
                        ],
                        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 8},
                        "yAxes": [
                            {"label": "Error Rate", "max": 1, "min": 0}
                        ]
                    },
                    
                    # Active Connections Panel
                    {
                        "id": 4,
                        "title": "Active gRPC Connections",
                        "type": "graph",
                        "targets": [
                            {
                                "expr": 'grpc_active_connections',
                                "legendFormat": "{{method}}"
                            },
                            {
                                "expr": 'grpc_total_active_connections',
                                "legendFormat": "Total"
                            }
                        ],
                        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 8},
                        "yAxes": [
                            {"label": "Connections"}
                        ]
                    },
                    
                    # System Resources Panel
                    {
                        "id": 5,
                        "title": "System Resources",
                        "type": "graph",
                        "targets": [
                            {
                                "expr": 'grpc_system_cpu_usage_percent',
                                "legendFormat": "CPU %"
                            },
                            {
                                "expr": 'grpc_system_memory_usage_mb',
                                "legendFormat": "Memory MB"
                            }
                        ],
                        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 16},
                        "yAxes": [
                            {"label": "Percentage / MB"}
                        ]
                    },
                    
                    # Business Metrics Panel
                    {
                        "id": 6,
                        "title": "Business Metrics",
                        "type": "graph",
                        "targets": [
                            {
                                "expr": 'grpc_chat_requests_per_second',
                                "legendFormat": "Chat RPS"
                            },
                            {
                                "expr": 'grpc_average_session_duration_seconds',
                                "legendFormat": "Avg Session Duration"
                            }
                        ],
                        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 16},
                        "yAxes": [
                            {"label": "Rate / Duration"}
                        ]
                    }
                ],
                "time": {
                    "from": "now-1h",
                    "to": "now"
                },
                "refresh": "5s"
            },
            "overwrite": True
        }
        
        return dashboard
    
    @staticmethod
    def save_dashboard_config(dashboard_config: dict, filename: str = 'grpc-dashboard.json'):
        """Save dashboard configuration to file."""
        import json
        
        with open(filename, 'w') as f:
            json.dump(dashboard_config, f, indent=2)
        
        _logger.info("grafana_dashboard_saved", filename=filename)
    
    @staticmethod
    def get_alert_rules() -> list[dict]:
        """Get Prometheus alert rules for gRPC metrics."""
        rules = [
            {
                "alert": "GrpcHighErrorRate",
                "expr": 'rate(grpc_errors_total[5m]) / rate(grpc_requests_total[5m]) > 0.1',
                "for": "2m",
                "labels": {
                    "severity": "warning"
                },
                "annotations": {
                    "summary": "gRPC error rate is high",
                    "description": "gRPC error rate is {{ $value | humanizePercentage }} for the last 5 minutes"
                }
            },
            {
                "alert": "GrpcHighLatency",
                "expr": 'histogram_quantile(0.95, grpc_request_duration_seconds_bucket) > 1.0',
                "for": "5m",
                "labels": {
                    "severity": "warning"
                },
                "annotations": {
                    "summary": "gRPC latency is high",
                    "description": "95th percentile latency is {{ $value }}s for the last 5 minutes"
                }
            },
            {
                "alert": "GrpcServiceDown",
                "expr": 'up{job="mindflow-grpc"} == 0',
                "for": "1m",
                "labels": {
                    "severity": "critical"
                },
                "annotations": {
                    "summary": "gRPC service is down",
                    "description": "gRPC service has been down for more than 1 minute"
                }
            },
            {
                "alert": "GrpcHighCpuUsage",
                "expr": 'grpc_system_cpu_usage_percent > 80',
                "for": "5m",
                "labels": {
                    "severity": "warning"
                },
                "annotations": {
                    "summary": "High CPU usage on gRPC service",
                    "description": "CPU usage is {{ $value }}% for the last 5 minutes"
                }
            },
            {
                "alert": "GrpcHighMemoryUsage",
                "expr": 'grpc_system_memory_usage_mb > 1024',
                "for": "5m",
                "labels": {
                    "severity": "warning"
                },
                "annotations": {
                    "summary": "High memory usage on gRPC service",
                    "description": "Memory usage is {{ $value }}MB for the last 5 minutes"
                }
            }
        ]
        
        return rules
