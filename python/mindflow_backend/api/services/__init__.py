"""API Services for MindFlow Backend.

DEPRECATED: These modules have been moved to centralized locations.
This file is maintained for backward compatibility during migration.

Use: from mindflow_backend.services import get_agent_service, get_session_service, etc.
"""

# Legacy compatibility aliases - import from centralized locations
from mindflow_backend.api.services.agent_service import AgentService
from mindflow_backend.api.services.session_service import SessionService
from mindflow_backend.api.services.provider_service import ProviderService
from mindflow_backend.api.services.orchestration_service import OrchestrationService

__all__ = [
    "AgentService",
    "SessionService", 
    "ProviderService",
    "OrchestrationService",
]
