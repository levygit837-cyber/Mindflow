"""Orchestration service for managing task decomposition and agent coordination.

This service provides comprehensive orchestration capabilities including
task decomposition, personality selection, workflow management, and agent coordination.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.services.interfaces.base_interfaces import BaseAbstractService
from mindflow_backend.services.interfaces.orchestration_interfaces import (
    OrchestrationServiceInterface,
)


class OrchestrationService(BaseAbstractService, OrchestrationServiceInterface):
    """Service for managing orchestration, task decomposition, and agent coordination.
    
    This service handles complex task decomposition, intelligent agent selection,
    workflow execution, and coordination between multiple agents.
    """
    
    def __init__(self) -> None:
        """Initialize orchestration service with dependencies."""
        super().__init__()
        
        # Lazy load dependencies to avoid circular imports
        self._agent_service = None
        self._task_service = None
        self._routing_service = None
        self._memory_service = None
        
        # Workflow registry
        self._active_workflows: dict[str, dict[str, Any]] = {}
        self._execution_history: list[dict[str, Any]] = []
    
    def _get_logger(self) -> Any:
        """Get logger instance for this service."""
        return get_logger(__name__)
    
    def _get_agent_service(self):
        """Get agent service instance (lazy loading)."""
        if self._agent_service is None:
            from mindflow_backend.services import get_agent_service
            self._agent_service = get_agent_service()
        return self._agent_service
    
    def _get_task_service(self):
        """Get task service instance (lazy loading)."""
        if self._task_service is None:
            from mindflow_backend.services import get_task_service
            self._task_service = get_task_service()
        return self._task_service
    
    def _get_routing_service(self):
        """Get routing service instance (lazy loading)."""
        if self._routing_service is None:
            from mindflow_backend.services import get_routing_service
            self._routing_service = get_routing_service()
        return self._routing_service
    
    def _get_memory_service(self):
        """Get memory service instance (lazy loading)."""
        if self._memory_service is None:
            from mindflow_backend.memory import get_memory_service
            self._memory_service = get_memory_service()
        return self._memory_service
    
    async def decompose_task(
        self,
        task_description: str,
        session_id: str | None = None,
        complexity_level: str | None = None
    ) -> dict[str, Any]:
        """Decompose a complex task into sub-tasks.
        
        Args:
            task_description: Description of task to decompose
            session_id: Optional session identifier
            complexity_level: Optional complexity level
            
        Returns:
            Dictionary containing decomposed tasks and metadata
        """
        self.log_operation(
            "decompose_task",
            task_description=task_description[:100],
            session_id=session_id,
            complexity_level=complexity_level
        )
        
        try:
            # Generate task ID
            task_id = f"task-{uuid.uuid4()}"
            
            # Analyze task complexity if not provided
            if complexity_level is None:
                complexity_level = await self._analyze_task_complexity(task_description)
            
            # Use task service for decomposition
            task_service = self._get_task_service()
            
            # Create main task
            main_task = await task_service.create_task(
                task_description=task_description,
                task_type="decomposition",
                session_id=session_id,
                priority="high"
            )
            
            # Generate sub-tasks based on complexity
            sub_tasks = await self._generate_sub_tasks(
                task_description, complexity_level, session_id, main_task["id"]
            )
            
            # Calculate execution order
            ordered_tasks = await task_service.optimize_task_order(sub_tasks)
            
            return {
                "task_id": task_id,
                "description": task_description,
                "complexity_level": complexity_level,
                "main_task_id": main_task["id"],
                "sub_tasks": ordered_tasks,
                "total_subtasks": len(sub_tasks),
                "estimated_duration": self._estimate_total_duration(ordered_tasks),
                "dependencies": self._extract_dependencies(ordered_tasks),
                "status": "decomposed",
                "created_at": datetime.now(UTC).isoformat()
            }
            
        except Exception as exc:
            self._logger.error(f"Error decomposing task: {str(exc)}")
            raise
    
    async def select_specialist(
        self,
        task_id: str,
        task_description: str,
        task_complexity: str,
        current_specialist: str | None = None
    ) -> dict[str, Any]:
        """Select optimal personality for a task.
        
        Args:
            task_id: Task identifier
            task_description: Description of task
            task_complexity: Complexity level of task
            current_specialist: Currently active personality
            
        Returns:
            Dictionary containing personality selection result
        """
        self.log_operation(
            "select_specialist",
            task_id=task_id,
            task_description=task_description[:100],
            task_complexity=task_complexity,
            current_specialist=current_specialist
        )
        
        try:
            # Use routing service for intelligent selection
            routing_service = self._get_routing_service()
            
            # Get available agents
            agent_service = self._get_agent_service()
            available_agents = await agent_service.list_available_agents()
            agent_types = [agent["name"].lower() for agent in available_agents["agents"].values()]
            
            # Select optimal agent for task
            routing_result = await routing_service.select_agent_for_task(
                task_description=task_description,
                task_complexity=task_complexity,
                available_agents=agent_types
            )
            
            # Get agent capabilities
            selected_agent_type = routing_result.get("selected_agent", "analyst")
            agent_capabilities = await agent_service.get_agent_capabilities(selected_agent_type)
            
            return {
                "task_id": task_id,
                "task_description": task_description,
                "task_complexity": task_complexity,
                "current_specialist": current_specialist,
                "selected_specialist": {
                    "agent_type": selected_agent_type,
                    "agent_name": agent_capabilities.get("specialization", "General Purpose"),
                    "confidence": routing_result.get("confidence", 0.7),
                    "reasoning": routing_result.get("reasoning", "Task-based selection"),
                    "capabilities": agent_capabilities.get("capabilities", []),
                    "tools": agent_capabilities.get("tools", [])
                },
                "alternatives": routing_result.get("alternatives", []),
                "selection_metadata": {
                    "routing_score": routing_result.get("score", 0.0),
                    "considered_agents": len(agent_types),
                    "selection_time": datetime.now(UTC).isoformat()
                },
                "status": "selected"
            }
            
        except Exception as exc:
            self._logger.error(f"Error selecting personality: {str(exc)}")
            raise
    
    async def execute_dag(
        self,
        dag_id: str,
        session_id: str | None = None
    ) -> dict[str, Any]:
        """Execute a Directed Acyclic Graph (DAG) of tasks.
        
        Args:
            dag_id: DAG identifier
            session_id: Optional session identifier
            
        Returns:
            Dictionary containing execution results
        """
        self.log_operation("execute_dag", dag_id=dag_id, session_id=session_id)
        
        try:
            # Get DAG definition (placeholder implementation)
            dag_definition = await self._get_dag_definition(dag_id)
            
            if not dag_definition:
                raise ValueError(f"DAG not found: {dag_id}")
            
            # Execute DAG tasks in order
            execution_results = []
            task_service = self._get_task_service()
            
            for node in dag_definition.get("nodes", []):
                # Execute each task node
                task_result = await task_service.update_task_status(
                    task_id=node["task_id"],
                    status="executing"
                )
                
                # In a real implementation, this would execute the actual task
                # For now, we'll simulate execution
                await self._simulate_task_execution(node)
                
                # Mark as completed
                completion_result = await task_service.update_task_status(
                    task_id=node["task_id"],
                    status="completed",
                    result={"status": "success", "output": f"Completed {node['task_type']}"}
                )
                
                execution_results.append(completion_result)
            
            return {
                "dag_id": dag_id,
                "session_id": session_id,
                "execution_id": f"exec-{uuid.uuid4()}",
                "nodes_executed": len(execution_results),
                "execution_results": execution_results,
                "status": "completed",
                "executed_at": datetime.now(UTC).isoformat()
            }
            
        except Exception as exc:
            self._logger.error(f"Error executing DAG {dag_id}: {str(exc)}")
            raise
    
    async def coordinate_agents(
        self,
        task_id: str,
        agent_sequence: list[str],
        session_id: str | None = None
    ) -> dict[str, Any]:
        """Coordinate multiple agents in sequence.
        
        Args:
            task_id: Task identifier
            agent_sequence: Sequence of agent types
            session_id: Optional session identifier
            
        Returns:
            Dictionary containing coordination results
        """
        self.log_operation(
            "coordinate_agents",
            task_id=task_id,
            agent_sequence=agent_sequence,
            session_id=session_id
        )
        
        try:
            agent_service = self._get_agent_service()
            coordination_results = []
            
            for i, agent_type in enumerate(agent_sequence):
                # Get agent capabilities
                agent_capabilities = await agent_service.get_agent_capabilities(agent_type)
                
                # Simulate agent coordination
                coordination_result = {
                    "step": i + 1,
                    "agent_type": agent_type,
                    "agent_name": agent_capabilities.get("specialization", "Unknown"),
                    "capabilities": agent_capabilities.get("capabilities", []),
                    "tools": agent_capabilities.get("tools", []),
                    "status": "ready",
                    "coordination_time": datetime.now(UTC).isoformat()
                }
                
                coordination_results.append(coordination_result)
                
                # In a real implementation, this would set up communication
                # channels between agents and manage data flow
            
            return {
                "task_id": task_id,
                "session_id": session_id,
                "agent_sequence": agent_sequence,
                "coordination_results": coordination_results,
                "total_agents": len(agent_sequence),
                "coordination_plan": self._generate_coordination_plan(agent_sequence),
                "status": "coordinated",
                "coordinated_at": datetime.now(UTC).isoformat()
            }
            
        except Exception as exc:
            self._logger.error(f"Error coordinating agents: {str(exc)}")
            raise
    
    async def get_execution_status(self, execution_id: str) -> dict[str, Any]:
        """Get execution status for a task or workflow.
        
        Args:
            execution_id: Execution identifier
            
        Returns:
            Dictionary containing execution status
        """
        self.log_operation("get_execution_status", execution_id=execution_id)
        
        try:
            # Search execution history
            execution_record = None
            for record in reversed(self._execution_history):
                if record.get("execution_id") == execution_id:
                    execution_record = record
                    break
            
            if not execution_record:
                raise ValueError(f"Execution not found: {execution_id}")
            
            # Calculate current status
            current_status = execution_record.get("status", "unknown")
            progress = self._calculate_execution_progress(execution_record)
            
            return {
                "execution_id": execution_id,
                "status": current_status,
                "progress": progress,
                "started_at": execution_record.get("started_at"),
                "updated_at": execution_record.get("updated_at"),
                "estimated_completion": execution_record.get("estimated_completion"),
                "current_step": execution_record.get("current_step"),
                "total_steps": execution_record.get("total_steps", 0)
            }
            
        except Exception as exc:
            self._logger.error(f"Error getting execution status: {str(exc)}")
            raise
    
    async def create_workflow(
        self,
        workflow_definition: dict[str, Any]
    ) -> dict[str, Any]:
        """Create a new workflow from definition.
        
        Args:
            workflow_definition: Workflow definition dictionary
            
        Returns:
            Dictionary containing created workflow
        """
        self.log_operation("create_workflow")
        
        try:
            # Validate workflow definition
            required_fields = ["name", "description", "nodes"]
            for field in required_fields:
                if field not in workflow_definition:
                    raise ValueError(f"Missing required field: {field}")
            
            # Generate workflow ID
            workflow_id = f"workflow-{uuid.uuid4()}"
            
            # Store workflow definition
            self._active_workflows[workflow_id] = {
                **workflow_definition,
                "id": workflow_id,
                "created_at": datetime.now(UTC).isoformat(),
                "status": "active"
            }
            
            return {
                "workflow_id": workflow_id,
                "name": workflow_definition["name"],
                "description": workflow_definition["description"],
                "node_count": len(workflow_definition.get("nodes", [])),
                "status": "created",
                "created_at": datetime.now(UTC).isoformat()
            }
            
        except Exception as exc:
            self._logger.error(f"Error creating workflow: {str(exc)}")
            raise
    
    async def execute_workflow(
        self,
        workflow_id: str,
        input_data: dict[str, Any],
        session_id: str | None = None
    ) -> dict[str, Any]:
        """Execute a workflow with input data.
        
        Args:
            workflow_id: Workflow identifier
            input_data: Input data for workflow
            session_id: Optional session identifier
            
        Returns:
            Dictionary containing workflow execution results
        """
        self.log_operation(
            "execute_workflow",
            workflow_id=workflow_id,
            session_id=session_id
        )
        
        try:
            workflow = self._active_workflows.get(workflow_id)
            if not workflow:
                raise ValueError(f"Workflow not found: {workflow_id}")
            
            # Execute workflow nodes
            execution_id = f"exec-{uuid.uuid4()}"
            execution_results = []
            
            for node in workflow.get("nodes", []):
                # Execute each node
                node_result = await self._execute_workflow_node(node, input_data, session_id)
                execution_results.append(node_result)
            
            # Record execution
            execution_record = {
                "execution_id": execution_id,
                "workflow_id": workflow_id,
                "input_data": input_data,
                "results": execution_results,
                "status": "completed",
                "started_at": datetime.now(UTC).isoformat(),
                "completed_at": datetime.now(UTC).isoformat()
            }
            
            self._execution_history.append(execution_record)
            
            return {
                "execution_id": execution_id,
                "workflow_id": workflow_id,
                "results": execution_results,
                "status": "completed",
                "executed_at": datetime.now(UTC).isoformat()
            }
            
        except Exception as exc:
            self._logger.error(f"Error executing workflow {workflow_id}: {str(exc)}")
            raise
    
    # Helper methods
    
    async def _analyze_task_complexity(self, task_description: str) -> str:
        """Analyze task complexity from description."""
        # Simple heuristic-based complexity analysis
        description_lower = task_description.lower()
        
        # Count complexity indicators
        complexity_indicators = {
            "simple": ["create", "write", "update", "get", "list", "show"],
            "medium": ["analyze", "design", "implement", "integrate", "test"],
            "complex": ["optimize", "refactor", "architecture", "system", "multiple", "coordinate"]
        }
        
        scores = {"simple": 0, "medium": 0, "complex": 0}
        
        for level, indicators in complexity_indicators.items():
            for indicator in indicators:
                if indicator in description_lower:
                    scores[level] += 1
        
        # Determine complexity based on scores
        if scores["complex"] > 0:
            return "complex"
        elif scores["medium"] > scores["simple"]:
            return "medium"
        else:
            return "simple"
    
    async def _generate_sub_tasks(
        self,
        task_description: str,
        complexity_level: str,
        session_id: str | None,
        main_task_id: str
    ) -> list[dict[str, Any]]:
        """Generate sub-tasks based on complexity."""
        task_service = self._get_task_service()
        sub_tasks = []
        
        if complexity_level == "simple":
            # Simple task - break into 2-3 sub-tasks
            sub_tasks = [
                await task_service.create_task(
                    task_description=f"Analyze requirements for: {task_description}",
                    task_type="analysis",
                    session_id=session_id,
                    priority="high"
                ),
                await task_service.create_task(
                    task_description=f"Execute: {task_description}",
                    task_type="execution",
                    session_id=session_id,
                    priority="high"
                )
            ]
        elif complexity_level == "medium":
            # Medium task - break into 4-6 sub-tasks
            sub_tasks = [
                await task_service.create_task(
                    task_description=f"Research: {task_description}",
                    task_type="research",
                    session_id=session_id,
                    priority="high"
                ),
                await task_service.create_task(
                    task_description=f"Design solution for: {task_description}",
                    task_type="design",
                    session_id=session_id,
                    priority="medium"
                ),
                await task_service.create_task(
                    task_description=f"Implement: {task_description}",
                    task_type="implementation",
                    session_id=session_id,
                    priority="medium"
                ),
                await task_service.create_task(
                    task_description=f"Test: {task_description}",
                    task_type="testing",
                    session_id=session_id,
                    priority="medium"
                )
            ]
        else:  # complex
            # Complex task - break into 6-10 sub-tasks
            sub_tasks = [
                await task_service.create_task(
                    task_description=f"Research requirements for: {task_description}",
                    task_type="research",
                    session_id=session_id,
                    priority="high"
                ),
                await task_service.create_task(
                    task_description=f"Design architecture for: {task_description}",
                    task_type="architecture",
                    session_id=session_id,
                    priority="high"
                ),
                await task_service.create_task(
                    task_description=f"Plan implementation: {task_description}",
                    task_type="planning",
                    session_id=session_id,
                    priority="high"
                ),
                await task_service.create_task(
                    task_description=f"Implement core components: {task_description}",
                    task_type="implementation",
                    session_id=session_id,
                    priority="medium"
                ),
                await task_service.create_task(
                    task_description=f"Integrate components: {task_description}",
                    task_type="integration",
                    session_id=session_id,
                    priority="medium"
                ),
                await task_service.create_task(
                    task_description=f"Test integration: {task_description}",
                    task_type="testing",
                    session_id=session_id,
                    priority="medium"
                ),
                await task_service.create_task(
                    task_description=f"Deploy solution: {task_description}",
                    task_type="deployment",
                    session_id=session_id,
                    priority="low"
                )
            ]
        
        # Add dependencies to main task
        for i, task in enumerate(sub_tasks):
            if i > 0:
                await task_service.add_task_dependency(
                    task_id=task["id"],
                    depends_on_task_id=sub_tasks[i-1]["id"]
                )
        
        return sub_tasks
    
    def _estimate_total_duration(self, tasks: list[dict[str, Any]]) -> str:
        """Estimate total duration for a list of tasks."""
        duration_map = {
            "analysis": "5m",
            "research": "10m",
            "design": "15m",
            "implementation": "30m",
            "testing": "10m",
            "planning": "5m",
            "integration": "20m",
            "deployment": "5m"
        }
        
        total_minutes = 0
        for task in tasks:
            task_type = task.get("task_type", "implementation")
            duration = duration_map.get(task_type, "15m")
            
            # Convert to minutes
            if duration.endswith("m"):
                total_minutes += int(duration[:-1])
            elif duration.endswith("h"):
                total_minutes += int(duration[:-1]) * 60
            else:
                total_minutes += 15
        
        # Convert back to readable format
        if total_minutes < 60:
            return f"{total_minutes}m"
        else:
            hours = total_minutes // 60
            minutes = total_minutes % 60
            return f"{hours}h{minutes}m"
    
    def _extract_dependencies(self, tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Extract dependency information from tasks."""
        dependencies = []
        for task in tasks:
            task_deps = task.get("dependencies", [])
            if task_deps:
                dependencies.append({
                    "task_id": task["id"],
                    "depends_on": task_deps,
                    "dependency_count": len(task_deps)
                })
        return dependencies
    
    async def _get_dag_definition(self, dag_id: str) -> dict[str, Any] | None:
        """Get DAG definition by ID."""
        # Placeholder implementation - in real system this would fetch from database
        return {
            "id": dag_id,
            "name": f"Sample DAG {dag_id}",
            "nodes": [
                {
                    "task_id": "task-1",
                    "task_type": "analysis",
                    "description": "Analyze requirements"
                },
                {
                    "task_id": "task-2",
                    "task_type": "implementation",
                    "description": "Implement solution"
                }
            ],
            "edges": [
                {"from": "task-1", "to": "task-2"}
            ]
        }
    
    async def _simulate_task_execution(self, node: dict[str, Any]) -> None:
        """Simulate task execution (placeholder)."""
        # In a real implementation, this would execute the actual task
        # For now, we'll just log it
        self._logger.info(f"Simulating task execution: {node.get('task_id')} - {node.get('description')}")
    
    def _generate_coordination_plan(self, agent_sequence: list[str]) -> dict[str, Any]:
        """Generate coordination plan for agent sequence."""
        plan = {
            "sequence": agent_sequence,
            "total_agents": len(agent_sequence),
            "coordination_strategy": "sequential",
            "communication_channels": self._setup_communication_channels(agent_sequence),
            "data_flow": self._define_data_flow(agent_sequence),
            "estimated_duration": f"{len(agent_sequence) * 5}m"
        }
        
        return plan
    
    def _setup_communication_channels(self, agent_sequence: list[str]) -> list[dict[str, Any]]:
        """Set up communication channels between agents."""
        channels = []
        for i in range(len(agent_sequence) - 1):
            channels.append({
                "from_agent": agent_sequence[i],
                "to_agent": agent_sequence[i + 1],
                "channel_type": "message_queue",
                "protocol": "grpc"
            })
        return channels
    
    def _define_data_flow(self, agent_sequence: list[str]) -> list[dict[str, Any]]:
        """Define data flow between agents."""
        flow = []
        for i in range(len(agent_sequence) - 1):
            flow.append({
                "from": agent_sequence[i],
                "to": agent_sequence[i + 1],
                "data_type": "task_result",
                "format": "json"
            })
        return flow
    
    async def _execute_workflow_node(self, node: dict[str, Any], input_data: dict[str, Any], session_id: str | None) -> dict[str, Any]:
        """Execute a single workflow node."""
        node_type = node.get("type", "task")
        
        if node_type == "task":
            # Execute as task
            task_service = self._get_task_service()
            return await task_service.update_task_status(
                task_id=node["task_id"],
                status="completed",
                result={"input_data": input_data, "output": f"Completed {node.get('description', '')}"}
            )
        else:
            # Handle other node types
            return {
                "node_id": node.get("id", "unknown"),
                "status": "completed",
                "result": {"input_data": input_data}
            }
    
    def _calculate_execution_progress(self, execution_record: dict[str, Any]) -> dict[str, Any]:
        """Calculate execution progress from record."""
        total_steps = execution_record.get("total_steps", 1)
        current_step = execution_record.get("current_step", 1)
        
        progress_percentage = (current_step / total_steps) * 100 if total_steps > 0 else 0
        
        return {
            "percentage": progress_percentage,
            "current_step": current_step,
            "total_steps": total_steps,
            "remaining_steps": total_steps - current_step,
            "status": "in_progress" if progress_percentage < 100 else "completed"
        }
