"""Coder agent interfaces.

DEPRECATED: This module has been moved to mindflow_backend.interfaces.agents.coder
This file is maintained for backward compatibility during migration.

Use: from mindflow_backend.interfaces.agents import Coder
"""

# Forward compatibility alias - import from new location
from mindflow_backend.interfaces.agents.coder import Coder

# Maintain backward compatibility
__all__ = ["Coder"]
