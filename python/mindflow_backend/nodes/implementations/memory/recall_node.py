"""MemoryRecallNode - Retrieve relevant memories for graph execution.

This node queries the Intelligent Memory System to retrieve
contextually relevant memories based on the current task,
providing agents with historical context and patterns.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.memory import MemoryService, SearchMode
from mindflow_backend.memory.category_manager import MemoryScope
from mindflow_backend.nodes.base.node import BaseNode, NodeCategory, NodeType

_logger = get_logger(__name__)


class MemoryRecallNodeInput(BaseModel):
    """Input schema for MemoryRecallNode."""

    task_description: str = Field(
        ...,
        description="Description of the current task for memory search",
    )
    recent_context: str | None = Field(
        default=None,
        description="Recent conversation context to enhance search",
    )
    scope: str | None = Field(
        default=None,
        description="Memory scope: 'global', 'project', or 'session'",
    )
    project_id: int | None = Field(
        default=None,
        description="Project ID for project-scoped search",
    )
    categories: list[str] | None = Field(
        default=None,
        description="Filter by specific memory categories",
    )
    memory_types: list[str] | None = Field(
        default=None,
        description="Filter by memory types: fact, pattern, preference, error",
    )
    tags: list[str] | None = Field(
        default=None,
        description="Filter by tags",
    )
    search_mode: str = Field(
        default="hybrid",
        description="Search mode: 'semantic', 'fulltext', or 'hybrid'",
    )
    limit: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum number of memories to retrieve",
    )
    min_importance: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Minimum importance threshold",
    )


class MemoryRecallNodeOutput(BaseModel):
    """Output schema for MemoryRecallNode."""

    context_summary: str = Field(
        ...,
        description="Formatted memory context for injection into LLM context",
    )
    memories_found: int = Field(
        ...,
        description="Number of memories found",
    )
    memories: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Detailed memory results",
    )
    search_metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata about the search execution",
    )


class MemoryRecallNode(BaseNode):
    """Retrieve relevant memories to enhance agent context.

    This node queries the Intelligent Memory System using multiple
    search strategies (semantic, full-text, hybrid) to find
    relevant historical context for the current task.

    Example usage in a graph:
        memory_recall_node -> search_node -> synthesis_node

    The node automatically formats memories for injection into
    the LLM context window.
    """

    def __init__(
        self,
        node_id: str = "memory_recall",
        memory_service: MemoryService | None = None,
    ) -> None:
        """Initialize MemoryRecallNode.

        Args:
            node_id: Unique identifier for this node
            memory_service: Optional MemoryService instance
        """
        super().__init__(
            node_id=node_id,
            node_type=NodeType.MEMORY,
            category=NodeCategory.DATA_PROCESSING,
            description="Retrieve relevant memories for context enhancement.",
        )

        self.config.required_inputs = {
            "task_description",
        }
        self.config.outputs = {
            "context_summary",
            "memories_found",
            "memories",
            "search_metadata",
        }

        # Initialize or store reference to MemoryService
        self._memory_service = memory_service

    async def _on_initialize(self) -> None:
        """Initialize the MemoryService if not provided."""
        if self._memory_service is None:
            self._memory_service = MemoryService()
            await self._memory_service.initialize()

    async def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """Execute memory recall.

        Args:
            state: Current graph state containing inputs

        Returns:
            State enriched with memory context
        """
        start_time = time.time()

        try:
            # Extract inputs from state
            task_description = state.get("task_description", "")
            recent_context = state.get("recent_context")
            scope = state.get("scope")
            project_id = state.get("project_id")
            categories = state.get("categories")
            memory_types = state.get("memory_types")
            tags = state.get("tags")
            search_mode = state.get("search_mode", "hybrid")
            limit = state.get("limit", 10)
            min_importance = state.get("min_importance", 0.3)

            _logger.debug(
                "memory_recall_start",
                node_id=self.node_id,
                task_preview=task_description[:100],
                scope=scope,
                project_id=project_id,
            )

            # Build search query
            query = self._build_search_query(task_description, recent_context)

            # Determine search mode
            mode = SearchMode.HYBRID
            if search_mode == "semantic":
                mode = SearchMode.SEMANTIC
            elif search_mode == "fulltext":
                mode = SearchMode.FULLTEXT

            # Execute search
            if not self._memory_service:
                await self._on_initialize()

            results = await self._memory_service.search_memories(
                query=query,
                scope=scope,
                project_id=project_id,
                categories=categories,
                memory_types=memory_types,
                tags=tags,
                min_importance=min_importance,
                search_mode=mode,
                limit=limit,
            )

            # Format results
            formatted_memories = []
            for result in results:
                memory = result.memory
                formatted_memories.append({
                    "id": memory.id,
                    "content": memory.content[:500] + "..." if len(memory.content) > 500 else memory.content,
                    "memory_type": memory.memory_type,
                    "category": memory.category.name if memory.category else None,
                    "scope": memory.scope,
                    "importance": memory.importance,
                    "score": result.score,
                    "search_type": result.search_type,
                    "source_agent": memory.source_agent_id,
                    "source_tool": memory.source_tool,
                    "created_at": memory.created_at.isoformat() if memory.created_at else None,
                })

            # Format context summary for LLM
            context_summary = self._format_context_summary(results)

            # Build output
            output = MemoryRecallNodeOutput(
                context_summary=context_summary,
                memories_found=len(results),
                memories=formatted_memories,
                search_metadata={
                    "query": query[:200],
                    "search_mode": search_mode,
                    "execution_time": time.time() - start_time,
                    "scope": scope,
                    "project_id": project_id,
                },
            )

            duration = time.time() - start_time
            _logger.info(
                "memory_recall_complete",
                node_id=self.node_id,
                duration=duration,
                memories_found=len(results),
            )

            # Merge with state
            return {**state, **output.model_dump()}

        except Exception as e:
            duration = time.time() - start_time
            _logger.error(
                "memory_recall_failed",
                node_id=self.node_id,
                duration=duration,
                error=str(e),
            )

            # Return graceful failure
            return {
                **state,
                "context_summary": "",
                "memories_found": 0,
                "memories": [],
                "search_metadata": {
                    "error": str(e),
                    "execution_time": duration,
                },
            }

    def validate_inputs(self, state: dict[str, Any]) -> list[str]:
        """Validate required inputs."""
        errors = []

        if not state.get("task_description"):
            errors.append("Missing required input: task_description")

        return errors

    def _build_search_query(
        self,
        task_description: str,
        recent_context: str | None,
    ) -> str:
        """Build rich search query from inputs.

        Combines task description with recent context for
        more accurate semantic search.

        Args:
            task_description: Primary task description
            recent_context: Optional recent conversation context

        Returns:
            Combined search query
        """
        parts = [task_description]

        if recent_context:
            # Include recent context but truncate if too long
            truncated_context = recent_context[:500] if len(recent_context) > 500 else recent_context
            parts.append(f"Context: {truncated_context}")

        return "\n\n".join(parts)

    def _format_context_summary(
        self,
        results: list,
    ) -> str:
        """Format memories for injection into LLM context.

        Groups memories by category and creates a readable
        summary that agents can use for context.

        Args:
            results: List of MemorySearchResult

        Returns:
            Formatted context string
        """
        if not results:
            return ""

        from collections import defaultdict

        # Group by category
        by_category: dict[str, list] = defaultdict(list)
        for result in results:
            category = result.memory.category.name if result.memory.category else "General"
            by_category[category].append(result)

        # Build formatted output
        sections = [
            "## Relevant Context from Memory System",
            f"*Retrieved {len(results)} relevant memories*\n",
        ]

        for category, memories in by_category.items():
            category_display = category.replace("_", " ").title()
            sections.append(f"### {category_display}")

            for i, result in enumerate(memories[:5], 1):  # Max 5 per category
                memory = result.memory
                content = memory.content[:200] + "..." if len(memory.content) > 200 else memory.content
                sections.append(f"{i}. {content}")

            sections.append("")  # Empty line between categories

        return "\n".join(sections)

    def get_input_schema(self) -> type[BaseModel]:
        """Get the input schema for this node."""
        return MemoryRecallNodeInput

    def get_output_schema(self) -> type[BaseModel]:
        """Get the output schema for this node."""
        return MemoryRecallNodeOutput
