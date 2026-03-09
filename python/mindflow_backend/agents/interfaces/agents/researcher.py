"""Enhanced research agent interface.

DEPRECATED: This module has been moved to mindflow_backend.interfaces.agents.researcher
This file is maintained for backward compatibility during migration.

Use: from mindflow_backend.interfaces.agents import EnhancedResearcher
"""

# Forward compatibility alias - import from new location
from mindflow_backend.interfaces.agents.researcher import EnhancedResearcher

# Maintain backward compatibility
__all__ = ["EnhancedResearcher"]
