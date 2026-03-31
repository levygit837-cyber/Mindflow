"""Orchestration service interfaces for MindFlow backend.

This module defines interfaces for task decomposition, agent coordination,
and intelligent routing in complex workflows.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class OrchestrationServiceInterface(Protocol):
    """Interface for orchestration service operations."""
    
    async def decompose_task(
        self,
        task_description: str,
        session_id: str | None = None,
        complexity_level: str | None = None
    ) -> dict[str, Any]:
        """Decompose a task."""
        ...
    
    async def select_specialist(
        self,
        task_id: str,
        task_description: str,
        task_complexity: str,
        current_specialist: str | None = None
    ) -> dict[str, Any]:
        """Select personality for task."""
        ...
    
    async def execute_dag(
        self,
        dag_id: str,
        session_id: str | None = None
    ) -> dict[str, Any]:
        """Execute a DAG."""
        ...
    
    async def coordinate_agents(
        self,
        task_id: str,
        agent_sequence: list[str],
        session_id: str | None = None
    ) -> dict[str, Any]:
        """Coordinate agents."""
        ...
    
    async def get_execution_status(self, execution_id: str) -> dict[str, Any]:
        """Get execution status."""
        ...
    
    async def create_workflow(
        self,
        workflow_definition: dict[str, Any]
    ) -> dict[str, Any]:
        """Create new workflow."""
        ...
    
    async def execute_workflow(
        self,
        workflow_id: str,
        input_data: dict[str, Any],
        session_id: str | None = None
    ) -> dict[str, Any]:
        """Execute workflow."""
        ...


@runtime_checkable
class TaskServiceInterface(Protocol):
    """Interface for task management operations."""
    
    async def create_task(
        self,
        task_description: str,
        task_type: str,
        session_id: str | None = None,
        priority: str = "medium"
    ) -> dict[str, Any]:
        """Create a new task."""
        ...
    
    async def get_task(self, task_id: str) -> dict[str, Any]:
        """Get task details."""
        ...
    
    async def update_task_status(
        self,
        task_id: str,
        status: str,
        result: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Update task status."""
        ...
    
    async def list_tasks(
        self,
        session_id: str | None = None,
        status: str | None = None,
        limit: int = 50
    ) -> list[dict[str, Any]]:
        """List tasks."""
        ...
    
    async def get_task_dependencies(self, task_id: str) -> list[dict[str, Any]]:
        """Get task dependencies."""
        ...
    
    async def add_task_dependency(
        self,
        task_id: str,
        depends_on_task_id: str
    ) -> dict[str, Any]:
        """Add task dependency."""
        ...
    
    async def calculate_task_complexity(self, task_description: str) -> dict[str, Any]:
        """Calculate task complexity score."""
        ...
    
    async def optimize_task_order(self, tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Optimize task execution order."""
        ...


@runtime_checkable
class RoutingServiceInterface(Protocol):
    """Interface for intelligent routing operations."""
    
    async def route_message(
        self,
        message: str,
        session_context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Route message to appropriate agent."""
        ...
    
    async def select_agent_for_task(
        self,
        task_description: str,
        task_complexity: str,
        available_agents: list[str]
    ) -> dict[str, Any]:
        """Select optimal agent for task."""
        ...
    
    async def get_routing_rules(self) -> list[dict[str, Any]]:
        """Get routing rules."""
        ...
    
    async def update_routing_rule(
        self,
        rule_id: str,
        rule_definition: dict[str, Any]
    ) -> dict[str, Any]:
        """Update routing rule."""
        ...
    
    async def analyze_message_intent(self, message: str) -> dict[str, Any]:
        """Analyze message intent for routing."""
        ...
    
    async def get_routing_performance_metrics(self) -> dict[str, Any]:
        """Get routing performance metrics."""
        ...
    
    async def optimize_routing_strategy(self) -> dict[str, Any]:
        """Optimize routing strategy based on performance."""
        ...


@runtime_checkable
class TodoPlanningServiceInterface(Protocol):
    """Interface for session-scoped planning/todo-list operations."""

    async def replace_list(
        self,
        session_id: str,
        task_id: str,
        goal: str,
        items: list[dict[str, Any]],
        source: str,
    ) -> Any:
        """Replace the current todo list for a task."""
        ...

    async def get_list(self, session_id: str, task_id: str) -> Any:
        """Return the current todo list for a task."""
        ...

    async def get_session_lists(self, session_id: str) -> list[Any]:
        """Return all todo lists associated with a session."""
        ...

    async def update_item_status(
        self,
        session_id: str,
        task_id: str,
        item_id: str,
        status: str,
        notes: str | None = None,
    ) -> Any:
        """Update the state for a single todo item."""
        ...

    async def focus_complex_items(
        self,
        session_id: str,
        task_id: str,
        limit: int = 3,
    ) -> Any:
        """Return the most relevant open todo items."""
        ...

    async def is_stale(self, session_id: str, task_id: str) -> bool:
        """Return whether the todo list is missing or outdated."""
        ...
