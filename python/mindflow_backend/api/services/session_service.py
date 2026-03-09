"""Session service for managing chat sessions and context.

DEPRECATED: This module has been moved to mindflow_backend.services.core.session_service
This file is maintained for backward compatibility during migration.

Use: from mindflow_backend.services import get_session_service
"""

# Forward compatibility alias - import from centralized location
from mindflow_backend.services.core.session_service import SessionService

# Maintain backward compatibility
__all__ = ["SessionService"]
