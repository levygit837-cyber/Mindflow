"""Memory Observer Coordinator for the Intelligent Memory System.

Coordinates multiple memory observers (EventBus, PostToolUse)
and manages their configuration and execution.

Provides:
- Unified configuration for all observers
- Lifecycle management (start/stop)
- Event routing to appropriate observer
- Statistics aggregation
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.memory.category_manager import CategoryManager
from mindflow_backend.memory.memory_service import MemoryService
from mindflow_backend.memory.observers.event_bus_observer import EventBusMemoryObserver
from mindflow_backend.memory.observers.post_tool_observer import PostToolUseObserver

_logger = get_logger(__name__)


@dataclass
class ObserverConfig:
    """Configuration for memory observers."""

    event_bus_enabled: bool = True
    event_buffer_interval: float = 30.0
    event_rate_limit: int = 20

    post_tool_enabled: bool = True
    post_tool_analyze_diffs: bool = True

    min_importance_threshold: float = 0.4
    auto_classify: bool = True


class MemoryObserverCoordinator:
    """Coordinates all memory observers for a graph execution.

    This is the main entry point for configuring and managing
    memory observation during graph execution.

    Example:
        coordinator = MemoryObserverCoordinator(memory_service)

        # Configure for a specific graph
        config = ObserverConfig(
            event_bus_enabled=True,
            post_tool_enabled=True,
        )

        # Start observing
        await coordinator.configure_for_graph(
            graph_execution_id="exec_123",
            mission_ids=["mission_1", "mission_2"],
            config=config,
        )

        # Use during execution
        await coordinator.on_tool_result(tool_name, tool_result, context)

        # Cleanup
        await coordinator.shutdown()
    """

    def __init__(
        self,
        memory_service: MemoryService,
        category_manager: CategoryManager | None = None,
    ) -> None:
        """Initialize the coordinator.

        Args:
            memory_service: Service for saving memories
            category_manager: Optional category manager
        """
        self.memory_service = memory_service
        self.category_manager = category_manager or CategoryManager()

        # Observers
        self._event_bus_observer: EventBusMemoryObserver | None = None
        self._post_tool_observer: PostToolUseObserver | None = None

        # Configuration
        self._config: ObserverConfig | None = None
        self._graph_execution_id: str | None = None
        self._is_running = False

    async def configure_for_graph(
        self,
        graph_execution_id: str,
        mission_ids: list[str] | None = None,
        config: ObserverConfig | None = None,
        project_id: int | None = None,
        session_id: str | None = None,
    ) -> None:
        """Configure observers for a graph execution.

        Args:
            graph_execution_id: Unique ID for this graph execution
            mission_ids: Optional list of mission IDs to observe
            config: Observer configuration
            project_id: Optional project ID for scoping memories
            session_id: Optional session ID for tracking
        """
        self._config = config or ObserverConfig()
        self._graph_execution_id = graph_execution_id

        _logger.info(
            "observer_coordinator_configured",
            graph_execution_id=graph_execution_id,
            event_bus=self._config.event_bus_enabled,
            post_tool=self._config.post_tool_enabled,
        )

        # Initialize EventBusObserver
        if self._config.event_bus_enabled:
            self._event_bus_observer = EventBusMemoryObserver(
                memory_service=self.memory_service,
                category_manager=self.category_manager,
                buffer_interval=self._config.event_buffer_interval,
            )

            if mission_ids:
                await self._event_bus_observer.start_observing(mission_ids)

        # Initialize PostToolUseObserver
        if self._config.post_tool_enabled:
            self._post_tool_observer = PostToolUseObserver(
                memory_service=self.memory_service,
                category_manager=self.category_manager,
            )

        self._is_running = True

    async def on_tool_result(
        self,
        tool_name: str,
        tool_result: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> None:
        """Route tool result to PostToolUse observer.

        This method should be called by the ToolExecutor after
        each tool execution.

        Args:
            tool_name: Name of the tool
            tool_result: Tool execution result
            context: Optional context (agent_id, session_id, project_id)
        """
        if not self._is_running or not self._post_tool_observer:
            return

        # Only process if the tool can be analyzed
        if not self._post_tool_observer.can_analyze(tool_name):
            return

        try:
            await self._post_tool_observer.on_tool_result(
                tool_name=tool_name,
                tool_result=tool_result,
                context=context,
            )
        except Exception as e:
            _logger.debug(
                "post_tool_observer_error",
                tool_name=tool_name,
                error=str(e),
            )

    async def on_event(self, event: dict[str, Any]) -> None:
        """Route event to EventBus observer.

        This method is automatically called by the AgentLogBus
        when the observer is subscribed to missions.

        Args:
            event: Event dict from AgentLogBus
        """
        if not self._is_running or not self._event_bus_observer:
            return

        try:
            await self._event_bus_observer._on_event(event)
        except Exception as e:
            _logger.debug(
                "event_bus_observer_error",
                error=str(e),
            )

    async def flush(self) -> None:
        """Flush any pending events from observers.

        Call this before shutdown or at checkpoint moments.
        """
        if self._event_bus_observer:
            await self._event_bus_observer._flush_buffer()

        _logger.debug("observer_coordinator_flushed")

    async def shutdown(self) -> None:
        """Shutdown all observers and cleanup."""
        if not self._is_running:
            return

        # Flush pending events
        await self.flush()

        # Stop EventBusObserver
        if self._event_bus_observer:
            await self._event_bus_observer.stop_observing()
            self._event_bus_observer = None

        # PostToolUseObserver doesn't need explicit shutdown
        self._post_tool_observer = None

        self._is_running = False
        self._config = None
        self._graph_execution_id = None

        _logger.info("observer_coordinator_shutdown")

    def get_stats(self) -> dict[str, Any]:
        """Get statistics from all observers."""
        stats = {
            "running": self._is_running,
            "graph_execution_id": self._graph_execution_id,
        }

        if self._event_bus_observer:
            stats["event_bus"] = self._event_bus_observer.get_stats()

        if self._post_tool_observer:
            stats["post_tool"] = {
                "enabled": True,
                "analyzable_tools": len(self._post_tool_observer.ANALYZABLE_TOOLS),
            }

        return stats

    def is_running(self) -> bool:
        """Check if coordinator is running."""
        return self._is_running

    def get_config(self) -> ObserverConfig | None:
        """Get current configuration."""
        return self._config
