"""Orchestration service for managing task decomposition and agent coordination."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import uuid

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.orchestrator.graph import OrchestratorGraph
from mindflow_backend.agents.interfaces.orchestrator.specialists import SpecialistSelector
from mindflow_backend.schemas.orchestration.orchestrator import AgentType, ThinkingLevel

_logger = get_logger(__name__)


class OrchestrationService:
    """Service for managing orchestration, task decomposition, and agent coordination."""
    
    def __init__(self):
        self.logger = _logger
        self._orchestrator_graph = OrchestratorGraph()
        self._specialist_selector = SpecialistSelector()
    
    async def decompose_task(
        self,
        task_description: str,
        session_id: Optional[str] = None,
        complexity_level: Optional[str] = None
    ) -> Dict[str, Any]:
        """Decompose a complex task into sub-tasks using real orchestration logic.
        
        Args:
            task_description: Description of the task to decompose
            session_id: Session identifier
            complexity_level: Task complexity level
            
        Returns:
            Dictionary containing decomposed tasks and metadata
        """
        self.logger.info(
            "Decomposing task",
            session_id=session_id,
            complexity_level=complexity_level
        )
        
        try:
            # Generate task ID
            task_id = f"task-{uuid.uuid4()}"
            
            # Use orchestrator graph for decomposition
            decomposition_result = await self._orchestrator_graph.decompose_task(
                task_description=task_description,
                session_id=session_id or f"sess-{uuid.uuid4()}",
                complexity_level=complexity_level or "medium"
            )
            
            # Format sub-tasks
            sub_tasks = []
            for i, sub_task in enumerate(decomposition_result.get("sub_tasks", [])):
                sub_tasks.append({
                    "id": f"subtask-{i+1}",
                    "description": sub_task.get("description", ""),
                    "agent_type": sub_task.get("agent_type", "analyst"),
                    "priority": sub_task.get("priority", "medium"),
                    "estimated_duration": sub_task.get("estimated_duration", "5m"),
                    "dependencies": sub_task.get("dependencies", []),
                    "status": "pending"
                })
            
            return {
                "task_id": task_id,
                "description": task_description,
                "sub_tasks": sub_tasks,
                "complexity_level": complexity_level or "medium",
                "dependencies": self._extract_dependencies(sub_tasks),
                "estimated_duration": self._calculate_total_duration(sub_tasks),
                "status": "decomposed"
            }
            
        except Exception as e:
            self.logger.error(f"Error decomposing task: {str(e)}")
            # Fallback to simple decomposition
            return self._fallback_decomposition(task_description, session_id, complexity_level)
    
    async def select_specialist(
        self,
        task_id: str,
        task_description: str,
        task_complexity: str,
        current_specialist: Optional[str] = None
    ) -> Dict[str, Any]:
        """Select optimal specialist for a task using real specialist logic.
        
        Args:
            task_id: Task identifier
            task_description: Description of the task
            task_complexity: Complexity level of the task
            current_specialist: Currently active specialist
            
        Returns:
            Dictionary containing specialist decision
        """
        self.logger.info(
            "Selecting specialist",
            task_id=task_id,
            task_complexity=task_complexity,
            current_specialist=current_specialist
        )
        
        try:
            # Use specialist selector for decision
            selection_result = self._specialist_selector.select_specialist(
                task_id=task_id,
                task_description=task_description,
                task_complexity=task_complexity,
                current_specialist=current_specialist
            )
            
            return {
                "task_id": task_id,
                "selected_specialist": selection_result.get("specialist", "analyst"),
                "rationale": selection_result.get("rationale", "Task requires analytical approach"),
                "confidence": selection_result.get("confidence", 0.8),
                "alternatives": selection_result.get("alternatives", []),
                "switch_required": current_specialist != selection_result.get("specialist"),
                "metadata": selection_result
            }
            
        except Exception as e:
            self.logger.error(f"Error selecting specialist: {str(e)}")
            # Fallback to simple selection
            return self._fallback_specialist_selection(task_id, task_description, task_complexity)
    
    async def execute_dag(
        self,
        dag_id: str,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Execute a Directed Acyclic Graph of tasks using real orchestration.
        
        Args:
            dag_id: DAG identifier
            session_id: Session identifier
            
        Returns:
            Dictionary containing execution results
        """
        self.logger.info(
            "Executing DAG",
            dag_id=dag_id,
            session_id=session_id
        )
        
        try:
            execution_id = f"exec-{uuid.uuid4()}"
            
            # Execute using orchestrator graph
            execution_result = await self._orchestrator_graph.execute_dag(
                dag_id=dag_id,
                session_id=session_id or f"sess-{uuid.uuid4()}",
                execution_id=execution_id
            )
            
            return {
                "dag_id": dag_id,
                "execution_id": execution_id,
                "status": execution_result.get("status", "running"),
                "tasks_completed": execution_result.get("tasks_completed", 0),
                "total_tasks": execution_result.get("total_tasks", 0),
                "results": execution_result.get("results", []),
                "started_at": execution_result.get("started_at"),
                "metadata": execution_result
            }
            
        except Exception as e:
            self.logger.error(f"Error executing DAG: {str(e)}")
            # Fallback execution
            return self._fallback_dag_execution(dag_id, session_id)
    
    async def coordinate_agents(
        self,
        task_id: str,
        agent_sequence: List[str],
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Coordinate multiple agents for a task using real coordination logic.
        
        Args:
            task_id: Task identifier
            agent_sequence: Sequence of agents to coordinate
            session_id: Session identifier
            
        Returns:
            Dictionary containing coordination results
        """
        self.logger.info(
            "Coordinating agents",
            task_id=task_id,
            agent_sequence=agent_sequence,
            session_id=session_id
        )
        
        try:
            coordination_id = f"coord-{uuid.uuid4()}"
            
            # Use orchestrator for coordination
            coordination_result = await self._orchestrator_graph.coordinate_agents(
                task_id=task_id,
                agent_sequence=agent_sequence,
                session_id=session_id or f"sess-{uuid.uuid4()}",
                coordination_id=coordination_id
            )
            
            return {
                "task_id": task_id,
                "coordination_id": coordination_id,
                "agent_sequence": agent_sequence,
                "current_step": coordination_result.get("current_step", 0),
                "status": coordination_result.get("status", "coordinating"),
                "total_steps": len(agent_sequence),
                "completed_steps": coordination_result.get("completed_steps", 0),
                "results": coordination_result.get("results", []),
                "metadata": coordination_result
            }
            
        except Exception as e:
            self.logger.error(f"Error coordinating agents: {str(e)}")
            # Fallback coordination
            return self._fallback_agent_coordination(task_id, agent_sequence, session_id)
    
    async def get_execution_status(
        self,
        execution_id: str
    ) -> Dict[str, Any]:
        """Get status of task execution using real tracking.
        
        Args:
            execution_id: Execution identifier
            
        Returns:
            Dictionary containing execution status
        """
        self.logger.info(f"Getting execution status: {execution_id}")
        
        try:
            # Get status from orchestrator
            status_result = await self._orchestrator_graph.get_execution_status(execution_id)
            
            return {
                "execution_id": execution_id,
                "status": status_result.get("status", "unknown"),
                "progress": status_result.get("progress", 0.0),
                "tasks_completed": status_result.get("tasks_completed", 0),
                "total_tasks": status_result.get("total_tasks", 0),
                "started_at": status_result.get("started_at"),
                "completed_at": status_result.get("completed_at"),
                "error": status_result.get("error"),
                "metadata": status_result
            }
            
        except Exception as e:
            self.logger.error(f"Error getting execution status: {str(e)}")
            # Fallback status
            return self._fallback_execution_status(execution_id)
    
    def _extract_dependencies(self, sub_tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract dependencies from sub-tasks."""
        dependencies = []
        for task in sub_tasks:
            for dep in task.get("dependencies", []):
                dependencies.append({
                    "from": dep,
                    "to": task["id"],
                    "type": "sequential"
                })
        return dependencies
    
    def _calculate_total_duration(self, sub_tasks: List[Dict[str, Any]]) -> str:
        """Calculate total estimated duration."""
        total_minutes = 0
        for task in sub_tasks:
            duration_str = task.get("estimated_duration", "5m")
            if duration_str.endswith("m"):
                total_minutes += int(duration_str[:-1])
            elif duration_str.endswith("h"):
                total_minutes += int(duration_str[:-1]) * 60
        
        if total_minutes < 60:
            return f"{total_minutes}m"
        else:
            hours = total_minutes // 60
            minutes = total_minutes % 60
            return f"{hours}h{minutes}m"
    
    def _fallback_decomposition(self, task_description: str, session_id: Optional[str], complexity_level: Optional[str]) -> Dict[str, Any]:
        """Fallback task decomposition."""
        return {
            "task_id": f"task-{uuid.uuid4()}",
            "description": task_description,
            "sub_tasks": [
                {
                    "id": "subtask-1",
                    "description": "Analyze requirements",
                    "agent_type": "analyst",
                    "priority": "high",
                    "estimated_duration": "10m",
                    "dependencies": [],
                    "status": "pending"
                }
            ],
            "complexity_level": complexity_level or "medium",
            "dependencies": [],
            "estimated_duration": "10m",
            "status": "decomposed_fallback"
        }
    
    def _fallback_specialist_selection(self, task_id: str, task_description: str, task_complexity: str) -> Dict[str, Any]:
        """Fallback specialist selection."""
        specialist_map = {
            "low": "coder",
            "medium": "analyst", 
            "high": "orchestrator"
        }
        
        selected = specialist_map.get(task_complexity, "analyst")
        
        return {
            "task_id": task_id,
            "selected_specialist": selected,
            "rationale": f"Selected {selected} based on {task_complexity} complexity",
            "confidence": 0.7,
            "alternatives": ["analyst", "coder"],
            "switch_required": False,
            "metadata": {"fallback": True}
        }
    
    def _fallback_dag_execution(self, dag_id: str, session_id: Optional[str]) -> Dict[str, Any]:
        """Fallback DAG execution."""
        return {
            "dag_id": dag_id,
            "execution_id": f"exec-{uuid.uuid4()}",
            "status": "running_fallback",
            "tasks_completed": 0,
            "total_tasks": 1,
            "results": [],
            "started_at": "2024-01-01T00:00:00Z",
            "metadata": {"fallback": True}
        }
    
    def _fallback_agent_coordination(self, task_id: str, agent_sequence: List[str], session_id: Optional[str]) -> Dict[str, Any]:
        """Fallback agent coordination."""
        return {
            "task_id": task_id,
            "coordination_id": f"coord-{uuid.uuid4()}",
            "agent_sequence": agent_sequence,
            "current_step": 0,
            "status": "coordinating_fallback",
            "total_steps": len(agent_sequence),
            "completed_steps": 0,
            "results": [],
            "metadata": {"fallback": True}
        }
    
    def _fallback_execution_status(self, execution_id: str) -> Dict[str, Any]:
        """Fallback execution status."""
        return {
            "execution_id": execution_id,
            "status": "unknown_fallback",
            "progress": 0.0,
            "tasks_completed": 0,
            "total_tasks": 0,
            "started_at": None,
            "completed_at": None,
            "error": None,
            "metadata": {"fallback": True}
        }
