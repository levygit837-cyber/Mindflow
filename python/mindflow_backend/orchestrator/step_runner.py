"""Shared runtime executor for explicit workflow steps.

This module now uses DelegationEngine as the backend for execution,
providing a unified execution path for all agent tasks.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from mindflow_backend.agents.specialists.runtime_policy import get_agent_runtime_policy
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.orchestrator.delegation.converter import (
    delegation_result_to_step_output,
    workflow_step_to_delegation_task,
)
from mindflow_backend.schemas.orchestration.workflow import WorkflowStep

_logger = get_logger(__name__)

ChunkDispatcher = Callable[[str], Awaitable[None]] | None
EventDispatcher = Callable[[str, dict[str, Any]], Awaitable[None]] | None


async def run_workflow_step(
    *,
    step: WorkflowStep,
    user_message: str,
    provider: str,
    model: str,
    session_id: str,
    folder_path: str | None = None,
    memory_context: str = "",
    memory_grounded: bool = False,
    conversation_history: list[dict[str, str]] | None = None,
    prior_context: str = "",
    chunk_dispatcher: ChunkDispatcher = None,
    event_dispatcher: EventDispatcher = None,
) -> dict[str, Any]:
    """Execute a single step using DelegationEngine backend.
    
    This function now uses DelegationEngine as the unified execution backend,
    converting WorkflowStep to DelegationTask and delegating the execution.
    
    Args:
        step: The WorkflowStep to execute
        user_message: The original user message
        provider: LLM provider
        model: LLM model
        session_id: Session ID
        folder_path: Working directory (optional)
        memory_context: RAG context from agent history (optional)
        memory_grounded: If response should prioritize memory context (optional)
        conversation_history: Full conversation history (optional)
        prior_context: Context from previous workflow steps (optional)
        chunk_dispatcher: Streaming dispatcher (currently not used, reserved for future)
        event_dispatcher: Event dispatcher for execution events (optional)
        
    Returns:
        Dict with agent_id, agent_role, specialist, status, key_findings, full_output, error
    """
    # Get agent runtime policy for max_iterations
    policy = get_agent_runtime_policy(agent_id=step.agent_id, session_id=session_id)
    
    # Convert WorkflowStep → DelegationTask
    delegation_task = workflow_step_to_delegation_task(
        step=step,
        user_message=user_message,
        session_id=session_id,
        memory_context=memory_context,
        memory_grounded=memory_grounded,
        conversation_history=conversation_history,
        prior_context=prior_context,
        folder_path=folder_path,
        max_iterations=policy.max_iterations,
    )
    
    # Use DelegationEngine for execution
    from mindflow_backend.orchestrator.delegation.engine import get_delegation_engine
    
    delegation_engine = get_delegation_engine()
    
    try:
        delegation_result = await delegation_engine.delegate_task(
            task=delegation_task,
            session=None,  # Session object is optional for step_runner
            session_id=session_id,
        )
        
        # Convert DelegationResult → step_runner output format
        result = delegation_result_to_step_output(delegation_result, step)
        
        _logger.info(
            "workflow_step_completed",
            agent_id=step.agent_id,
            status=result["status"],
        )
        
        return result
        
    except Exception as exc:
        _logger.error(
            "workflow_step_failed",
            agent_id=step.agent_id,
            error=str(exc),
        )
        return {
            "agent_id": step.agent_id,
            "agent_role": step.agent_role.value,
            "specialist": step.specialist.value if step.specialist else None,
            "status": "failed",
            "key_findings": "",
            "full_output": "",
            "error": str(exc),
        }
