"""Error schemas for MindFlow.

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
from .base_exceptions import (
    MindFlowErrorSchema,
    SystemErrorSchema,
    ConfigurationErrorSchema,
    InfrastructureErrorSchema,
    NetworkErrorSchema,
    ResourceErrorSchema,
    TimeoutErrorSchema,
    BusinessLogicErrorSchema,
    ValidationErrorSchema,
    AuthenticationErrorSchema,
    AuthorizationErrorSchema,
    BusinessRuleErrorSchema,
    ConflictErrorSchema,
    DomainErrorSchema,
    NotFoundErrorSchema,
    WorkflowErrorSchema,
)
from .api_errors import (
    RoutingErrorSchema,
    RequestValidationErrorSchema,
    AuthenticationErrorSchema as ApiAuthenticationErrorSchema,
    AuthorizationErrorSchema as ApiAuthorizationErrorSchema,
    StreamingErrorSchema,
    RateLimitErrorSchema,
    ApiTimeoutErrorSchema,
)
from .agent_errors import (
    AgentErrorSchema,
    AgentExecutionErrorSchema,
    AgentTimeoutErrorSchema,
    ContextRetrievalErrorSchema,
)
from .provider_errors import (
    ProviderErrorSchema,
    RateLimitErrorSchema as ProviderRateLimitErrorSchema,
    TokenLimitErrorSchema,
    ModelUnavailableErrorSchema,
)
from .orchestrator_errors import (
    OrchestratorErrorSchema,
    RoutingErrorSchema as OrchestratorRoutingErrorSchema,
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
