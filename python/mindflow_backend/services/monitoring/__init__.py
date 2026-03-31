"""Monitoring services for MindFlow backend.

This module provides services for health checks, metrics collection,
and session review/optimization.
"""

from __future__ import annotations


# Factory functions for monitoring services
def get_health_service():
    """Factory function for HealthService."""
    from mindflow_backend.services.monitoring.health_service import HealthService
    return HealthService()

def get_metrics_service():
    """Factory function for MetricsService."""
    from mindflow_backend.services.monitoring.metrics_service import MetricsService
    return MetricsService()

def get_review_service():
    """Factory function for ReviewService."""
    from mindflow_backend.services.monitoring.review_service import ReviewService
    return ReviewService()

# Public exports
__all__ = [
    "get_health_service",
    "get_metrics_service",
    "get_review_service",
]
