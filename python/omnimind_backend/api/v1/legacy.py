"""Legacy endpoints with deprecation warnings."""

from __future__ import annotations

from typing import Any, Dict
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse

from omnimind_backend.api.controllers.base_controller import BaseController
from omnimind_backend.infra.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/legacy", tags=["legacy"])


class LegacyController(BaseController):
    """Controller for legacy endpoints with deprecation warnings."""
    
    def __init__(self):
        super().__init__()
    
    def _add_deprecation_headers(self, response: JSONResponse) -> JSONResponse:
        """Add deprecation headers to response."""
        response.headers["Deprecation"] = "true"
        response.headers["Sunset"] = "2025-01-01"  # Example sunset date
        response.headers["Link"] = '</v1/agent/chat/stream>; rel="successor-version"'
        return response
    
    def _log_deprecation_warning(self, endpoint: str, client_ip: str = None) -> None:
        """Log deprecation warning for monitoring."""
        self.logger.warning(
            f"Legacy endpoint accessed: {endpoint}",
            client_ip=client_ip,
            recommendation="Please migrate to v1 endpoints",
            sunset_date="2025-01-01"
        )


# Initialize controller
legacy_controller = LegacyController()


@router.post("/agent/chat/stream")
async def legacy_agent_chat_stream(request: Dict[str, Any]):
    """Legacy agent chat stream endpoint - DEPRECATED.
    
    **DEPRECATED**: This endpoint will be removed on 2025-01-01.
    Please migrate to `/v1/agent/chat/stream`.
    
    Migration guide:
    - Change URL from `/legacy/agent/chat/stream` to `/v1/agent/chat/stream`
    - Request format remains the same
    - Response format remains the same
    """
    client_ip = "unknown"  # Would get from request in real implementation
    legacy_controller._log_deprecation_warning("/legacy/agent/chat/stream", client_ip)
    
    # Forward to new endpoint
    try:
        # This would forward to the actual v1 endpoint
        # For now, return deprecation response
        response = JSONResponse(
            status_code=301,
            content={
                "error": "Legacy endpoint deprecated",
                "message": "This endpoint is deprecated and will be removed on 2025-01-01",
                "migration": {
                    "new_endpoint": "/v1/agent/chat/stream",
                    "url": "/v1/agent/chat/stream"
                },
                "deprecation": {
                    "deprecated_since": "2024-01-01",
                    "sunset_date": "2025-01-01",
                    "reason": "Endpoint moved to v1 API structure"
                }
            }
        )
        response.headers["Location"] = "/v1/agent/chat/stream"
        return legacy_controller._add_deprecation_headers(response)
        
    except Exception as e:
        logger.error(f"Error in legacy endpoint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/chat/sessions")
async def legacy_list_sessions():
    """Legacy session listing endpoint - DEPRECATED.
    
    **DEPRECATED**: This endpoint will be removed on 2025-01-01.
    Please migrate to `/v1/chat/sessions`.
    """
    client_ip = "unknown"
    legacy_controller._log_deprecation_warning("/legacy/chat/sessions", client_ip)
    
    response = JSONResponse(
        status_code=301,
        content={
            "error": "Legacy endpoint deprecated",
            "message": "This endpoint is deprecated and will be removed on 2025-01-01",
            "migration": {
                "new_endpoint": "/v1/chat/sessions",
                "url": "/v1/chat/sessions"
            },
            "deprecation": {
                "deprecated_since": "2024-01-01",
                "sunset_date": "2025-01-01",
                "reason": "Endpoint moved to v1 API structure"
            }
        }
    )
    response.headers["Location"] = "/v1/chat/sessions"
    return legacy_controller._add_deprecation_headers(response)


@router.get("/chat/sessions/{session_id}")
async def legacy_get_session(session_id: str):
    """Legacy session retrieval endpoint - DEPRECATED.
    
    **DEPRECATED**: This endpoint will be removed on 2025-01-01.
    Please migrate to `/v1/chat/sessions/{session_id}`.
    """
    client_ip = "unknown"
    legacy_controller._log_deprecation_warning(f"/legacy/chat/sessions/{session_id}", client_ip)
    
    response = JSONResponse(
        status_code=301,
        content={
            "error": "Legacy endpoint deprecated",
            "message": "This endpoint is deprecated and will be removed on 2025-01-01",
            "migration": {
                "new_endpoint": f"/v1/chat/sessions/{session_id}",
                "url": f"/v1/chat/sessions/{session_id}"
            },
            "deprecation": {
                "deprecated_since": "2024-01-01",
                "sunset_date": "2025-01-01",
                "reason": "Endpoint moved to v1 API structure"
            }
        }
    )
    response.headers["Location"] = f"/v1/chat/sessions/{session_id}"
    return legacy_controller._add_deprecation_headers(response)


@router.get("/deprecation-info")
async def get_deprecation_info():
    """Get information about deprecated endpoints and migration guidance."""
    deprecation_info = {
        "policy": {
            "deprecation_period": "12 months",
            "sunset_date": "2025-01-01",
            "notification_methods": [
                "HTTP headers (Deprecation, Sunset, Link)",
                "Response warnings",
                "Documentation updates",
                "Monitoring alerts"
            ]
        },
        "deprecated_endpoints": {
            "/legacy/agent/chat/stream": {
                "deprecated_since": "2024-01-01",
                "sunset_date": "2025-01-01",
                "replacement": "/v1/agent/chat/stream",
                "impact": "Breaking change - URL change",
                "migration_complexity": "Low - just change URL"
            },
            "/legacy/chat/sessions": {
                "deprecated_since": "2024-01-01",
                "sunset_date": "2025-01-01",
                "replacement": "/v1/chat/sessions",
                "impact": "Breaking change - URL change",
                "migration_complexity": "Low - just change URL"
            },
            "/legacy/chat/sessions/{id}": {
                "deprecated_since": "2024-01-01",
                "sunset_date": "2025-01-01",
                "replacement": "/v1/chat/sessions/{id}",
                "impact": "Breaking change - URL change",
                "migration_complexity": "Low - just change URL"
            }
        },
        "migration_guide": {
            "steps": [
                "1. Update API client base URL from /legacy to /v1",
                "2. Test new endpoints in development environment",
                "3. Update production clients before sunset date",
                "4. Monitor for any breaking changes"
            ],
            "tools": [
                "Use /api-info endpoint for comprehensive API documentation",
                "Check /v1/metrics for migration status",
                "Review OpenAPI docs at /docs"
            ],
            "support": {
                "documentation": "/docs",
                "api_info": "/api-info",
                "metrics": "/v1/metrics",
                "contact": "api-support@omnimind.ai"
            }
        },
        "timeline": {
            "2024-01-01": "Legacy endpoints marked as deprecated",
            "2024-06-01": "Begin deprecation warnings in client libraries",
            "2024-09-01": "Increase deprecation warning frequency",
            "2024-12-01": "Final deprecation notices",
            "2025-01-01": "Legacy endpoints removed (SUNSET)"
        }
    }
    
    return deprecation_info


@router.get("/migration-status")
async def get_migration_status():
    """Get migration status and statistics."""
    # This would track actual migration metrics
    # For now, return placeholder data
    migration_status = {
        "legacy_usage": {
            "total_requests": 0,
            "unique_clients": 0,
            "most_used_endpoints": [],
            "trend": "decreasing"
        },
        "v1_usage": {
            "total_requests": 0,
            "unique_clients": 0,
            "adoption_rate": 0.0,
            "trend": "increasing"
        },
        "migration_progress": {
            "percentage_migrated": 0.0,
            "estimated_completion": "2024-12-01",
            "on_track": True
        },
        "alerts": [
            {
                "level": "info",
                "message": "Migration tracking is active",
                "action": "Monitor legacy endpoint usage"
            }
        ],
        "recommendations": [
            "Update client applications to use v1 endpoints",
            "Test migration in staging environment",
            "Monitor error rates during transition",
            "Plan for complete migration before sunset date"
        ]
    }
    
    return migration_status
