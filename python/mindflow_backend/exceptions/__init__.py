"""Exception definitions for MindFlow.

Centralized exception hierarchy for better error handling
and debugging across the system.
"""

# New simplified exceptions
# Domain-specific exceptions
from .agents import (
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
    ResultParsingError,
    RuleEngineError,
    SpecialistSelectionError,
)
from .api import (
    AuthenticationError,
    AuthorizationError,
    RequestValidationError,
    RoutingError,
    StreamingError,
)
from .base.business_new import (
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    ValidationError,
)
from .base.core_new import (
    BusinessLogicError,
    ErrorFactory,
    InfrastructureError,
    MindFlowError,
    NetworkError,
    ResourceError,
    SystemError,
    TimeoutError,
)
from .external import (
    IntegrationError,
    NetworkError,
    ThirdPartyAPIError,
)
from .infrastructure import (
    CircuitOpenError,
    MiddlewareError,
    MonitoringError,
)
from .infrastructure import (
    ConfigurationError as InfraConfigurationError,
)
from .orchestrator import (
    DecompositionError,
    DependencyError,
    GraphExecutionError,
    SchedulingError,
)
from .runtime import (
    ExecutionError,
    ProviderError,
    ResourceError,
    TimeoutError,
)
from .storage import (
    CacheError as StorageCacheError,
)
from .storage import (
    ConnectionError,
    DatabaseError,
    MigrationError,
)
from .storage import (
    VectorStoreError as StorageVectorStoreError,
)
from .validation import (
    SanitizationError,
    SchemaError,
    SecurityValidationError,
)

# Re-export commonly used exceptions
__all__ = [
    # Base
    "MindFlowError",
    "SystemError",
    "BusinessLogicError",
    "InfrastructureError",
    "NetworkError",
    "TimeoutError",
    "ResourceError",
    "ErrorFactory",
    
    # Agents
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
    
    # API
    "AuthenticationError",
    "AuthorizationError",
    "RequestValidationError",
    "StreamingError",
    "RoutingError",
    
    # Storage
    "DatabaseError",
    "ConnectionError",
    "MigrationError",
    
    # Orchestrator
    "DecompositionError",
    "SchedulingError",
    "GraphExecutionError",
    "DependencyError",
    
    # Runtime
    "ProviderError",
    "ExecutionError",
    "TimeoutError",
    "ResourceError",
    
    # Infrastructure
    "CircuitOpenError",
    "MonitoringError",
    "MiddlewareError",
    
    # Validation
    "SchemaError",
    "SanitizationError",
    "SecurityValidationError",
    
    # External
    "NetworkError",
    "ThirdPartyAPIError",
    "IntegrationError",
]
