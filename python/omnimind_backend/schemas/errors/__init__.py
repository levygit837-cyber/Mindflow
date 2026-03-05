"""Error schemas for OmniMind.

Provides standardized error response formats and error metadata schemas
for consistent error handling across the system.
"""

from .base import (
    ErrorSchema,
    ErrorSeverity,
    ErrorCategory,
    ErrorContext,
    ErrorResponse,
)
from .agent_errors import (
    AgentErrorSchema,
    AgentExecutionErrorSchema,
    AgentTimeoutErrorSchema,
    ContextRetrievalErrorSchema,
)
from .provider_errors import (
    ProviderErrorSchema,
    RateLimitErrorSchema,
    TokenLimitErrorSchema,
    ModelUnavailableErrorSchema,
)
from .orchestrator_errors import (
    OrchestratorErrorSchema,
    RoutingErrorSchema,
    DecompositionErrorSchema,
    SchedulingErrorSchema,
)

__all__ = [
    # Base schemas
    "ErrorSchema",
    "ErrorSeverity", 
    "ErrorCategory",
    "ErrorContext",
    "ErrorResponse",
    
    # Agent errors
    "AgentErrorSchema",
    "AgentExecutionErrorSchema",
    "AgentTimeoutErrorSchema",
    "ContextRetrievalErrorSchema",
    
    # Provider errors
    "ProviderErrorSchema",
    "RateLimitErrorSchema",
    "TokenLimitErrorSchema",
    "ModelUnavailableErrorSchema",
    
    # Orchestrator errors
    "OrchestratorErrorSchema",
    "RoutingErrorSchema",
    "DecompositionErrorSchema",
    "SchedulingErrorSchema",
]
