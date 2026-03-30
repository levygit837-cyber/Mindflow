"""Enhanced analyst agent interface.

DEPRECATED: This module has been moved to mindflow_backend.interfaces.agents.enhanced.analyst
This file is maintained for backward compatibility during migration.

Use: from mindflow_backend.interfaces.agents.enhanced import EnhancedAnalyst
"""

# Forward compatibility alias - import from new location
from mindflow_backend.interfaces.agents.enhanced.analyst import EnhancedAnalyst

# Maintain backward compatibility
__all__ = ["EnhancedAnalyst"]
