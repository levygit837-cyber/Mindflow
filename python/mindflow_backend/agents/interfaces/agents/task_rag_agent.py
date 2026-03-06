"""Task RAG Agent interface for real-time context retrieval and semantic memory exchange.

Extends agent contracts with RAG capabilities for Task pipeline components,
enabling semantic context sharing and intelligent dependency resolution.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable, Any

from mindflow_backend.agents.interfaces.agents.core_personality import (
    CorePersonalityContract,
)


@runtime_checkable
class TaskRagAgent(CorePersonalityContract, Protocol):
    """Contract for agents with Task RAG capabilities.
    
    Extends core personality capabilities with real-time context retrieval,
    semantic memory exchange, and dependency-aware processing.
    """
    
    async def retrieve_component_context(
        self,
        component_id: str,
        query: str | None = None,
        context_type: str = "current",
    ) -> dict[str, Any]:
        """Retrieve context for a specific component.
        
        Args:
            component_id: ID of the component to get context for
            query: Optional query to filter context
            context_type: Type of context (current, historical, dependency)
            
        Returns:
            Component context with semantic embeddings and metadata
        """
        ...
    
    async def search_related_components(
        self,
        query_vector: list[float],
        component_types: list[str] | None = None,
        similarity_threshold: float = 0.7,
        max_results: int = 10,
    ) -> list[dict[str, Any]]:
        """Search for semantically related components.
        
        Args:
            query_vector: Query vector for semantic search
            component_types: Types of components to search
            similarity_threshold: Minimum similarity threshold
            max_results: Maximum number of results
            
        Returns:
            List of related components with similarity scores
        """
        ...
    
    async def update_component_memory(
        self,
        component_id: str,
        memory_data: dict[str, Any],
        memory_type: str = "context",
    ) -> str:
        """Update memory for a component with new context.
        
        Args:
            component_id: ID of the component
            memory_data: Data to store in component memory
            memory_type: Type of memory (context, artifact, dependency)
            
        Returns:
            Memory vector ID for reference
        """
        ...
    
    async def validate_dependencies(
        self,
        component_id: str,
        dependencies: list[str],
    ) -> dict[str, Any]:
        """Validate that component dependencies are contextually ready.
        
        Args:
            component_id: ID of the component checking dependencies
            dependencies: List of dependency component IDs
            
        Returns:
            Dependency validation results with readiness scores
        """
        ...
    
    async def get_dependency_context(
        self,
        dependency_id: str,
        context_requirements: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Get context from a specific dependency component.
        
        Args:
            dependency_id: ID of the dependency component
            context_requirements: Specific context requirements
            
        Returns:
            Dependency context with relevance scoring
        """
        ...
    
    async def exchange_semantic_memory(
        self,
        target_component_id: str,
        memory_payload: dict[str, Any],
        exchange_type: str = "context_sharing",
    ) -> dict[str, Any]:
        """Exchange semantic memory with another component.
        
        Args:
            target_component_id: ID of target component
            memory_payload: Memory data to exchange
            exchange_type: Type of exchange (sharing, request, sync)
            
        Returns:
            Exchange result with confirmation and updated context
        """
        ...
    
    async def pause_for_dependencies(
        self,
        component_id: str,
        missing_dependencies: list[str],
        wait_strategy: str = "semantic_polling",
    ) -> bool:
        """Pause execution until dependencies are ready.
        
        Args:
            component_id: ID of the component pausing
            missing_dependencies: List of missing dependency IDs
            wait_strategy: Strategy for waiting (polling, event_driven)
            
        Returns:
            True if successfully paused, False otherwise
        """
        ...
    
    async def resume_with_context(
        self,
        component_id: str,
        available_context: dict[str, Any],
    ) -> dict[str, Any]:
        """Resume execution with newly available context.
        
        Args:
            component_id: ID of the component resuming
            available_context: Context that became available
            
        Returns:
            Resume result with context integration status
        """
        ...
    
    async def analyze_context_gaps(
        self,
        component_id: str,
        current_context: dict[str, Any],
        required_context: list[str],
    ) -> dict[str, Any]:
        """Analyze gaps in current context vs requirements.
        
        Args:
            component_id: ID of the component
            current_context: Currently available context
            required_context: List of required context elements
            
        Returns:
            Gap analysis with recommendations
        """
        ...
    
    async def generate_context_query(
        self,
        component_id: str,
        intent: str,
        context_requirements: dict[str, Any],
    ) -> list[float]:
        """Generate query vector for context search.
        
        Args:
            component_id: ID of the component
            intent: Search intent description
            context_requirements: Specific context requirements
            
        Returns:
            Query vector for semantic search
        """
        ...
    
    async def integrate_external_context(
        self,
        component_id: str,
        external_context: dict[str, Any],
        integration_strategy: str = "semantic_merge",
    ) -> dict[str, Any]:
        """Integrate external context into component memory.
        
        Args:
            component_id: ID of the component
            external_context: Context from external sources
            integration_strategy: How to integrate (merge, replace, augment)
            
        Returns:
            Integration result with updated memory
        """
        ...
    
    async def monitor_context_freshness(
        self,
        component_id: str,
        freshness_threshold: float = 0.8,
    ) -> dict[str, Any]:
        """Monitor freshness of component context.
        
        Args:
            component_id: ID of the component
            freshness_threshold: Minimum freshness score
            
        Returns:
            Freshness assessment with update recommendations
        """
        ...
    
    async def optimize_context_usage(
        self,
        component_id: str,
        usage_patterns: dict[str, Any],
    ) -> dict[str, Any]:
        """Optimize context usage based on patterns.
        
        Args:
            component_id: ID of the component
            usage_patterns: Historical context usage patterns
            
        Returns:
            Optimization recommendations and strategies
        """
        ...


@runtime_checkable
class TaskRagAgentWithSynthesis(TaskRagAgent, Protocol):
    """Extended Task RAG Agent with synthesis capabilities.
    
    Adds context synthesis and multi-task integration capabilities
    for complex Task pipeline scenarios.
    """
    
    async def synthesize_multi_task_context(
        self,
        component_ids: list[str],
        synthesis_goal: str,
        synthesis_strategy: str = "semantic_fusion",
    ) -> dict[str, Any]:
        """Synthesize context from multiple components.
        
        Args:
            component_ids: List of component IDs to synthesize from
            synthesis_goal: Goal of the synthesis operation
            synthesis_strategy: How to synthesize (fusion, merge, hierarchy)
            
        Returns:
            Synthesized context with provenance tracking
        """
        ...
    
    async def resolve_context_conflicts(
        self,
        conflicting_contexts: list[dict[str, Any]],
        resolution_strategy: str = "semantic_priority",
    ) -> dict[str, Any]:
        """Resolve conflicts between different context sources.
        
        Args:
            conflicting_contexts: List of conflicting contexts
            resolution_strategy: How to resolve conflicts
            
        Returns:
            Resolved context with conflict resolution log
        """
        ...
    
    async def create_context_abstraction(
        self,
        source_contexts: list[dict[str, Any]],
        abstraction_level: str = "semantic",
    ) -> dict[str, Any]:
        """Create higher-level abstraction from multiple contexts.
        
        Args:
            source_contexts: Contexts to abstract from
            abstraction_level: Level of abstraction (semantic, functional, structural)
            
        Returns:
            Abstracted context with meta-information
        """
        ...
    
    async def propagate_context_updates(
        self,
        source_component_id: str,
        update_payload: dict[str, Any],
        propagation_scope: str = "dependencies",
    ) -> dict[str, Any]:
        """Propagate context updates to related components.
        
        Args:
            source_component_id: Source of the update
            update_payload: Context update data
            propagation_scope: Scope of propagation (dependencies, all, custom)
            
        Returns:
            Propagation results with affected components
        """
        ...
