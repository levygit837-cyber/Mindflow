"""Infrastructure error handler interface.

Defines contracts for handling infrastructure component failures,
system resource issues, and operational problems.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable, Any, Dict, Optional, List, Union
from abc import abstractmethod

from mindflow_backend.schemas.errors import (
    InfrastructureErrorSchema,
    CircuitOpenErrorSchema,
    ConfigurationErrorSchema,
    MonitoringErrorSchema,
    MiddlewareErrorSchema,
    ResourceErrorSchema,
    ErrorCategory,
    ErrorSeverity,
)

from .base_error_handler import BaseErrorHandlerContract


@runtime_checkable
class InfrastructureErrorHandlerContract(BaseErrorHandlerContract, Protocol):
    """Contract for infrastructure error handling.
    
    Specialized interface for handling infrastructure component failures,
    system resource issues, configuration problems, and operational errors.
    """

    @abstractmethod
    async def handle_infrastructure_error(
        self,
        exception: Exception,
        *,
        service: Optional[str] = None,
        operation: Optional[str] = None,
        endpoint: Optional[str] = None,
        health_check: Optional[bool] = None,
        **context: Any,
    ) -> InfrastructureErrorSchema:
        """Handle infrastructure component failures.
        
        Args:
            exception: The infrastructure exception
            service: Infrastructure service name
            operation: Operation being performed
            endpoint: Service endpoint
            health_check: Service health status
            **context: Additional context
            
        Returns:
            Infrastructure error schema with service context
        """
        ...

    @abstractmethod
    async def handle_circuit_open_error(
        self,
        exception: Exception,
        *,
        service_name: Optional[str] = None,
        failure_threshold: Optional[int] = None,
        recovery_timeout: Optional[float] = None,
        current_state: Optional[str] = None,
        failure_count: Optional[int] = None,
        **context: Any,
    ) -> CircuitOpenErrorSchema:
        """Handle circuit breaker open errors.
        
        Args:
            exception: The circuit breaker exception
            service_name: Name of the protected service
            failure_threshold: Failure threshold that was exceeded
            recovery_timeout: Recovery timeout period
            current_state: Current circuit breaker state
            failure_count: Current failure count
            **context: Additional context
            
        Returns:
            Circuit open error schema with circuit context
        """
        ...

    @abstractmethod
    async def handle_configuration_error(
        self,
        exception: Exception,
        *,
        config_key: Optional[str] = None,
        expected_type: Optional[str] = None,
        actual_value: Optional[Any] = None,
        config_file: Optional[str] = None,
        config_section: Optional[str] = None,
        **context: Any,
    ) -> ConfigurationErrorSchema:
        """Handle configuration errors.
        
        Args:
            exception: The configuration exception
            config_key: Configuration key that caused error
            expected_type: Expected configuration type
            actual_value: Actual configuration value
            config_file: Configuration file path
            config_section: Configuration section
            **context: Additional context
            
        Returns:
            Configuration error schema with config context
        """
        ...

    @abstractmethod
    async def handle_monitoring_error(
        self,
        exception: Exception,
        *,
        monitoring_system: Optional[str] = None,
        metric_name: Optional[str] = None,
        monitoring_operation: Optional[str] = None,
        alert_threshold: Optional[float] = None,
        current_value: Optional[float] = None,
        **context: Any,
    ) -> MonitoringErrorSchema:
        """Handle monitoring system errors.
        
        Args:
            exception: The monitoring exception
            monitoring_system: Name of monitoring system
            metric_name: Metric being monitored
            monitoring_operation: Monitoring operation that failed
            alert_threshold: Alert threshold
            current_value: Current metric value
            **context: Additional context
            
        Returns:
            Monitoring error schema with monitoring context
        """
        ...

    @abstractmethod
    async def handle_middleware_error(
        self,
        exception: Exception,
        *,
        middleware_name: Optional[str] = None,
        middleware_type: Optional[str] = None,
        request_path: Optional[str] = None,
        processing_stage: Optional[str] = None,
        **context: Any,
    ) -> MiddlewareErrorSchema:
        """Handle middleware processing errors.
        
        Args:
            exception: The middleware exception
            middleware_name: Name of the middleware
            middleware_type: Type of middleware (auth, logging, etc.)
            request_path: Request path being processed
            processing_stage: Stage of processing that failed
            **context: Additional context
            
        Returns:
            Middleware error schema with middleware context
        """
        ...

    @abstractmethod
    async def handle_resource_error(
        self,
        exception: Exception,
        *,
        resource_type: Optional[str] = None,
        current_usage: Optional[str] = None,
        resource_limit: Optional[str] = None,
        allocation_failure: Optional[bool] = None,
        resource_id: Optional[str] = None,
        **context: Any,
    ) -> ResourceErrorSchema:
        """Handle resource exhaustion errors.
        
        Args:
            exception: The resource exception
            resource_type: Type of resource (CPU, memory, disk, etc.)
            current_usage: Current resource usage
            resource_limit: Resource limit
            allocation_failure: Whether resource allocation failed
            resource_id: Resource identifier
            **context: Additional context
            
        Returns:
            Resource error schema with resource context
        """
        ...

    @abstractmethod
    def get_system_health_status(
        self,
        component: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get system health status for infrastructure components.
        
        Args:
            component: Specific component to check
            
        Returns:
            System health status information
        """
        ...

    @abstractmethod
    def get_resource_utilization(
        self,
        resource_type: str,
        time_window: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get resource utilization metrics.
        
        Args:
            resource_type: Type of resource (cpu, memory, disk, network)
            time_window: Time window for metrics (1m, 5m, 15m, 1h, etc.)
            
        Returns:
            Resource utilization information
        """
        ...

    @abstractmethod
    def check_circuit_breaker_status(
        self,
        service_name: str,
    ) -> Dict[str, Any]:
        """Check circuit breaker status for a service.
        
        Args:
            service_name: Name of the protected service
            
        Returns:
            Circuit breaker status information
        """
        ...

    @abstractmethod
    def validate_configuration(
        self,
        config_file: Optional[str] = None,
        config_section: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Validate system configuration.
        
        Args:
            config_file: Configuration file to validate
            config_section: Specific configuration section
            
        Returns:
            Configuration validation results
        """
        ...

    @abstractmethod
    async def restart_component(
        self,
        component_name: str,
        *,
        force: bool = False,
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Attempt to restart an infrastructure component.
        
        Args:
            component_name: Name of component to restart
            force: Force restart even if running
            timeout: Restart operation timeout
            
        Returns:
            Restart operation results
        """
        ...

    @abstractmethod
    def get_component_dependencies(
        self,
        component_name: str,
    ) -> List[str]:
        """Get list of component dependencies.
        
        Args:
            component_name: Name of the component
            
        Returns:
            List of dependent components
        """
        ...

    # Infrastructure-specific convenience methods
    
    def get_infrastructure_dashboard(
        self,
        components: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Get infrastructure dashboard information.
        
        Args:
            components: List of components to include (None for all)
            
        Returns:
            Infrastructure dashboard data
        """
        # Default implementation - subclasses should override
        return {
            "timestamp": None,
            "components": {},
            "overall_status": "unknown",
            "total_components": 0,
            "healthy_components": 0,
            "degraded_components": 0,
            "unhealthy_components": 0,
            "resource_utilization": {
                "cpu": 0.0,
                "memory": 0.0,
                "disk": 0.0,
                "network": 0.0,
            },
        }

    def analyze_performance_trends(
        self,
        component: str,
        metric_type: str,
        time_range: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Analyze performance trends for a component.
        
        Args:
            component: Component name to analyze
            metric_type: Type of metric to analyze
            time_range: Time range for analysis (1h, 24h, 7d, etc.)
            
        Returns:
            Performance trend analysis
        """
        # Default implementation - subclasses should override
        return {
            "component": component,
            "metric_type": metric_type,
            "time_range": time_range,
            "trend": "stable",
            "average": 0.0,
            "peak": 0.0,
            "minimum": 0.0,
            "anomalies": [],
            "recommendations": [],
        }

    def create_capacity_report(
        self,
        resource_types: Optional[List[str]] = None,
        forecast_days: int = 7,
    ) -> Dict[str, Any]:
        """Create capacity planning report.
        
        Args:
            resource_types: Types of resources to include
            forecast_days: Number of days to forecast
            
        Returns:
            Capacity planning report
        """
        # Default implementation - subclasses should override
        return {
            "report_timestamp": None,
            "forecast_days": forecast_days,
            "resources": {},
            "recommendations": [],
            "risk_assessment": {
                "overall_risk": "low",
                "resource_risks": {},
            },
        }

    def get_alert_configuration(
        self,
        component: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get alert configuration for components.
        
        Args:
            component: Specific component to get alerts for
            
        Returns:
            Alert configuration
        """
        # Default implementation - subclasses should override
        return {
            "component": component,
            "alerts": {
                "cpu_threshold": 80.0,
                "memory_threshold": 85.0,
                "disk_threshold": 90.0,
                "error_rate_threshold": 5.0,
            },
            "notification_channels": ["email", "slack"],
            "escalation_rules": [],
        }

    def test_component_connectivity(
        self,
        component_name: str,
        *,
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Test connectivity to an infrastructure component.
        
        Args:
            component_name: Name of component to test
            timeout: Test timeout
            
        Returns:
            Connectivity test results
        """
        # Default implementation - subclasses should override
        return {
            "component": component_name,
            "connectivity": "unknown",
            "response_time": None,
            "error": None,
            "timestamp": None,
        }
