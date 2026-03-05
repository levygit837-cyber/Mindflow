"""OpenAPI documentation configuration and customizations."""

from __future__ import annotations

from typing import Dict, Any

from fastapi import FastAPI
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import HTMLResponse

from omnimind_backend.infra.config import get_settings

settings = get_settings()


def custom_openapi(app: FastAPI) -> Dict[str, Any]:
    """Generate custom OpenAPI schema with enhanced documentation."""
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="OmniMind API",
        version="2.0.0",
        description="""
        # OmniMind Backend API

        ## Overview
        The OmniMind API provides a comprehensive interface for managing AI agents, sessions, orchestration, providers, and memory operations.

        ## Architecture
        - **Controllers**: Handle HTTP requests and responses
        - **Services**: Implement business logic
        - **Middleware**: Provide security, validation, and performance optimization
        - **Database**: PostgreSQL for persistent storage
        - **Caching**: Redis/in-memory for performance

        ## Authentication
        All endpoints require API key authentication using the `Authorization: Bearer <key>` header.

        ## Rate Limiting
        - 100 requests per minute per IP
        - Additional limits may apply per endpoint

        ## Error Handling
        - Standardized error responses with proper HTTP status codes
        - Detailed error messages for debugging
        - Request IDs for tracing

        ## Pagination
        List endpoints support pagination using `limit` and `offset` parameters.

        ## Versioning
        Current API version is v1. Legacy endpoints are maintained for backward compatibility.

        ## Security
        - Input validation and sanitization
        - SQL injection prevention
        - XSS protection
        - CORS configuration
        """,
        routes=app.routes,
        servers=[
            {"url": "http://localhost:8000", "description": "Development server"},
            {"url": "https://api.omnimind.ai", "description": "Production server"},
        ],
        contact={
            "name": "OmniMind Team",
            "email": "api@omnimind.ai",
            "url": "https://omnimind.ai"
        },
        license_info={
            "name": "MIT License",
            "url": "https://opensource.org/licenses/MIT"
        },
        tags=[
            {
                "name": "agent",
                "description": "Agent management and chat operations"
            },
            {
                "name": "chat",
                "description": "Session and message management"
            },
            {
                "name": "orchestration",
                "description": "Task decomposition and agent coordination"
            },
            {
                "name": "providers",
                "description": "LLM provider management"
            },
            {
                "name": "memory",
                "description": "Memory and context operations"
            },
            {
                "name": "metrics",
                "description": "Performance and health metrics"
            }
        ]
    )
    
    # Add custom components
    openapi_schema["components"] = openapi_schema.get("components", {})
    openapi_schema["components"]["schemas"] = openapi_schema["components"].get("schemas", {})
    
    # Add common response schemas
    openapi_schema["components"]["schemas"]["BaseResponse"] = {
        "type": "object",
        "properties": {
            "success": {"type": "boolean", "description": "Whether the operation was successful"},
            "message": {"type": "string", "description": "Human-readable message"},
            "timestamp": {"type": "string", "format": "date-time", "description": "Response timestamp"}
        },
        "required": ["success"]
    }
    
    openapi_schema["components"]["schemas"]["ErrorResponse"] = {
        "allOf": [
            {"$ref": "#/components/schemas/BaseResponse"},
            {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean", "enum": [false]},
                    "error_code": {"type": "string", "description": "Machine-readable error code"},
                    "error_detail": {"type": "string", "description": "Detailed error information"},
                    "request_id": {"type": "string", "description": "Unique request identifier for tracing"}
                }
            }
        ]
    }
    
    openapi_schema["components"]["schemas"]["PaginationParams"] = {
        "type": "object",
        "properties": {
            "limit": {"type": "integer", "minimum": 1, "maximum": 1000, "default": 50, "description": "Maximum items per page"},
            "offset": {"type": "integer", "minimum": 0, "default": 0, "description": "Number of items to skip"}
        }
    }
    
    openapi_schema["components"]["schemas"]["PaginationResponse"] = {
        "type": "object",
        "properties": {
            "items": {"type": "array", "description": "Array of items"},
            "total": {"type": "integer", "description": "Total number of items"},
            "limit": {"type": "integer", "description": "Items per page"},
            "offset": {"type": "integer", "description": "Items skipped"},
            "has_next": {"type": "boolean", "description": "Whether there are more items"},
            "has_prev": {"type": "boolean", "description": "Whether there are previous items"}
        },
        "required": ["items", "total", "limit", "offset", "has_next", "has_prev"]
    }
    
    # Add security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "Authorization",
            "description": "API key authentication. Use format: 'Bearer <your-api-key>'"
        }
    }
    
    # Add global security requirement
    openapi_schema["security"] = [{"ApiKeyAuth": []}]
    
    # Add examples
    openapi_schema["components"]["examples"] = {
        "AgentChatRequest": {
            "summary": "Example agent chat request",
            "value": {
                "message": "Analyze this code for security vulnerabilities",
                "agent_type": "analyst",
                "provider": "google",
                "model": "gemini-pro",
                "sessionId": "sess-12345",
                "orchestrate": false
            }
        },
        "SessionCreateRequest": {
            "summary": "Example session creation request",
            "value": {
                "title": "Security Analysis Session",
                "user_id": "user-12345",
                "metadata": {"project": "omnimind", "type": "security"}
            }
        },
        "OrchestrationRequest": {
            "summary": "Example orchestration request",
            "value": {
                "task_description": "Perform comprehensive security audit of the codebase",
                "complexity_level": "high",
                "agent_sequence": ["analyst", "reviewer"],
                "sessionId": "sess-12345"
            }
        }
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema


def setup_documentation_routes(app: FastAPI) -> None:
    """Setup custom documentation routes."""
    
    @app.get("/docs", include_in_schema=False)
    async def custom_swagger_ui_html() -> HTMLResponse:
        """Custom Swagger UI documentation."""
        return get_swagger_ui_html(
            openapi_url=app.openapi_url,
            title=f"{app.title} - Swagger UI",
            oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
            swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
            swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
            swagger_favicon_url="https://fastapi.tiangolo.com/img/favicon.png",
        )
    
    @app.get("/redoc", include_in_schema=False)
    async def redoc_html() -> HTMLResponse:
        """ReDoc documentation."""
        return get_redoc_html(
            openapi_url=app.openapi_url,
            title=f"{app.title} - ReDoc",
            redoc_js_url="https://cdn.jsdelivr.net/npm/redoc@2.0.0/bundles/redoc.standalone.js",
            redoc_favicon_url="https://fastapi.tiangolo.com/img/favicon.png",
        )
    
    @app.get("/openapi.json", include_in_schema=False)
    async def get_openapi_endpoint() -> Dict[str, Any]:
        """Get OpenAPI schema."""
        return custom_openapi(app)


def add_operation_examples(app: FastAPI) -> None:
    """Add examples to specific operations."""
    
    if app.openapi_schema:
        # Add examples to agent endpoints
        paths = app.openapi_schema.get("paths", {})
        
        # Agent chat stream example
        if "/v1/agent/chat/stream" in paths:
            agent_path = paths["/v1/agent/chat/stream"]
            if "post" in agent_path:
                agent_path["post"]["requestBody"] = {
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/AgentChatRequest"},
                            "example": {
                                "message": "Help me analyze this Python code for potential bugs",
                                "agent_type": "analyst",
                                "provider": "google",
                                "model": "gemini-pro",
                                "sessionId": "sess-12345",
                                "orchestrate": False
                            }
                        }
                    },
                    "required": True
                }
        
        # Session creation example
        if "/v1/chat/sessions" in paths:
            session_path = paths["/v1/chat/sessions"]
            if "post" in session_path:
                session_path["post"]["requestBody"] = {
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/SessionCreateRequest"},
                            "example": {
                                "title": "Code Review Session",
                                "user_id": "user-12345",
                                "metadata": {"project": "omnimind", "type": "review"}
                            }
                        }
                    },
                    "required": True
                }


def create_api_info() -> Dict[str, Any]:
    """Create comprehensive API information."""
    return {
        "title": "OmniMind API",
        "description": "Advanced AI agent orchestration and management platform",
        "version": "2.0.0",
        "documentation": {
            "swagger": "/docs",
            "redoc": "/redoc",
            "openapi": "/openapi.json"
        },
        "endpoints": {
            "agent": {
                "path": "/v1/agent",
                "description": "Agent operations and chat streaming",
                "endpoints": [
                    "POST /chat/stream - Stream agent chat",
                    "GET /capabilities/{agent_type} - Get agent capabilities",
                    "GET /list - List available agents",
                    "POST /validate - Validate agent request"
                ]
            },
            "chat": {
                "path": "/v1/chat",
                "description": "Session and message management",
                "endpoints": [
                    "POST /sessions - Create session",
                    "GET /sessions - List sessions",
                    "GET /sessions/{id} - Get session details",
                    "PUT /sessions/{id} - Update session",
                    "DELETE /sessions/{id} - Delete session",
                    "POST /sessions/{id}/messages - Add message"
                ]
            },
            "orchestration": {
                "path": "/v1/orchestration",
                "description": "Task decomposition and coordination",
                "endpoints": [
                    "POST /decompose - Decompose task",
                    "POST /execute - Execute orchestration",
                    "GET /execution/{id} - Get execution status",
                    "POST /select-personality - Select personality",
                    "POST /coordinate/{task_id} - Coordinate agents"
                ]
            },
            "providers": {
                "path": "/v1/providers",
                "description": "LLM provider management",
                "endpoints": [
                    "GET / - List providers",
                    "GET /{id}/models - Get provider models",
                    "POST /{id}/test - Test provider",
                    "GET /{id}/config - Get configuration",
                    "PUT /{id}/config - Update configuration",
                    "GET /fallback-chain - Get fallback chain",
                    "GET /health-check - Health check all providers"
                ]
            },
            "memory": {
                "path": "/v1/memory",
                "description": "Memory and context operations",
                "endpoints": [
                    "GET /agents/{id}/sessions/{id} - Get agent memory",
                    "POST /search - Search memory",
                    "POST /agents/{id}/sessions/{id}/events - Add memory event",
                    "GET /sessions/{id}/context - Get context window",
                    "POST /agents/{id}/sessions/{id}/summary - Create summary"
                ]
            },
            "metrics": {
                "path": "/v1/metrics",
                "description": "Performance and health metrics",
                "endpoints": [
                    "GET /performance - Performance metrics",
                    "GET /health - Health metrics",
                    "GET /api - API metrics",
                    "GET /summary - Metrics summary"
                ]
            }
        },
        "authentication": {
            "type": "API Key",
            "header": "Authorization: Bearer <your-api-key>",
            "docs": "See authentication section in API documentation"
        },
        "rate_limiting": {
            "default": "100 requests/minute/IP",
            "notes": "Additional limits may apply per endpoint"
        },
        "errors": {
            "format": "Standardized JSON error responses",
            "codes": {
                "400": "Bad Request - Validation error",
                "401": "Unauthorized - Invalid API key",
                "403": "Forbidden - Insufficient permissions",
                "404": "Not Found - Resource not found",
                "429": "Too Many Requests - Rate limit exceeded",
                "500": "Internal Server Error"
            }
        },
        "compatibility": {
            "current_version": "v1",
            "legacy_support": "Yes",
            "deprecation_notice": "Legacy endpoints will be deprecated in v3"
        }
    }
