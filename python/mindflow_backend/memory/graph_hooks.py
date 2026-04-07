"""Memory hooks for automatic integration with graph execution.

Provides hooks that can be registered with the graph execution system
to automatically:
- Inject memory context at graph start
- Observe tool executions
- Flush observers at checkpoints
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.memory.category_manager import MemoryScope
from mindflow_backend.memory.observers import MemoryObserverCoordinator, ObserverConfig

if TYPE_CHECKING:
    from mindflow_backend.memory.memory_service import MemoryService

_logger = get_logger(__name__)


class MemoryHooks:
    """Hooks for automatic memory integration in graph execution.

    Usage:
        hooks = MemoryHooks()

        # Before graph execution
        await hooks.on_graph_start(
            graph_execution_id="exec_123",
            initial_state={"task": "...", "project_id": 1},
            config={"auto_memory_recall": True},
        )

        # After each tool execution (called by executor)
        await hooks.on_tool_executed(
            graph_execution_id="exec_123",
            tool_name="write_file",
            tool_result={...},
            context={"agent_id": "..."},
        )

        # At checkpoint (before graph ends)
        await hooks.on_graph_checkpoint("exec_123")

        # At graph end
        await hooks.on_graph_end("exec_123")
    """

    def __init__(
        self,
        memory_service: "MemoryService" | None = None,
    ) -> None:
        """Initialize memory hooks.

        Args:
            memory_service: Optional MemoryService instance
        """
        self.memory_service = memory_service
        self._coordinators: dict[str, MemoryObserverCoordinator] = {}
        self._recall_cache: dict[str, str] = {}  # graph_id -> context_summary

    async def on_graph_start(
        self,
        graph_execution_id: str,
        initial_state: dict[str, Any],
        config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Called when a graph execution starts.

        Can optionally inject memory context into initial state.

        Args:
            graph_execution_id: Unique graph execution ID
            initial_state: Initial graph state
            config: Configuration dict
                - auto_memory_recall: Inject memories automatically
                - observer_enabled: Enable observation
                - observer_config: ObserverConfig dict

        Returns:
            Potentially modified initial_state
        """
        config = config or {}
        task = initial_state.get("task", "")
        project_id = initial_state.get("project_id")

        _logger.debug(
            "memory_hook_graph_start",
            graph_execution_id=graph_execution_id,
            auto_recall=config.get("auto_memory_recall", False),
        )

        # Initialize MemoryService if needed
        if self.memory_service is None:
            from mindflow_backend.memory.memory_service import MemoryService
            self.memory_service = MemoryService()
            await self.memory_service.initialize()

        # Auto memory recall
        if config.get("auto_memory_recall") and task:
            try:
                context_summary = await self._perform_memory_recall(
                    task=task,
                    project_id=project_id,
                    recent_context=initial_state.get("recent_context"),
                )

                if context_summary:
                    self._recall_cache[graph_execution_id] = context_summary
                    initial_state["memory_context"] = context_summary
                    _logger.debug(
                        "memory_hook_injected_context",
                        graph_execution_id=graph_execution_id,
                        context_length=len(context_summary),
                    )

            except Exception as e:
                _logger.warning(
                    "memory_hook_recall_failed",
                    graph_execution_id=graph_execution_id,
                    error=str(e),
                )

        # Initialize observer coordinator
        if config.get("observer_enabled", True):
            coordinator = MemoryObserverCoordinator(
                memory_service=self.memory_service,
            )

            observer_config = config.get("observer_config", {})
            await coordinator.configure_for_graph(
                graph_execution_id=graph_execution_id,
                mission_ids=initial_state.get("mission_ids"),
                config=ObserverConfig(
                    event_bus_enabled=observer_config.get("event_bus", True),
                    post_tool_enabled=observer_config.get("post_tool", True),
                ),
                project_id=project_id,
                session_id=initial_state.get("session_id"),
            )

            self._coordinators[graph_execution_id] = coordinator

        return initial_state

    async def on_tool_executed(
        self,
        graph_execution_id: str,
        tool_name: str,
        tool_result: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> None:
        """Called after each tool execution.

        Routes tool result to the observer coordinator for analysis.

        Args:
            graph_execution_id: Current graph execution ID
            tool_name: Name of the tool that executed
            tool_result: Tool execution result
            context: Optional execution context
        """
        coordinator = self._coordinators.get(graph_execution_id)
        if not coordinator:
            return

        try:
            await coordinator.on_tool_result(
                tool_name=tool_name,
                tool_result=tool_result,
                context=context,
            )
        except Exception as e:
            _logger.debug(
                "memory_hook_tool_observer_error",
                graph_execution_id=graph_execution_id,
                tool_name=tool_name,
                error=str(e),
            )

    async def on_graph_checkpoint(self, graph_execution_id: str) -> None:
        """Called at graph checkpoint (e.g., before pausing).

        Flushes pending observations to ensure no data is lost.

        Args:
            graph_execution_id: Current graph execution ID
        """
        coordinator = self._coordinators.get(graph_execution_id)
        if not coordinator:
            return

        try:
            await coordinator.flush()
            _logger.debug(
                "memory_hook_checkpoint_flush",
                graph_execution_id=graph_execution_id,
            )
        except Exception as e:
            _logger.debug(
                "memory_hook_flush_error",
                graph_execution_id=graph_execution_id,
                error=str(e),
            )

    async def on_graph_end(
        self,
        graph_execution_id: str,
        final_state: dict[str, Any] | None = None,
    ) -> None:
        """Called when graph execution ends.

        Shuts down observers and cleans up.

        Args:
            graph_execution_id: Current graph execution ID
            final_state: Optional final graph state
        """
        coordinator = self._coordinators.pop(graph_execution_id, None)

        if coordinator:
            try:
                await coordinator.shutdown()
                _logger.debug(
                    "memory_hook_observer_shutdown",
                    graph_execution_id=graph_execution_id,
                )
            except Exception as e:
                _logger.debug(
                    "memory_hook_shutdown_error",
                    graph_execution_id=graph_execution_id,
                    error=str(e),
                )

        # Cleanup cache
        self._recall_cache.pop(graph_execution_id, None)

    async def _perform_memory_recall(
        self,
        task: str,
        project_id: int | None,
        recent_context: str | None,
    ) -> str:
        """Perform memory recall and return formatted context.

        Args:
            task: Task description
            project_id: Optional project ID
            recent_context: Optional recent context

        Returns:
            Formatted context summary
        """
        from mindflow_backend.memory.memory_service import SearchMode

        query = task
        if recent_context:
            query = f"{task}\n\nContext: {recent_context[:500]}"

        results = await self.memory_service.search_memories(
            query=query,
            scope="project" if project_id else "global",
            project_id=project_id,
            search_mode=SearchMode.HYBRID,
            limit=10,
            min_importance=0.4,
        )

        if not results:
            return ""

        # Format similar to MemoryRecallNode
        from collections import defaultdict

        by_category: dict[str, list] = defaultdict(list)
        for result in results:
            category = result.memory.category.name if result.memory.category else "General"
            by_category[category].append(result)

        sections = [
            "## Relevant Context from Memory System",
            f"*Retrieved {len(results)} relevant memories*\n",
        ]

        for category, memories in by_category.items():
            category_display = category.replace("_", " ").title()
            sections.append(f"### {category_display}")

            for i, result in enumerate(memories[:5], 1):
                memory = result.memory
                content = memory.content[:200] + "..." if len(memory.content) > 200 else memory.content
                sections.append(f"{i}. {content}")

            sections.append("")

        return "\n".join(sections)

    def get_coordinator(self, graph_execution_id: str) -> MemoryObserverCoordinator | None:
        """Get the coordinator for a graph execution.

        Args:
            graph_execution_id: Graph execution ID

        Returns:
            MemoryObserverCoordinator or None
        """
        return self._coordinators.get(graph_execution_id)

    def get_injected_context(self, graph_execution_id: str) -> str | None:
        """Get the memory context injected at graph start.

        Args:
            graph_execution_id: Graph execution ID

        Returns:
            Injected context or None
        """
        return self._recall_cache.get(graph_execution_id)
