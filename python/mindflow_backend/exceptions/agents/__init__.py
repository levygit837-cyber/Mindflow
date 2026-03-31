"""Agent system exceptions.

Simplified exception hierarchy for agent operations following best practices.
All exceptions now inherit directly from MindFlowError with clear context.
"""

from .system import (
    AgentCacheError,
    AgentCommunicationError,
    AgentConfigurationError,
    AgentErrors,
    AgentExecutionError,
    AgentRegistrationError,
    AgentSystemError,
    AgentTimeoutError,
    AgentVectorStoreError,
    ContentAnalysisError,
    ContextRetrievalError,
    DependencyInjectionError,
    # Backward compatibility
    PersonalitySelectionError,
    ResultParsingError,
    RuleEngineError,
    SpecialistSelectionError,
)

__all__ = [
    "AgentSystemError",
    "ContextRetrievalError",
    "AgentVectorStoreError",
    "SpecialistSelectionError",
    "RuleEngineError",
    "ContentAnalysisError",
    "ResultParsingError",
    "AgentCacheError",
    "AgentConfigurationError",
    "DependencyInjectionError",
    "AgentRegistrationError",
    "AgentExecutionError",
    "AgentTimeoutError",
    "AgentCommunicationError",
    "AgentErrors",
    # Backward compatibility
    "PersonalitySelectionError",
]
