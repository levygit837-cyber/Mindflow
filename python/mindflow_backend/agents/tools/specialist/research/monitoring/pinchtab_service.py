"""PinchTab research service for agent research operations.

DEPRECATED: This module has been moved to mindflow_backend.services.core.pinchtab_service
This file is maintained for backward compatibility during migration.

Use: from mindflow_backend.services.core import get_pinchtab_service
"""

# Forward compatibility alias - import from centralized location
from mindflow_backend.services.core.pinchtab_service import PinchTabService, get_pinchtab_service

# Maintain backward compatibility
__all__ = ["PinchTabService", "get_pinchtab_service"]
