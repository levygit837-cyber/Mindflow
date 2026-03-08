"""Advanced API infrastructure for OmniMind backend.

Provides API Gateway patterns, request routing,
middleware pipeline, and advanced API management.
"""

from .gateway import APIGateway, get_api_gateway
from .router import RequestRouter, get_request_router
from .middleware import MiddlewarePipeline, get_middleware_pipeline

__all__ = [
    "APIGateway",
    "get_api_gateway",
    "RequestRouter",
    "get_request_router",
    "MiddlewarePipeline",
    "get_middleware_pipeline",
]
