"""External error handler interface.

Defines contracts for handling external service errors, network failures,
and third-party API integration problems.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable, Any, Dict, Optional, List, Union
from abc import abstractmethod

from mindflow_backend.schemas.errors import (
    NetworkErrorSchema,
    ThirdPartyAPIErrorSchema,
    IntegrationErrorSchema,
    ErrorCategory,
    ErrorSeverity,
)

from .base_error_handler import BaseErrorHandlerContract


@runtime_checkable
class ExternalErrorHandlerContract(BaseErrorHandlerContract, Protocol):
    """Contract for external service error handling.
    
    Specialized interface for handling errors from external APIs,
    network operations, and third-party service integrations.
    """

    @abstractmethod
    async def handle_network_error(
        self,
        exception: Exception,
        *,
        endpoint: Optional[str] = None,
        timeout: Optional[float] = None,
        retry_count: Optional[int] = None,
        network_type: Optional[str] = None,
        protocol: Optional[str] = None,
        **context: Any,
    ) -> NetworkErrorSchema:
        """Handle network operation errors.
        
        Args:
            exception: The network exception
            endpoint: Network endpoint that failed
            timeout: Network timeout duration
            retry_count: Number of retry attempts
            network_type: Type of network (HTTP, TCP, UDP, etc.)
            protocol: Network protocol
            **context: Additional context
            
        Returns:
            Network error schema with network context
        """
        ...

    @abstractmethod
    async def handle_third_party_api_error(
        self,
        exception: Exception,
        *,
        api_name: Optional[str] = None,
        api_endpoint: Optional[str] = None,
        request_method: Optional[str] = None,
        status_code: Optional[int] = None,
        response_body: Optional[str] = None,
        rate_limit: Optional[Dict[str, Any]] = None,
        **context: Any,
    ) -> ThirdPartyAPIErrorSchema:
        """Handle third-party API errors.
        
        Args:
            exception: The API exception
            api_name: Name of the third-party API
            api_endpoint: API endpoint that failed
            request_method: HTTP method used
            status_code: HTTP status code received
            response_body: API response body
            rate_limit: Rate limit information
            **context: Additional context
            
        Returns:
            Third-party API error schema with API context
        """
        ...

    @abstractmethod
    async def handle_integration_error(
        self,
        exception: Exception,
        *,
        service_name: Optional[str] = None,
        integration_type: Optional[str] = None,
        operation: Optional[str] = None,
        configuration: Optional[Dict[str, Any]] = None,
        dependency: Optional[str] = None,
        **context: Any,
    ) -> IntegrationErrorSchema:
        """Handle service integration errors.
        
        Args:
            exception: The integration exception
            service_name: Name of the service being integrated
            integration_type: Type of integration (REST, GraphQL, gRPC, etc.)
            operation: Integration operation that failed
            configuration: Integration configuration
            dependency: Service dependency that failed
            **context: Additional context
            
        Returns:
            Integration error schema with integration context
        """
        ...

    @abstractmethod
    def check_service_health(
        self,
        service_name: str,
        *,
        endpoint: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Check health status of an external service.
        
        Args:
            service_name: Name of the service to check
            endpoint: Service health endpoint
            timeout: Health check timeout
            
        Returns:
            Service health status information
        """
        ...

    @abstractmethod
    def get_retry_strategy_for_api(
        self,
        api_name: str,
        error_type: str,
        status_code: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """Get retry strategy for specific API errors.
        
        Args:
            api_name: Name of the API
            error_type: Type of error encountered
            status_code: HTTP status code
            
        Returns:
            Retry strategy configuration
        """
        ...

    @abstractmethod
    def get_fallback_service(
        self,
        primary_service: str,
        operation: Optional[str] = None,
    ) -> Optional[str]:
        """Get fallback service for high availability.
        
        Args:
            primary_service: Primary service that failed
            operation: Operation being performed
            
        Returns:
            Fallback service name or None
        """
        ...

    @abstractmethod
    async def test_connectivity(
        self,
        endpoint: str,
        *,
        timeout: Optional[float] = None,
        protocol: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Test connectivity to an external endpoint.
        
        Args:
            endpoint: Endpoint to test
            timeout: Test timeout
            protocol: Protocol to use
            
        Returns:
            Connectivity test results
        """
        ...

    @abstractmethod
    def get_rate_limit_info(
        self,
        api_name: str,
        response_headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Get rate limiting information for an API.
        
        Args:
            api_name: Name of the API
            response_headers: HTTP response headers
            
        Returns:
            Rate limiting information
        """
        ...

    @abstractmethod
    def should_circuit_break(
        self,
        service_name: str,
        error_rate: float,
        time_window: Optional[str] = None,
    ) -> bool:
        """Determine if circuit breaker should be triggered.
        
        Args:
            service_name: Name of the service
            error_rate: Current error rate (0.0 to 1.0)
            time_window: Time window for error rate calculation
            
        Returns:
            True if circuit breaker should trigger
        """
        ...

    @abstractmethod
    def get_service_dependencies(
        self,
        service_name: str,
    ) -> List[str]:
        """Get list of service dependencies.
        
        Args:
            service_name: Name of the service
            
        Returns:
            List of dependent services
        """
        ...

    # External service-specific convenience methods
    
    def get_api_status_dashboard(
        self,
        services: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Get API status dashboard information.
        
        Args:
            services: List of services to include (None for all)
            
        Returns:
            API status dashboard data
        """
        # Default implementation - subclasses should override
        return {
            "timestamp": None,
            "services": {},
            "overall_status": "unknown",
            "total_services": 0,
            "healthy_services": 0,
            "degraded_services": 0,
            "unhealthy_services": 0,
        }

    def analyze_error_patterns(
        self,
        service_name: str,
        time_range: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Analyze error patterns for a service.
        
        Args:
            service_name: Name of the service to analyze
            time_range: Time range for analysis (1h, 24h, 7d, etc.)
            
        Returns:
            Error pattern analysis
        """
        # Default implementation - subclasses should override
        return {
            "service_name": service_name,
            "time_range": time_range,
            "total_errors": 0,
            "error_types": {},
            "peak_error_times": [],
            "common_endpoints": [],
            "trending_errors": [],
            "recommendations": [],
        }

    def create_service_report(
        self,
        service_name: str,
        include_metrics: bool = True,
        include_errors: bool = True,
        include_recommendations: bool = True,
    ) -> Dict[str, Any]:
        """Create comprehensive service report.
        
        Args:
            service_name: Name of the service
            include_metrics: Include performance metrics
            include_errors: Include error analysis
            include_recommendations: Include recommendations
            
        Returns:
            Service report
        """
        # Default implementation - subclasses should override
        return {
            "service_name": service_name,
            "report_timestamp": None,
            "status": "unknown",
            "metrics": {} if include_metrics else None,
            "errors": {} if include_errors else None,
            "recommendations": [] if include_recommendations else None,
        }

    def validate_api_configuration(
        self,
        api_name: str,
        configuration: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Validate API configuration.
        
        Args:
            api_name: Name of the API
            configuration: Configuration to validate
            
        Returns:
            Configuration validation results
        """
        # Default implementation - subclasses should override
        return {
            "api_name": api_name,
            "valid": True,
            "errors": [],
            "warnings": [],
            "missing_fields": [],
            "invalid_fields": [],
        }

    def get_service_metrics(
        self,
        service_name: str,
        metric_types: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Get service metrics for monitoring.
        
        Args:
            service_name: Name of the service
            metric_types: Types of metrics to retrieve
            
        Returns:
            Service metrics
        """
        # Default implementation - subclasses should override
        return {
            "service_name": service_name,
            "timestamp": None,
            "metrics": {
                "request_count": 0,
                "error_count": 0,
                "response_time": 0.0,
                "throughput": 0.0,
                "availability": 0.0,
            }
        }
