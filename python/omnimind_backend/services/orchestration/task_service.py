"""Task service for managing task lifecycle and dependencies.

This service provides comprehensive task management including
creation, status tracking, dependency management, and optimization.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, UTC
from uuid import uuid4

from omnimind_backend.infra.logging import get_logger
from omnimind_backend.services.interfaces.base_interfaces import BaseAbstractService
from omnimind_backend.services.interfaces.orchestration_interfaces import TaskServiceInterface


class TaskService(BaseAbstractService, TaskServiceInterface):
    """Service for task management and lifecycle operations.
    
    This service provides comprehensive task management including
    dependency tracking, optimization, and execution coordination.
    """
    
    def __init__(self) -> None:
        """Initialize task service with storage and configuration."""
        super().__init__()
        
        # Task storage
        self._tasks: Dict[str, Dict[str, Any]] = {}
        self._task_dependencies: Dict[str, List[str]] = {}
        self._task_executions: Dict[str, List[Dict[str, Any]]] = {}
        
        # Task configuration
        self._task_types = {
            "analysis": {"priority": 1, "estimated_duration": "5m"},
            "research": {"priority": 2, "estimated_duration": "10m"},
            "design": {"priority": 2, "estimated_duration": "15m"},
            "implementation": {"priority": 3, "estimated_duration": "30m"},
            "testing": {"priority": 2, "estimated_duration": "10m"},
            "deployment": {"priority": 1, "estimated_duration": "5m"},
            "decomposition": {"priority": 1, "estimated_duration": "2m"},
            "coordination": {"priority": 1, "estimated_duration": "3m"}
        }
        
        # Lazy load dependencies
        self._agent_service = None
        self._routing_service = None
    
    def _get_logger(self) -> Any:
        """Get logger instance for this service."""
        return get_logger(__name__)
    
    def _get_agent_service(self):
        """Get agent service instance (lazy loading)."""
        if self._agent_service is None:
            from omnimind_backend.services import get_agent_service
            self._agent_service = get_agent_service()
        return self._agent_service
    
    def _get_routing_service(self):
        """Get routing service instance (lazy loading)."""
        if self._routing_service is None:
            from omnimind_backend.services import get_routing_service
            self._routing_service = get_routing_service()
        return self._routing_service
    
    async def create_task(
        self,
        task_description: str,
        task_type: str,
        session_id: Optional[str] = None,
        priority: str = "medium"
    ) -> Dict[str, Any]:
        """Create a new task.
        
        Args:
            task_description: Description of the task
            task_type: Type of task
            session_id: Optional session identifier
            priority: Task priority
            
        Returns:
            Dictionary containing created task data
        """
        self.log_operation(
            "create_task",
            task_description=task_description[:100],
            task_type=task_type,
            session_id=session_id,
            priority=priority
        )
        
        try:
            # Validate task type
            if task_type not in self._task_types:
                raise ValueError(f"Unknown task type: {task_type}. Available: {list(self._task_types.keys())}")
            
            # Generate task ID
            task_id = f"task-{uuid4()}"
            
            # Get task type configuration
            type_config = self._task_types[task_type]
            
            # Create task
            task = {
                "id": task_id,
                "description": task_description,
                "type": task_type,
                "session_id": session_id,
                "priority": priority,
                "status": "pending",
                "created_at": datetime.now(UTC).isoformat(),
                "updated_at": datetime.now(UTC).isoformat(),
                "dependencies": [],
                "dependents": [],
                "estimated_duration": type_config["estimated_duration"],
                "type_priority": type_config["priority"],
                "metadata": {
                    "complexity": self._estimate_task_complexity(task_description),
                    "agent_requirements": self._get_agent_requirements(task_type),
                    "resource_needs": self._estimate_resource_needs(task_type)
                }
            }
            
            self._tasks[task_id] = task
            
            return {
                "task_id": task_id,
                "description": task_description,
                "type": task_type,
                "status": "created",
                "priority": priority,
                "session_id": session_id,
                "estimated_duration": type_config["estimated_duration"],
                "created_at": task["created_at"]
            }
            
        except Exception as exc:
            self._logger.error(f"Error creating task: {str(exc)}")
            raise
    
    async def get_task(self, task_id: str) -> Dict[str, Any]:
        """Get task details by ID.
        
        Args:
            task_id: Task identifier
            
        Returns:
            Dictionary containing task details
        """
        self.log_operation("get_task", task_id=task_id)
        
        try:
            task = self._tasks.get(task_id)
            if not task:
                raise ValueError(f"Task not found: {task_id}")
            
            # Get execution history
            executions = self._task_executions.get(task_id, [])
            
            return {
                "task_id": task_id,
                "description": task["description"],
                "type": task["type"],
                "status": task["status"],
                "priority": task["priority"],
                "session_id": task["session_id"],
                "created_at": task["created_at"],
                "updated_at": task["updated_at"],
                "dependencies": task["dependencies"],
                "dependents": task["dependents"],
                "estimated_duration": task["estimated_duration"],
                "metadata": task["metadata"],
                "execution_history": executions,
                "execution_count": len(executions)
            }
            
        except Exception as exc:
            self._logger.error(f"Error getting task {task_id}: {str(exc)}")
            raise
    
    async def update_task_status(
        self,
        task_id: str,
        status: str,
        result: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Update task status and optionally add result.
        
        Args:
            task_id: Task identifier
            status: New status
            result: Optional task result
            
        Returns:
            Dictionary containing update result
        """
        self.log_operation(
            "update_task_status",
            task_id=task_id,
            status=status
        )
        
        try:
            task = self._tasks.get(task_id)
            if not task:
                raise ValueError(f"Task not found: {task_id}")
            
            # Update task
            old_status = task["status"]
            task["status"] = status
            task["updated_at"] = datetime.now(UTC).isoformat()
            
            if result:
                task["result"] = result
            
            # Create execution record
            execution = {
                "id": f"exec-{uuid4()}",
                "task_id": task_id,
                "old_status": old_status,
                "new_status": status,
                "result": result,
                "timestamp": datetime.now(UTC).isoformat()
            }
            
            if task_id not in self._task_executions:
                self._task_executions[task_id] = []
            
            self._task_executions[task_id].append(execution)
            
            return {
                "task_id": task_id,
                "old_status": old_status,
                "new_status": status,
                "result": result,
                "updated_at": execution["timestamp"],
                "execution_count": len(self._task_executions[task_id])
            }
            
        except Exception as exc:
            self._logger.error(f"Error updating task status for {task_id}: {str(exc)}")
            raise
    
    async def list_tasks(
        self,
        session_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """List tasks with optional filtering.
        
        Args:
            session_id: Optional session filter
            status: Optional status filter
            limit: Maximum number of tasks to return
            
        Returns:
            List of task dictionaries
        """
        self.log_operation(
            "list_tasks",
            session_id=session_id,
            status=status,
            limit=limit
        )
        
        try:
            # Filter tasks
            filtered_tasks = []
            
            for task in self._tasks.values():
                # Apply filters
                if session_id and task.get("session_id") != session_id:
                    continue
                
                if status and task.get("status") != status:
                    continue
                
                # Create task summary
                task_summary = {
                    "task_id": task["id"],
                    "description": task["description"],
                    "type": task["type"],
                    "status": task["status"],
                    "priority": task["priority"],
                    "session_id": task["session_id"],
                    "created_at": task["created_at"],
                    "estimated_duration": task["estimated_duration"],
                    "dependency_count": len(task.get("dependencies", []))
                }
                
                filtered_tasks.append(task_summary)
            
            # Sort by priority and creation time
            filtered_tasks.sort(key=lambda x: (
                -self._task_types.get(x["type"], {}).get("priority", 3),
                x["created_at"]
            ))
            
            return filtered_tasks[:limit]
            
        except Exception as exc:
            self._logger.error(f"Error listing tasks: {str(exc)}")
            raise
    
    async def get_task_dependencies(self, task_id: str) -> List[Dict[str, Any]]:
        """Get dependencies for a specific task.
        
        Args:
            task_id: Task identifier
            
        Returns:
            List of task dependencies
        """
        self.log_operation("get_task_dependencies", task_id=task_id)
        
        try:
            task = self._tasks.get(task_id)
            if not task:
                raise ValueError(f"Task not found: {task_id}")
            
            dependencies = self._task_dependencies.get(task_id, [])
            dependency_details = []
            
            for dep_id in dependencies:
                dep_task = self._tasks.get(dep_id)
                if dep_task:
                    dependency_details.append({
                        "task_id": dep_id,
                        "description": dep_task["description"],
                        "type": dep_task["type"],
                        "status": dep_task["status"],
                        "priority": dep_task["priority"],
                        "created_at": dep_task["created_at"]
                    })
            
            return dependency_details
            
        except Exception as exc:
            self._logger.error(f"Error getting task dependencies for {task_id}: {str(exc)}")
            raise
    
    async def add_task_dependency(
        self,
        task_id: str,
        depends_on_task_id: str
    ) -> Dict[str, Any]:
        """Add a dependency relationship between tasks.
        
        Args:
            task_id: Task that depends on another
            depends_on_task_id: Task that is being depended on
            
        Returns:
            Dictionary containing dependency addition result
        """
        self.log_operation(
            "add_task_dependency",
            task_id=task_id,
            depends_on_task_id=depends_on_task_id
        )
        
        try:
            # Validate tasks exist
            if task_id not in self._tasks:
                raise ValueError(f"Task not found: {task_id}")
            
            if depends_on_task_id not in self._tasks:
                raise ValueError(f"Dependency task not found: {depends_on_task_id}")
            
            # Check for circular dependency
            if await self._would_create_circular_dependency(task_id, depends_on_task_id):
                raise ValueError(f"Adding this dependency would create a circular dependency")
            
            # Add dependency
            if task_id not in self._task_dependencies:
                self._task_dependencies[task_id] = []
            
            if depends_on_task_id not in self._task_dependencies[task_id]:
                self._task_dependencies[task_id].append(depends_on_task_id)
            
            # Update task records
            self._tasks[task_id]["dependencies"].append(depends_on_task_id)
            self._tasks[depends_on_task_id]["dependents"].append(task_id)
            
            return {
                "task_id": task_id,
                "depends_on_task_id": depends_on_task_id,
                "status": "dependency_added",
                "added_at": datetime.now(UTC).isoformat(),
                "total_dependencies": len(self._task_dependencies[task_id])
            }
            
        except Exception as exc:
            self._logger.error(f"Error adding task dependency: {str(exc)}")
            raise
    
    async def calculate_task_complexity(self, task_description: str) -> Dict[str, Any]:
        """Calculate complexity score for a task.
        
        Args:
            task_description: Description of the task
            
        Returns:
            Dictionary containing complexity analysis
        """
        self.log_operation(
            "calculate_task_complexity",
            task_description=task_description[:100]
        )
        
        try:
            complexity = self._estimate_task_complexity(task_description)
            
            # Determine complexity level
            if complexity < 3:
                level = "simple"
                estimated_duration = "5m"
            elif complexity < 7:
                level = "medium"
                estimated_duration = "15m"
            else:
                level = "complex"
                estimated_duration = "45m"
            
            return {
                "task_description": task_description,
                "complexity_score": complexity,
                "complexity_level": level,
                "estimated_duration": estimated_duration,
                "factors": self._analyze_complexity_factors(task_description),
                "calculated_at": datetime.now(UTC).isoformat()
            }
            
        except Exception as exc:
            self._logger.error(f"Error calculating task complexity: {str(exc)}")
            raise
    
    async def optimize_task_order(self, tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Optimize task execution order based on dependencies and priority.
        
        Args:
            tasks: List of tasks to optimize
            
        Returns:
            Optimized list of tasks
        """
        self.log_operation("optimize_task_order", task_count=len(tasks))
        
        try:
            # Create task lookup
            task_lookup = {task["task_id"]: task for task in tasks}
            
            # Build dependency graph
            dependency_graph = {}
            for task in tasks:
                task_id = task["task_id"]
                dependencies = self._task_dependencies.get(task_id, [])
                dependency_graph[task_id] = [dep for dep in dependencies if dep in task_lookup]
            
            # Topological sort for execution order
            optimized_order = []
            visited = set()
            temp_visited = set()
            
            def visit(task_id: str):
                if task_id in temp_visited:
                    raise ValueError(f"Circular dependency detected involving task: {task_id}")
                
                if task_id in visited:
                    return
                
                temp_visited.add(task_id)
                
                # Visit dependencies first
                for dep_id in dependency_graph.get(task_id, []):
                    visit(dep_id)
                
                temp_visited.remove(task_id)
                visited.add(task_id)
                
                # Add to optimized order
                task = task_lookup[task_id]
                if task:
                    optimized_order.append(task)
            
            # Visit all tasks
            for task in tasks:
                if task["task_id"] not in visited:
                    visit(task["task_id"])
            
            # Sort by priority within dependency constraints
            optimized_order.sort(key=lambda x: (
                -self._task_types.get(x["type"], {}).get("priority", 3),
                x["created_at"]
            ))
            
            return optimized_order
            
        except Exception as exc:
            self._logger.error(f"Error optimizing task order: {str(exc)}")
            raise
    
    # Helper methods
    
    def _estimate_task_complexity(self, task_description: str) -> int:
        """Estimate task complexity from description."""
        complexity_indicators = {
            "simple": ["create", "write", "update", "get", "list", "show"],
            "medium": ["analyze", "design", "implement", "integrate", "test"],
            "complex": ["optimize", "refactor", "architecture", "system", "multiple", "coordinate"]
        }
        
        description_lower = task_description.lower()
        complexity_score = 1  # Base complexity
        
        for level, indicators in complexity_indicators.items():
            for indicator in indicators:
                if indicator in description_lower:
                    if level == "simple":
                        complexity_score += 1
                    elif level == "medium":
                        complexity_score += 2
                    elif level == "complex":
                        complexity_score += 3
        
        # Adjust for length
        if len(task_description) > 200:
            complexity_score += 1
        elif len(task_description) > 500:
            complexity_score += 2
        
        return min(complexity_score, 10)  # Cap at 10
    
    def _get_agent_requirements(self, task_type: str) -> List[str]:
        """Get agent requirements for task type."""
        requirements = {
            "analysis": ["analyst"],
            "research": ["researcher"],
            "design": ["analyst", "coder"],
            "implementation": ["coder"],
            "testing": ["reviewer", "coder"],
            "deployment": ["coder"],
            "decomposition": ["analyst"],
            "coordination": ["analyst"]
        }
        
        return requirements.get(task_type, ["analyst"])
    
    def _estimate_resource_needs(self, task_type: str) -> Dict[str, Any]:
        """Estimate resource requirements for task type."""
        resource_needs = {
            "analysis": {"cpu": "low", "memory": "low", "time": "5m"},
            "research": {"cpu": "medium", "memory": "medium", "time": "10m"},
            "design": {"cpu": "medium", "memory": "medium", "time": "15m"},
            "implementation": {"cpu": "high", "memory": "high", "time": "30m"},
            "testing": {"cpu": "medium", "memory": "medium", "time": "10m"},
            "deployment": {"cpu": "low", "memory": "low", "time": "5m"},
            "decomposition": {"cpu": "low", "memory": "low", "time": "2m"},
            "coordination": {"cpu": "low", "memory": "low", "time": "3m"}
        }
        
        return resource_needs.get(task_type, {"cpu": "medium", "memory": "medium", "time": "15m"})
    
    def _analyze_complexity_factors(self, task_description: str) -> List[str]:
        """Analyze factors contributing to task complexity."""
        factors = []
        description_lower = task_description.lower()
        
        # Check for various complexity factors
        if any(word in description_lower for word in ["multiple", "several", "various"]):
            factors.append("multiple_components")
        
        if any(word in description_lower for word in ["integrate", "combine", "merge"]):
            factors.append("integration_required")
        
        if any(word in description_lower for word in ["optimize", "performance", "efficiency"]):
            factors.append("optimization_needed")
        
        if any(word in description_lower for word in ["api", "external", "service"]):
            factors.append("external_dependencies")
        
        if any(word in description_lower for word in ["database", "storage", "persistence"]):
            factors.append("data_operations")
        
        if len(task_description) > 300:
            factors.append("lengthy_description")
        
        return factors
    
    async def _would_create_circular_dependency(self, task_id: str, depends_on: str) -> bool:
        """Check if adding dependency would create a circular dependency."""
        visited = set()
        
        def check_circular(current_id: str) -> bool:
            if current_id == task_id:
                return True  # Circular dependency found
            
            if current_id in visited:
                return False
            
            visited.add(current_id)
            
            for dep_id in self._task_dependencies.get(current_id, []):
                if check_circular(dep_id):
                    return True
            
            visited.remove(current_id)
            return False
        
        return check_circular(depends_on)
