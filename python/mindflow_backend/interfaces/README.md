# Global Interfaces for MindFlow Backend

This directory contains the centralized interface definitions for the entire MindFlow system, providing consistency, testability, and maintainability across all components.

## Overview

The interface system solves the problem of fragmented interfaces that were previously scattered across multiple domain-specific directories. Now all interfaces are centralized in a single location with a clear hierarchical organization.

## Structure

```
interfaces/
├── __init__.py                 # Global exports and base interfaces
├── core/                       # Fundamental interfaces for all components
│   ├── base.py                # BaseComponentInterface and composites
│   ├── lifecycle.py           # Lifecycle management
│   ├── config.py              # Configuration management
│   └── logging.py             # Standardized logging
├── agents/                     # Agent-specific interfaces
│   ├── core_personality.py    # Core agent personality contract
│   ├── streaming.py           # Streaming operations
│   ├── session.py             # Session management
│   ├── context.py             # Context retrieval and storage
│   ├── specialist.py          # Specialist selection
│   ├── personality.py          # Personality management
│   ├── orchestrator.py        # Orchestration contracts
│   └── enhanced/              # Enhanced agent contracts
├── services/                   # Service layer interfaces
│   ├── base.py                # Base service contracts
│   ├── communication.py       # Service communication
│   ├── context.py             # Context services
│   ├── core.py                # Core service operations
│   ├── monitoring.py          # Monitoring and metrics
│   ├── orchestration.py       # Orchestration services
│   ├── storage.py             # Storage services
│   ├── cache.py               # Caching services
│   └── decomposition.py       # Task decomposition services
├── api/                        # API layer interfaces
│   ├── controllers.py         # Controller contracts
│   ├── services.py            # API service contracts
│   ├── middleware.py          # Middleware contracts
│   └── routing.py             # Routing contracts
├── infrastructure/             # Infrastructure components
│   ├── grpc.py                # gRPC client/server contracts
│   ├── database.py            # Database interfaces
│   ├── cache.py               # Cache interfaces
│   ├── messaging.py           # Message queue interfaces
│   ├── storage.py             # Storage interfaces
│   ├── config.py              # Configuration storage
│   ├── load_balancing.py      # Load balancing strategies
│   └── compression.py         # Compression strategies
└── tools/                      # Tool interfaces for agents
    ├── base.py                # Base tool interface
    ├── async_tools.py         # Async tool interface
    ├── stateful.py            # Stateful tool interface
    ├── filesystem.py          # Filesystem tools
    ├── system.py              # System tools
    └── web.py                 # Web tools
```

## Core Interface Hierarchy

### Base Interfaces

All components implement one or more base interfaces:

```python
# Base interface for ALL components
BaseComponentInterface

# Composite interfaces for specific component types
ServiceInterface      # Extends Base + Lifecycle + Configurable + Loggable
AgentInterface        # Extends Base + Configurable + Loggable
ToolInterface         # Extends Base + Loggable
InfrastructureInterface # Extends Base + Lifecycle + Configurable + Loggable
```

### Interface Composition

The interface system uses composition to provide flexible capabilities:

```python
# Example: A service component
class MyService(ServiceInterface):
    # Implements: BaseComponentInterface + LifecycleInterface + 
    #            ConfigurableInterface + LoggableInterface
    pass

# Example: An agent component  
class MyAgent(AgentInterface):
    # Implements: BaseComponentInterface + ConfigurableInterface + 
    #            LoggableInterface
    pass
```

## Interface Categories

### Core Interfaces
- **BaseComponentInterface**: Foundation for all components
- **LifecycleInterface**: Initialization, shutdown, health checks
- **ConfigurableInterface**: Dynamic configuration management
- **LoggableInterface**: Standardized logging with context

### Agent Interfaces
- **CorePersonalityContract**: Base contract for all agents
- **StreamingContract**: Real-time streaming capabilities
- **SessionManagerContract**: Session lifecycle management
- **Enhanced Agents**: Specialized contracts (Coder, Analyst, Researcher, Reviewer)

### Service Interfaces
- **BaseServiceInterface**: Foundation for all services
- **CommunicationServiceInterface**: Inter-service communication
- **MonitoringServiceInterface**: Health monitoring and metrics
- **OrchestrationServiceInterface**: Task orchestration

### API Interfaces
- **Controller Interfaces**: HTTP controller contracts
- **Service Interfaces**: API service layer contracts
- **Middleware Interfaces**: Request/response processing

### Infrastructure Interfaces
- **GrpcClient/GrpcServer**: gRPC communication
- **Database Interface**: Database operations
- **Cache Interface**: Caching strategies
- **MessageQueue Interface**: Asynchronous messaging

### Tool Interfaces
- **ToolInterface**: Base contract for all tools
- **AsyncToolInterface**: Asynchronous tool operations
- **StatefulToolInterface**: Tools that maintain state
- **Specialized Tools**: Filesystem, system, web tools

## Usage Patterns

### Implementing an Interface

```python
from mindflow_backend.interfaces import ServiceInterface
from mindflow_backend.interfaces.core import ComponentStatus

class DatabaseService(ServiceInterface):
    def __init__(self):
        self._name = "database_service"
        self._version = "1.0.0"
        self._status = ComponentStatus.INITIALIZING
    
    def get_name(self) -> str:
        return self._name
    
    async def initialize(self) -> None:
        # Initialize database connections
        self.set_status(ComponentStatus.RUNNING)
    
    async def process_request(self, request: Any) -> Any:
        # Process database request
        return result
```

### Using an Interface

```python
from mindflow_backend.interfaces import ServiceInterface

async def handle_request(service: ServiceInterface, request: Any):
    if not service.is_healthy():
        raise ServiceUnavailableError()
    
    result = await service.process_request(request)
    return result
```

### Interface Composition

```python
from mindflow_backend.interfaces.core import (
    BaseComponentInterface,
    ConfigurableInterface,
    LoggableInterface
)

class CustomComponent(BaseComponentInterface, ConfigurableInterface, LoggableInterface):
    # Implement required methods from all interfaces
    pass
```

## Migration Guide

### From Old Interface Locations

Old imports:
```python
# Old scattered imports
from mindflow_backend.agents.interfaces.core.streaming import StreamingContract
from mindflow_backend.services.interfaces.base_interfaces import BaseServiceInterface
from mindflow_backend.grpc.interfaces.client import GrpcClient
```

New imports:
```python
# New centralized imports
from mindflow_backend.interfaces.agents import StreamingContract
from mindflow_backend.interfaces.services import BaseServiceInterface  
from mindflow_backend.interfaces.infrastructure import GrpcClient
```

### Forward Compatibility

During migration, forward compatibility aliases are maintained:

```python
# Old location still works (temporary)
from mindflow_backend.agents.interfaces.core.streaming import StreamingContract
# Actually imports from new location:
# from mindflow_backend.interfaces.agents.streaming import StreamingContract
```

## Benefits

### 1. Centralization
- All interfaces in one location
- Easy discovery and usage
- Consistent patterns

### 2. Consistency
- Standardized naming conventions
- Common base interfaces
- Unified documentation

### 3. Maintainability
- Single place for interface updates
- Clear dependency relationships
- Simplified testing

### 4. Extensibility
- Easy to add new interfaces
- Clear inheritance patterns
- Composable capabilities

### 5. Type Safety
- All interfaces use `@runtime_checkable`
- Strong typing with Protocol
- IDE support and validation

## Best Practices

### 1. Interface Design
- Keep interfaces focused and minimal
- Use composition over deep inheritance
- Provide comprehensive docstrings

### 2. Implementation
- Always implement all required methods
- Use proper error handling
- Follow logging standards

### 3. Testing
- Test interface compliance
- Mock interfaces for unit tests
- Validate type checking

### 4. Documentation
- Document interface purpose
- Provide usage examples
- Explain implementation requirements

## Validation

The interface system includes validation tools:

```python
from mindflow_backend.interfaces.core import validate_interface_implementation

# Validate that a class implements an interface correctly
is_valid = validate_interface_implementation(MyComponent, ServiceInterface)
```

## Contributing

When adding new interfaces:

1. Choose the appropriate category directory
2. Follow naming conventions (`XxxInterface` or `XxxContract`)
3. Use `@runtime_checkable` with `Protocol`
4. Provide comprehensive docstrings
5. Add to appropriate `__init__.py` exports
6. Update this documentation
7. Add tests for interface compliance

## Future Roadmap

- [ ] Interface validation tools
- [ ] Auto-generation of interface documentation
- [ ] Interface versioning strategy
- [ ] Performance optimization for interface checks
- [ ] Integration with external interface definition languages
