"""Error schemas for MindFlow.

Provides standardized error response formats and error metadata schemas
for consistent error handling across the system.
"""

from .agent_errors import (
    AgentErrorSchema,
    AgentExecutionErrorSchema,
    AgentTimeoutErrorSchema,
    ContextRetrievalErrorSchema,
)
from .api_errors import (
    ApiTimeoutErrorSchema,
    RateLimitErrorSchema,
    RequestValidationErrorSchema,
    RoutingErrorSchema,
    StreamingErrorSchema,
)
from .api_errors import (
    AuthenticationErrorSchema as ApiAuthenticationErrorSchema,
)
from .api_errors import (
    AuthorizationErrorSchema as ApiAuthorizationErrorSchema,
)
from .base import (
    ErrorCategory,
    ErrorContext,
    ErrorResponse,
    ErrorSchema,
    ErrorSeverity,
)
from .base_exceptions import (
    AuthenticationErrorSchema,
    AuthorizationErrorSchema,
    BusinessLogicErrorSchema,
    BusinessRuleErrorSchema,
    ConfigurationErrorSchema,
    ConflictErrorSchema,
    DomainErrorSchema,
    InfrastructureErrorSchema,
    MindFlowErrorSchema,
    NetworkErrorSchema,
    NotFoundErrorSchema,
    ResourceErrorSchema,
    SystemErrorSchema,
    TimeoutErrorSchema,
    ValidationErrorSchema,
    WorkflowErrorSchema,
)
from .orchestrator_errors import (
    DecompositionErrorSchema,
    OrchestratorErrorSchema,
    SchedulingErrorSchema,
)
from .orchestrator_errors import (
    RoutingErrorSchema as OrchestratorRoutingErrorSchema,
)
from .provider_errors import (
    ModelUnavailableErrorSchema,
    ProviderErrorSchema,
    TokenLimitErrorSchema,
)
from .provider_errors import (
    RateLimitErrorSchema as ProviderRateLimitErrorSchema,
)

__all__ = [
    # Base schemas
    "ErrorSchema",
    "ErrorSeverity", 
    "ErrorCategory",
    "ErrorContext",
    "ErrorResponse",
    
    # Base exception schemas
    "MindFlowErrorSchema",
    "SystemErrorSchema",
    "ConfigurationErrorSchema",
    "InfrastructureErrorSchema",
    "NetworkErrorSchema",
    "ResourceErrorSchema",
    "TimeoutErrorSchema",
    "BusinessLogicErrorSchema",
    "ValidationErrorSchema",
    "AuthenticationErrorSchema",
    "AuthorizationErrorSchema",
    "BusinessRuleErrorSchema",
    "ConflictErrorSchema",
    "DomainErrorSchema",
    "NotFoundErrorSchema",
    "WorkflowErrorSchema",
    
    # API error schemas
    "RoutingErrorSchema",
    "RequestValidationErrorSchema",
    "ApiAuthenticationErrorSchema",
    "ApiAuthorizationErrorSchema",
    "StreamingErrorSchema",
    "RateLimitErrorSchema",
    "ApiTimeoutErrorSchema",
    
    # Agent errors
    "AgentErrorSchema",
    "AgentExecutionErrorSchema",
    "AgentTimeoutErrorSchema",
    "ContextRetrievalErrorSchema",
    
    # Provider errors
    "ProviderErrorSchema",
    "ProviderRateLimitErrorSchema",
    "TokenLimitErrorSchema",
    "ModelUnavailableErrorSchema",
    
    # Orchestrator errors
    "OrchestratorErrorSchema",
    "OrchestratorRoutingErrorSchema",
    "DecompositionErrorSchema",
    "SchedulingErrorSchema",
]
