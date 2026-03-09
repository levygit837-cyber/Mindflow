"""Core personality contract.

DEPRECATED: This module has been moved to mindflow_backend.interfaces.agents.core_personality
This file is maintained for backward compatibility during migration.

Use: from mindflow_backend.interfaces.agents import CorePersonalityContract
"""

# Forward compatibility alias - import from new location
from mindflow_backend.interfaces.agents.core_personality import CorePersonalityContract

# Maintain backward compatibility
__all__ = ["CorePersonalityContract"]
