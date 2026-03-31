"""Graph factory for the canonical orchestration runtime.

Only the simple orchestrator graph is a supported production runtime here.
Other graph construction paths are compatibility utilities until a follow-up
cleanup removes or formalizes them.
"""

from __future__ import annotations

from typing import Any

from mindflow_backend.graphs.base.graph import BaseGraph
from mindflow_backend.graphs.base.types import GraphConfig, GraphType
from mindflow_backend.graphs.implementations.orchestrator.simple_flow import (
    SimpleOrchestratorGraph,
)
from mindflow_backend.graphs.implementations.orchestrator.simple_flow import (
    build_simple_orchestrator_flow as _build_simple_orchestrator_flow,
)
from mindflow_backend.infra.logging import get_logger


class GraphFactory:
    """Factory for creating graph instances."""
    
    def __init__(self) -> None:
        self._graph_classes: dict[GraphType, type[BaseGraph]] = {}
        self._graph_instances: dict[str, BaseGraph] = {}
        self._default_configs: dict[GraphType, GraphConfig] = {}
        self._logger = get_logger(__name__)
        
        # Register built-in graph types
        self._register_builtin_graphs()
    
    def register_graph_class(
        self,
        graph_type: GraphType,
        graph_class: type[BaseGraph],
        default_config: GraphConfig | None = None
    ) -> None:
        """Register a graph class for a specific type."""
        if not issubclass(graph_class, BaseGraph):
            raise ValueError("Graph class must inherit from BaseGraph")
        
        self._graph_classes[graph_type] = graph_class
        if default_config:
            self._default_configs[graph_type] = default_config
        
        self._logger.info("graph_class_registered", 
                         graph_type=graph_type.value, 
                         graph_class=graph_class.__name__)
    
    def create_graph(
        self,
        graph_type: GraphType,
        graph_id: str,
        config: GraphConfig | None = None,
        **kwargs
    ) -> BaseGraph:
        """Create a registered graph instance.

        This factory is authoritative only for registered runtime graphs.
        """
        if graph_type not in self._graph_classes:
            raise ValueError(f"Unknown graph type: {graph_type}")
        
        # Use provided config or default
        graph_config = config or self._default_configs.get(graph_type, GraphConfig())
        graph_config.graph_type = graph_type
        
        # Create graph instance
        graph_class = self._graph_classes[graph_type]
        graph = graph_class(graph_id=graph_id, config=graph_config, **kwargs)
        
        # Store instance
        self._graph_instances[graph_id] = graph
        
        self._logger.info("graph_created", 
                         graph_id=graph_id, 
                         graph_type=graph_type.value)
        
        return graph
    
    def get_graph(self, graph_id: str) -> BaseGraph | None:
        """Get an existing graph instance."""
        return self._graph_instances.get(graph_id)
    
    def remove_graph(self, graph_id: str) -> bool:
        """Remove a graph instance."""
        if graph_id in self._graph_instances:
            del self._graph_instances[graph_id]
            self._logger.info("graph_removed", graph_id=graph_id)
            return True
        return False
    
    def list_graphs(self) -> list[str]:
        """List all graph instance IDs."""
        return list(self._graph_instances.keys())
    
    def get_available_types(self) -> list[GraphType]:
        """Get all available graph types."""
        return list(self._graph_classes.keys())
    
    def validate_graph_type(self, graph_type: GraphType) -> list[str]:
        """Validate a registered graph type."""
        if graph_type not in self._graph_classes:
            return [f"Graph type {graph_type} is not registered"]
        
        graph_class = self._graph_classes[graph_type]
        
        try:
            # Create a temporary instance to validate
            temp_graph = graph_class(graph_id="temp_test")
            return temp_graph.validate()
        except Exception as e:
            return [f"Failed to create graph instance: {e}"]
    
    def get_graph_info(self, graph_id: str) -> dict[str, Any] | None:
        """Get information about a graph instance."""
        graph = self._graph_instances.get(graph_id)
        if not graph:
            return None
        
        return graph.get_graph_info()
    
    def get_factory_stats(self) -> dict[str, Any]:
        """Get factory statistics."""
        return {
            "registered_types": {
                graph_type.value: graph_class.__name__
                for graph_type, graph_class in self._graph_classes.items()
            },
            "active_instances": len(self._graph_instances),
            "instance_ids": list(self._graph_instances.keys()),
            "default_configs": {
                graph_type.value: config.dict()
                for graph_type, config in self._default_configs.items()
            },
        }
    
    def _register_builtin_graphs(self) -> None:
        """Register built-in graph types."""
        # Register Simple Orchestrator
        self.register_graph_class(
            graph_type=GraphType.SIMPLE,
            graph_class=SimpleOrchestratorGraph,
            default_config=GraphConfig(
                graph_type=GraphType.SIMPLE,
                enable_streaming=True,
                timeout_per_node=30.0,
            )
        )

        # === Fase 2A: Analysis graphs ===
        from mindflow_backend.graphs.implementations.analysis import (
            AnalysisGraph,
            CodeReviewGraph,
            DeepInvestigationGraph,
            SecurityAuditGraph,
        )

        self.register_graph_class(
            graph_type=GraphType.ANALYSIS,
            graph_class=AnalysisGraph,
            default_config=GraphConfig(
                graph_type=GraphType.ANALYSIS,
                enable_streaming=True,
                timeout_per_node=60.0,
            ),
        )
        self.register_graph_class(
            graph_type=GraphType.DEEP_INVESTIGATION,
            graph_class=DeepInvestigationGraph,
            default_config=GraphConfig(
                graph_type=GraphType.DEEP_INVESTIGATION,
                enable_streaming=True,
                timeout_per_node=120.0,
            ),
        )
        self.register_graph_class(
            graph_type=GraphType.SECURITY_AUDIT,
            graph_class=SecurityAuditGraph,
            default_config=GraphConfig(
                graph_type=GraphType.SECURITY_AUDIT,
                enable_streaming=True,
                timeout_per_node=60.0,
            ),
        )
        self.register_graph_class(
            graph_type=GraphType.CODE_REVIEW,
            graph_class=CodeReviewGraph,
            default_config=GraphConfig(
                graph_type=GraphType.CODE_REVIEW,
                enable_streaming=True,
                timeout_per_node=60.0,
            ),
        )

        # === Fase 2A: Coding graphs ===
        from mindflow_backend.graphs.implementations.coding import (
            BugFixGraph,
            CodingGraph,
            RefactorGraph,
        )

        self.register_graph_class(
            graph_type=GraphType.CODING_TASK,
            graph_class=CodingGraph,
            default_config=GraphConfig(
                graph_type=GraphType.CODING_TASK,
                enable_streaming=True,
                timeout_per_node=60.0,
            ),
        )
        self.register_graph_class(
            graph_type=GraphType.BUG_FIX,
            graph_class=BugFixGraph,
            default_config=GraphConfig(
                graph_type=GraphType.BUG_FIX,
                enable_streaming=True,
                timeout_per_node=60.0,
            ),
        )
        self.register_graph_class(
            graph_type=GraphType.REFACTOR,
            graph_class=RefactorGraph,
            default_config=GraphConfig(
                graph_type=GraphType.REFACTOR,
                enable_streaming=True,
                timeout_per_node=60.0,
            ),
        )

        # === Fase 2A: Research graphs ===
        from mindflow_backend.graphs.implementations.research import (
            ComparisonGraph,
            ResearchGraph,
        )

        self.register_graph_class(
            graph_type=GraphType.WEB_RESEARCH,
            graph_class=ResearchGraph,
            default_config=GraphConfig(
                graph_type=GraphType.WEB_RESEARCH,
                enable_streaming=True,
                timeout_per_node=60.0,
            ),
        )
        self.register_graph_class(
            graph_type=GraphType.COMPARISON,
            graph_class=ComparisonGraph,
            default_config=GraphConfig(
                graph_type=GraphType.COMPARISON,
                enable_streaming=True,
                timeout_per_node=60.0,
            ),
        )
    
    def create_orchestrator_graph(
        self,
        graph_id: str = "orchestrator",
        config: GraphConfig | None = None
    ) -> SimpleOrchestratorGraph:
        """Create the standard orchestrator graph."""
        return self.create_graph(
            graph_type=GraphType.SIMPLE,
            graph_id=graph_id,
            config=config
        )
    
    def create_custom_graph(
        self,
        graph_id: str,
        graph_class: type[BaseGraph],
        config: GraphConfig | None = None,
        **kwargs
    ) -> BaseGraph:
        """Create a custom graph instance.

        Compatibility surface only; custom graphs are not part of the canonical
        production orchestration runtime.
        """
        # Create instance directly without registration
        graph_config = config or GraphConfig()
        graph = graph_class(graph_id=graph_id, config=graph_config, **kwargs)
        
        # Store instance
        self._graph_instances[graph_id] = graph
        
        return graph


# Global factory instance
_global_factory: GraphFactory | None = None


def get_graph_factory() -> GraphFactory:
    """Get the global graph factory instance."""
    global _global_factory
    if _global_factory is None:
        _global_factory = GraphFactory()
    return _global_factory


# Convenience functions
def create_orchestrator_graph(
    graph_id: str = "orchestrator",
    config: GraphConfig | None = None
) -> SimpleOrchestratorGraph:
    """Create the standard orchestrator graph."""
    factory = get_graph_factory()
    return factory.create_orchestrator_graph(graph_id, config)


def build_simple_orchestrator_flow() -> Any:
    """Build the canonical compiled LangGraph orchestrator flow."""
    return _build_simple_orchestrator_flow()
