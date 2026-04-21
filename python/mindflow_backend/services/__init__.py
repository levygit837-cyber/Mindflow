"""MindFlow backend services package.

The old eager imports pulled in memory, runtime monitoring, and cache backends
just to resolve a single service submodule. Keep this package lazy so importers
can depend on narrow services without booting the whole graph.
"""

from __future__ import annotations

from importlib import import_module

__all__ = [
    "AgentServiceInterface",
    "BaseServiceInterface",
    "EmbeddingServiceInterface",
    "GrpcServiceInterface",
    "HealthServiceInterface",
    "LLMService",
    "MemoryFacadeInterface",
    "MemoryServiceInterface",
    "MetricsServiceInterface",
    "OrchestrationServiceInterface",
    "ProviderServiceInterface",
    "RetrievalServiceInterface",
    "ReviewServiceInterface",
    "RoutingServiceInterface",
    "SessionServiceInterface",
    "StreamingServiceInterface",
    "TaskServiceInterface",
    "TodoPlanningServiceInterface",
    "VectorStoreInterface",
    "get_agent_runtime_service",
    "get_agent_service",
    "get_container",
    "get_embedding_service",
    "get_execution_task_service",
    "get_grpc_service",
    "get_health_service",
    "get_llm_service",
    "get_memory_facade_service",
    "get_memory_service",
    "get_metrics_service",
    "get_orchestration_service",
    "get_planning_service",
    "get_provider_service",
    "get_retrieval_service",
    "get_review_service",
    "get_routing_service",
    "get_service",
    "get_session_service",
    "get_shell_tab_service",
    "get_streaming_service",
    "get_task_management_service",
    "get_task_service",
    "get_todo_planning_service",
    "get_vector_service",
    "initialize_core_services",
    "register_service",
    "reset_llm_service",
]

_LAZY_ATTRS: dict[str, tuple[str, str]] = {
    "get_agent_runtime_service": (
        "mindflow_backend.services.communication",
        "get_agent_runtime_service",
    ),
    "get_grpc_service": ("mindflow_backend.services.communication", "get_grpc_service"),
    "get_streaming_service": (
        "mindflow_backend.services.communication",
        "get_streaming_service",
    ),
    "get_embedding_service": ("mindflow_backend.services.context", "get_embedding_service"),
    "get_retrieval_service": ("mindflow_backend.services.context", "get_retrieval_service"),
    "get_vector_service": ("mindflow_backend.services.context", "get_vector_service"),
    "get_agent_service": ("mindflow_backend.services.core", "get_agent_service"),
    "get_provider_service": ("mindflow_backend.services.core", "get_provider_service"),
    "get_session_service": ("mindflow_backend.services.core", "get_session_service"),
    "get_shell_tab_service": ("mindflow_backend.services.core", "get_shell_tab_service"),
    "LLMService": ("mindflow_backend.services.llm", "LLMService"),
    "get_llm_service": ("mindflow_backend.services.llm", "get_llm_service"),
    "reset_llm_service": ("mindflow_backend.services.llm", "reset_llm_service"),
    "get_container": ("mindflow_backend.services.core.container", "get_container"),
    "get_service": ("mindflow_backend.services.core.container", "get_service"),
    "initialize_core_services": (
        "mindflow_backend.services.core.container",
        "initialize_core_services",
    ),
    "register_service": ("mindflow_backend.services.core.container", "register_service"),
    "AgentServiceInterface": (
        "mindflow_backend.services.interfaces",
        "AgentServiceInterface",
    ),
    "BaseServiceInterface": (
        "mindflow_backend.services.interfaces",
        "BaseServiceInterface",
    ),
    "EmbeddingServiceInterface": (
        "mindflow_backend.services.interfaces",
        "EmbeddingServiceInterface",
    ),
    "GrpcServiceInterface": (
        "mindflow_backend.services.interfaces",
        "GrpcServiceInterface",
    ),
    "HealthServiceInterface": (
        "mindflow_backend.services.interfaces",
        "HealthServiceInterface",
    ),
    "MemoryFacadeInterface": (
        "mindflow_backend.services.interfaces",
        "MemoryFacadeInterface",
    ),
    "MemoryServiceInterface": (
        "mindflow_backend.services.interfaces",
        "MemoryServiceInterface",
    ),
    "MetricsServiceInterface": (
        "mindflow_backend.services.interfaces",
        "MetricsServiceInterface",
    ),
    "OrchestrationServiceInterface": (
        "mindflow_backend.services.interfaces",
        "OrchestrationServiceInterface",
    ),
    "ProviderServiceInterface": (
        "mindflow_backend.services.interfaces",
        "ProviderServiceInterface",
    ),
    "RetrievalServiceInterface": (
        "mindflow_backend.services.interfaces",
        "RetrievalServiceInterface",
    ),
    "ReviewServiceInterface": (
        "mindflow_backend.services.interfaces",
        "ReviewServiceInterface",
    ),
    "RoutingServiceInterface": (
        "mindflow_backend.services.interfaces",
        "RoutingServiceInterface",
    ),
    "SessionServiceInterface": (
        "mindflow_backend.services.interfaces",
        "SessionServiceInterface",
    ),
    "StreamingServiceInterface": (
        "mindflow_backend.services.interfaces",
        "StreamingServiceInterface",
    ),
    "TaskServiceInterface": (
        "mindflow_backend.services.interfaces",
        "TaskServiceInterface",
    ),
    "TodoPlanningServiceInterface": (
        "mindflow_backend.services.interfaces",
        "TodoPlanningServiceInterface",
    ),
    "VectorStoreInterface": ("mindflow_backend.services.interfaces", "VectorStoreInterface"),
    "get_memory_service": ("mindflow_backend.services.memory", "get_memory_service"),
    "get_memory_facade_service": (
        "mindflow_backend.services.memory",
        "get_memory_facade_service",
    ),
    "get_health_service": ("mindflow_backend.services.monitoring", "get_health_service"),
    "get_metrics_service": ("mindflow_backend.services.monitoring", "get_metrics_service"),
    "get_review_service": ("mindflow_backend.services.monitoring", "get_review_service"),
    "get_execution_task_service": (
        "mindflow_backend.services.orchestration",
        "get_execution_task_service",
    ),
    "get_orchestration_service": (
        "mindflow_backend.services.orchestration",
        "get_orchestration_service",
    ),
    "get_planning_service": ("mindflow_backend.services.orchestration", "get_planning_service"),
    "get_routing_service": ("mindflow_backend.services.orchestration", "get_routing_service"),
    "get_task_management_service": (
        "mindflow_backend.services.orchestration",
        "get_task_management_service",
    ),
    "get_task_service": ("mindflow_backend.services.orchestration", "get_task_service"),
    "get_todo_planning_service": (
        "mindflow_backend.services.orchestration",
        "get_todo_planning_service",
    ),
}


def __getattr__(name: str):
    try:
        module_name, attr_name = _LAZY_ATTRS[name]
    except KeyError as exc:  # pragma: no cover - Python fallback path
        raise AttributeError(name) from exc
    module = import_module(module_name)
    return getattr(module, attr_name)


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
