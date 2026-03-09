"""Provider service for managing LLM providers and configurations.

DEPRECATED: This module has been moved to mindflow_backend.services.core.provider_service
This file is maintained for backward compatibility during migration.

Use: from mindflow_backend.services import get_provider_service
"""

# Forward compatibility alias - import from centralized location
from mindflow_backend.services.core.provider_service import ProviderService

# Maintain backward compatibility
__all__ = ["ProviderService"]
