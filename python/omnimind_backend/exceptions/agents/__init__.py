"""Agent system exceptions.

All exceptions related to agent operations, personalities, and communication.
"""

# Re-export existing exceptions for backward compatibility
from omnimind_backend.agents.core.exceptions import (
    AgentSystemError,
    ContextRetrievalError,
    VectorStoreError,
    PersonalitySelectionError,
    RuleEngineError,
    ContentAnalysisError,
    ResultParsingError,
    CacheError,
    ConfigurationError,
    DependencyInjectionError,
    SessionReviewError,
    AgentRegistrationError,
)

# New agent-specific exceptions
from .core import AgentExecutionError, AgentTimeoutError
from .communication import AgentCommunicationError

__all__ = [
    # Existing exceptions
    "AgentSystemError",
    "ContextRetrievalError",
    "VectorStoreError",
    "PersonalitySelectionError",
    "RuleEngineError",
    "ContentAnalysisError",
    "ResultParsingError",
    "CacheError",
    "ConfigurationError",
    "DependencyInjectionError",
    "SessionReviewError",
    "AgentRegistrationError",
    # New exceptions
    "AgentExecutionError",
    "AgentTimeoutError",
    "AgentCommunicationError",
]
