"""Health check schemas for gRPC services."""

from typing import Literal

from pydantic import BaseModel, Field


class HealthStatus(Literal["healthy", "unhealthy", "unknown"]):
    """Health status enumeration."""
    pass


class GrpcHealthRequest(BaseModel):
    """gRPC health check request."""
    service: str = Field(default="agent_runtime", description="Service name to check")
    timeout_seconds: int = Field(default=10, description="Timeout for health check")


class GrpcHealthResponse(BaseModel):
    """gRPC health check response."""
    status: HealthStatus = Field(description="Health status of the service")
    version: str = Field(description="Version of the service")
    uptime_seconds: float = Field(description="Server uptime in seconds")
    timestamp: str = Field(description="Response timestamp in ISO format")
    details: dict[str, str] = Field(default_factory=dict, description="Additional health details")
    error_message: str | None = Field(default=None, description="Error message if unhealthy")
