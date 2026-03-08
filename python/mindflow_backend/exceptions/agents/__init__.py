"""Agent system exceptions.

Simplified exception hierarchy for agent operations following best practices.
All exceptions now inherit directly from MindFlowError with clear context.
"""

from .system import (
    AgentSystemError,
    ContextRetrievalError,
    AgentVectorStoreError,
    SpecialistSelectionError,
    RuleEngineError,
    ContentAnalysisError,
    ResultParsingError,
    AgentCacheError,
    AgentConfigurationError,
    DependencyInjectionError,
    AgentRegistrationError,
    AgentExecutionError,
    AgentTimeoutError,
    AgentCommunicationError,
    AgentErrors,
    # Backward compatibility
    PersonalitySelectionError,
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
