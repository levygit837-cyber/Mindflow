"""Orchestration controller for managing task decomposition and agent coordination."""

from __future__ import annotations

from typing import Any
from fastapi import Request

from omnimind_backend.api.controllers.base_controller import BaseController, require_auth, audit_log
from omnimind_backend.api.schemas.requests import (
    OrchestrationRequest,
    TaskDecompositionRequest,
    PersonalitySelectionRequest
)
from omnimind_backend.api.schemas.responses import (
    OrchestrationResponse,
    TaskDecompositionResponse,
    PersonalitySelectionResponse,
    ExecutionStatusResponse
)
from omnimind_backend.services import get_orchestration_service


class OrchestrationController(BaseController):
    """Controller for orchestration operations and task management."""
    
    def __init__(self):
        super().__init__()
        self.orchestration_service = get_orchestration_service()
    
    @require_auth
    @audit_log("orchestration_decompose")
    async def decompose_task(self, request: TaskDecompositionRequest, req: Request) -> TaskDecompositionResponse:
        """Decompose a complex task into sub-tasks."""
        try:
            self.log_request(req, "decompose_task", task_description=request.task_description[:100])
            
            result = await self.orchestration_service.decompose_task(
                task_description=request.task_description,
                session_id=request.session_id,
                complexity_level=request.complexity_level
            )
            
            return TaskDecompositionResponse(
                success=True,
                message="Task decomposition completed",
                task_id=result["task_id"],
                description=result["description"],
                sub_tasks=result["sub_tasks"],
                complexity_level=result["complexity_level"],
                dependencies=result.get("dependencies", []),
                estimated_duration=result.get("estimated_duration"),
                metadata=result
            )
            
        except Exception as e:
            raise self.handle_error(e, "decompose_task")
    
    @require_auth
    @audit_log("orchestration_execute")
    async def execute_orchestration(self, request: OrchestrationRequest, req: Request) -> OrchestrationResponse:
        """Execute orchestration with agent coordination."""
        try:
            self.log_request(req, "execute_orchestration", task_description=request.task_description[:100])
            
            # First decompose the task
            decomposition = await self.orchestration_service.decompose_task(
                task_description=request.task_description,
                session_id=request.session_id,
                complexity_level=request.complexity_level
            )
            
            # Execute the DAG
            execution = await self.orchestration_service.execute_dag(
                dag_id=decomposition["task_id"],
                session_id=request.session_id
            )
            
            return OrchestrationResponse(
                success=True,
                message="Orchestration started",
                task_id=decomposition["task_id"],
                execution_id=execution["execution_id"],
                status=execution["status"],
                sub_tasks=decomposition["sub_tasks"],
                results=execution["results"],
                metadata={
                    "decomposition": decomposition,
                    "execution": execution
                }
            )
            
        except Exception as e:
            raise self.handle_error(e, "execute_orchestration")
    
    @require_auth
    @audit_log("orchestration_status")
    async def get_execution_status(self, execution_id: str, req: Request) -> ExecutionStatusResponse:
        """Get status of task execution."""
        try:
            self.log_request(req, "get_execution_status", execution_id=execution_id)
            
            status = await self.orchestration_service.get_execution_status(execution_id)
            
            return ExecutionStatusResponse(
                success=True,
                message="Execution status retrieved",
                execution_id=status["execution_id"],
                status=status["status"],
                progress=status.get("progress"),
                tasks_completed=status.get("tasks_completed"),
                total_tasks=status.get("total_tasks"),
                started_at=status.get("started_at"),
                completed_at=status.get("completed_at"),
                error=status.get("error"),
                metadata=status
            )
            
        except Exception as e:
            raise self.handle_error(e, "get_execution_status")
    
    @require_auth
    @audit_log("orchestration_select_personality")
    async def select_personality(self, request: PersonalitySelectionRequest, req: Request) -> PersonalitySelectionResponse:
        """Select optimal personality for a task."""
        try:
            self.log_request(req, "select_personality", task_id=request.task_id)
            
            result = await self.orchestration_service.select_personality(
                task_id=request.task_id,
                task_description=request.task_description,
                task_complexity=request.task_complexity,
                current_personality=request.current_personality
            )
            
            return PersonalitySelectionResponse(
                success=True,
                message="Personality selection completed",
                task_id=result["task_id"],
                selected_personality=result["selected_personality"],
                rationale=result["rationale"],
                confidence=result["confidence"],
                alternatives=result.get("alternatives", []),
                metadata=result
            )
            
        except Exception as e:
            raise self.handle_error(e, "select_personality")
    
    @require_auth
    @audit_log("orchestration_coordinate")
    async def coordinate_agents(
        self,
        task_id: str,
        agent_sequence: list[str],
        session_id: str | None = None,
        req: Request = None
    ) -> OrchestrationResponse:
        """Coordinate multiple agents for a task."""
        try:
            self.log_request(req, "coordinate_agents", task_id=task_id, agent_sequence=agent_sequence)
            
            result = await self.orchestration_service.coordinate_agents(
                task_id=task_id,
                agent_sequence=agent_sequence,
                session_id=session_id
            )
            
            return OrchestrationResponse(
                success=True,
                message="Agent coordination started",
                task_id=task_id,
                execution_id=result["coordination_id"],
                status=result["status"],
                metadata={
                    "coordination": result,
                    "agent_sequence": agent_sequence
                }
            )
            
        except Exception as e:
            raise self.handle_error(e, "coordinate_agents")
