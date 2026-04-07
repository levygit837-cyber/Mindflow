"""P2P communication helper utilities for Coder nodes.

This module provides helper functions for P2P communication with
other agents, particularly for architectural consultations with the Analyst.
"""

from __future__ import annotations

import time
from typing import Any

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


async def consult_analyst_architecture(
    agent_id: str,
    question: str,
    state: dict[str, Any],
    timeout: float = 30.0,
) -> dict[str, Any]:
    """Consult Analyst via P2P for architectural questions.

    Args:
        agent_id: Current agent ID (e.g., "coder")
        question: Architectural question to ask
        state: Current graph state
        timeout: Timeout for response

    Returns:
        Dictionary with consultation result
    """
    comm_bus = state.get("comm_bus")
    session_id = state.get("session_id", "unknown")

    if not comm_bus:
        _logger.warning("p2p_unavailable_no_bus", agent_id=agent_id)
        return {
            "success": False,
            "error": "Communication bus not available",
            "response": None,
        }

    if not comm_bus.is_available:
        _logger.warning("p2p_unavailable_bus_down", agent_id=agent_id)
        return {
            "success": False,
            "error": "Communication bus not available",
            "response": None,
        }

    try:
        from mindflow_backend.communication.mixins.agent_communication import AgentCommunicationMixin

        comm = AgentCommunicationMixin(
            agent_id=agent_id,
            bus=comm_bus
        )

        _logger.info(
            "p2p_consult_start",
            from_agent=agent_id,
            to_agent="analyst",
            question_preview=question[:100],
            timeout=timeout,
        )

        response = await comm.request_from(
            to_agent="analyst",
            content=question,
            timeout=timeout,
        )

        if response:
            _logger.info(
                "p2p_consult_success",
                from_agent="analyst",
                response_length=len(response),
            )
            return {
                "success": True,
                "response": response,
                "error": None,
            }
        else:
            _logger.warning(
                "p2p_consult_timeout",
                to_agent="analyst",
                timeout=timeout,
            )
            return {
                "success": False,
                "error": "Response timeout",
                "response": None,
            }

    except Exception as e:
        _logger.error("p2p_consult_error", agent_id=agent_id, error=str(e))
        return {
            "success": False,
            "error": str(e),
            "response": None,
        }


async def notify_orchestrator_progress(
    agent_id: str,
    percentage: int,
    current_step: str,
    state: dict[str, Any],
) -> bool:
    """Notify Orchestrator of mission progress.

    Args:
        agent_id: Current agent ID
        percentage: Progress percentage (0-100)
        current_step: Current step description
        state: Current graph state

    Returns:
        True if notification sent successfully
    """
    comm_bus = state.get("comm_bus")

    if not comm_bus or not comm_bus.is_available:
        _logger.debug("notify_progress_skipped_no_bus", agent_id=agent_id)
        return False

    try:
        from mindflow_backend.communication.mixins.agent_communication import AgentCommunicationMixin

        comm = AgentCommunicationMixin(
            agent_id=agent_id,
            bus=comm_bus
        )

        await comm.notify_progress(percentage, current_step)

        _logger.debug(
            "notify_progress_sent",
            agent_id=agent_id,
            percentage=percentage,
            step=current_step,
        )
        return True

    except Exception as e:
        _logger.error("notify_progress_error", agent_id=agent_id, error=str(e))
        return False


async def annotate_architectural_doubt(
    question: str,
    state: dict[str, Any],
) -> dict[str, Any]:
    """Annotate architectural doubt in memory when P2P fails.

    Args:
        question: The question that couldn't be answered
        state: Current graph state

    Returns:
        Dictionary with annotation result
    """
    agent_id = state.get("agent_id", "unknown")
    mission_type = state.get("mission_type", "unknown")
    session_id = state.get("session_id", "unknown")

    try:
        annotation = {
            "content": f"Architectural doubt (P2P unavailable): {question}",
            "agent_id": agent_id,
            "mission_type": mission_type,
            "session_id": session_id,
            "type": "architectural_doubt",
            "timestamp": time.time(),
            "requires_review": True,
        }

        # Add to annotations in state
        annotations = state.get("annotations", [])
        annotations.append(annotation)
        state["annotations"] = annotations

        _logger.info(
            "architectural_doubt_annotated",
            agent_id=agent_id,
            question_preview=question[:100],
        )

        return {
            "success": True,
            "annotation": annotation,
        }

    except Exception as e:
        _logger.error("annotation_error", error=str(e))
        return {
            "success": False,
            "error": str(e),
        }


async def request_specialist_help(
    agent_id: str,
    task_description: str,
    specialist_hint: str | None,
    state: dict[str, Any],
    timeout: float = 60.0,
) -> dict[str, Any]:
    """Request help from a specialist agent via Orchestrator.

    Args:
        agent_id: Current agent ID
        task_description: Description of the task needing help
        specialist_hint: Optional hint about which specialist to use
        state: Current graph state
        timeout: Timeout for response

    Returns:
        Dictionary with request result
    """
    comm_bus = state.get("comm_bus")

    if not comm_bus or not comm_bus.is_available:
        _logger.warning("specialist_help_skipped_no_bus", agent_id=agent_id)
        return {
            "success": False,
            "error": "Communication bus not available",
            "result": None,
        }

    try:
        from mindflow_backend.communication.mixins.agent_communication import AgentCommunicationMixin

        comm = AgentCommunicationMixin(
            agent_id=agent_id,
            bus=comm_bus
        )

        _logger.info(
            "requesting_specialist_help",
            from_agent=agent_id,
            specialist_hint=specialist_hint,
            task_preview=task_description[:100],
        )

        result = await comm.request_specialist_help(
            task_description=task_description,
            specialist_hint=specialist_hint,
            timeout=timeout,
        )

        if result:
            _logger.info("specialist_help_received", result_length=len(result))
            return {
                "success": True,
                "result": result,
            }
        else:
            _logger.warning("specialist_help_timeout", timeout=timeout)
            return {
                "success": False,
                "error": "Specialist help timeout",
                "result": None,
            }

    except Exception as e:
        _logger.error("specialist_help_error", agent_id=agent_id, error=str(e))
        return {
            "success": False,
            "error": str(e),
            "result": None,
        }


async def check_p2p_availability(state: dict[str, Any]) -> dict[str, Any]:
    """Check if P2P communication is available.

    Args:
        state: Current graph state

    Returns:
        Dictionary with availability status
    """
    comm_bus = state.get("comm_bus")

    if not comm_bus:
        return {
            "available": False,
            "reason": "No communication bus in state",
        }

    if not comm_bus.is_available:
        return {
            "available": False,
            "reason": "Communication bus is not available",
        }

    return {
        "available": True,
        "reason": None,
    }


async def graceful_p2p_fallback(
    operation: str,
    error: str,
    state: dict[str, Any],
    annotation_content: str | None = None,
) -> dict[str, Any]:
    """Handle P2P failure gracefully with annotation.

    Args:
        operation: Name of the operation that failed
        error: Error message
        state: Current graph state
        annotation_content: Optional custom annotation content

    Returns:
        Dictionary with fallback result
    """
    _logger.warning(
        "p2p_fallback",
        operation=operation,
        error=error,
    )

    # Create annotation
    if annotation_content is None:
        annotation_content = f"P2P operation '{operation}' failed: {error}"

    annotation_result = await annotate_architectural_doubt(annotation_content, state)

    return {
        "success": False,
        "error": error,
        "fallback_used": True,
        "annotation_result": annotation_result,
    }
