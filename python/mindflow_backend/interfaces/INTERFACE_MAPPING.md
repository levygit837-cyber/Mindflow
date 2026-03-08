# Interface Migration Mapping

This document maps all existing interfaces to their new locations in the centralized `/interfaces/` structure.

## Current → New Structure Mapping

### Core Interfaces (Already Mapped)
| Current Location | Interface | New Location | Status |
|------------------|-----------|--------------|---------|
| N/A | BaseComponentInterface | `/interfaces/core/base.py` | ✅ Created |
| N/A | LifecycleInterface | `/interfaces/core/lifecycle.py` | ✅ Created |
| N/A | ConfigurableInterface | `/interfaces/core/config.py` | ✅ Created |
| N/A | LoggableInterface | `/interfaces/core/logging.py` | ✅ Created |
| N/A | ServiceInterface | `/interfaces/core/base.py` | ✅ Created |
| N/A | AgentInterface | `/interfaces/core/base.py` | ✅ Created |
| N/A | ToolInterface | `/interfaces/core/base.py` | ✅ Created |
| N/A | InfrastructureInterface | `/interfaces/core/base.py` | ✅ Created |

### Agents Interfaces Mapping
| Current Location | Interface | New Location | Migration Priority |
|------------------|-----------|--------------|-------------------|
| `/agents/interfaces/core/streaming.py` | StreamingContract | `/interfaces/agents/streaming.py` | High |
| `/agents/interfaces/core/session_manager.py` | SessionManagerContract | `/interfaces/agents/session.py` | High |
| `/agents/interfaces/core/context.py` | ContextRetriever, VectorStore, Cache | `/interfaces/agents/context.py` | High |
| `/agents/interfaces/core/specialists.py` | SpecialistSelector, RuleEngine | `/interfaces/agents/specialist.py` | High |
| `/agents/interfaces/core/runtime.py` | AgentRuntime, AgentFactory, ContentAnalyzer, ResultParser | `/interfaces/agents/runtime.py` | Medium |
| `/agents/interfaces/core/personality.py` | PersonalitySelector | `/interfaces/agents/personality.py` | High |
| `/agents/interfaces/core/logging.py` | Logger, AgentLogBus | `/interfaces/agents/logging.py` | Medium |
| `/agents/interfaces/agents/core_personality.py` | CorePersonalityContract | `/interfaces/agents/core_personality.py` | High |
| `/agents/interfaces/agents/enhanced_coder.py` | EnhancedCoder | `/interfaces/agents/enhanced/coder.py` | Medium |
| `/agents/interfaces/agents/enhanced_analyst.py` | EnhancedAnalyst | `/interfaces/agents/enhanced/analyst.py` | Medium |
| `/agents/interfaces/agents/enhanced_researcher.py` | EnhancedResearcher | `/interfaces/agents/enhanced/researcher.py` | Medium |
| `/agents/interfaces/agents/enhanced_reviewer.py` | EnhancedReviewer | `/interfaces/agents/enhanced/reviewer.py` | Medium |
| `/agents/interfaces/agents/task_rag_agent.py` | TaskRagAgent | `/interfaces/agents/rag.py` | Low |
| `/agents/interfaces/orchestrator/core.py` | OrchestratorCoreContract | `/interfaces/agents/orchestrator.py` | High |
| `/agents/interfaces/orchestrator/personality.py` | PersonalityManagerContract | `/interfaces/agents/orchestrator.py` | High |
| `/agents/interfaces/orchestrator/delegation_manager.py` | DelegationManagerContract | `/interfaces/agents/orchestrator.py` | High |
| `/agents/interfaces/orchestrator/specialists.py` | SpecialistManagerContract | `/interfaces/agents/orchestrator.py` | High |

### Services Interfaces Mapping
| Current Location | Interface | New Location | Migration Priority |
|------------------|-----------|--------------|-------------------|
| `/services/interfaces/base_interfaces.py` | BaseServiceInterface | `/interfaces/services/base.py` | High |
| `/services/interfaces/base_interfaces.py` | ServiceLifecycleInterface | `/interfaces/services/lifecycle.py` | High |
| `/services/interfaces/base_interfaces.py` | CacheableServiceInterface | `/interfaces/services/cache.py` | Medium |
| `/services/interfaces/base_interfaces.py` | ConfigurableServiceInterface | `/interfaces/services/config.py` | Medium |
| `/services/interfaces/communication_interfaces.py` | CommunicationServiceInterface | `/interfaces/services/communication.py` | High |
| `/services/interfaces/context_interfaces.py` | ContextServiceInterface | `/interfaces/services/context.py` | High |
| `/services/interfaces/core_interfaces.py` | CoreServiceInterface | `/interfaces/services/core.py` | High |
| `/services/interfaces/monitoring_interfaces.py` | MonitoringServiceInterface | `/interfaces/services/monitoring.py` | High |
| `/services/interfaces/orchestration_interfaces.py` | OrchestrationServiceInterface | `/interfaces/services/orchestration.py` | High |

### API Interfaces Mapping
| Current Location | Interface | New Location | Migration Priority |
|------------------|-----------|--------------|-------------------|
| `/api/interfaces/controller_interface.py` | AgentControllerInterface | `/interfaces/api/controllers.py` | High |
| `/api/interfaces/controller_interface.py` | SessionControllerInterface | `/interfaces/api/controllers.py` | High |
| `/api/interfaces/controller_interface.py` | OrchestrationControllerInterface | `/interfaces/api/controllers.py` | High |
| `/api/interfaces/controller_interface.py` | ProviderControllerInterface | `/interfaces/api/controllers.py` | Medium |
| `/api/interfaces/controller_interface.py` | MemoryControllerInterface | `/interfaces/api/controllers.py` | Medium |
| `/api/interfaces/controller_interface.py` | BaseControllerInterface | `/interfaces/api/controllers.py` | High |
| `/api/interfaces/service_interface.py` | AgentServiceInterface | `/interfaces/api/services.py` | High |
| `/api/interfaces/service_interface.py` | SessionServiceInterface | `/interfaces/api/services.py` | High |
| `/api/interfaces/service_interface.py` | OrchestrationServiceInterface | `/interfaces/api/services.py` | High |
| `/api/interfaces/service_interface.py` | ProviderServiceInterface | `/interfaces/api/services.py` | Medium |
| `/api/interfaces/service_interface.py` | MemoryServiceInterface | `/interfaces/api/services.py` | Medium |
| `/api/interfaces/service_interface.py` | BaseServiceInterface | `/interfaces/api/services.py` | High |

### Infrastructure Interfaces Mapping
| Current Location | Interface | New Location | Migration Priority |
|------------------|-----------|--------------|-------------------|
| `/grpc/interfaces/client.py` | GrpcClient | `/interfaces/infrastructure/grpc.py` | High |
| `/grpc/interfaces/server.py` | GrpcServer | `/interfaces/infrastructure/grpc.py` | High |
| `/grpc/config/dynamic/storage.py` | ConfigStorage | `/interfaces/infrastructure/config.py` | Medium |
| `/grpc/config/profiles/__init__.py` | EnvironmentProfile | `/interfaces/infrastructure/config.py` | Medium |
| `/grpc/performance/load_balancing/strategies.py` | LoadBalancingStrategy | `/interfaces/infrastructure/load_balancing.py` | Low |
| `/grpc/performance/compression/strategies.py` | CompressionStrategy | `/interfaces/infrastructure/compression.py` | Low |

### Tools Interfaces Mapping
| Current Location | Interface | New Location | Migration Priority |
|------------------|-----------|--------------|-------------------|
| `/agents/tools/base/tool_interface.py` | ToolInterface | `/interfaces/tools/base.py` | High |
| `/agents/tools/base/tool_interface.py` | AsyncToolInterface | `/interfaces/tools/async.py` | High |
| `/agents/tools/base/tool_interface.py` | StatefulToolInterface | `/interfaces/tools/stateful.py` | High |
| `/agents/tools/filesystem/search_tools.py` | GrepSearchTool, GlobSearchTool, FindFilesTool | `/interfaces/tools/filesystem.py` | Medium |
| `/agents/tools/filesystem/file_operations.py` | FileReadTool, FileWriteTool, FileEditTool, etc. | `/interfaces/tools/filesystem.py` | Medium |
| `/agents/tools/system/sandbox.py` | MindFlowSandbox | `/interfaces/tools/system.py` | Medium |
| `/agents/tools/system/process_manager.py` | ProcessManagerTool | `/interfaces/tools/system.py` | Medium |
| `/agents/tools/web/api_client.py` | ApiClientTool | `/interfaces/tools/web.py` | Medium |
| `/agents/tools/web/http_client.py` | HttpClientTool | `/interfaces/tools/web.py` | Medium |
| `/agents/tools/web/browser_search.py` | BrowserSearchTool | `/interfaces/tools/web.py` | Medium |

### Decomposition Interfaces Mapping
| Current Location | Interface | New Location | Migration Priority |
|------------------|-----------|--------------|-------------------|
| `/decomposition/engine.py` | TaskDecomposer, TaskResolver, TaskScheduler, TaskSynthesizerBase | `/interfaces/services/decomposition.py` | High |
| `/schemas/orchestration/decomposition/decomposition_v2.py` | MainTaskContract, SubTaskContract, SynthesisContract | `/interfaces/services/decomposition.py` | High |

### Storage Interfaces Mapping
| Current Location | Interface | New Location | Migration Priority |
|------------------|-----------|--------------|-------------------|
| `/storage/kuzudb/vector_store.py` | VectorStore implementations | `/interfaces/infrastructure/storage.py` | Medium |
| `/agents/context/vector_store.py` | VectorStore implementations | `/interfaces/infrastructure/storage.py` | Medium |

## Migration Strategy

### Phase 1: High Priority Interfaces (Week 1)
- Core agent interfaces (streaming, session, context, specialist, personality)
- Core service interfaces (base, communication, context, monitoring, orchestration)
- API controller and service interfaces
- gRPC interfaces
- Base tool interfaces

### Phase 2: Medium Priority Interfaces (Week 2)
- Enhanced agent interfaces
- Runtime and logging interfaces
- Infrastructure configuration interfaces
- Filesystem and system tools
- Web tools
- Storage interfaces

### Phase 3: Low Priority Interfaces (Week 3)
- Performance optimization interfaces
- Advanced tool interfaces
- Legacy interfaces (for backward compatibility)

## Forward Compatibility Aliases

During migration, we'll maintain backward compatibility by creating aliases in the old locations:

```python
# Example: /agents/interfaces/core/streaming.py
from mindflow_backend.interfaces.agents.streaming import StreamingContract

# Maintain backward compatibility
__all__ = ["StreamingContract"]
```

## Validation Checklist

- [ ] All interfaces mapped to new locations
- [ ] Dependencies identified and documented
- [ ] Forward compatibility aliases created
- [ ] Import paths updated in critical modules
- [ ] Tests updated to use new interfaces
- [ ] Documentation updated with new structure
- [ ] Performance impact assessed
- [ ] Migration scripts created and tested

## Risk Assessment

### High Risk Interfaces
- **StreamingContract**: Used extensively across the system
- **SessionManagerContract**: Critical for session management
- **OrchestratorCoreContract**: Core orchestration logic

### Medium Risk Interfaces
- **Enhanced Agent Contracts**: Used by specialized agents
- **Service Interfaces**: Backend service communication
- **Tool Interfaces**: Agent tool capabilities

### Low Risk Interfaces
- **Infrastructure Interfaces**: Internal system components
- **Performance Interfaces**: Optimization features
- **Legacy Interfaces**: Maintained for compatibility

## Success Metrics

- [ ] 100% of interfaces successfully migrated
- [ ] Zero breaking changes in public APIs
- [ ] All tests passing with new interfaces
- [ ] Performance maintained or improved
- [ ] Documentation complete and accurate
- [ ] Developer feedback positive
