"""Streaming interface.

DEPRECATED: This module has been moved to mindflow_backend.interfaces.agents.streaming
This file is maintained for backward compatibility during migration.

Use: from mindflow_backend.interfaces.agents import StreamingContract
"""

# Forward compatibility alias - import from new location
from mindflow_backend.interfaces.agents.streaming import StreamingContract

# Maintain backward compatibility
__all__ = ["StreamingContract"]
