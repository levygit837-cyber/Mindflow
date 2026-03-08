"""Exception definitions for MindFlow.

Centralized exception hierarchy for better error handling
and debugging across the system.
"""

# Base exceptions
from .base import (
    MindFlowError, 
    SystemError, 
    BusinessLogicError,
    InfrastructureError,
    NetworkError,
    TimeoutError,
    ResourceError,
    ErrorFactory,
)

# Domain-specific exceptions
from .agents import (
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
)

from .api import (
    AuthenticationError,
    AuthorizationError,
    RequestValidationError,
    StreamingError,
    RoutingError,
)

from .storage import (
    DatabaseError,
    ConnectionError,
    MigrationError,
    VectorStoreError as StorageVectorStoreError,
    CacheError as StorageCacheError,
)

from .orchestrator import (
    DecompositionError,
    SchedulingError,
    GraphExecutionError,
    DependencyError,
)

from .runtime import (
    ProviderError,
    ExecutionError,
    TimeoutError,
    ResourceError,
)

from .infrastructure import (
    CircuitOpenError,
    ConfigurationError as InfraConfigurationError,
    MonitoringError,
    MiddlewareError,
)

from .validation import (
    SchemaError,
    SanitizationError,
    SecurityValidationError,
)

from .external import (
    NetworkError,
    ThirdPartyAPIError,
    IntegrationError,
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
