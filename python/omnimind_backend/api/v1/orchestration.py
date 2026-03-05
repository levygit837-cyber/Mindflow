"""Orchestration API endpoints."""

from fastapi import APIRouter

from omnimind_backend.api.controllers.orchestration_controller import OrchestrationController
from omnimind_backend.api.schemas.requests import (
    OrchestrationRequest,
    TaskDecompositionRequest,
    PersonalitySelectionRequest
)

router = APIRouter(prefix="/orchestration", tags=["orchestration"])

# Initialize controller
orchestration_controller = OrchestrationController()


@router.post("/decompose")
async def decompose_task(request: TaskDecompositionRequest):
    """Decompose a complex task into sub-tasks."""
    return await orchestration_controller.decompose_task(request)


@router.post("/execute")
async def execute_orchestration(request: OrchestrationRequest):
    """Execute orchestration with agent coordination."""
    return await orchestration_controller.execute_orchestration(request)


@router.get("/execution/{execution_id}")
async def get_execution_status(execution_id: str):
    """Get status of task execution."""
    return await orchestration_controller.get_execution_status(execution_id)


@router.post("/select-personality")
async def select_personality(request: PersonalitySelectionRequest):
    """Select optimal personality for a task."""
    return await orchestration_controller.select_personality(request)


@router.post("/coordinate/{task_id}")
async def coordinate_agents(
    task_id: str,
    agent_sequence: list[str],
    session_id: str | None = None
):
    """Coordinate multiple agents for a task."""
    return await orchestration_controller.coordinate_agents(
        task_id, agent_sequence, session_id
    )
