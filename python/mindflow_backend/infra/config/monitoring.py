"""Monitoring configuration settings.

Provides comprehensive monitoring configuration with metrics,
health checks, alerting, and observability settings.
"""

from __future__ import annotations

from typing import Optional, Dict, Any, List
from pydantic import field_validator,  Field, validator
from pydantic_settings import BaseSettings


class MonitoringConfig(BaseSettings):
    """Monitoring configuration with comprehensive settings.
    
    Features:
    - Metrics collection configuration
    - Health check settings
    - Alerting configuration
    - Distributed tracing
    - Performance monitoring
    """
    
    # General Monitoring Configuration
    enabled: bool = Field(default=True, description="Enable monitoring")
    debug_mode: bool = Field(default=False, description="Enable debug monitoring")
    metrics_port: int = Field(default=9090, description="Metrics server port")
    
    # Metrics Configuration
    enable_metrics: bool = Field(default=True, description="Enable metrics collection")
    metrics_interval: int = Field(default=60, description="Metrics collection interval in seconds")
    metrics_retention_hours: int = Field(default=24, description="Metrics retention period in hours")
    metrics_buffer_size: int = Field(default=1000, description="Metrics buffer size")
    
    # Prometheus Configuration
    prometheus_enabled: bool = Field(default=True, description="Enable Prometheus metrics")
    prometheus_port: int = Field(default=9090, description="Prometheus metrics port")
    prometheus_path: str = Field(default="/metrics", description="Prometheus metrics path")
    prometheus_registry: str = Field(default="default", description="Prometheus registry name")
    
    # Health Check Configuration
    health_check_enabled: bool = Field(default=True, description="Enable health checks")
    health_check_interval: int = Field(default=30, description="Health check interval in seconds")
    health_check_timeout: int = Field(default=5, description="Health check timeout in seconds")
    health_check_path: str = Field(default="/health", description="Health check endpoint path")
    
    # Component Health Checks
    check_database: bool = Field(default=True, description="Check database health")
    check_cache: bool = Field(default=True, description="Check cache health")
    check_external_apis: bool = Field(default=True, description="Check external API health")
    check_disk_space: bool = Field(default=True, description="Check disk space")
    check_memory_usage: bool = Field(default=True, description="Check memory usage")
    
    # Alerting Configuration
    alerting_enabled: bool = Field(default=True, description="Enable alerting")
    alert_webhook_url: Optional[str] = Field(default=None, description="Alert webhook URL")
    alert_email_recipients: List[str] = Field(default_factory=list, description="Alert email recipients")
    alert_slack_webhook: Optional[str] = Field(default=None, description="Slack webhook URL")
    alert_discord_webhook: Optional[str] = Field(default=None, description="Discord webhook URL")
    
    # Alert Thresholds
    alert_cpu_threshold: float = Field(default=80.0, description="CPU usage alert threshold (%)")
    alert_memory_threshold: float = Field(default=80.0, description="Memory usage alert threshold (%)")
    alert_disk_threshold: float = Field(default=80.0, description="Disk usage alert threshold (%)")
    alert_error_rate_threshold: float = Field(default=5.0, description="Error rate alert threshold (%)")
    alert_response_time_threshold: float = Field(default=1000.0, description="Response time alert threshold (ms)")
    
    # Distributed Tracing Configuration
    tracing_enabled: bool = Field(default=True, description="Enable distributed tracing")
    tracing_sample_rate: float = Field(default=1.0, description="Tracing sample rate (0.0-1.0)")
    tracing_service_name: str = Field(default="mindflow-backend", description="Tracing service name")
    tracing_endpoint: Optional[str] = Field(default=None, description="Tracing collector endpoint")
    
    # OpenTelemetry Configuration
    otel_enabled: bool = Field(default=False, description="Enable OpenTelemetry")
    otel_exporter: str = Field(default="otlp", description="OpenTelemetry exporter type")
    otel_endpoint: Optional[str] = Field(default=None, description="OpenTelemetry endpoint")
    otel_headers: Optional[str] = Field(default=None, description="OpenTelemetry headers")
    
    # Performance Monitoring Configuration
    performance_monitoring_enabled: bool = Field(default=True, description="Enable performance monitoring")
    slow_query_threshold_ms: float = Field(default=1000.0, description="Slow query threshold in milliseconds")
    slow_request_threshold_ms: float = Field(default=500.0, description="Slow request threshold in milliseconds")
    enable_profiling: bool = Field(default=False, description="Enable performance profiling")
    
    # Resource Monitoring Configuration
    resource_monitoring_enabled: bool = Field(default=True, description="Enable resource monitoring")
    resource_interval: int = Field(default=30, description="Resource monitoring interval in seconds")
    cpu_monitoring_enabled: bool = Field(default=True, description="Enable CPU monitoring")
    memory_monitoring_enabled: bool = Field(default=True, description="Enable memory monitoring")
    disk_monitoring_enabled: bool = Field(default=True, description="Enable disk monitoring")
    network_monitoring_enabled: bool = Field(default=True, description="Enable network monitoring")
    
    # Application Metrics Configuration
    app_metrics_enabled: bool = Field(default=True, description="Enable application metrics")
    request_metrics_enabled: bool = Field(default=True, description="Enable request metrics")
    error_metrics_enabled: bool = Field(default=True, description="Enable error metrics")
    business_metrics_enabled: bool = Field(default=True, description="Enable business metrics")
    
    # Dashboard Configuration
    dashboard_enabled: bool = Field(default=True, description="Enable dashboard")
    dashboard_refresh_interval: int = Field(default=30, description="Dashboard refresh interval in seconds")
    dashboard_url: Optional[str] = Field(default=None, description="Dashboard URL")
    
    # Logging Configuration for Monitoring
    enable_monitoring_logs: bool = Field(default=True, description="Enable monitoring logs")
    monitoring_log_level: str = Field(default="INFO", description="Monitoring log level")
    log_metrics: bool = Field(default=False, description="Log metrics to file")
    
    # Anomaly Detection Configuration
    anomaly_detection_enabled: bool = Field(default=False, description="Enable anomaly detection")
    anomaly_detection_window: int = Field(default=300, description="Anomaly detection window in seconds")
    anomaly_threshold: float = Field(default=2.0, description="Anomaly detection threshold (standard deviations)")
    
    # Custom Metrics Configuration
    custom_metrics_enabled: bool = Field(default=True, description="Enable custom metrics")
    custom_metrics_prefix: str = Field(default="mindflow_", description="Custom metrics prefix")
    
    # Export Configuration
    export_enabled: bool = Field(default=False, description="Enable metrics export")
    export_format: str = Field(default="json", description="Export format (json, csv, prometheus)")
    export_interval: int = Field(default=3600, description="Export interval in seconds")
    export_path: Optional[str] = Field(default=None, description="Export file path")

    @field_validator("tracing_sample_rate")
    def validate_tracing_sample_rate(cls, v: float) -> float:
        """Validate tracing sample rate."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("Tracing sample rate must be between 0.0 and 1.0")
        return v

    @field_validator("otel_exporter")
    def validate_otel_exporter(cls, v: str) -> str:
        """Validate OpenTelemetry exporter type."""
        valid_exporters = ["otlp", "jaeger", "zipkin", "prometheus"]
        if v not in valid_exporters:
            raise ValueError(f"OpenTelemetry exporter must be one of: {valid_exporters}")
        return v

    @field_validator("export_format")
    def validate_export_format(cls, v: str) -> str:
        """Validate export format."""
        valid_formats = ["json", "csv", "prometheus", "influx"]
        if v not in valid_formats:
            raise ValueError(f"Export format must be one of: {valid_formats}")
        return v

    @field_validator("monitoring_log_level")
    def validate_monitoring_log_level(cls, v: str) -> str:
        """Validate monitoring log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v not in valid_levels:
            raise ValueError(f"Monitoring log level must be one of: {valid_levels}")
        return v

    @field_validator("alert_cpu_threshold", "alert_memory_threshold", "alert_disk_threshold")
    def validate_percentage_thresholds(cls, v: float) -> float:
        """Validate percentage thresholds."""
        if not 0.0 <= v <= 100.0:
            raise ValueError("Percentage thresholds must be between 0.0 and 100.0")
        return v

    @field_validator("slow_query_threshold_ms", "slow_request_threshold_ms", "alert_response_time_threshold")
    def validate_time_thresholds(cls, v: float) -> float:
        """Validate time thresholds."""
        if v <= 0:
            raise ValueError("Time thresholds must be positive")
        return v

    @field_validator("anomaly_threshold")
    def validate_anomaly_threshold(cls, v: float) -> float:
        """Validate anomaly detection threshold."""
        if v <= 0:
            raise ValueError("Anomaly threshold must be positive")
        return v

    def get_metrics_config(self) -> Dict[str, Any]:
        """Get metrics configuration.
        
        Returns:
            Dictionary with metrics configuration.
        """
        return {
            "enabled": self.enable_metrics,
            "interval": self.metrics_interval,
            "retention_hours": self.metrics_retention_hours,
            "buffer_size": self.metrics_buffer_size,
            "prometheus": {
                "enabled": self.prometheus_enabled,
                "port": self.prometheus_port,
                "path": self.prometheus_path,
                "registry": self.prometheus_registry,
            },
        }

    def get_health_check_config(self) -> Dict[str, Any]:
        """Get health check configuration.
        
        Returns:
            Dictionary with health check configuration.
        """
        return {
            "enabled": self.health_check_enabled,
            "interval": self.health_check_interval,
            "timeout": self.health_check_timeout,
            "path": self.health_check_path,
            "components": {
                "database": self.check_database,
                "cache": self.check_cache,
                "external_apis": self.check_external_apis,
                "disk_space": self.check_disk_space,
                "memory_usage": self.check_memory_usage,
            },
        }

    def get_alerting_config(self) -> Dict[str, Any]:
        """Get alerting configuration.
        
        Returns:
            Dictionary with alerting configuration.
        """
        return {
            "enabled": self.alerting_enabled,
            "webhook_url": self.alert_webhook_url,
            "email_recipients": self.alert_email_recipients,
            "slack_webhook": self.alert_slack_webhook,
            "discord_webhook": self.alert_discord_webhook,
            "thresholds": {
                "cpu": self.alert_cpu_threshold,
                "memory": self.alert_memory_threshold,
                "disk": self.alert_disk_threshold,
                "error_rate": self.alert_error_rate_threshold,
                "response_time": self.alert_response_time_threshold,
            },
        }

    def get_tracing_config(self) -> Dict[str, Any]:
        """Get tracing configuration.
        
        Returns:
            Dictionary with tracing configuration.
        """
        return {
            "enabled": self.tracing_enabled,
            "sample_rate": self.tracing_sample_rate,
            "service_name": self.tracing_service_name,
            "endpoint": self.tracing_endpoint,
            "otel": {
                "enabled": self.otel_enabled,
                "exporter": self.otel_exporter,
                "endpoint": self.otel_endpoint,
                "headers": self.otel_headers,
            },
        }

    def get_performance_config(self) -> Dict[str, Any]:
        """Get performance monitoring configuration.
        
        Returns:
            Dictionary with performance configuration.
        """
        return {
            "enabled": self.performance_monitoring_enabled,
            "slow_query_threshold_ms": self.slow_query_threshold_ms,
            "slow_request_threshold_ms": self.slow_request_threshold_ms,
            "enable_profiling": self.enable_profiling,
        }

    def get_resource_config(self) -> Dict[str, Any]:
        """Get resource monitoring configuration.
        
        Returns:
            Dictionary with resource monitoring configuration.
        """
        return {
            "enabled": self.resource_monitoring_enabled,
            "interval": self.resource_interval,
            "components": {
                "cpu": self.cpu_monitoring_enabled,
                "memory": self.memory_monitoring_enabled,
                "disk": self.disk_monitoring_enabled,
                "network": self.network_monitoring_enabled,
            },
        }

    def get_app_metrics_config(self) -> Dict[str, Any]:
        """Get application metrics configuration.
        
        Returns:
            Dictionary with application metrics configuration.
        """
        return {
            "enabled": self.app_metrics_enabled,
            "request_metrics": self.request_metrics_enabled,
            "error_metrics": self.error_metrics_enabled,
            "business_metrics": self.business_metrics_enabled,
            "custom_metrics": {
                "enabled": self.custom_metrics_enabled,
                "prefix": self.custom_metrics_prefix,
            },
        }

    def get_anomaly_detection_config(self) -> Dict[str, Any]:
        """Get anomaly detection configuration.
        
        Returns:
            Dictionary with anomaly detection configuration.
        """
        return {
            "enabled": self.anomaly_detection_enabled,
            "window": self.anomaly_detection_window,
            "threshold": self.anomaly_threshold,
        }

    def get_export_config(self) -> Dict[str, Any]:
        """Get export configuration.
        
        Returns:
            Dictionary with export configuration.
        """
        return {
            "enabled": self.export_enabled,
            "format": self.export_format,
            "interval": self.export_interval,
            "path": self.export_path,
        }
