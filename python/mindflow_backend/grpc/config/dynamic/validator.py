"""Configuration validation for dynamic gRPC configuration.

Provides comprehensive validation rules for gRPC configuration
including type checking, range validation, dependency validation,
and security validation for sensitive configurations.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from mindflow_backend.grpc.config import GrpcClientConfig, GrpcConfig
from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


@dataclass
class ValidationError:
    """Individual validation error."""
    field: str
    message: str
    severity: str = "error"  # error, warning, info
    code: str = "VALIDATION_ERROR"


@dataclass
class ValidationResult:
    """Result of configuration validation."""
    is_valid: bool
    errors: list[ValidationError] = field(default_factory=list)
    warnings: list[ValidationError] = field(default_factory=list)
    info: list[ValidationError] = field(default_factory=list)
    
    def add_error(self, field: str, message: str, code: str = "VALIDATION_ERROR"):
        self.errors.append(ValidationError(field, message, "error", code))
        self.is_valid = False
    
    def add_warning(self, field: str, message: str, code: str = "VALIDATION_WARNING"):
        self.warnings.append(ValidationError(field, message, "warning", code))
    
    def add_info(self, field: str, message: str, code: str = "VALIDATION_INFO"):
        self.info.append(ValidationError(field, message, "info", code))
    
    def has_issues(self) -> bool:
        """Check if there are any issues (errors, warnings, or info)."""
        return len(self.errors) > 0 or len(self.warnings) > 0 or len(self.info) > 0


class ConfigValidator:
    """Comprehensive configuration validator for gRPC settings."""
    
    def __init__(self):
        self.validation_rules = self._setup_validation_rules()
    
    async def validate_config(self, config: GrpcConfig) -> ValidationResult:
        """Validate complete gRPC configuration."""
        result = ValidationResult(is_valid=True)
        
        # Server configuration validation
        await self._validate_server_config(config, result)
        
        # Security configuration validation
        await self._validate_security_config(config, result)
        
        # Connection configuration validation
        await self._validate_connection_config(config, result)
        
        # Performance configuration validation
        await self._validate_performance_config(config, result)
        
        # Monitoring configuration validation
        await self._validate_monitoring_config(config, result)
        
        # Feature dependency validation
        await self._validate_feature_dependencies(config, result)
        
        return result
    
    async def validate_partial_update(self, updates: dict[str, Any]) -> ValidationResult:
        """Validate partial configuration updates."""
        result = ValidationResult(is_valid=True)
        
        # Create temporary config with updates
        try:
            # This would need the current config to merge with
            # For now, validate individual fields
            for field, value in updates.items():
                await self._validate_field(field, value, result)
        except Exception as exc:
            result.add_error("general", f"Validation failed: {str(exc)}", "VALIDATION_EXCEPTION")
        
        return result
    
    async def _validate_field(self, field: str, value: Any, result: ValidationResult):
        """Validate individual configuration field."""
        if field == "port":
            await self._validate_port(value, result)
        elif field == "host":
            await self._validate_host(value, result)
        elif field.startswith("tls_"):
            await self._validate_tls_field(field, value, result)
        elif field.endswith("_timeout_seconds"):
            await self._validate_timeout(field, value, result)
        elif field.endswith("_connections"):
            await self._validate_connections(field, value, result)
        elif field.startswith("max_") and field.endswith("_length"):
            await self._validate_message_size(field, value, result)
    
    async def _validate_server_config(self, config: GrpcConfig, result: ValidationResult):
        """Validate server-specific configuration."""
        # Port validation
        await self._validate_port(config.port, result)
        
        # Host validation
        await self._validate_host(config.host, result)
        
        # Enabled status
        if not isinstance(config.enabled, bool):
            result.add_error("enabled", "enabled must be a boolean", "INVALID_TYPE")
        
        # Auto-start validation
        if not isinstance(config.auto_start, bool):
            result.add_error("auto_start", "auto_start must be a boolean", "INVALID_TYPE")
    
    async def _validate_security_config(self, config: GrpcConfig, result: ValidationResult):
        """Validate security-related configuration."""
        # TLS configuration
        if config.secure:
            await self._validate_tls_config(config, result)
        
        # Debug mode validation
        if config.debug_mode and config.secure:
            result.add_warning("debug_mode", "Debug mode enabled with TLS - consider security implications", "SECURITY_WARNING")
        
        # Reflection validation
        if config.reflection_enabled and config.secure:
            result.add_warning("reflection_enabled", "gRPC reflection enabled with TLS - potential security risk", "SECURITY_WARNING")
    
    async def _validate_connection_config(self, config: GrpcConfig, result: ValidationResult):
        """Validate connection-related configuration."""
        # Connection timeout
        await self._validate_timeout("connection_timeout_seconds", config.connection_timeout_seconds, result)
        
        # Keepalive settings
        await self._validate_keepalive(config, result)
        
        # Retry configuration
        await self._validate_retry_config(config, result)
    
    async def _validate_performance_config(self, config: GrpcConfig, result: ValidationResult):
        """Validate performance-related configuration."""
        # Message size limits
        await self._validate_message_size("max_receive_message_length", config.max_receive_message_length, result)
        await self._validate_message_size("max_send_message_length", config.max_send_message_length, result)
        
        # Connection limits
        await self._validate_connections("max_connections", config.max_connections, result)
        
        # Default timeout
        await self._validate_timeout("default_timeout_seconds", config.default_timeout_seconds, result)
    
    async def _validate_monitoring_config(self, config: GrpcConfig, result: ValidationResult):
        """Validate monitoring-related configuration."""
        # Health check interval
        if config.health_check_interval_seconds <= 0:
            result.add_error("health_check_interval_seconds", "Health check interval must be positive", "INVALID_RANGE")
        
        if config.health_check_interval_seconds > 300:
            result.add_warning("health_check_interval_seconds", "Health check interval > 5 minutes may miss issues", "PERFORMANCE_WARNING")
        
        # Metrics and health check validation
        if config.enable_metrics and config.enable_health_check:
            result.add_info("monitoring", "Both metrics and health check enabled - comprehensive monitoring", "MONITORING_INFO")
    
    async def _validate_feature_dependencies(self, config: GrpcConfig, result: ValidationResult):
        """Validate feature dependencies and conflicts."""
        # Metrics dependency on health check (optional)
        if config.enable_metrics and not config.enable_health_check:
            result.add_info("metrics", "Metrics enabled without health check - consider enabling health check", "FEATURE_DEPENDENCY")
        
        # Security features
        if config.secure and config.debug_mode:
            result.add_warning("security", "Secure mode with debug enabled - review security settings", "SECURITY_CONFLICT")
        
        # Performance implications
        if config.max_connections > 1000:
            result.add_warning("max_connections", "High connection limit may impact performance", "PERFORMANCE_WARNING")
    
    async def _validate_port(self, port: int, result: ValidationResult):
        """Validate port number."""
        if not isinstance(port, int):
            result.add_error("port", "Port must be an integer", "INVALID_TYPE")
            return
        
        if not (1 <= port <= 65535):
            result.add_error("port", f"Port {port} must be between 1 and 65535", "INVALID_RANGE")
        
        # Warn about privileged ports
        if port < 1024:
            result.add_warning("port", f"Port {port} is privileged - ensure proper permissions", "PRIVILEGED_PORT")
        
        # Warn about common port conflicts
        common_ports = {80, 443, 8080, 8443, 3000, 5000, 8000, 9000}
        if port in common_ports:
            result.add_warning("port", f"Port {port} commonly used by other services", "PORT_CONFLICT")
    
    async def _validate_host(self, host: str, result: ValidationResult):
        """Validate host address."""
        if not isinstance(host, str):
            result.add_error("host", "Host must be a string", "INVALID_TYPE")
            return
        
        if not host.strip():
            result.add_error("host", "Host cannot be empty", "INVALID_VALUE")
            return
        
        # Check for valid host patterns
        valid_patterns = ["0.0.0.0", "127.0.0.1", "localhost"]
        if host not in valid_patterns and not self._is_valid_ip_or_hostname(host):
            result.add_warning("host", f"Host '{host}' may not be valid - verify network configuration", "HOST_VALIDATION")
    
    async def _validate_tls_config(self, config: GrpcConfig, result: ValidationResult):
        """Validate TLS configuration."""
        if not config.tls_cert_path:
            result.add_error("tls_cert_path", "TLS certificate path required when secure=True", "MISSING_REQUIRED")
            return
        
        if not config.tls_key_path:
            result.add_error("tls_key_path", "TLS private key path required when secure=True", "MISSING_REQUIRED")
            return
        
        # Check file existence
        cert_path = Path(config.tls_cert_path)
        key_path = Path(config.tls_key_path)
        
        if not cert_path.exists():
            result.add_error("tls_cert_path", f"TLS certificate not found: {config.tls_cert_path}", "FILE_NOT_FOUND")
        
        if not key_path.exists():
            result.add_error("tls_key_path", f"TLS private key not found: {config.tls_key_path}", "FILE_NOT_FOUND")
        
        # Check file permissions
        if cert_path.exists():
            if not os.access(cert_path, os.R_OK):
                result.add_error("tls_cert_path", f"TLS certificate not readable: {config.tls_cert_path}", "FILE_PERMISSION")
        
        if key_path.exists():
            if not os.access(key_path, os.R_OK):
                result.add_error("tls_key_path", f"TLS private key not readable: {config.tls_key_path}", "FILE_PERMISSION")
            # Warn about private key permissions
            if os.stat(key_path).st_mode & 0o077:  # Check if others can read
                result.add_warning("tls_key_path", f"Private key may be readable by others: {config.tls_key_path}", "SECURITY_WARNING")
        
        # CA certificate validation (optional)
        if config.tls_ca_path:
            ca_path = Path(config.tls_ca_path)
            if not ca_path.exists():
                result.add_error("tls_ca_path", f"TLS CA certificate not found: {config.tls_ca_path}", "FILE_NOT_FOUND")
    
    async def _validate_timeout(self, field: str, timeout: int, result: ValidationResult):
        """Validate timeout configuration."""
        if not isinstance(timeout, int):
            result.add_error(field, f"{field} must be an integer", "INVALID_TYPE")
            return
        
        if timeout <= 0:
            result.add_error(field, f"{field} must be positive", "INVALID_RANGE")
        
        if timeout > 3600:  # 1 hour
            result.add_warning(field, f"{field} > 1 hour may indicate configuration issue", "TIMEOUT_WARNING")
        
        # Specific timeout validations
        if "connection" in field and timeout > 300:
            result.add_warning(field, "Connection timeout > 5 minutes may cause issues", "TIMEOUT_WARNING")
        
        if "default" in field and timeout < 30:
            result.add_warning(field, "Default timeout < 30 seconds may cause premature failures", "TIMEOUT_WARNING")
    
    async def _validate_connections(self, field: str, connections: int, result: ValidationResult):
        """Validate connection limits."""
        if not isinstance(connections, int):
            result.add_error(field, f"{field} must be an integer", "INVALID_TYPE")
            return
        
        if connections <= 0:
            result.add_error(field, f"{field} must be positive", "INVALID_RANGE")
        
        if connections > 10000:
            result.add_warning(field, f"{field} > 10000 may cause resource exhaustion", "RESOURCE_WARNING")
        
        # Specific connection validations
        if "max" in field and connections < 10:
            result.add_warning(field, "Max connections < 10 may limit scalability", "SCALABILITY_WARNING")
    
    async def _validate_message_size(self, field: str, size: int, result: ValidationResult):
        """Validate message size limits."""
        if not isinstance(size, int):
            result.add_error(field, f"{field} must be an integer", "INVALID_TYPE")
            return
        
        if size <= 0:
            result.add_error(field, f"{field} must be positive", "INVALID_RANGE")
        
        if size > 100 * 1024 * 1024:  # 100MB
            result.add_warning(field, f"{field} > 100MB may cause memory issues", "MEMORY_WARNING")
        
        # Check for reasonable defaults
        if size < 1024:  # 1KB
            result.add_warning(field, f"{field} < 1KB may be too small for most use cases", "SIZE_WARNING")
    
    async def _validate_keepalive(self, config: GrpcConfig, result: ValidationResult):
        """Validate keepalive configuration."""
        if config.keepalive_time_seconds <= 0:
            result.add_error("keepalive_time_seconds", "Keepalive time must be positive", "INVALID_RANGE")
        
        if config.keepalive_timeout_seconds <= 0:
            result.add_error("keepalive_timeout_seconds", "Keepalive timeout must be positive", "INVALID_RANGE")
        
        if config.keepalive_timeout_seconds >= config.keepalive_time_seconds:
            result.add_warning("keepalive", "Keepalive timeout >= keepalive time may cause issues", "KEEPALIVE_WARNING")
        
        # Reasonable keepalive intervals
        if config.keepalive_time_seconds > 300:  # 5 minutes
            result.add_warning("keepalive_time_seconds", "Keepalive time > 5 minutes may not detect connection issues", "KEEPALIVE_WARNING")
    
    async def _validate_retry_config(self, config: GrpcConfig, result: ValidationResult):
        """Validate retry configuration."""
        if config.max_attempts <= 0:
            result.add_error("max_attempts", "Max attempts must be positive", "INVALID_RANGE")
        
        if config.max_attempts > 10:
            result.add_warning("max_attempts", "Max attempts > 10 may cause excessive retries", "RETRY_WARNING")
        
        if config.retry_backoff_multiplier <= 1.0:
            result.add_warning("retry_backoff_multiplier", "Backoff multiplier <= 1.0 may not provide exponential backoff", "RETRY_WARNING")
        
        if config.initial_retry_delay_ms <= 0:
            result.add_error("initial_retry_delay_ms", "Initial retry delay must be positive", "INVALID_RANGE")
        
        if config.max_retry_delay_ms <= config.initial_retry_delay_ms:
            result.add_warning("retry", "Max retry delay <= initial delay may not provide effective backoff", "RETRY_WARNING")
    
    def _is_valid_ip_or_hostname(self, host: str) -> bool:
        """Check if host is a valid IP address or hostname."""
        import ipaddress
        import re
        
        # Check if it's a valid IP address
        try:
            ipaddress.ip_address(host)
            return True
        except ValueError:
            pass
        
        # Check if it's a valid hostname
        hostname_pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$'
        return bool(re.match(hostname_pattern, host))
    
    def _setup_validation_rules(self) -> dict[str, Any]:
        """Setup validation rules and constraints."""
        return {
            "port": {"min": 1, "max": 65535, "type": int},
            "timeout": {"min": 1, "max": 3600, "type": int},
            "connections": {"min": 1, "max": 10000, "type": int},
            "message_size": {"min": 1024, "max": 100 * 1024 * 1024, "type": int},
            "keepalive_time": {"min": 1, "max": 300, "type": int},
            "keepalive_timeout": {"min": 1, "max": 60, "type": int},
            "max_attempts": {"min": 1, "max": 10, "type": int},
            "retry_multiplier": {"min": 1.1, "max": 10.0, "type": float},
        }


class ClientConfigValidator:
    """Validator for gRPC client configuration."""
    
    def __init__(self):
        self.validator = ConfigValidator()
    
    async def validate_client_config(self, config: GrpcClientConfig) -> ValidationResult:
        """Validate gRPC client configuration."""
        result = ValidationResult(is_valid=True)
        
        # Host and port validation
        await self.validator._validate_host(config.host, result)
        await self.validator._validate_port(config.port, result)
        
        # Pool configuration
        await self._validate_pool_config(config, result)
        
        # Load balancing validation
        await self._validate_load_balancing(config, result)
        
        # Compression validation
        await self._validate_compression(config, result)
        
        return result
    
    async def _validate_pool_config(self, config: GrpcClientConfig, result: ValidationResult):
        """Validate connection pool configuration."""
        if config.pool_size <= 0:
            result.add_error("pool_size", "Pool size must be positive", "INVALID_RANGE")
        
        if config.max_pool_size < config.pool_size:
            result.add_error("max_pool_size", "Max pool size must be >= pool size", "INVALID_RANGE")
        
        if config.max_pool_size > 1000:
            result.add_warning("max_pool_size", "Max pool size > 1000 may cause resource issues", "RESOURCE_WARNING")
        
        if config.pool_timeout_seconds <= 0:
            result.add_error("pool_timeout_seconds", "Pool timeout must be positive", "INVALID_RANGE")
    
    async def _validate_load_balancing(self, config: GrpcClientConfig, result: ValidationResult):
        """Validate load balancing configuration."""
        valid_policies = ["round_robin", "pick_first", "random"]
        if config.load_balancing_policy not in valid_policies:
            result.add_error("load_balancing_policy", f"Must be one of: {valid_policies}", "INVALID_VALUE")
    
    async def _validate_compression(self, config: GrpcClientConfig, result: ValidationResult):
        """Validate compression configuration."""
        valid_algorithms = ["none", "gzip", "deflate"]
        if config.compression_algorithm not in valid_algorithms:
            result.add_error("compression_algorithm", f"Must be one of: {valid_algorithms}", "INVALID_VALUE")
        
        if config.compression_algorithm != "none":
            result.add_info("compression", f"Compression enabled: {config.compression_algorithm}", "COMPRESSION_INFO")
