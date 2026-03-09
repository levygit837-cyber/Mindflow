"""Task RAG Agent interface.

DEPRECATED: This module has been moved to mindflow_backend.interfaces.agents.task_rag_agent
This file is maintained for backward compatibility during migration.

Use: from mindflow_backend.interfaces.agents import TaskRagAgent
"""

# Forward compatibility alias - import from new location
from mindflow_backend.interfaces.agents.task_rag_agent import TaskRagAgent

# Maintain backward compatibility
__all__ = ["TaskRagAgent"]
