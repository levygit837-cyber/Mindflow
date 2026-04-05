"""Agent runtime service for gRPC communication.

DEPRECATED: This module has been moved to mindflow_backend.services.communication.agent_runtime_service
This file is maintained for backward compatibility during migration.

Use: from mindflow_backend.services.communication import get_agent_runtime_service
"""

# Forward compatibility alias - import from centralized location
from mindflow_backend.services.communication.agent_runtime_service import AgentRuntimeServiceImpl

# Maintain backward compatibility
__all__ = ["AgentRuntimeServiceImpl"]
