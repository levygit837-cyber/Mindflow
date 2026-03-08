"""Session manager interface.

DEPRECATED: This module has been moved to mindflow_backend.interfaces.agents.session
This file is maintained for backward compatibility during migration.

Use: from mindflow_backend.interfaces.agents import SessionManagerContract
"""

# Forward compatibility alias - import from new location
from mindflow_backend.interfaces.agents.session import SessionManagerContract

# Maintain backward compatibility
__all__ = ["SessionManagerContract"]
