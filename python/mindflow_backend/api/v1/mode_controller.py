"""API endpoints for permission mode management."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Any
from loguru import logger

from mindflow_backend.permissions.mode_controller import ModeController
from mindflow_backend.permissions.types import PermissionMode

_logger = logger.bind(name=__name__)
router = APIRouter(prefix="/api/v1/modes", tags=["modes"])


class ModeToggleRequest(BaseModel):
    """Request to toggle permission mode."""
    session_id: str = Field(..., description="Session identifier")
    direction: str = Field(
        default="next",
        description="Direction: 'next', 'previous', or 'direct'"
    )
    target_mode: PermissionMode | None = Field(
        default=None,
        description="Target mode when direction is 'direct'"
    )


class ModeToggleResponse(BaseModel):
    """Response from mode toggle."""
    old_mode: str
    new_mode: str
    mode_info: dict[str, Any]
    success: bool
    message: str


class ModeInfoResponse(BaseModel):
    """Response with current mode info."""
    session_id: str
    current_mode: str
    mode_info: dict[str, Any]
    cycle_order: list[str]


@router.post("/toggle", response_model=ModeToggleResponse)
async def toggle_mode(request: ModeToggleRequest) -> ModeToggleResponse:
    """Toggle permission mode for a session.
    
    Supports:
    - "next": Move to next mode in cycle
    - "previous": Move to previous mode in cycle
    - "direct": Jump to specific mode (requires target_mode)
    """
    controller = ModeController()
    
    # Get current mode from session
    from mindflow_backend.services.core.session_service import get_session_service
    session_service = get_session_service()
    
    try:
        current_mode = await session_service.get_permission_mode(request.session_id)
    except Exception as e:
        _logger.error(f"Failed to get current mode: {e}")
        raise HTTPException(status_code=404, detail=f"Session {request.session_id} not found")
    
    # Determine new mode
    if request.direction == "next":
        new_mode = controller.get_next_mode(current_mode)
    elif request.direction == "previous":
        new_mode = controller.get_previous_mode(current_mode)
    elif request.direction == "direct" and request.target_mode:
        new_mode = request.target_mode
    else:
        raise HTTPException(
            status_code=400,
            detail="Invalid direction or missing target_mode for 'direct' direction"
        )
    
    # Validate transition
    is_valid, reason = controller.validate_transition(
        from_mode=current_mode,
        to_mode=new_mode,
    )
    
    if not is_valid:
        raise HTTPException(status_code=400, detail=reason)
    
    # Apply mode change
    try:
        await session_service.set_permission_mode(
            request.session_id,
            new_mode,
            pre_plan_mode=current_mode if new_mode == PermissionMode.PLAN else None,
        )
    except Exception as e:
        _logger.error(f"Failed to set mode: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update mode: {str(e)}")
    
    # Get mode info
    mode_info = controller.get_mode_info(new_mode)
    
    # Dispatch event
    from mindflow_backend.hooks.event_broadcaster import dispatch_custom_event
    await dispatch_custom_event("mode_changed", {
        "session_id": request.session_id,
        "old_mode": current_mode.value if hasattr(current_mode, "value") else str(current_mode),
        "new_mode": new_mode.value if hasattr(new_mode, "value") else str(new_mode),
    })
    
    _logger.info(
        "mode_toggled",
        session_id=request.session_id,
        old_mode=current_mode.value if hasattr(current_mode, "value") else str(current_mode),
        new_mode=new_mode.value if hasattr(new_mode, "value") else str(new_mode),
        direction=request.direction,
    )
    
    return ModeToggleResponse(
        old_mode=current_mode.value if hasattr(current_mode, "value") else str(current_mode),
        new_mode=new_mode.value if hasattr(new_mode, "value") else str(new_mode),
        mode_info=mode_info,
        success=True,
        message=f"Mode changed: {current_mode.value if hasattr(current_mode, 'value') else str(current_mode)} → {new_mode.value if hasattr(new_mode, 'value') else str(new_mode)}",
    )


@router.get("/current/{session_id}", response_model=ModeInfoResponse)
async def get_current_mode(session_id: str) -> ModeInfoResponse:
    """Get current permission mode for a session."""
    from mindflow_backend.services.core.session_service import get_session_service
    session_service = get_session_service()
    
    try:
        mode = await session_service.get_permission_mode(session_id)
    except Exception as e:
        _logger.error(f"Failed to get current mode: {e}")
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    
    controller = ModeController()
    mode_info = controller.get_mode_info(mode)
    cycle_order = [m.value for m in controller.get_cycle_order()]
    
    return ModeInfoResponse(
        session_id=session_id,
        current_mode=mode.value if hasattr(mode, "value") else str(mode),
        mode_info=mode_info,
        cycle_order=cycle_order,
    )


@router.get("/cycle", response_model=list[dict[str, Any]])
async def get_mode_cycle() -> list[dict[str, Any]]:
    """Get the full mode cycle with info for each mode."""
    controller = ModeController()
    cycle = controller.get_cycle_order()
    
    return [
        {
            "mode": mode.value,
            **controller.get_mode_info(mode),
        }
        for mode in cycle
    ]