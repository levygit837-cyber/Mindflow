"""Context-Control-Arch main governance function.

Implements the core context governance logic for session management,
token window tracking, and automatic session creation.
"""

from __future__ import annotations

import math
from uuid import uuid4

from mindflow_backend.infra.config import get_settings
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.schemas.session.contracts import (
    ContextControlResult,
    ContextWindowInfo,
    SessionMode,
    SessionReview,
    SubSessionReview,
)

_logger = get_logger(__name__)


def _calculate_window_info(
    current_tokens: int,
    window_size: int,
    total_tokens: int | None = None,
) -> ContextWindowInfo:
    """Calculate current, previous, and next window information."""
    current_window_index = current_tokens // window_size
    current_window_start = current_window_index * window_size
    current_window_end = (current_window_index + 1) * window_size
    
    # Calculate adjacent windows
    previous_window = None
    if current_window_index > 0:
        prev_start = (current_window_index - 1) * window_size
        prev_end = current_window_index * window_size
        previous_window = (prev_start, prev_end)
    
    next_window = None
    if total_tokens is None or current_window_end < total_tokens:
        next_start = (current_window_index + 1) * window_size
        next_end = (current_window_index + 2) * window_size
        next_window = (next_start, next_end)
    
    # Calculate progress
    progress = current_tokens / total_tokens if total_tokens and total_tokens > 0 else 0.0
    
    return ContextWindowInfo(
        current_window=(current_window_start, current_window_end),
        current_window_index=current_window_index,
        previous_window=previous_window,
        next_window=next_window,
        window_size=window_size,
        total_tokens=total_tokens or current_tokens,
        progress_percentage=progress,
    )


def _format_token_range(start: int, end: int) -> str:
    """Format token range as human-readable string."""
    if end >= 1000:
        return f"{start//1000}k-{end//1000}k"
    return f"{start}-{end}"


async def context_control_arch(
    session_id: str,
    current_tokens: int,
    execution_window_size: int | None = None,
    context_analysis_window: int | None = None,
    total_tokens: int | None = None,
    existing_session: SessionReview | None = None,
) -> ContextControlResult:
    """
    Main context governance controller.
    
    Tracks current execution window position, creates new sessions when
    boundaries are crossed, and establishes parent-child relationships.
    
    Args:
        session_id: Current session identifier
        current_tokens: Current token count
        execution_window_size: Size of execution windows (default from config)
        context_analysis_window: Size of context analysis windows (default from config)
        total_tokens: Total expected tokens (for progress calculation)
        existing_session: Existing session review if available
        
    Returns:
        ContextControlResult with action taken and updated session information
    """
    settings = get_settings()
    
    # Use defaults from config if not provided
    exec_window_size = execution_window_size or settings.execution_window_size
    context_window_size = context_analysis_window or settings.context_analysis_window
    
    # Calculate window information
    window_info = _calculate_window_info(
        current_tokens=current_tokens,
        window_size=exec_window_size,
        total_tokens=total_tokens,
    )
    
    _logger.info(
        "context_control_arch_called",
        session_id=session_id,
        current_tokens=current_tokens,
        current_window=f"{window_info.current_window[0]}-{window_info.current_window[1]}",
        window_index=window_info.current_window_index,
    )
    
    # Check if we need to create a new session
    if existing_session is None:
        # First session - create as main session
        session_review = SessionReview(
            session_id=uuid4(),
            main_session_id=uuid4(),  # Will be set to session_id after creation
            token_range=_format_token_range(0, exec_window_size),
            execution_window=(0, exec_window_size),
            context_window=(0, context_window_size),
            mode=SessionMode.NORMAL,
            current_window_position=window_info.current_window_index,
            total_tokens_processed=current_tokens,
        )
        session_review.main_session_id = session_review.session_id
        
        return ContextControlResult(
            action_taken="session_created",
            session_review=session_review,
            window_info=window_info,
            tokens_processed=current_tokens,
            message=f"Created new main session {session_review.session_id}",
        )
    
    # Check if we've crossed into a new execution window
    current_window_index = window_info.current_window_index
    if current_window_index > existing_session.current_window_position:
        # Advanced to new window - create sub-session
        new_window_start = current_window_index * exec_window_size
        new_window_end = (current_window_index + 1) * exec_window_size
        
        sub_session = SubSessionReview(
            session_id=uuid4(),
            parent_session_id=existing_session.session_id,
            main_session_id=existing_session.main_session_id,
            token_sub_range=_format_token_range(new_window_start, new_window_end),
            execution_window=(new_window_start, new_window_end),
        )
        
        # Update existing session
        updated_session = existing_session.model_copy()
        updated_session.current_window_position = current_window_index
        updated_session.total_tokens_processed = current_tokens
        updated_session.updated_at = window_info.current_window[0]  # Use current time
        
        return ContextControlResult(
            action_taken="window_advanced",
            session_review=updated_session,
            sub_session_review=sub_session,
            window_info=window_info,
            tokens_processed=current_tokens,
            message=f"Advanced to window {current_window_index}, created sub-session {sub_session.session_id}",
        )
    
    # No action needed - just update token count
    updated_session = existing_session.model_copy()
    updated_session.total_tokens_processed = current_tokens
    updated_session.updated_at = window_info.current_window[0]
    
    return ContextControlResult(
        action_taken="none",
        session_review=updated_session,
        window_info=window_info,
        tokens_processed=current_tokens,
        message="No action required - within current window",
    )


def get_window_position(tokens: int, window_size: int) -> int:
    """Get the window index for a given token count."""
    return tokens // window_size


def get_window_bounds(window_index: int, window_size: int) -> tuple[int, int]:
    """Get the token bounds for a specific window index."""
    start = window_index * window_size
    end = (window_index + 1) * window_size
    return start, end


def is_window_boundary_crossed(
    previous_tokens: int,
    current_tokens: int,
    window_size: int,
) -> bool:
    """Check if token count crossed a window boundary."""
    prev_window = previous_tokens // window_size
    curr_window = current_tokens // window_size
    return prev_window != curr_window


def calculate_session_hierarchy(
    session_review: SessionReview,
    all_sub_sessions: list[SubSessionReview],
) -> dict[str, list[str]]:
    """Calculate the complete session hierarchy."""
    hierarchy = {str(session_review.session_id): []}
    
    for sub_session in all_sub_sessions:
        parent_id = str(sub_session.parent_session_id)
        if parent_id not in hierarchy:
            hierarchy[parent_id] = []
        hierarchy[parent_id].append(str(sub_session.session_id))
    
    return hierarchy
