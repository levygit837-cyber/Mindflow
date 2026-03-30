"""Analyst agent interfaces.

DEPRECATED: This module has been moved to mindflow_backend.interfaces.agents.analyst
This file is maintained for backward compatibility during migration.

Use: from mindflow_backend.interfaces.agents import Analyst
"""

# Forward compatibility alias - import from new location
from mindflow_backend.interfaces.agents.analyst import Analyst

# Maintain backward compatibility
__all__ = ["Analyst"]
