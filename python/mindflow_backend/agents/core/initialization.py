"""Initialization for agent system core.

Sets up dependency injection container and registers
all core services and implementations.
"""

from __future__ import annotations

from mindflow_backend.agents.core.container import (
    register_singleton,
)
from mindflow_backend.agents.core.interfaces import (
    Cache,
    ContentAnalyzer,
    ResultParser,
    RuleEngine,
    VectorStore,
)
from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


def initialize_agent_system() -> None:
    """Initialize the agent system with all dependencies."""
    try:
        _logger.info("agent_system_initialization_started")
        
        # Register core implementations
        _register_core_implementations()
        
        # Register context implementations
        _register_context_implementations()
        
        # Register specialist implementations
        _register_specialist_implementations()
        
        
        _logger.info("agent_system_initialization_completed")
    
    except Exception as e:
        _logger.error("agent_system_initialization_failed", error=str(e))
        raise


def _register_core_implementations() -> None:
    """Register core system implementations."""
    # Lazy imports to avoid circular dependencies
    from mindflow_backend.agents.context.cache import ContextCache
    from mindflow_backend.agents.specialists.cache import SpecialistCache

    # Register cache implementations
    register_singleton(Cache, ContextCache)
    register_singleton(ContextCache, ContextCache)
    register_singleton(SpecialistCache, SpecialistCache)

    _logger.debug("core_implementations_registered")


def _register_context_implementations() -> None:
    """Register context retrieval implementations."""
    # Lazy imports to avoid circular dependencies
    from mindflow_backend.agents.context.analyzer import SessionContentAnalyzer
    from mindflow_backend.agents.context.vector_store import InMemoryVectorStore

    # Register vector store
    register_singleton(VectorStore, InMemoryVectorStore)

    # Register context analyzer
    register_singleton(ContentAnalyzer, SessionContentAnalyzer)

    _logger.debug("context_implementations_registered")


def _register_specialist_implementations() -> None:
    """Register specialist system implementations."""
    # Lazy imports to avoid circular dependencies
    from mindflow_backend.agents.specialists.configuration import (
        DelegationTaskBuilder,
        SpecialistConfigurationBuilder,
    )
    from mindflow_backend.agents.specialists.rule_engine import SpecialistRuleEngine

    # Register rule engine
    register_singleton(RuleEngine, SpecialistRuleEngine)

    # Register configuration builders
    register_singleton(SpecialistConfigurationBuilder, SpecialistConfigurationBuilder)
    register_singleton(DelegationTaskBuilder, DelegationTaskBuilder)

    _logger.debug("specialist_implementations_registered")




def get_initialization_status() -> dict[str, bool]:
    """Get status of all registered implementations."""
    # Lazy imports to avoid circular dependencies
    from mindflow_backend.agents.context.cache import ContextCache
    from mindflow_backend.agents.core.container import get_container
    from mindflow_backend.agents.specialists.cache import SpecialistCache
    from mindflow_backend.agents.specialists.configuration import (
        DelegationTaskBuilder,
        SpecialistConfigurationBuilder,
    )

    container = get_container()

    implementations = [
        (Cache, "Cache"),
        (ContextCache, "ContextCache"),
        (SpecialistCache, "SpecialistCache"),
        (VectorStore, "VectorStore"),
        (ContentAnalyzer, "ContentAnalyzer"),
        (RuleEngine, "RuleEngine"),
        (SpecialistConfigurationBuilder, "SpecialistConfigurationBuilder"),
        (DelegationTaskBuilder, "DelegationTaskBuilder"),
        (ResultParser, "ResultParser"),
    ]
    
    status = {}
    for interface, name in implementations:
        status[name] = container.has(interface)
    
    return status


def validate_dependencies() -> bool:
    """Validate that all required dependencies are registered."""
    status = get_initialization_status()
    
    required_implementations = [
        "Cache",
        "VectorStore", 
        "ContentAnalyzer",
        "RuleEngine",
    ]
    
    missing = [
        name for name in required_implementations
        if not status.get(name, False)
    ]
    
    if missing:
        _logger.error("dependency_validation_failed", missing=missing)
        return False
    
    _logger.info("dependency_validation_passed")
    return True
