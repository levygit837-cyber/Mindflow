"""MindFlow Agent System.

Unified agent architecture with modular components:
- Context retrieval with RAG and vector search
- Specialist system with dynamic prompts and specialists  
- Core interfaces and dependency injection

Public API:
    - ``BaseAgent`` — immutable agent configuration
    - ``AgentRegistry`` — specialist registry singleton
    - ``get_agent`` — retrieve a specialist by type
    - ``register_all_specialists`` — startup bootstrap
    - Context and Specialist subsystems
"""

# Core agent system
from mindflow_backend.agents._base import AgentPersonality, BaseAgent
from mindflow_backend.agents._registry import (
    AgentRegistry,
    get_agent,
    get_registry,
    register_all_personalities,
)

# Modular subsystems
from mindflow_backend.agents import context
from mindflow_backend.agents import specialists

# Legacy compatibility (deprecated - use subsystems above)
from mindflow_backend.agents.context import get_agent_context_retriever
from mindflow_backend.agents.specialists import get_specialist_selector

__all__ = [
    # Core system
    "AgentPersonality",
    "AgentRegistry", 
    "BaseAgent",
    "get_agent",
    "get_registry",
    "register_all_specialists",
    
    # Subsystems
    "context",
    "specialists", 
    
    # Legacy compatibility
    "get_agent_context_retriever",
    "get_specialist_selector",
]
