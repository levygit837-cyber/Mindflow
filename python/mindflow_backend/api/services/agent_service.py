"""Agent service for handling agent-related business logic.

DEPRECATED: This module has been moved to mindflow_backend.services.core.agent_service
This file is maintained for backward compatibility during migration.

Use: from mindflow_backend.services import get_agent_service
"""

# Forward compatibility alias - import from centralized location
from mindflow_backend.services.core.agent_service import AgentService

# Maintain backward compatibility
__all__ = ["AgentService"]
