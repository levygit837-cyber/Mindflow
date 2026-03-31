"""Advanced API infrastructure for OmniMind backend.

Provides API Gateway patterns, request routing,
middleware pipeline, and advanced API management.
"""

from .gateway import APIGateway, get_api_gateway
from .middleware import MiddlewarePipeline, get_middleware_pipeline
from .router import RequestRouter, get_request_router

__all__ = [
    "APIGateway",
    "get_api_gateway",
    "RequestRouter",
    "get_request_router",
    "MiddlewarePipeline",
    "get_middleware_pipeline",
]
