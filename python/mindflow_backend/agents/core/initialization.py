"""Initialization for agent system core.

Sets up dependency injection container and registers
all core services and implementations.
"""

from __future__ import annotations

from mindflow_backend.agents.core.container import (
    DIContainer,
    register_singleton,
    register_factory,
    register_instance,
)
from mindflow_backend.agents.core.interfaces import (
    ContextRetriever,
    VectorStore,
    PersonalitySelector,
    ContentAnalyzer,
    ResultParser,
    Cache,
    RuleEngine,
)
from mindflow_backend.agents.context.cache import get_context_cache, ContextCache
from mindflow_backend.agents.context.vector_store import get_vector_store, InMemoryVectorStore
from mindflow_backend.agents.context.analyzer import get_content_analyzer, SessionContentAnalyzer
from mindflow_backend.agents.personality.cache import get_personality_cache, PersonalityCache
from mindflow_backend.agents.personality.rule_engine import get_personality_rule_engine, PersonalityRuleEngine
from mindflow_backend.agents.personality.configuration import (
    get_personality_config_builder,
    get_delegation_task_builder,
    PersonalityConfigurationBuilder,
    DelegationTaskBuilder,
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
        
        # Register personality implementations
        _register_personality_implementations()
        
        
        _logger.info("agent_system_initialization_completed")
    
    except Exception as e:
        _logger.error("agent_system_initialization_failed", error=str(e))
        raise


def _register_core_implementations() -> None:
    """Register core system implementations."""
    # Register cache implementations
    register_singleton(Cache, ContextCache)
    register_singleton(ContextCache, ContextCache)
    register_singleton(PersonalityCache, PersonalityCache)
    
    _logger.debug("core_implementations_registered")


def _register_context_implementations() -> None:
    """Register context retrieval implementations."""
    # Register vector store
    register_singleton(VectorStore, InMemoryVectorStore)
    
    # Register context analyzer
    register_singleton(ContentAnalyzer, SessionContentAnalyzer)
    
    _logger.debug("context_implementations_registered")


def _register_personality_implementations() -> None:
    """Register personality system implementations."""
    # Register rule engine
    register_singleton(RuleEngine, PersonalityRuleEngine)
    
    # Register configuration builders
    register_singleton(PersonalityConfigurationBuilder, PersonalityConfigurationBuilder)
    register_singleton(DelegationTaskBuilder, DelegationTaskBuilder)
    
    _logger.debug("personality_implementations_registered")




def get_initialization_status() -> dict[str, bool]:
    """Get status of all registered implementations."""
    from mindflow_backend.agents.core.container import get_container
    
    container = get_container()
    
    implementations = [
        (Cache, "Cache"),
        (ContextCache, "ContextCache"),
        (PersonalityCache, "PersonalityCache"),
        (VectorStore, "VectorStore"),
        (ContentAnalyzer, "ContentAnalyzer"),
        (RuleEngine, "RuleEngine"),
        (PersonalityConfigurationBuilder, "PersonalityConfigurationBuilder"),
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
