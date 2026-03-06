"""Agent task definitions and utilities."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.workers.infrastructure.queue_manager import get_queue_manager

_logger = get_logger(__name__)


@dataclass
class AgentTask:
    """Base class for agent tasks."""
    
    task_type: str
    session_id: str
    agent_type: str
    priority: str = "medium"
    task_data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self) -> None:
        """Generate task ID if not provided."""
        if "task_id" not in self.metadata:
            self.metadata["task_id"] = str(uuid.uuid4())
    
    @property
    def task_id(self) -> str:
        """Get task ID."""
        return self.metadata["task_id"]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary for queue publishing."""
        return {
            "task_type": self.task_type,
            "task_id": self.task_id,
            "session_id": self.session_id,
            "agent_type": self.agent_type,
            "priority": self.priority,
            "task_data": self.task_data,
            "metadata": self.metadata,
        }


class AgentTaskDefinitions:
    """Definitions and utilities for agent tasks."""
    
    # Coder Agent Tasks
    @staticmethod
    def create_code_analysis_task(
        session_id: str,
        file_path: str,
        analysis_type: str = "basic",
        priority: str = "medium",
    ) -> AgentTask:
        """Create a code analysis task."""
        return AgentTask(
            task_type="code_analysis",
            session_id=session_id,
            agent_type="coder",
            priority=priority,
            task_data={
                "file_path": file_path,
                "analysis_type": analysis_type,
            },
            metadata={
                "created_at": "2024-03-02T10:00:00Z",
                "estimated_duration": 30,
            },
        )
    
    @staticmethod
    def create_dependency_scan_task(
        session_id: str,
        project_path: str,
        scan_depth: str = "direct",
        priority: str = "medium",
    ) -> AgentTask:
        """Create a dependency scanning task."""
        return AgentTask(
            task_type="dependency_scan",
            session_id=session_id,
            agent_type="coder",
            priority=priority,
            task_data={
                "project_path": project_path,
                "scan_depth": scan_depth,
            },
            metadata={
                "created_at": "2024-03-02T10:00:00Z",
                "estimated_duration": 60,
            },
        )
    
    @staticmethod
    def create_test_execution_task(
        session_id: str,
        test_path: str,
        test_type: str = "unit",
        parallel: bool = False,
        priority: str = "medium",
    ) -> AgentTask:
        """Create a test execution task."""
        return AgentTask(
            task_type="test_execution",
            session_id=session_id,
            agent_type="coder",
            priority=priority,
            task_data={
                "test_path": test_path,
                "test_type": test_type,
                "parallel": parallel,
            },
            metadata={
                "created_at": "2024-03-02T10:00:00Z",
                "estimated_duration": 120,
            },
        )
    
    @staticmethod
    def create_code_generation_task(
        session_id: str,
        prompt: str,
        language: str = "python",
        context: Optional[Dict[str, Any]] = None,
        priority: str = "medium",
    ) -> AgentTask:
        """Create a code generation task."""
        return AgentTask(
            task_type="code_generation",
            session_id=session_id,
            agent_type="coder",
            priority=priority,
            task_data={
                "prompt": prompt,
                "language": language,
                "context": context or {},
            },
            metadata={
                "created_at": "2024-03-02T10:00:00Z",
                "estimated_duration": 45,
            },
        )
    
    @staticmethod
    def create_refactoring_task(
        session_id: str,
        file_path: str,
        refactoring_type: str = "extract_method",
        priority: str = "medium",
    ) -> AgentTask:
        """Create a refactoring task."""
        return AgentTask(
            task_type="refactoring",
            session_id=session_id,
            agent_type="coder",
            priority=priority,
            task_data={
                "file_path": file_path,
                "refactoring_type": refactoring_type,
            },
            metadata={
                "created_at": "2024-03-02T10:00:00Z",
                "estimated_duration": 90,
            },
        )
    
    # Analyst Agent Tasks
    @staticmethod
    def create_metrics_calculation_task(
        session_id: str,
        metrics_type: str,
        data_source: str,
        time_range: str = "24h",
        priority: str = "medium",
    ) -> AgentTask:
        """Create a metrics calculation task."""
        return AgentTask(
            task_type="metrics_calculation",
            session_id=session_id,
            agent_type="analyst",
            priority=priority,
            task_data={
                "metrics_type": metrics_type,
                "data_source": data_source,
                "time_range": time_range,
            },
            metadata={
                "created_at": "2024-03-02T10:00:00Z",
                "estimated_duration": 60,
            },
        )
    
    @staticmethod
    def create_data_processing_task(
        session_id: str,
        dataset_path: str,
        processing_type: str = "aggregation",
        batch_size: int = 1000,
        priority: str = "medium",
    ) -> AgentTask:
        """Create a data processing task."""
        return AgentTask(
            task_type="data_processing",
            session_id=session_id,
            agent_type="analyst",
            priority=priority,
            task_data={
                "dataset_path": dataset_path,
                "processing_type": processing_type,
                "batch_size": batch_size,
            },
            metadata={
                "created_at": "2024-03-02T10:00:00Z",
                "estimated_duration": 180,
            },
        )
    
    @staticmethod
    def create_report_generation_task(
        session_id: str,
        report_type: str,
        data_sources: List[str],
        format_type: str = "json",
        priority: str = "medium",
    ) -> AgentTask:
        """Create a report generation task."""
        return AgentTask(
            task_type="report_generation",
            session_id=session_id,
            agent_type="analyst",
            priority=priority,
            task_data={
                "report_type": report_type,
                "data_sources": data_sources,
                "format": format_type,
            },
            metadata={
                "created_at": "2024-03-02T10:00:00Z",
                "estimated_duration": 90,
            },
        )
    
    # Researcher Agent Tasks
    @staticmethod
    def create_web_search_task(
        session_id: str,
        query: str,
        search_depth: str = "standard",
        sources: List[str] = None,
        max_results: int = 10,
        priority: str = "medium",
    ) -> AgentTask:
        """Create a web search task."""
        return AgentTask(
            task_type="web_search",
            session_id=session_id,
            agent_type="researcher",
            priority=priority,
            task_data={
                "query": query,
                "search_depth": search_depth,
                "sources": sources or ["web"],
                "max_results": max_results,
            },
            metadata={
                "created_at": "2024-03-02T10:00:00Z",
                "estimated_duration": 120,
            },
        )
    
    @staticmethod
    def create_source_validation_task(
        session_id: str,
        sources: List[str],
        validation_criteria: List[str],
        strict_mode: bool = False,
        priority: str = "medium",
    ) -> AgentTask:
        """Create a source validation task."""
        return AgentTask(
            task_type="source_validation",
            session_id=session_id,
            agent_type="researcher",
            priority=priority,
            task_data={
                "sources": sources,
                "validation_criteria": validation_criteria,
                "strict_mode": strict_mode,
            },
            metadata={
                "created_at": "2024-03-02T10:00:00Z",
                "estimated_duration": 45,
            },
        )
    
    @staticmethod
    def create_content_synthesis_task(
        session_id: str,
        research_data: List[Dict[str, Any]],
        synthesis_type: str = "summary",
        target_audience: str = "technical",
        priority: str = "medium",
    ) -> AgentTask:
        """Create a content synthesis task."""
        return AgentTask(
            task_type="content_synthesis",
            session_id=session_id,
            agent_type="researcher",
            priority=priority,
            task_data={
                "research_data": research_data,
                "synthesis_type": synthesis_type,
                "target_audience": target_audience,
            },
            metadata={
                "created_at": "2024-03-02T10:00:00Z",
                "estimated_duration": 90,
            },
        )
    
    # Orchestrator Agent Tasks
    @staticmethod
    def create_task_decomposition_task(
        session_id: str,
        complex_task: str,
        complexity_level: str = "medium",
        target_agents: List[str] = None,
        priority: str = "high",
    ) -> AgentTask:
        """Create a task decomposition task."""
        return AgentTask(
            task_type="task_decomposition",
            session_id=session_id,
            agent_type="orchestrator",
            priority=priority,
            task_data={
                "complex_task": complex_task,
                "complexity_level": complexity_level,
                "target_agents": target_agents or [],
            },
            metadata={
                "created_at": "2024-03-02T10:00:00Z",
                "estimated_duration": 30,
            },
        )
    
    @staticmethod
    def create_workflow_execution_task(
        session_id: str,
        workflow_id: str,
        workflow_definition: Dict[str, Any],
        execution_context: Dict[str, Any] = None,
        priority: str = "high",
    ) -> AgentTask:
        """Create a workflow execution task."""
        return AgentTask(
            task_type="workflow_execution",
            session_id=session_id,
            agent_type="orchestrator",
            priority=priority,
            task_data={
                "workflow_id": workflow_id,
                "workflow_definition": workflow_definition,
                "execution_context": execution_context or {},
            },
            metadata={
                "created_at": "2024-03-02T10:00:00Z",
                "estimated_duration": 300,
            },
        )
    
    @staticmethod
    def create_resource_allocation_task(
        session_id: str,
        tasks: List[Dict[str, Any]],
        available_resources: Dict[str, Any],
        allocation_strategy: str = "balanced",
        priority: str = "medium",
    ) -> AgentTask:
        """Create a resource allocation task."""
        return AgentTask(
            task_type="resource_allocation",
            session_id=session_id,
            agent_type="orchestrator",
            priority=priority,
            task_data={
                "tasks": tasks,
                "available_resources": available_resources,
                "allocation_strategy": allocation_strategy,
            },
            metadata={
                "created_at": "2024-03-02T10:00:00Z",
                "estimated_duration": 45,
            },
        )


class AgentTaskPublisher:
    """Utility class for publishing agent tasks to queues."""
    
    def __init__(self) -> None:
        """Initialize the task publisher."""
        self.queue_manager = get_queue_manager()
    
    async def publish_task(self, task: AgentTask) -> bool:
        """Publish an agent task to the appropriate queue.
        
        Args:
            task: Agent task to publish
            
        Returns:
            True if task was published successfully
        """
        # Determine queue name based on agent type and priority
        queue_name = self._get_queue_name(task.agent_type, task.priority)
        
        # Convert task to dictionary
        task_dict = task.to_dict()
        
        # Set message priority based on task priority
        priority = self._get_message_priority(task.priority)
        
        # Publish to queue
        success = await self.queue_manager.publish_message(
            queue_name=queue_name,
            message_data=task_dict,
            priority=priority,
        )
        
        if success:
            _logger.info(f"Published {task.task_type} task {task.task_id} to {queue_name}")
        else:
            _logger.error(f"Failed to publish task {task.task_id} to {queue_name}")
        
        return success
    
    def _get_queue_name(self, agent_type: str, priority: str) -> str:
        """Get queue name for agent type and priority."""
        # Map agent types and priorities to queue names
        queue_mappings = {
            ("coder", "critical"): "coder_critical",
            ("coder", "high"): "coder_high",
            ("coder", "medium"): "coder_high",
            ("coder", "low"): "coder_high",
            
            ("analyst", "critical"): "analyst_high",
            ("analyst", "high"): "analyst_high",
            ("analyst", "medium"): "analyst_high",
            ("analyst", "low"): "analyst_high",
            
            ("researcher", "critical"): "researcher_high",
            ("researcher", "high"): "researcher_high",
            ("researcher", "medium"): "researcher_high",
            ("researcher", "low"): "researcher_high",
            
            ("orchestrator", "critical"): "orchestrator_critical",
            ("orchestrator", "high"): "orchestrator_critical",
            ("orchestrator", "medium"): "orchestrator_critical",
            ("orchestrator", "low"): "orchestrator_critical",
        }
        
        return queue_mappings.get((agent_type, priority), f"{agent_type}_high")
    
    def _get_message_priority(self, task_priority: str) -> int:
        """Convert task priority to message priority."""
        priority_mapping = {
            "critical": 9,
            "high": 7,
            "medium": 5,
            "low": 3,
        }
        
        return priority_mapping.get(task_priority, 5)
    
    async def publish_multiple_tasks(self, tasks: List[AgentTask]) -> Dict[str, bool]:
        """Publish multiple tasks to queues.
        
        Args:
            tasks: List of tasks to publish
            
        Returns:
            Dictionary mapping task IDs to success status
        """
        results = {}
        
        for task in tasks:
            results[task.task_id] = await self.publish_task(task)
        
        return results


# Global task publisher instance
_task_publisher: Optional[AgentTaskPublisher] = None


def get_agent_task_publisher() -> AgentTaskPublisher:
    """Get the global agent task publisher instance."""
    global _task_publisher
    if _task_publisher is None:
        _task_publisher = AgentTaskPublisher()
    return _task_publisher
