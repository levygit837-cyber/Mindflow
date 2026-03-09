# Documentação da Estrutura do Projeto MindFlow Backend
==================================================
# Estrutura de Diretórios

## Diretórios Mapeados

@python/agents
@python/agents/context
@python/agents/core
@python/agents/interfaces
@python/agents/interfaces/agents
@python/agents/interfaces/api
@python/agents/interfaces/core
@python/agents/interfaces/errors
@python/agents/interfaces/errors/recovery
@python/agents/interfaces/infrastructure
@python/agents/interfaces/orchestrator
@python/agents/prompts
@python/agents/prompts/backup
@python/agents/prompts/composite
@python/agents/prompts/core
@python/agents/prompts/specialized
@python/agents/research
@python/agents/specialists
@python/agents/tools
@python/agents/tools/ai
@python/agents/tools/base
@python/agents/tools/code
@python/agents/tools/data
@python/agents/tools/filesystem
@python/agents/tools/integration
@python/agents/tools/research
@python/agents/tools/system
@python/agents/tools/web
@python/api
@python/api/controllers
@python/api/interfaces
@python/api/middleware
@python/api/schemas
@python/api/services
@python/api/v1
@python/chains
@python/chains/base
@python/chains/builders
@python/chains/managers
@python/chains/templates
@python/config
@python/decomposition
@python/decomposition/context
@python/decomposition/pipeline
@python/decomposition/scoring
@python/docs
@python/examples
@python/exceptions
@python/exceptions/agents
@python/exceptions/api
@python/exceptions/base
@python/exceptions/external
@python/exceptions/infrastructure
@python/exceptions/orchestrator
@python/exceptions/runtime
@python/exceptions/storage
@python/exceptions/validation
@python/graphs
@python/graphs/base
@python/graphs/chains
@python/graphs/implementations
@python/graphs/implementations/orchestrator
@python/graphs/implementations/specialized
@python/graphs/implementations/workflow
@python/grpc
@python/grpc/config
@python/grpc/config/dynamic
@python/grpc/config/features
@python/grpc/config/profiles
@python/grpc/generated
@python/grpc/interceptors
@python/grpc/interfaces
@python/grpc/monitoring
@python/grpc/performance
@python/grpc/performance/caching
@python/grpc/performance/compression
@python/grpc/performance/load_balancing
@python/grpc/performance/monitoring
@python/grpc/performance/optimization
@python/grpc/performance/pooling
@python/grpc/proto
@python/grpc/resilience
@python/grpc/services
@python/infra
@python/infra/api
@python/infra/cache
@python/infra/config
@python/infra/database
@python/infra/logging
@python/infra/middleware
@python/infra/monitoring
@python/infra/performance
@python/infra/security
@python/infra/tracing
@python/interfaces
@python/interfaces/agents
@python/interfaces/api
@python/interfaces/core
@python/interfaces/infrastructure
@python/interfaces/services
@python/interfaces/tools
@python/memory
@python/memory/api
@python/memory/core
@python/memory/embeddings
@python/memory/retrieval
@python/memory/storage
@python/memory/windows
@python/memory_backup
@python/nodes
@python/nodes/agents
@python/nodes/base
@python/nodes/control
@python/nodes/implementations
@python/nodes/implementations/control
@python/nodes/implementations/integration
@python/nodes/implementations/io
@python/nodes/implementations/orchestrator
@python/nodes/implementations/processing
@python/nodes/orchestrator
@python/orchestrator
@python/orchestrator/context
@python/orchestrator/decomposition
@python/orchestrator/delegation
@python/orchestrator/routing
@python/runtime
@python/runtime/agents
@python/runtime/core
@python/runtime/execution
@python/runtime/monitoring
@python/runtime/processing
@python/runtime/providers
@python/runtime/registry
@python/runtime/streaming
@python/runtime/utils
@python/schemas
@python/schemas/agents
@python/schemas/chat
@python/schemas/config
@python/schemas/core
@python/schemas/errors
@python/schemas/grpc
@python/schemas/orchestration
@python/schemas/orchestration/decomposition
@python/schemas/session
@python/schemas/tools
@python/services
@python/services/communication
@python/services/context
@python/services/core
@python/services/interfaces
@python/services/monitoring
@python/services/orchestration
@python/storage
@python/storage/kuzudb
@python/storage/langgraph
@python/storage/postgresql
@python/storage/postgresql/migrations
@python/storage/postgresql/migrations/versions
@python/storage/utils
@python/tools_backup
@python/tools_backup/ai
@python/tools_backup/core
@python/tools_backup/data
@python/tools_backup/filesystem
@python/tools_backup/integration
@python/tools_backup/system
@python/tools_backup/web
@python/utils
@python/utils/collections
@python/utils/core
@python/utils/error_handling
@python/utils/formatting
@python/utils/monitoring
@python/utils/network
@python/utils/performance
@python/utils/security
@python/utils/validation
@python/workers
@python/workers/agents
@python/workers/archive
@python/workers/archive/legacy_rq_workers_20260305_163354
@python/workers/base
@python/workers/config
@python/workers/infrastructure
@python/workers/research
@python/workers/system
@python/workers/tasks

# Arquivos Python

## Arquivos Mapeados por Diretório


### agents

@python/agents/__init__.py
@python/agents/_base.py
@python/agents/_registry.py
@python/agents/node_registry.py
@python/agents/output_categorizer.py
@python/agents/session_review_agent.py
@python/agents/stream_event_queue.py
@python/agents/tools.py

### agents/context

@python/agents/context/__init__.py
@python/agents/context/analyzer.py
@python/agents/context/cache.py
@python/agents/context/retriever.py
@python/agents/context/vector_store.py

### agents/core

@python/agents/core/container.py
@python/agents/core/exceptions.py
@python/agents/core/initialization.py
@python/agents/core/interfaces.py

### agents/interfaces

@python/agents/interfaces/__init__.py
@python/agents/interfaces/validate_contracts.py

### agents/interfaces/agents

@python/agents/interfaces/agents/__init__.py
@python/agents/interfaces/agents/analyst.py
@python/agents/interfaces/agents/coder.py
@python/agents/interfaces/agents/core_personality.py
@python/agents/interfaces/agents/enhanced_analyst.py
@python/agents/interfaces/agents/enhanced_coder.py
@python/agents/interfaces/agents/enhanced_reviewer.py
@python/agents/interfaces/agents/researcher.py
@python/agents/interfaces/agents/reviewer.py
@python/agents/interfaces/agents/task_rag_agent.py

### agents/interfaces/api

@python/agents/interfaces/api/__init__.py
@python/agents/interfaces/api/agent.py
@python/agents/interfaces/api/chat.py

### agents/interfaces/core

@python/agents/interfaces/core/__init__.py
@python/agents/interfaces/core/context.py
@python/agents/interfaces/core/logging.py
@python/agents/interfaces/core/personality.py
@python/agents/interfaces/core/runtime.py
@python/agents/interfaces/core/session_manager.py
@python/agents/interfaces/core/specialists.py
@python/agents/interfaces/core/streaming.py

### agents/interfaces/errors

@python/agents/interfaces/errors/__init__.py
@python/agents/interfaces/errors/api_error_handler.py
@python/agents/interfaces/errors/base_error_handler.py
@python/agents/interfaces/errors/external_error_handler.py
@python/agents/interfaces/errors/infrastructure_error_handler.py
@python/agents/interfaces/errors/storage_error_handler.py
@python/agents/interfaces/errors/validation_error_handler.py

### agents/interfaces/errors/recovery

@python/agents/interfaces/errors/recovery/__init__.py
@python/agents/interfaces/errors/recovery/circuit_breaker.py
@python/agents/interfaces/errors/recovery/error_recovery.py
@python/agents/interfaces/errors/recovery/fallback_handler.py
@python/agents/interfaces/errors/recovery/retry_strategy.py

### agents/interfaces/infrastructure

@python/agents/interfaces/infrastructure/__init__.py
@python/agents/interfaces/infrastructure/backend.py

### agents/interfaces/orchestrator

@python/agents/interfaces/orchestrator/__init__.py
@python/agents/interfaces/orchestrator/core.py
@python/agents/interfaces/orchestrator/delegation_manager.py
@python/agents/interfaces/orchestrator/personality.py
@python/agents/interfaces/orchestrator/resolver.py
@python/agents/interfaces/orchestrator/scheduler.py
@python/agents/interfaces/orchestrator/scorer.py
@python/agents/interfaces/orchestrator/specialists.py
@python/agents/interfaces/orchestrator/synthesizer.py
@python/agents/interfaces/orchestrator/tasker.py

### agents/prompts

@python/agents/prompts/__init__.py
@python/agents/prompts/base.py

### agents/prompts/backup

@python/agents/prompts/backup/analyst.py
@python/agents/prompts/backup/arch_tech.py
@python/agents/prompts/backup/coder.py
@python/agents/prompts/backup/orchestrator.py
@python/agents/prompts/backup/researcher.py

### agents/prompts/composite

@python/agents/prompts/composite/__init__.py
@python/agents/prompts/composite/full_analyst.py
@python/agents/prompts/composite/full_coder.py
@python/agents/prompts/composite/full_orchestrator.py

### agents/prompts/core

@python/agents/prompts/core/__init__.py
@python/agents/prompts/core/analyst.py
@python/agents/prompts/core/coder.py
@python/agents/prompts/core/orchestrator.py
@python/agents/prompts/core/researcher.py

### agents/prompts/specialized

@python/agents/prompts/specialized/__init__.py
@python/agents/prompts/specialized/agent_delegation.py
@python/agents/prompts/specialized/architecture_review.py
@python/agents/prompts/specialized/brainstorming.py
@python/agents/prompts/specialized/code_review.py
@python/agents/prompts/specialized/context_governance.py
@python/agents/prompts/specialized/deep_analysis.py
@python/agents/prompts/specialized/orchestrator_chains.py
@python/agents/prompts/specialized/orchestrator_reflection.py
@python/agents/prompts/specialized/planning.py
@python/agents/prompts/specialized/security_analysis.py
@python/agents/prompts/specialized/tasker.py

### agents/research

@python/agents/research/__init__.py
@python/agents/research/action_trail.py
@python/agents/research/enhanced_query_planner.py
@python/agents/research/enhanced_researcher.py
@python/agents/research/pinchtab_service.py
@python/agents/research/pitchtab_monitor.py
@python/agents/research/query_engine.py
@python/agents/research/result_synthesizer.py
@python/agents/research/source_trust_engine.py

### agents/specialists

@python/agents/specialists/__init__.py
@python/agents/specialists/cache.py
@python/agents/specialists/configuration.py
@python/agents/specialists/dynamic_prompts.py
@python/agents/specialists/factories.py
@python/agents/specialists/rule_engine.py
@python/agents/specialists/selector.py
@python/agents/specialists/specialists.py

### agents/tools

@python/agents/tools/__init__.py
@python/agents/tools/browser_search.py
@python/agents/tools/sandbox.py
@python/agents/tools/search_web.py

### agents/tools/ai

@python/agents/tools/ai/__init__.py
@python/agents/tools/ai/model_tools.py

### agents/tools/base

@python/agents/tools/base/__init__.py
@python/agents/tools/base/tool_interface.py
@python/agents/tools/base/tool_registry.py
@python/agents/tools/base/tool_schemas.py

### agents/tools/code

@python/agents/tools/code/__init__.py

### agents/tools/data

@python/agents/tools/data/__init__.py
@python/agents/tools/data/data_tools.py

### agents/tools/filesystem

@python/agents/tools/filesystem/__init__.py
@python/agents/tools/filesystem/file_operations.py
@python/agents/tools/filesystem/operations.py
@python/agents/tools/filesystem/search_tools.py

### agents/tools/integration

@python/agents/tools/integration/__init__.py
@python/agents/tools/integration/integration_tools.py

### agents/tools/research

@python/agents/tools/research/__init__.py

### agents/tools/system

@python/agents/tools/system/__init__.py
@python/agents/tools/system/process_manager.py
@python/agents/tools/system/resource_monitor.py
@python/agents/tools/system/sandbox.py
@python/agents/tools/system/shell_executor.py
@python/agents/tools/system/system_info.py

### agents/tools/web

@python/agents/tools/web/__init__.py
@python/agents/tools/web/api_client.py
@python/agents/tools/web/browser_search.py
@python/agents/tools/web/http_client.py
@python/agents/tools/web/web_scraper.py

### api

@python/api/__init__.py
@python/api/docs.py
@python/api/router.py

### api/controllers

@python/api/controllers/__init__.py
@python/api/controllers/agent_controller.py
@python/api/controllers/base_controller.py
@python/api/controllers/orchestration_controller.py
@python/api/controllers/provider_controller.py
@python/api/controllers/session_controller.py

### api/interfaces

@python/api/interfaces/__init__.py
@python/api/interfaces/controller_interface.py
@python/api/interfaces/service_interface.py

### api/middleware

@python/api/middleware/__init__.py
@python/api/middleware/caching.py
@python/api/middleware/error_handler.py
@python/api/middleware/performance.py
@python/api/middleware/validation.py

### api/schemas

@python/api/schemas/__init__.py
@python/api/schemas/common.py
@python/api/schemas/requests.py
@python/api/schemas/responses.py

### api/services

@python/api/services/__init__.py
@python/api/services/agent_service.py
@python/api/services/orchestration_service.py
@python/api/services/provider_service.py
@python/api/services/session_service.py

### api/v1

@python/api/v1/__init__.py
@python/api/v1/agent.py
@python/api/v1/chat.py
@python/api/v1/config.py
@python/api/v1/health.py
@python/api/v1/legacy.py
@python/api/v1/metrics.py
@python/api/v1/monitoring.py
@python/api/v1/orchestration.py
@python/api/v1/performance.py
@python/api/v1/providers.py
@python/api/v1/resilience.py

### chains

@python/chains/__init__.py
@python/chains/catalog.py

### chains/base

@python/chains/base/__init__.py
@python/chains/base/chain.py
@python/chains/base/executor.py
@python/chains/base/step.py
@python/chains/base/types.py

### chains/builders

@python/chains/builders/__init__.py
@python/chains/builders/conditional_builder.py
@python/chains/builders/sequential_builder.py

### chains/managers

@python/chains/managers/__init__.py
@python/chains/managers/chain_manager.py

### chains/templates

@python/chains/templates/__init__.py
@python/chains/templates/coding_chain.py
@python/chains/templates/coding_task_chain.py
@python/chains/templates/research_chain.py

### config

@python/config/__init__.py
@python/config/agents.py
@python/config/specialist_rules.py

### decomposition

@python/decomposition/__init__.py
@python/decomposition/engine.py

### decomposition/context

@python/decomposition/context/__init__.py

### decomposition/pipeline

@python/decomposition/pipeline/__init__.py
@python/decomposition/pipeline/resolver.py
@python/decomposition/pipeline/scheduler.py
@python/decomposition/pipeline/synthesizer.py
@python/decomposition/pipeline/tasker.py

### decomposition/scoring

@python/decomposition/scoring/__init__.py

### examples

@python/examples/enhanced_exceptions_demo.py
@python/examples/error_handling_demo.py
@python/examples/error_handling_integration.py
@python/examples/error_handling_summary.py
@python/examples/semantic_context_examples.py
@python/examples/service_with_error_handling.py

### exceptions

@python/exceptions/__init__.py
@python/exceptions/agents.py

### exceptions/agents

@python/exceptions/agents/__init__.py
@python/exceptions/agents/system.py

### exceptions/api

@python/exceptions/api/__init__.py
@python/exceptions/api/auth.py
@python/exceptions/api/routing.py
@python/exceptions/api/streaming.py
@python/exceptions/api/validation.py

### exceptions/base

@python/exceptions/base/__init__.py
@python/exceptions/base/business.py
@python/exceptions/base/core.py
@python/exceptions/base/core_simple.py
@python/exceptions/base/patterns.py

### exceptions/external

@python/exceptions/external/__init__.py
@python/exceptions/external/integration.py
@python/exceptions/external/network.py
@python/exceptions/external/third_party.py

### exceptions/infrastructure

@python/exceptions/infrastructure/__init__.py
@python/exceptions/infrastructure/configuration.py
@python/exceptions/infrastructure/middleware.py
@python/exceptions/infrastructure/monitoring.py
@python/exceptions/infrastructure/resilience.py

### exceptions/orchestrator

@python/exceptions/orchestrator/__init__.py
@python/exceptions/orchestrator/decomposition.py
@python/exceptions/orchestrator/dependency.py
@python/exceptions/orchestrator/graph.py
@python/exceptions/orchestrator/scheduling.py

### exceptions/runtime

@python/exceptions/runtime/__init__.py
@python/exceptions/runtime/execution.py
@python/exceptions/runtime/providers.py
@python/exceptions/runtime/resources.py
@python/exceptions/runtime/timeout.py

### exceptions/storage

@python/exceptions/storage/__init__.py
@python/exceptions/storage/cache.py
@python/exceptions/storage/database.py
@python/exceptions/storage/vector.py

### exceptions/validation

@python/exceptions/validation/__init__.py
@python/exceptions/validation/sanitization.py
@python/exceptions/validation/schema.py
@python/exceptions/validation/security.py

### graphs

@python/graphs/__init__.py
@python/graphs/factory.py

### graphs/base

@python/graphs/base/__init__.py
@python/graphs/base/graph.py
@python/graphs/base/state.py
@python/graphs/base/types.py

### graphs/implementations

@python/graphs/implementations/__init__.py

### graphs/implementations/orchestrator

@python/graphs/implementations/orchestrator/__init__.py
@python/graphs/implementations/orchestrator/simple_flow.py

### graphs/implementations/specialized

@python/graphs/implementations/specialized/__init__.py

### graphs/implementations/workflow

@python/graphs/implementations/workflow/__init__.py
@python/graphs/implementations/workflow/conditional_workflow.py
@python/graphs/implementations/workflow/parallel_workflow.py
@python/graphs/implementations/workflow/sequential_workflow.py

### grpc

@python/grpc/__init__.py
@python/grpc/client.py
@python/grpc/server.py

### grpc/config

@python/grpc/config/__init__.py
@python/grpc/config/config.py

### grpc/config/dynamic

@python/grpc/config/dynamic/__init__.py
@python/grpc/config/dynamic/api.py
@python/grpc/config/dynamic/manager.py
@python/grpc/config/dynamic/storage.py
@python/grpc/config/dynamic/validator.py
@python/grpc/config/dynamic/watcher.py

### grpc/config/features

@python/grpc/config/features/__init__.py

### grpc/config/profiles

@python/grpc/config/profiles/__init__.py

### grpc/generated

@python/grpc/generated/__init__.py
@python/grpc/generated/mindflow_backend_pb2.py
@python/grpc/generated/mindflow_backend_pb2_grpc.py

### grpc/interceptors

@python/grpc/interceptors/__init__.py
@python/grpc/interceptors/error_handler.py

### grpc/interfaces

@python/grpc/interfaces/__init__.py
@python/grpc/interfaces/client.py
@python/grpc/interfaces/server.py

### grpc/monitoring

@python/grpc/monitoring/__init__.py
@python/grpc/monitoring/alerting.py
@python/grpc/monitoring/health.py
@python/grpc/monitoring/interceptor.py
@python/grpc/monitoring/metrics.py
@python/grpc/monitoring/prometheus.py

### grpc/performance

@python/grpc/performance/__init__.py

### grpc/performance/caching

@python/grpc/performance/caching/__init__.py
@python/grpc/performance/caching/cache.py
@python/grpc/performance/caching/strategies.py

### grpc/performance/compression

@python/grpc/performance/compression/__init__.py
@python/grpc/performance/compression/compressor.py
@python/grpc/performance/compression/strategies.py

### grpc/performance/load_balancing

@python/grpc/performance/load_balancing/__init__.py
@python/grpc/performance/load_balancing/strategies.py

### grpc/performance/monitoring

@python/grpc/performance/monitoring/__init__.py
@python/grpc/performance/monitoring/profiler.py

### grpc/performance/optimization

@python/grpc/performance/optimization/__init__.py
@python/grpc/performance/optimization/optimizer.py
@python/grpc/performance/optimization/tuner.py

### grpc/performance/pooling

@python/grpc/performance/pooling/__init__.py
@python/grpc/performance/pooling/factory.py
@python/grpc/performance/pooling/health.py
@python/grpc/performance/pooling/manager.py
@python/grpc/performance/pooling/pool.py

### grpc/resilience

@python/grpc/resilience/__init__.py
@python/grpc/resilience/advanced_retry.py
@python/grpc/resilience/bulkhead.py
@python/grpc/resilience/circuit_breaker.py
@python/grpc/resilience/enhanced_circuit_breaker.py
@python/grpc/resilience/fallback.py
@python/grpc/resilience/retry.py
@python/grpc/resilience/timeout.py

### grpc/services

@python/grpc/services/__init__.py
@python/grpc/services/agent_runtime_service.py

### infra

@python/infra/__init__.py
@python/infra/config.py
@python/infra/logging.py
@python/infra/normalizer.py
@python/infra/redis.py
@python/infra/resilience.py
@python/infra/sanitizer.py

### infra/api

@python/infra/api/__init__.py
@python/infra/api/gateway.py
@python/infra/api/middleware.py
@python/infra/api/router.py

### infra/cache

@python/infra/cache/__init__.py
@python/infra/cache/cache_manager.py
@python/infra/cache/invalidation.py
@python/infra/cache/redis_client.py
@python/infra/cache/warming.py

### infra/config

@python/infra/config/__init__.py
@python/infra/config/cache.py
@python/infra/config/database.py
@python/infra/config/monitoring.py
@python/infra/config/settings.py

### infra/database

@python/infra/database/__init__.py
@python/infra/database/connection.py
@python/infra/database/health.py
@python/infra/database/migrations.py
@python/infra/database/transactions.py

### infra/logging

@python/infra/logging/__init__.py
@python/infra/logging/correlation.py
@python/infra/logging/sampling.py
@python/infra/logging/structured.py

### infra/middleware

@python/infra/middleware/__init__.py
@python/infra/middleware/auth.py
@python/infra/middleware/rate_limiter.py
@python/infra/middleware/request_context.py
@python/infra/middleware/security_headers.py

### infra/monitoring

@python/infra/monitoring/__init__.py
@python/infra/monitoring/health_checks.py
@python/infra/monitoring/metrics.py

### infra/performance

@python/infra/performance/__init__.py
@python/infra/performance/monitor.py
@python/infra/performance/profiler.py
@python/infra/performance/query_optimizer.py

### infra/security

@python/infra/security/__init__.py
@python/infra/security/auth.py
@python/infra/security/rate_limiter.py

### infra/tracing

@python/infra/tracing/__init__.py
@python/infra/tracing/span.py
@python/infra/tracing/trace_analyzer.py
@python/infra/tracing/tracer.py

### interfaces

@python/interfaces/__init__.py

### interfaces/agents

@python/interfaces/agents/__init__.py
@python/interfaces/agents/context.py
@python/interfaces/agents/session.py
@python/interfaces/agents/specialist.py
@python/interfaces/agents/streaming.py

### interfaces/api

@python/interfaces/api/__init__.py
@python/interfaces/api/controllers.py

### interfaces/core

@python/interfaces/core/__init__.py
@python/interfaces/core/base.py
@python/interfaces/core/config.py
@python/interfaces/core/lifecycle.py
@python/interfaces/core/logging.py

### interfaces/infrastructure

@python/interfaces/infrastructure/__init__.py
@python/interfaces/infrastructure/grpc.py

### interfaces/services

@python/interfaces/services/__init__.py
@python/interfaces/services/base.py
@python/interfaces/services/communication.py
@python/interfaces/services/core.py
@python/interfaces/services/monitoring.py
@python/interfaces/services/orchestration.py

### interfaces/tools

@python/interfaces/tools/__init__.py
@python/interfaces/tools/ai.py
@python/interfaces/tools/base.py
@python/interfaces/tools/data.py
@python/interfaces/tools/filesystem.py
@python/interfaces/tools/integration.py
@python/interfaces/tools/system.py
@python/interfaces/tools/web.py

### memory

@python/memory/__init__.py

### memory/api

@python/memory/api/__init__.py
@python/memory/api/controller.py
@python/memory/api/routes.py
@python/memory/api/schemas.py

### memory/core

@python/memory/core/__init__.py
@python/memory/core/agent_memory_service.py
@python/memory/core/interfaces.py
@python/memory/core/service.py
@python/memory/core/types.py

### memory/embeddings

@python/memory/embeddings/__init__.py
@python/memory/embeddings/providers.py
@python/memory/embeddings/similarity.py
@python/memory/embeddings/vector_store.py

### memory/retrieval

@python/memory/retrieval/__init__.py
@python/memory/retrieval/context.py
@python/memory/retrieval/ranking.py
@python/memory/retrieval/semantic.py

### memory/storage

@python/memory/storage/__init__.py
@python/memory/storage/database.py
@python/memory/storage/models.py
@python/memory/storage/vector_db.py

### memory/windows

@python/memory/windows/__init__.py
@python/memory/windows/chunks.py
@python/memory/windows/rolling.py
@python/memory/windows/summary.py

### memory_backup

@python/memory_backup/memory.py
@python/memory_backup/memory_controller.py
@python/memory_backup/memory_service.py
@python/memory_backup/service.py

### nodes

@python/nodes/__init__.py
@python/nodes/registry.py

### nodes/base

@python/nodes/base/__init__.py
@python/nodes/base/node.py
@python/nodes/base/stateful.py
@python/nodes/base/streamable.py

### nodes/implementations

@python/nodes/implementations/__init__.py

### nodes/implementations/control

@python/nodes/implementations/control/__init__.py
@python/nodes/implementations/control/condition_node.py
@python/nodes/implementations/control/loop_node.py
@python/nodes/implementations/control/parallel_node.py

### nodes/implementations/integration

@python/nodes/implementations/integration/__init__.py
@python/nodes/implementations/integration/agent_bridge.py
@python/nodes/implementations/integration/memory_bridge.py
@python/nodes/implementations/integration/tool_bridge.py

### nodes/implementations/io

@python/nodes/implementations/io/__init__.py
@python/nodes/implementations/io/input_node.py
@python/nodes/implementations/io/output_node.py
@python/nodes/implementations/io/stream_node.py

### nodes/implementations/orchestrator

@python/nodes/implementations/orchestrator/__init__.py
@python/nodes/implementations/orchestrator/execute_node.py
@python/nodes/implementations/orchestrator/respond_node.py
@python/nodes/implementations/orchestrator/route_node.py

### nodes/implementations/processing

@python/nodes/implementations/processing/__init__.py
@python/nodes/implementations/processing/aggregate_node.py
@python/nodes/implementations/processing/filter_node.py
@python/nodes/implementations/processing/transform_node.py

### nodes/orchestrator

@python/nodes/orchestrator/__init__.py
@python/nodes/orchestrator/execute_node.py
@python/nodes/orchestrator/respond_node.py
@python/nodes/orchestrator/route_node.py

### orchestrator

@python/orchestrator/__init__.py
@python/orchestrator/delegation_engine.py
@python/orchestrator/graph.py
@python/orchestrator/intelligent_router.py
@python/orchestrator/router.py

### orchestrator/context

@python/orchestrator/context/__init__.py
@python/orchestrator/context/budget.py
@python/orchestrator/context/control.py
@python/orchestrator/context/semantic.py
@python/orchestrator/context/validation.py

### orchestrator/decomposition

@python/orchestrator/decomposition/__init__.py

### orchestrator/delegation

@python/orchestrator/delegation/__init__.py
@python/orchestrator/delegation/engine.py

### orchestrator/routing

@python/orchestrator/routing/__init__.py
@python/orchestrator/routing/complexity.py
@python/orchestrator/routing/intelligent_router.py
@python/orchestrator/routing/router.py

### root

@python/__init__.py
@python/main.py

### runtime

@python/runtime/__init__.py
@python/runtime/node_registry.py
@python/runtime/output_categorizer.py
@python/runtime/stream.py
@python/runtime/stream_event_queue.py

### runtime/execution

@python/runtime/execution/safe_backend.py

### runtime/monitoring

@python/runtime/monitoring/log_bus.py

### runtime/processing

@python/runtime/processing/chunk_scorer.py
@python/runtime/processing/output_categorizer.py

### runtime/providers

@python/runtime/providers/__init__.py
@python/runtime/providers/providers.py

### runtime/registry

@python/runtime/registry/node_registry.py

### runtime/streaming

@python/runtime/streaming/chunk_extract.py
@python/runtime/streaming/normalizer.py
@python/runtime/streaming/stream.py
@python/runtime/streaming/stream_event_queue.py

### runtime/utils

@python/runtime/utils/response_parser.py

### schemas

@python/schemas/__init__.py
@python/schemas/agent.py

### schemas/agents

@python/schemas/agents/__init__.py
@python/schemas/agents/analyst.py
@python/schemas/agents/creative.py
@python/schemas/agents/research.py
@python/schemas/agents/security_guard.py

### schemas/chat

@python/schemas/chat/__init__.py
@python/schemas/chat/agent.py

### schemas/config

@python/schemas/config/__init__.py
@python/schemas/config/normalization.py
@python/schemas/config/settings.py

### schemas/core

@python/schemas/core/__init__.py
@python/schemas/core/common.py

### schemas/errors

@python/schemas/errors/__init__.py
@python/schemas/errors/agent_errors.py
@python/schemas/errors/api_errors.py
@python/schemas/errors/base.py
@python/schemas/errors/base_exceptions.py
@python/schemas/errors/orchestrator_errors.py
@python/schemas/errors/provider_errors.py

### schemas/grpc

@python/schemas/grpc/__init__.py
@python/schemas/grpc/health.py
@python/schemas/grpc/requests.py
@python/schemas/grpc/responses.py

### schemas/orchestration

@python/schemas/orchestration/__init__.py
@python/schemas/orchestration/delegation.py
@python/schemas/orchestration/orchestrator.py
@python/schemas/orchestration/personality.py
@python/schemas/orchestration/specialists.py

### schemas/orchestration/decomposition

@python/schemas/orchestration/decomposition/__init__.py
@python/schemas/orchestration/decomposition/decomposition.py
@python/schemas/orchestration/decomposition/decomposition_v2.py

### schemas/session

@python/schemas/session/__init__.py
@python/schemas/session/chunk.py
@python/schemas/session/contracts.py
@python/schemas/session/governance.py
@python/schemas/session/review.py

### schemas/tools

@python/schemas/tools/__init__.py
@python/schemas/tools/ai_schemas.py
@python/schemas/tools/data_schemas.py
@python/schemas/tools/integration_schemas.py
@python/schemas/tools/model_config.py
@python/schemas/tools/tool_config.py
@python/schemas/tools/tool_execution.py
@python/schemas/tools/tool_permissions.py

### services

@python/services/__init__.py
@python/services/multilingual_embeddings.py
@python/services/session_retriever.py
@python/services/session_review_service.py
@python/services/vector_manager.py

### services/communication

@python/services/communication/__init__.py
@python/services/communication/grpc_service.py
@python/services/communication/streaming_service.py

### services/context

@python/services/context/__init__.py
@python/services/context/embedding_service.py
@python/services/context/retrieval_service.py
@python/services/context/vector_service.py

### services/core

@python/services/core/__init__.py
@python/services/core/agent_service.py
@python/services/core/container.py
@python/services/core/provider_service.py
@python/services/core/session_service.py

### services/interfaces

@python/services/interfaces/__init__.py
@python/services/interfaces/base_interfaces.py
@python/services/interfaces/communication_interfaces.py
@python/services/interfaces/context_interfaces.py
@python/services/interfaces/core_interfaces.py
@python/services/interfaces/monitoring_interfaces.py
@python/services/interfaces/orchestration_interfaces.py

### services/monitoring

@python/services/monitoring/__init__.py
@python/services/monitoring/health_service.py
@python/services/monitoring/metrics_service.py
@python/services/monitoring/review_service.py

### services/orchestration

@python/services/orchestration/__init__.py
@python/services/orchestration/orchestration_service.py
@python/services/orchestration/routing_service.py
@python/services/orchestration/task_service.py

### storage

@python/storage/__init__.py

### storage/kuzudb

@python/storage/kuzudb/__init__.py
@python/storage/kuzudb/vector_store.py

### storage/langgraph

@python/storage/langgraph/__init__.py
@python/storage/langgraph/checkpointer.py

### storage/postgresql

@python/storage/postgresql/__init__.py
@python/storage/postgresql/connection.py
@python/storage/postgresql/models.py
@python/storage/postgresql/repositories.py
@python/storage/postgresql/review_repository.py

### storage/postgresql/migrations

@python/storage/postgresql/migrations/__init__.py
@python/storage/postgresql/migrations/env.py

### storage/postgresql/migrations/versions

@python/storage/postgresql/migrations/versions/20260227_0001_initial.py
@python/storage/postgresql/migrations/versions/20260227_0002_agent_mind_refactor.py
@python/storage/postgresql/migrations/versions/20260302_0003_chat_compat_tables.py
@python/storage/postgresql/migrations/versions/20260302_0004_chat_session_id_len_64.py
@python/storage/postgresql/migrations/versions/20260302_0005_agent_memory_tables.py
@python/storage/postgresql/migrations/versions/20260304_0006_research_tables.py
@python/storage/postgresql/migrations/versions/20260304_0007_session_chunks.py
@python/storage/postgresql/migrations/versions/__init__.py

### storage/utils

@python/storage/utils/__init__.py
@python/storage/utils/migration_helpers.py

### tools_backup

@python/tools_backup/__init__.py

### tools_backup/ai

@python/tools_backup/ai/__init__.py
@python/tools_backup/ai/model_tools.py

### tools_backup/core

@python/tools_backup/core/__init__.py
@python/tools_backup/core/executor.py
@python/tools_backup/core/permissions.py
@python/tools_backup/core/registry.py

### tools_backup/data

@python/tools_backup/data/__init__.py
@python/tools_backup/data/data_tools.py

### tools_backup/filesystem

@python/tools_backup/filesystem/__init__.py
@python/tools_backup/filesystem/file_operations.py
@python/tools_backup/filesystem/operations.py
@python/tools_backup/filesystem/search.py
@python/tools_backup/filesystem/search_tools.py

### tools_backup/integration

@python/tools_backup/integration/__init__.py
@python/tools_backup/integration/integration_tools.py

### tools_backup/system

@python/tools_backup/system/__init__.py
@python/tools_backup/system/info_collector.py
@python/tools_backup/system/resource_monitor.py
@python/tools_backup/system/shell_tools.py

### tools_backup/web

@python/tools_backup/web/__init__.py
@python/tools_backup/web/web_tools.py

### utils

@python/utils/__init__.py

### utils/collections

@python/utils/collections/__init__.py

### utils/core

@python/utils/core/__init__.py
@python/utils/core/base64_utils.py
@python/utils/core/datetime_utils.py
@python/utils/core/file_utils.py
@python/utils/core/hash_utils.py
@python/utils/core/json_utils.py
@python/utils/core/string_utils.py
@python/utils/core/uuid_utils.py

### utils/error_handling

@python/utils/error_handling/__init__.py
@python/utils/error_handling/error_handling.py
@python/utils/error_handling/error_setup.py

### utils/formatting

@python/utils/formatting/__init__.py
@python/utils/formatting/converters.py
@python/utils/formatting/formatters.py
@python/utils/formatting/parsers.py

### utils/monitoring

@python/utils/monitoring/__init__.py
@python/utils/monitoring/health_utils.py
@python/utils/monitoring/metrics_utils.py

### utils/network

@python/utils/network/__init__.py
@python/utils/network/http_utils.py
@python/utils/network/port_utils.py
@python/utils/network/retry_utils.py
@python/utils/network/url_utils.py

### utils/performance

@python/utils/performance/__init__.py

### utils/security

@python/utils/security/__init__.py

### utils/validation

@python/utils/validation/__init__.py
@python/utils/validation/sanitizers.py
@python/utils/validation/validators.py

### workers

@python/workers/__init__.py
@python/workers/main.py

### workers/agents

@python/workers/agents/__init__.py
@python/workers/agents/analyst_worker.py
@python/workers/agents/coder_worker.py
@python/workers/agents/orchestrator_worker.py
@python/workers/agents/researcher_worker.py

### workers/archive/legacy_rq_workers_20260305_163354

@python/workers/archive/legacy_rq_workers_20260305_163354/queue.py
@python/workers/archive/legacy_rq_workers_20260305_163354/tasks.py
@python/workers/archive/legacy_rq_workers_20260305_163354/worker.py

### workers/base

@python/workers/base/__init__.py
@python/workers/base/exceptions.py
@python/workers/base/worker.py

### workers/config

@python/workers/config/__init__.py
@python/workers/config/queues.py
@python/workers/config/settings.py

### workers/infrastructure

@python/workers/infrastructure/__init__.py
@python/workers/infrastructure/monitoring.py
@python/workers/infrastructure/queue_manager.py
@python/workers/infrastructure/worker_factory.py

### workers/research

@python/workers/research/__init__.py
@python/workers/research/browser_worker.py
@python/workers/research/content_worker.py

### workers/system

@python/workers/system/__init__.py
@python/workers/system/health_worker.py
@python/workers/system/memory_worker.py
@python/workers/system/session_review_worker.py
@python/workers/system/vector_worker.py

### workers/tasks

@python/workers/tasks/__init__.py
@python/workers/tasks/agent_tasks.py
@python/workers/tasks/research_tasks.py
@python/workers/tasks/system_tasks.py

# Estatísticas do Mapeamento

- **Total de Diretórios**: 188
- **Total de Arquivos Python**: 682
- **Total de Arquivos**: 880
- **Diretórios com Arquivos Python**: 181
## ⚠️ Problemas Encontrados:

- Diretório sem arquivos Python: docs
- Diretório sem arquivos Python: graphs/chains
- Diretório sem arquivos Python: grpc/proto
- Diretório sem arquivos Python: nodes/agents
- Diretório sem arquivos Python: nodes/control
- Diretório sem arquivos Python: runtime/agents
- Diretório sem arquivos Python: runtime/core
- Diretório sem arquivos Python: workers/archive