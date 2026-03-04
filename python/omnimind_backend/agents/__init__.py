"""OmniMind Agent System.

Unified agent architecture with modular components:
- Context retrieval with RAG and vector search
- Personality system with dynamic prompts and sub-personalities  
- Session review with structured analysis
- Core interfaces and dependency injection

Public API:
    - ``BaseAgent`` — immutable agent configuration
    - ``AgentRegistry`` — personality registry singleton
    - ``get_agent`` — retrieve a personality by type
    - ``register_all_personalities`` — startup bootstrap
    - Context, Personality, and Review subsystems
"""

# Core agent system
from omnimind_backend.agents._base import AgentPersonality, BaseAgent
from omnimind_backend.agents._registry import (
    AgentRegistry,
    get_agent,
    get_registry,
    register_all_personalities,
)

# Modular subsystems
from omnimind_backend.agents import context
from omnimind_backend.agents import personality
from omnimind_backend.agents import review

# Legacy compatibility (deprecated - use subsystems above)
from omnimind_backend.agents.context import get_agent_context_retriever
from omnimind_backend.agents.personality import get_personality_selector
from omnimind_backend.agents.review import get_session_review_agent

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
    "review",
    
    # Legacy compatibility
    "get_agent_context_retriever",
    "get_personality_selector",
    "get_session_review_agent",
]
