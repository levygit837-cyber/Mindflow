"""Event Bus Memory Observer for the Intelligent Memory System.

Observes graph executions asynchronously via AgentLogBus,
analyzing events in real-time to extract insights and patterns.

This observer runs continuously during graph execution and:
- Buffers events for batch processing
- Extracts insights using LLM periodically
- Saves memories to the unified memory system
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.memory.memory_service import MemoryService, SearchMode
from mindflow_backend.runtime.monitoring.log_bus import AgentLogBus

if TYPE_CHECKING:
    from mindflow_backend.memory.category_manager import CategoryManager

_logger = get_logger(__name__)


@dataclass
class EventBuffer:
    """Buffer for batching events before processing."""

    events: list[dict[str, Any]] = field(default_factory=list)
    start_time: datetime = field(default_factory=lambda: datetime.now(UTC))
    agent_contexts: dict[str, dict] = field(default_factory=dict)


class EventBusMemoryObserver:
    """Async observer that monitors graph executions via AgentLogBus.

    Runs as a background task, receiving events from the AgentLogBus
    and periodically extracting insights to save as memories.

    Features:
    - Event buffering for efficient batch processing
    - Cross-agent pattern detection
    - Automatic categorization
    - Rate limiting and deduplication
    """

    # Configuration
    BUFFER_FLUSH_INTERVAL = 30  # seconds
    BUFFER_MAX_SIZE = 100  # max events before forced flush
    RATE_LIMIT_PER_MINUTE = 20  # max memories saved per minute
    MIN_IMPORTANCE_THRESHOLD = 0.4

    def __init__(
        self,
        memory_service: MemoryService,
        category_manager: CategoryManager | None = None,
        buffer_interval: float | None = None,
    ) -> None:
        """Initialize the Event Bus Memory Observer.

        Args:
            memory_service: Service for saving and searching memories
            category_manager: Optional category manager for classification
            buffer_interval: Custom buffer flush interval in seconds
        """
        self.memory_service = memory_service
        self.category_manager = category_manager
        self.buffer_interval = buffer_interval or self.BUFFER_FLUSH_INTERVAL

        # State
        self._running = False
        self._task: asyncio.Task | None = None
        self._buffer = EventBuffer()
        self._buffer_lock = asyncio.Lock()

        # Rate limiting
        self._memories_this_minute = 0
        self._last_rate_reset = datetime.now(UTC)

        # Tracking
        self._observed_missions: set[str] = set()
        self._processed_events: set[str] = set()  # For deduplication
        self._session_insights: dict[str, list[str]] = defaultdict(list)

    async def start_observing(self, mission_ids: list[str] | None = None) -> None:
        """Start observing graph executions.

        Args:
            mission_ids: Optional list of mission IDs to observe
        """
        if self._running:
            return

        self._running = True

        # Subscribe to AgentLogBus
        log_bus = AgentLogBus()

        if mission_ids:
            for mission_id in mission_ids:
                log_bus.subscribe_to_mission(
                    mission_id=mission_id,
                    observer_id=f"event_bus_observer_{id(self)}",
                    handler=self._on_event,
                )
                self._observed_missions.add(mission_id)

        # Start background processing
        self._task = asyncio.create_task(
            self._processing_loop(),
            name=f"event_bus_observer_{id(self)}",
        )

        _logger.info(
            "event_bus_observer_started",
            mission_count=len(mission_ids or []),
        )

    async def stop_observing(self) -> None:
        """Stop observing and cleanup."""
        self._running = False

        # Unsubscribe from all missions
        log_bus = AgentLogBus()
        observer_id = f"event_bus_observer_{id(self)}"

        for mission_id in self._observed_missions:
            # Note: unsubscribe_from_mission needs the handler, so this is simplified
            pass

        # Cancel background task
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        # Flush remaining events
        await self._flush_buffer()

        _logger.info(
            "event_bus_observer_stopped",
            total_missions=len(self._observed_missions),
        )

    async def _on_event(self, event: dict[str, Any]) -> None:
        """Handle incoming event from AgentLogBus.

        Args:
            event: Event dict from the log bus
        """
        if not self._running:
            return

        # Deduplication
        event_id = self._get_event_id(event)
        if event_id in self._processed_events:
            return
        self._processed_events.add(event_id)

        # Cleanup old processed events periodically
        if len(self._processed_events) > 10000:
            self._processed_events.clear()

        async with self._buffer_lock:
            self._buffer.events.append(event)

            # Track agent context
            agent_id = event.get("agent_id", "unknown")
            if agent_id not in self._buffer.agent_contexts:
                self._buffer.agent_contexts[agent_id] = {
                    "event_count": 0,
                    "tools_used": set(),
                    "files_modified": set(),
                }

            ctx = self._buffer.agent_contexts[agent_id]
            ctx["event_count"] += 1

            # Track tool usage
            if event.get("type") == "tool_result":
                tool_name = event.get("data", {}).get("tool_name")
                if tool_name:
                    ctx["tools_used"].add(tool_name)

            # Track file modifications
            code_info = self._extract_code_change(event)
            if code_info:
                ctx["files_modified"].add(code_info["file_path"])

            # Force flush if buffer is full
            if len(self._buffer.events) >= self.BUFFER_MAX_SIZE:
                await self._flush_buffer()

    async def _processing_loop(self) -> None:
        """Main processing loop."""
        while self._running:
            try:
                await asyncio.sleep(self.buffer_interval)
                await self._flush_buffer()
                await self._reset_rate_limit()
            except asyncio.CancelledError:
                break
            except Exception as e:
                _logger.error("event_bus_observer_loop_error", error=str(e))

    async def _flush_buffer(self) -> None:
        """Flush event buffer and extract insights."""
        async with self._buffer_lock:
            if not self._buffer.events:
                return

            # Get current buffer and reset
            events_to_process = self._buffer.events
            agent_contexts = dict(self._buffer.agent_contexts)

            self._buffer = EventBuffer()

        try:
            # Extract and save insights
            await self._extract_and_save_insights(events_to_process, agent_contexts)

        except Exception as e:
            _logger.error("event_bus_flush_error", error=str(e))

    async def _extract_and_save_insights(
        self,
        events: list[dict[str, Any]],
        agent_contexts: dict[str, dict],
    ) -> None:
        """Extract insights from events and save as memories.

        Args:
            events: List of events to analyze
            agent_contexts: Aggregated context per agent
        """
        # Skip if rate limited
        if self._memories_this_minute >= self.RATE_LIMIT_PER_MINUTE:
            _logger.debug("event_bus_rate_limited", skipped_events=len(events))
            return

        # Analyze events for patterns
        insights = self._analyze_events(events, agent_contexts)

        # Save insights as memories
        for insight in insights:
            if self._memories_this_minute >= self.RATE_LIMIT_PER_MINUTE:
                break

            try:
                await self.memory_service.save_memory(
                    content=insight["content"],
                    memory_type=insight["memory_type"],
                    scope=insight.get("scope", "session"),
                    project_id=insight.get("project_id"),
                    session_id=insight.get("session_id"),
                    category=insight.get("category"),
                    subcategory=insight.get("subcategory"),
                    importance=insight.get("importance", 0.5),
                    source_agent_id=insight.get("agent_id"),
                    source_tool=insight.get("tool_name"),
                    tags=insight.get("tags", []),
                    generate_embedding=True,
                )
                self._memories_this_minute += 1

            except Exception as e:
                _logger.warning("event_bus_save_insight_failed", error=str(e))

    def _analyze_events(
        self,
        events: list[dict[str, Any]],
        agent_contexts: dict[str, dict],
    ) -> list[dict[str, Any]]:
        """Analyze events and extract insights.

        Uses heuristics and pattern detection (no LLM calls here,
        those happen in SessionReviewWorker).

        Args:
            events: List of events
            agent_contexts: Per-agent aggregated context

        Returns:
            List of insight dicts ready to be saved as memories
        """
        insights: list[dict[str, Any]] = []

        # Group events by type
        events_by_type: dict[str, list[dict]] = defaultdict(list)
        for event in events:
            event_type = event.get("type", "unknown")
            events_by_type[event_type].append(event)

        # Analyze tool usage patterns
        if "tool_result" in events_by_type:
            tool_insights = self._analyze_tool_patterns(
                events_by_type["tool_result"], agent_contexts
            )
            insights.extend(tool_insights)

        # Analyze code changes
        code_changes = [e for e in events if self._extract_code_change(e)]
        if code_changes:
            code_insights = self._analyze_code_patterns(code_changes)
            insights.extend(code_insights)

        # Analyze execution patterns
        execution_insights = self._analyze_execution_patterns(events_by_type)
        insights.extend(execution_insights)

        # Detect errors and solutions
        error_events = [e for e in events if e.get("level") in ("ERROR", "WARNING")]
        if error_events:
            error_insights = self._analyze_errors(error_events)
            insights.extend(error_insights)

        return insights

    def _analyze_tool_patterns(
        self,
        tool_events: list[dict],
        agent_contexts: dict[str, dict],
    ) -> list[dict[str, Any]]:
        """Analyze tool usage patterns."""
        insights: list[dict] = []

        # Count tool usage
        tool_counts: dict[str, int] = defaultdict(int)
        for event in tool_events:
            tool_name = event.get("data", {}).get("tool_name", "unknown")
            tool_counts[tool_name] += 1

        # Detect frequently used tools
        total_tools = len(tool_events)
        for tool_name, count in tool_counts.items():
            if count > 3 and count / total_tools > 0.3:
                insights.append({
                    "content": f"Agent frequently uses tool '{tool_name}' ({count} times in this session). "
                              f"This suggests '{tool_name}' is important for the current workflow.",
                    "memory_type": "pattern",
                    "category": "tool_usage",
                    "importance": 0.5 + min(count / 10, 0.3),
                    "tags": ["tool_usage", tool_name, "pattern"],
                })

        return insights

    def _analyze_code_patterns(
        self,
        code_events: list[dict],
    ) -> list[dict[str, Any]]:
        """Analyze code modification patterns."""
        insights: list[dict] = []

        # Group by file extension
        files_by_ext: dict[str, list[str]] = defaultdict(list)
        for event in code_events:
            code_info = self._extract_code_change(event)
            if code_info:
                file_path = code_info["file_path"]
                ext = file_path.split(".")[-1] if "." in file_path else "unknown"
                files_by_ext[ext].append(file_path)

        # Detect file type patterns
        for ext, files in files_by_ext.items():
            if len(files) > 3:
                insights.append({
                    "content": f"Significant activity on .{ext} files ({len(files)} modifications). "
                              f"Files: {', '.join(files[:3])}{'...' if len(files) > 3 else ''}",
                    "memory_type": "pattern",
                    "category": "code_patterns",
                    "importance": 0.6,
                    "tags": ["code_pattern", ext, "files"],
                })

        return insights

    def _analyze_execution_patterns(
        self,
        events_by_type: dict[str, list[dict]],
    ) -> list[dict[str, Any]]:
        """Analyze execution flow patterns."""
        insights: list[dict] = []

        # Detect decision patterns
        if "agent_decision" in events_by_type:
            decisions = events_by_type["agent_decision"]
            if len(decisions) > 2:
                insights.append({
                    "content": f"Agent made {len(decisions)} explicit decisions during execution. "
                              f"This indicates complex reasoning was required.",
                    "memory_type": "insight",
                    "category": "execution_patterns",
                    "importance": 0.5,
                    "tags": ["execution", "decisions", "reasoning"],
                })

        return insights

    def _analyze_errors(
        self,
        error_events: list[dict],
    ) -> list[dict[str, Any]]:
        """Analyze error patterns."""
        insights: list[dict] = []

        # Group errors by type
        errors_by_type: dict[str, list[dict]] = defaultdict(list)
        for event in error_events:
            error_msg = event.get("data", {}).get("error", "unknown")
            error_type = error_msg.split(":")[0] if ":" in error_msg else "unknown"
            errors_by_type[error_type].append(event)

        # Detect recurring errors
        for error_type, errors in errors_by_type.items():
            if len(errors) > 1:
                insights.append({
                    "content": f"Recurring error type '{error_type}' occurred {len(errors)} times. "
                              f"This may indicate a systemic issue that needs attention.",
                    "memory_type": "error",
                    "category": "error_patterns",
                    "importance": 0.8,  # High importance for errors
                    "tags": ["error", error_type, "recurring"],
                })

        return insights

    def _extract_code_change(self, event: dict[str, Any]) -> dict[str, Any] | None:
        """Extract code change info from event."""
        event_type = event.get("type", "")
        data = event.get("data", {})

        if event_type == "tool_result":
            tool_name = data.get("tool_name", "")
            if tool_name in ("write_file", "edit_file", "replace_in_file"):
                file_path = data.get("file_path") or data.get("path")
                if file_path:
                    return {
                        "file_path": file_path,
                        "operation": tool_name,
                        "lines": data.get("lines_modified", {}),
                    }

        return None

    def _get_event_id(self, event: dict[str, Any]) -> str:
        """Generate unique ID for event (for deduplication)."""
        agent_id = event.get("agent_id", "unknown")
        event_type = event.get("type", "unknown")
        timestamp = event.get("timestamp", "")
        message = event.get("message", "")[:50]

        import hashlib

        content = f"{agent_id}:{event_type}:{timestamp}:{message}"
        return hashlib.md5(content.encode()).hexdigest()[:16]

    async def _reset_rate_limit(self) -> None:
        """Reset rate limit counter every minute."""
        now = datetime.now(UTC)
        if (now - self._last_rate_reset) >= timedelta(minutes=1):
            self._memories_this_minute = 0
            self._last_rate_reset = now

    def get_stats(self) -> dict[str, Any]:
        """Get observer statistics."""
        return {
            "running": self._running,
            "observed_missions": len(self._observed_missions),
            "buffer_size": len(self._buffer.events),
            "memories_this_minute": self._memories_this_minute,
            "processed_events": len(self._processed_events),
        }
