"""MindFlow Agent System.

Unified agent architecture with modular components:
- Context retrieval with RAG and vector search
- Personality system with dynamic prompts and sub-personalities  
- Core interfaces and dependency injection

Public API:
    - ``BaseAgent`` — immutable agent configuration
    - ``AgentRegistry`` — personality registry singleton
    - ``get_agent`` — retrieve a personality by type
    - ``register_all_personalities`` — startup bootstrap
    - Context and Personality subsystems
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
from mindflow_backend.agents import personality

# Legacy compatibility (deprecated - use subsystems above)
from mindflow_backend.agents.context import get_agent_context_retriever
from mindflow_backend.agents.personality import get_personality_selector

__all__ = [
    # Core system
    "AgentPersonality",
    "AgentRegistry", 
    "BaseAgent",
    "get_agent",
    "get_registry",
    "register_all_personalities",
    
    # Subsystems
    "context",
    "personality", 
    
    # Legacy compatibility
    "get_agent_context_retriever",
    "get_personality_selector",
]
