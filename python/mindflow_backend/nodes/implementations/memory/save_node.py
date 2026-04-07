"""MemorySaveNode - Explicitly save memories from graph execution.

This node allows agents to save insights, patterns, and other
important information discovered during execution.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.memory import MemoryService
from mindflow_backend.memory.category_manager import MemoryScope
from mindflow_backend.nodes.base.node import BaseNode, NodeCategory, NodeType

_logger = get_logger(__name__)


class MemorySaveNodeInput(BaseModel):
    """Input schema for MemorySaveNode."""

    content: str = Field(
        ...,
        description="Content to save as memory",
        min_length=10,
    )
    memory_type: str = Field(
        default="insight",
        description="Type: fact, pattern, preference, error, insight, context",
    )
    scope: str = Field(
        default="session",
        description="Scope: 'global', 'project', or 'session'",
    )
    project_id: int | None = Field(
        default=None,
        description="Project ID for project-scoped memories",
    )
    category: str | None = Field(
        default=None,
        description="Category name (auto-classified if not provided)",
    )
    subcategory: str | None = Field(
        default=None,
        description="Sub-category name",
    )
    importance: float | None = Field(
        default=None,
        description="Importance 0.0-1.0 (auto-set if not provided)",
    )
    tags: list[str] | None = Field(
        default=None,
        description="Tags for the memory",
    )
    source_context: str | None = Field(
        default=None,
        description="Additional context about where this insight came from",
    )
    file_path: str | None = Field(
        default=None,
        description="Associated file path if relevant",
    )
    structured_data: dict[str, Any] | None = Field(
        default=None,
        description="Optional structured data (JSON)",
    )


class MemorySaveNodeOutput(BaseModel):
    """Output schema for MemorySaveNode."""

    memory_id: int | None = Field(
        None,
        description="ID of the saved memory",
    )
    saved_successfully: bool = Field(
        False,
        description="Whether the save was successful",
    )
    category: str | None = Field(
        None,
        description="Category assigned to the memory",
    )
    subcategory: str | None = Field(
        None,
        description="Sub-category assigned to the memory",
    )
    scope: str | None = Field(
        None,
        description="Scope of the saved memory",
    )
    importance: float | None = Field(
        None,
        description="Final importance score assigned",
    )
    error: str | None = Field(
        None,
        description="Error message if save failed",
    )


class MemorySaveNode(BaseNode):
    """Save important insights as memories.

    This node allows agents to explicitly save learnings,
    patterns, and important context discovered during execution.
    Useful for capturing key insights that should be remembered
    across sessions.

    Example usage:
        After a complex analysis, save the key findings:
        "Discovered that the auth system uses JWT with refresh tokens"

        After a bug fix, save the solution:
        "Fixed race condition by adding transaction lock in user_service.py"
    """

    def __init__(
        self,
        node_id: str = "memory_save",
        memory_service: MemoryService | None = None,
    ) -> None:
        """Initialize MemorySaveNode.

        Args:
            node_id: Unique identifier for this node
            memory_service: Optional MemoryService instance
        """
        super().__init__(
            node_id=node_id,
            node_type=NodeType.MEMORY,
            category=NodeCategory.DATA_PROCESSING,
            description="Save important insights as memories.",
        )

        self.config.required_inputs = {
            "content",
        }
        self.config.outputs = {
            "memory_id",
            "saved_successfully",
            "category",
            "subcategory",
            "scope",
            "importance",
        }

        self._memory_service = memory_service

    async def _on_initialize(self) -> None:
        """Initialize the MemoryService if not provided."""
        if self._memory_service is None:
            self._memory_service = MemoryService()
            await self._memory_service.initialize()

    async def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """Execute memory save.

        Args:
            state: Current graph state containing inputs

        Returns:
            State enriched with save result
        """
        start_time = time.time()

        try:
            # Extract inputs
            content = state.get("content", "")
            memory_type = state.get("memory_type", "insight")
            scope = state.get("scope", "session")
            project_id = state.get("project_id")
            category = state.get("category")
            subcategory = state.get("subcategory")
            importance = state.get("importance")
            tags = state.get("tags")
            source_context = state.get("source_context")
            file_path = state.get("file_path")
            structured_data = state.get("structured_data")

            # Get agent context from state
            agent_id = state.get("agent_id")
            session_id = state.get("session_id")

            # Enhance content with source context if provided
            if source_context:
                content = f"{content}\n\nSource Context: {source_context}"

            _logger.debug(
                "memory_save_start",
                node_id=self.node_id,
                content_preview=content[:100],
                memory_type=memory_type,
                scope=scope,
            )

            # Initialize service
            if not self._memory_service:
                await self._on_initialize()

            # Save memory
            memory = await self._memory_service.save_memory(
                content=content,
                memory_type=memory_type,
                scope=scope,
                project_id=project_id,
                session_id=session_id,
                category=category,
                subcategory=subcategory,
                importance=importance,
                source_agent_id=agent_id,
                tags=tags,
                file_path=file_path,
                structured_data=structured_data,
                generate_embedding=True,
            )

            # Build output
            output = MemorySaveNodeOutput(
                memory_id=memory.id,
                saved_successfully=True,
                category=memory.category.name if memory.category else None,
                scope=memory.scope,
                importance=memory.importance,
            )

            duration = time.time() - start_time
            _logger.info(
                "memory_save_complete",
                node_id=self.node_id,
                memory_id=memory.id,
                duration=duration,
                category=output.category,
                scope=scope,
            )

            return {**state, **output.model_dump()}

        except Exception as e:
            duration = time.time() - start_time
            _logger.error(
                "memory_save_failed",
                node_id=self.node_id,
                duration=duration,
                error=str(e),
            )

            return {
                **state,
                "memory_id": None,
                "saved_successfully": False,
                "error": str(e),
            }

    def validate_inputs(self, state: dict[str, Any]) -> list[str]:
        """Validate required inputs."""
        errors = []

        content = state.get("content", "")
        if not content:
            errors.append("Missing required input: content")
        elif len(content) < 10:
            errors.append("Content too short (minimum 10 characters)")

        # Validate scope
        scope = state.get("scope", "session")
        valid_scopes = ["global", "project", "session"]
        if scope not in valid_scopes:
            errors.append(f"Invalid scope: {scope}. Must be one of: {valid_scopes}")

        # Validate project_id if scope is project
        if scope == "project" and not state.get("project_id"):
            errors.append("project_id is required when scope is 'project'")

        return errors

    def get_input_schema(self) -> type[BaseModel]:
        """Get the input schema for this node."""
        return MemorySaveNodeInput

    def get_output_schema(self) -> type[BaseModel]:
        """Get the output schema for this node."""
        return MemorySaveNodeOutput
