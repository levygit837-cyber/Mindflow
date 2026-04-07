"""Orchestrator worker for handling task orchestration and workflow management."""

from __future__ import annotations

import time
from typing import Any

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.workers.base.worker import BaseWorker, WorkerResult
from mindflow_backend.workers.config.queues import QueueConfig

_logger = get_logger(__name__)


class OrchestratorWorker(BaseWorker):
    """Worker specialized for Orchestrator Agent tasks."""
    
    def __init__(self, queue_config: QueueConfig) -> None:
        """Initialize the Orchestrator worker."""
        super().__init__(queue_config, worker_name="orchestrator_worker")
    
    async def process_message(self, message_data: dict[str, Any]) -> WorkerResult:
        """Process orchestration and workflow tasks.
        
        Supported task types:
        - task_decomposition: Break down complex tasks
        - workflow_execution: Execute multi-agent workflows
        - resource_allocation: Allocate resources to tasks
        - agent_coordination: Coordinate between agents
        - progress_monitoring: Monitor task progress
        """
        message_data = self._normalize_message_data(message_data)
        start_time = time.time()
        task_type = message_data.get("task_type", "unknown")
        task_id = message_data.get("task_id", "unknown")
        
        try:
            _logger.info(f"OrchestratorWorker processing {task_type} task {task_id}")
            
            if task_type == "task_decomposition":
                result = await self._handle_task_decomposition(message_data)
            elif task_type == "workflow_execution":
                result = await self._handle_workflow_execution(message_data)
            elif task_type == "resource_allocation":
                result = await self._handle_resource_allocation(message_data)
            elif task_type == "agent_coordination":
                result = await self._handle_agent_coordination(message_data)
            elif task_type == "progress_monitoring":
                result = await self._handle_progress_monitoring(message_data)
            else:
                result = WorkerResult(
                    success=False,
                    message=f"Unsupported task type: {task_type}",
                    processing_time=time.time() - start_time,
                )
            
            _logger.info(
                f"OrchestratorWorker completed {task_type} task {task_id} "
                f"({'SUCCESS' if result.success else 'FAILED'})"
            )
            
            return result
            
        except Exception as e:
            _logger.error(
                f"OrchestratorWorker failed to process {task_type} task {task_id}: {e}",
                exc_info=True
            )
            return WorkerResult(
                success=False,
                message=f"Task processing failed: {e}",
                error=e,
                processing_time=time.time() - start_time,
            )
    
    async def _handle_task_decomposition(self, message_data: dict[str, Any]) -> WorkerResult:
        """Handle complex task decomposition using LLM-based planning."""
        complex_task = message_data.get("complex_task")
        complexity_level = message_data.get("complexity_level", "medium")
        target_agents = message_data.get("target_agents", [])
        
        if not complex_task:
            return WorkerResult(
                success=False,
                message="No complex task provided for decomposition",
                data={"error": "complex_task is required"},
            )
        
        try:
            from mindflow_backend.services.llm import get_llm_service
            
            llm_service = get_llm_service()
            
            # Generate decomposition using LLM
            prompt = f"""Decompose this complex task into subtasks:

Task: {complex_task}
Complexity Level: {complexity_level}
Available Agents: {', '.join(target_agents) if target_agents else 'analyst, coder, researcher, orchestrator'}

Generate 3-5 subtasks with the following format for each:
- Description: [clear description]
- Assigned Agent: [agent type]
- Priority: [high/medium/low]
- Estimated Time: [seconds]
- Dependencies: [list of other subtask numbers it depends on]

Output should be structured and parseable."""
            
            decomposition = await llm_service.generate(
                prompt=prompt,
                system_message="You are a task decomposition expert. Create clear, actionable subtasks.",
                temperature=0.3,
                max_tokens=1000,
            )
            
            # Parse the decomposition into structured subtasks
            subtasks = self._parse_decomposition(decomposition, target_agents)
            
            # Build dependencies map
            dependencies = {}
            for i, subtask in enumerate(subtasks):
                if subtask.get("dependencies"):
                    dependencies[f"subtask_{i+1}"] = [
                        f"subtask_{d}" for d in subtask["dependencies"]
                    ]
            
            # Calculate execution order using topological sort
            execution_order = self._calculate_execution_order(subtasks, dependencies)
            
            total_time = sum(s.get("estimated_time", 300) for s in subtasks)
            
            return WorkerResult(
                success=True,
                message=f"Task decomposition completed for: {complex_task}",
                data={
                    "original_task": complex_task,
                    "complexity_level": complexity_level,
                    "subtasks": subtasks,
                    "dependencies": dependencies,
                    "total_estimated_time": total_time,
                    "recommended_execution_order": execution_order,
                    "decomposition_raw": decomposition,
                },
            )
            
        except Exception as exc:
            return WorkerResult(
                success=False,
                message=f"Task decomposition failed: {exc}",
                data={"error": str(exc)},
            )
    
    @staticmethod
    def _parse_decomposition(text: str, available_agents: list[str]) -> list[dict[str, Any]]:
        """Parse LLM decomposition output into structured subtasks."""
        import re
        
        default_agents = ["analyst", "coder", "researcher", "orchestrator"]
        agents = available_agents if available_agents else default_agents
        
        subtasks = []
        sections = re.split(r'\n\n|\n(?=Subtask|Task \d)', text)
        
        for i, section in enumerate(sections[:5], 1):  # Limit to 5 subtasks
            if not section.strip():
                continue
            
            # Extract fields using regex
            desc_match = re.search(r'Description:\s*(.+?)(?=\n|$)', section, re.IGNORECASE)
            agent_match = re.search(r'Assigned Agent:\s*(\w+)', section, re.IGNORECASE)
            priority_match = re.search(r'Priority:\s*(\w+)', section, re.IGNORECASE)
            time_match = re.search(r'Estimated Time:\s*(\d+)', section, re.IGNORECASE)
            deps_match = re.search(r'Dependencies:\s*([\d,\s]*)', section, re.IGNORECASE)
            
            subtasks.append({
                "id": f"subtask_{i}",
                "description": desc_match.group(1).strip() if desc_match else f"Task component {i}",
                "assigned_agent": agent_match.group(1).lower() if agent_match else agents[i % len(agents)],
                "priority": priority_match.group(1).lower() if priority_match else "medium",
                "estimated_time": int(time_match.group(1)) if time_match else 300,
                "dependencies": [int(d.strip()) for d in deps_match.group(1).split(",") if d.strip().isdigit()] if deps_match else [],
            })
        
        return subtasks if subtasks else [
            {
                "id": "subtask_1",
                "description": complex_task,
                "assigned_agent": agents[0],
                "priority": "high",
                "estimated_time": 600,
                "dependencies": [],
            }
        ]
    
    @staticmethod
    def _calculate_execution_order(subtasks: list[dict], dependencies: dict[str, list[str]]) -> list[str]:
        """Calculate execution order using simple topological sort."""
        # Simple approach: tasks with no dependencies first, then dependent tasks
        order = []
        completed = set()
        
        # First, add tasks with no dependencies
        for subtask in subtasks:
            task_id = subtask["id"]
            if not dependencies.get(task_id):
                order.append(task_id)
                completed.add(task_id)
        
        # Then, add tasks whose dependencies are completed
        max_iterations = len(subtasks) * 2
        iteration = 0
        
        while len(order) < len(subtasks) and iteration < max_iterations:
            iteration += 1
            for subtask in subtasks:
                task_id = subtask["id"]
                if task_id in completed:
                    continue
                
                deps = dependencies.get(task_id, [])
                if all(d in completed for d in deps):
                    order.append(task_id)
                    completed.add(task_id)
        
        return order
    
    async def _handle_workflow_execution(self, message_data: dict[str, Any]) -> WorkerResult:
        """Handle multi-agent workflow execution using AgentTeamManager."""
        workflow_id = message_data.get("workflow_id")
        workflow_definition = message_data.get("workflow_definition")
        execution_context = message_data.get("execution_context", {})
        
        if not workflow_id:
            return WorkerResult(
                success=False,
                message="No workflow_id provided",
                data={"error": "workflow_id is required"},
            )
        
        try:
            from mindflow_backend.execution.agent_team_manager import AgentTeamManager
            from mindflow_backend.execution.missions import MissionGraphType
            
            team_manager = AgentTeamManager()
            
            # Extract workflow components
            if workflow_definition:
                tasks = workflow_definition.get("tasks", [])
                agents = workflow_definition.get("agents", [])
                execution_mode = workflow_definition.get("mode", "sequential")
            else:
                # Default workflow from context
                tasks = [{"task": execution_context.get("task", "")}]
                agents = execution_context.get("agents", ["orchestrator"])
                execution_mode = "sequential"
            
            if not tasks:
                return WorkerResult(
                    success=True,
                    message=f"Workflow {workflow_id} has no tasks to execute",
                    data={"workflow_id": workflow_id, "tasks_executed": 0},
                )
            
            # Execute workflow based on mode
            session_id = execution_context.get("session_id", workflow_id)
            results = []
            failed_tasks = []
            
            if execution_mode == "parallel":
                # Execute tasks in parallel using team session
                result = await team_manager.run_team_session(
                    task=tasks[0].get("task", "Execute workflow"),
                    agent_ids=agents,
                    session_id=session_id,
                    skip_discussion=False,
                )
                results.append(result)
                if not result.success:
                    failed_tasks.append(tasks[0])
            else:
                # Sequential execution
                for task in tasks:
                    try:
                        result = await team_manager.run_team_session(
                            task=task.get("task", ""),
                            agent_ids=[task.get("agent", agents[0])],
                            session_id=session_id,
                            skip_discussion=True,
                        )
                        results.append(result)
                        if not result.success:
                            failed_tasks.append(task)
                    except Exception as task_exc:
                        failed_tasks.append(task)
                        results.append(None)
            
            # Calculate metrics
            total_tasks = len(tasks)
            successful_tasks = total_tasks - len(failed_tasks)
            
            # Count agent contributions
            agent_contributions = {}
            for agent in agents:
                agent_contributions[agent] = sum(
                    1 for task in tasks 
                    if task.get("agent") == agent and task not in failed_tasks
                )
            
            return WorkerResult(
                success=len(failed_tasks) == 0,
                message=f"Workflow execution completed: {workflow_id}",
                data={
                    "workflow_id": workflow_id,
                    "execution_status": "completed" if len(failed_tasks) == 0 else "partial_failure",
                    "tasks_executed": total_tasks,
                    "tasks_successful": successful_tasks,
                    "tasks_failed": len(failed_tasks),
                    "execution_time": sum(r.duration_seconds for r in results if r) if results else 0,
                    "agent_contributions": agent_contributions,
                    "failed_tasks": failed_tasks,
                    "results": {
                        "output_generated": successful_tasks > 0,
                        "quality_score": successful_tasks / total_tasks if total_tasks > 0 else 0,
                        "efficiency_score": 1.0 - (len(failed_tasks) / total_tasks) if total_tasks > 0 else 0,
                    },
                },
            )
            
        except Exception as exc:
            return WorkerResult(
                success=False,
                message=f"Workflow execution failed: {exc}",
                data={"error": str(exc), "workflow_id": workflow_id},
            )
    
    async def _handle_resource_allocation(self, message_data: dict[str, Any]) -> WorkerResult:
        """Handle resource allocation to tasks using AgentTeamManager."""
        tasks = message_data.get("tasks", [])
        available_resources = message_data.get("available_resources", {})
        allocation_strategy = message_data.get("allocation_strategy", "balanced")
        
        try:
            from mindflow_backend.execution.agent_team_manager import AgentTeamManager
            import psutil
            
            team_manager = AgentTeamManager()
            
            # Get real system resource metrics
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            
            # Calculate available agents
            available_agents = list(team_manager._agent_capabilities.keys())
            
            # Perform allocation based on strategy
            allocations = []
            total_priority_score = 0
            
            for i, task in enumerate(tasks):
                # Determine task priority
                priority = task.get("priority", "medium")
                priority_score = {"high": 3, "medium": 2, "low": 1}.get(priority, 1)
                total_priority_score += priority_score
                
                # Select best agent for task based on task type
                task_type = task.get("type", "general")
                assigned_agent = self._select_agent_for_task(task_type, available_agents)
                
                # Calculate resource allocation based on priority
                if allocation_strategy == "priority":
                    cpu_share = (priority_score / max(total_priority_score, 1)) * 100
                    memory_share = (priority_score / max(total_priority_score, 1)) * memory.available / (1024 * 1024)
                else:  # balanced
                    cpu_share = 100 / max(len(tasks), 1)
                    memory_share = (memory.available / (1024 * 1024)) / max(len(tasks), 1)
                
                allocations.append({
                    "task_id": task.get("id", f"task_{i}"),
                    "assigned_resources": {
                        "agent": assigned_agent,
                        "cpu_percent": round(cpu_share, 1),
                        "memory_mb": round(memory_share, 0),
                    },
                    "priority": priority,
                    "estimated_duration": task.get("estimated_duration", "unknown"),
                })
            
            # Calculate optimization score
            utilization_score = min(100, len(allocations) * 15)  # Approximate
            balance_score = 100 - (cpu_percent / 2)  # Lower CPU usage = better balance
            optimization_score = (utilization_score + balance_score) / 2
            
            _logger.info(
                "resource_allocation_completed",
                tasks_allocated=len(allocations),
                strategy=allocation_strategy,
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
            )
            
            return WorkerResult(
                success=True,
                message=f"Resource allocation completed for {len(tasks)} tasks using {allocation_strategy} strategy",
                data={
                    "allocation_strategy": allocation_strategy,
                    "tasks_allocated": len(allocations),
                    "resource_utilization": {
                        "cpu_percent": round(cpu_percent, 1),
                        "memory_percent": round(memory.percent, 1),
                        "agents_available": len(available_agents),
                        "agents_allocated": len(set(a["assigned_resources"]["agent"] for a in allocations)),
                    },
                    "allocations": allocations,
                    "optimization_score": round(optimization_score / 100, 2),
                },
            )
            
        except Exception as exc:
            _logger.error("resource_allocation_failed", error=str(exc))
            return WorkerResult(
                success=False,
                message=f"Resource allocation failed: {str(exc)}",
                data={"error": str(exc)},
            )
    
    async def _handle_agent_coordination(self, message_data: dict[str, Any]) -> WorkerResult:
        """Handle coordination between agents using AgentTeamManager."""
        coordination_type = message_data.get("coordination_type", "collaboration")
        participating_agents = message_data.get("participating_agents", [])
        coordination_context = message_data.get("coordination_context", {})
        task = message_data.get("task", "")
        session_id = message_data.get("session_id", "")

        if not participating_agents:
            return WorkerResult(
                success=False,
                message="No participating agents specified",
                data={"error": "participating_agents is required"},
            )

        if not task:
            return WorkerResult(
                success=False,
                message="No task specified for coordination",
                data={"error": "task is required"},
            )

        try:
            # Import AgentTeamManager
            from mindflow_backend.execution.agent_team_manager import AgentTeamManager

            # Create team manager
            team_manager = AgentTeamManager()

            if coordination_type == "collaboration":
                # Run full team session
                result = await team_manager.run_team_session(
                    task=task,
                    agent_ids=participating_agents,
                    session_id=session_id,
                    skip_discussion=False,
                )

                return WorkerResult(
                    success=result.success,
                    message=f"Team collaboration completed: {len(result.mission_results)} missions executed",
                    data={
                        "coordination_type": coordination_type,
                        "participating_agents": participating_agents,
                        "team_id": result.team_id,
                        "mission_count": len(result.mission_results),
                        "synthesized_response": result.synthesized_response,
                        "success": result.success,
                    },
                )

            elif coordination_type == "delegation":
                # Simple delegation without discussion
                result = await team_manager.run_team_session(
                    task=task,
                    agent_ids=participating_agents,
                    session_id=session_id,
                    skip_discussion=True,
                )

                return WorkerResult(
                    success=result.success,
                    message=f"Agent delegation completed",
                    data={
                        "coordination_type": coordination_type,
                        "participating_agents": participating_agents,
                        "mission_count": len(result.mission_results),
                        "success": result.success,
                    },
                )

            else:
                return WorkerResult(
                    success=False,
                    message=f"Unknown coordination type: {coordination_type}",
                    data={"error": f"Unsupported coordination_type: {coordination_type}"},
                )

        except Exception as exc:
            return WorkerResult(
                success=False,
                message=f"Agent coordination failed: {exc}",
                data={
                    "error": str(exc),
                    "coordination_type": coordination_type,
                    "participating_agents": participating_agents,
                },
            )
    
    async def _handle_progress_monitoring(self, message_data: dict[str, Any]) -> WorkerResult:
        """Handle task and workflow progress monitoring using real data."""
        monitoring_target = message_data.get("monitoring_target")
        monitoring_scope = message_data.get("monitoring_scope", "workflow")
        update_frequency = message_data.get("update_frequency", "real_time")
        
        try:
            from mindflow_backend.execution.agent_team_manager import AgentTeamManager
            from datetime import datetime, timedelta
            
            team_manager = AgentTeamManager()
            
            # Get actual team status
            active_teams = list(team_manager._teams.keys())
            
            # Calculate progress metrics
            if monitoring_scope == "workflow":
                # Check workflow progress across teams
                completed_missions = 0
                in_progress_missions = 0
                pending_missions = 0
                
                for team_id, team_data in team_manager._teams.items():
                    missions = team_data.get("missions", [])
                    for mission in missions:
                        status = mission.get("status", "pending")
                        if status == "completed":
                            completed_missions += 1
                        elif status == "in_progress":
                            in_progress_missions += 1
                        else:
                            pending_missions += 1
                
                total_missions = completed_missions + in_progress_missions + pending_missions
                progress_percentage = (completed_missions / max(total_missions, 1)) * 100
                
                milestones = {
                    "completed": completed_missions,
                    "in_progress": in_progress_missions,
                    "pending": pending_missions,
                }
                
                # Estimate completion based on average mission duration
                if in_progress_missions > 0:
                    avg_duration = 300  # 5 minutes per mission as default
                    remaining_seconds = in_progress_missions * avg_duration + pending_missions * avg_duration
                    estimated_completion = (datetime.now() + timedelta(seconds=remaining_seconds)).isoformat()
                else:
                    estimated_completion = datetime.now().isoformat()
                
                # Identify bottlenecks
                bottlenecks = []
                if in_progress_missions > completed_missions * 2:
                    bottlenecks.append({
                        "type": "execution_backlog",
                        "description": "Too many missions in progress",
                        "impact": "high",
                        "recommendation": "Consider adding more agents or parallelizing tasks",
                    })
                
                # Generate recommendations
                recommendations = []
                if pending_missions > 0 and in_progress_missions < 3:
                    recommendations.append("Start pending missions to improve throughput")
                if completed_missions > 0 and progress_percentage < 50:
                    recommendations.append("Review mission complexity - may need decomposition")
                
            else:  # task scope
                progress_percentage = 50.0  # Placeholder for single task
                milestones = {"completed": 0, "in_progress": 1, "pending": 0}
                estimated_completion = (datetime.now() + timedelta(minutes=10)).isoformat()
                bottlenecks = []
                recommendations = []
            
            _logger.info(
                "progress_monitoring_completed",
                target=monitoring_target,
                scope=monitoring_scope,
                progress=progress_percentage,
            )
            
            return WorkerResult(
                success=True,
                message=f"Progress monitoring active for: {monitoring_target} ({monitoring_scope} scope)",
                data={
                    "monitoring_target": monitoring_target,
                    "monitoring_scope": monitoring_scope,
                    "update_frequency": update_frequency,
                    "current_status": "in_progress" if in_progress_missions > 0 else "completed",
                    "progress_percentage": round(progress_percentage, 1),
                    "estimated_completion": estimated_completion,
                    "milestones": milestones,
                    "active_teams": len(active_teams),
                    "bottlenecks": bottlenecks,
                    "recommendations": recommendations,
                },
            )
            
        except Exception as exc:
            _logger.error("progress_monitoring_failed", error=str(exc))
            return WorkerResult(
                success=False,
                message=f"Progress monitoring failed: {str(exc)}",
                data={"error": str(exc)},
            )

    def _select_agent_for_task(self, task_type: str, available_agents: list[str]) -> str:
        """Select the best agent for a given task type.
        
        Args:
            task_type: Type of task (coding, research, analysis, etc.)
            available_agents: List of available agent types
            
        Returns:
            Selected agent type
        """
        # Map task types to preferred agents
        task_agent_map = {
            "coding": ["coder", "planner"],
            "research": ["researcher", "explorer"],
            "analysis": ["analyst", "reviewer"],
            "testing": ["tester"],
            "planning": ["planner", "orchestrator"],
            "review": ["reviewer"],
            "general": ["general"],
        }
        
        # Get preferred agents for this task type
        preferred = task_agent_map.get(task_type.lower(), ["general"])
        
        # Find first available preferred agent
        for agent in preferred:
            if agent in available_agents:
                return agent
        
        # Fallback to first available agent or general
        return available_agents[0] if available_agents else "general"
