"""Converter for WorkflowStep → DelegationTask transformation.

This module provides utilities to convert WorkflowStep (from workflow planning)
to DelegationTask (for DelegationEngine execution), enabling the migration
from step_runner to DelegationEngine.
"""

from __future__ import annotations

from uuid import UUID

from mindflow_backend.schemas.orchestration.delegation import DelegationTask
from mindflow_backend.schemas.orchestration.orchestrator import Priority
from mindflow_backend.schemas.orchestration.workflow import WorkflowStep


def workflow_step_to_delegation_task(
    step: WorkflowStep,
    user_message: str,
    session_id: str,
    *,
    memory_context: str = "",
    memory_grounded: bool = False,
    conversation_history: list[dict[str, str]] | None = None,
    prior_context: str = "",
    folder_path: str | None = None,
    max_iterations: int = 1,
) -> DelegationTask:
    """Convert WorkflowStep to DelegationTask for DelegationEngine execution.
    
    This function maps the fields from WorkflowStep to DelegationTask,
    preserving all necessary information for the delegation execution.
    
    Args:
        step: The WorkflowStep to convert
        user_message: The original user message
        session_id: The session ID
        memory_context: RAG context from agent history (optional)
        memory_grounded: If response should prioritize memory context (optional)
        conversation_history: Full conversation history (optional)
        prior_context: Context from previous workflow steps (optional)
        folder_path: Working directory for filesystem tools (optional)
        max_iterations: Maximum iteration rounds (default: 1)
        
    Returns:
        DelegationTask configured for execution via DelegationEngine
    """
    return DelegationTask(
        agent=step.agent_role,
        agent_role=step.agent_role,
        specialist=step.specialist,
        agent_id=step.agent_id,
        objective=step.objective or user_message,
        scope=[],  # WorkflowStep doesn't have scope field
        exclusions=[],  # WorkflowStep doesn't have exclusions field
        expected_output="",  # WorkflowStep doesn't have expected_output field
        context_from_session=prior_context,  # Map prior_context to context_from_session
        priority=Priority.NORMAL,  # Default priority
        tools=step.tools,  # Preserve tool scope from step
        root_dir=folder_path,
        max_iterations=max_iterations,
        session_id=session_id,
        # New fields from step_runner integration
        memory_context=memory_context,
        memory_grounded=memory_grounded,
        conversation_history=conversation_history or [],
        streaming_enabled=False,  # Streaming not yet supported
    )


def delegation_result_to_step_output(
    delegation_result: DelegationTask,
    step: WorkflowStep,
) -> dict[str, any]:
    """Convert DelegationResult back to step_runner output format.
    
    This function converts the DelegationResult from DelegationEngine
    to the dict format expected by step_runner callers, maintaining
    backward compatibility.
    
    Args:
        delegation_result: The DelegationResult from DelegationEngine
        step: The original WorkflowStep
        
    Returns:
        Dict in the format expected by step_runner callers
    """
    return {
        "agent_id": step.agent_id,
        "agent_role": step.agent_role.value,
        "specialist": step.specialist.value if step.specialist else None,
        "status": delegation_result.status.value,
        "key_findings": delegation_result.key_findings,
        "full_output": delegation_result.full_output,
        "error": delegation_result.error_message,
    }
