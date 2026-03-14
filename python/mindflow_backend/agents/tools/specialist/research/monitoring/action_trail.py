"""Action trail logging system for browser automation.

Tracks every browser action with database persistence, audit trails,
and performance metrics for research operations.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.schemas.agents.research import (
    BrowserAction,
    BrowserActionRequest,
    BrowserActionResponse,
    IterationType,
)
from mindflow_backend.storage import BrowserActionTrail

_logger = get_logger(__name__)


class ActionTrailLogger:
    """Logger for browser action trails with database persistence."""
    
    def __init__(self, db_session: Session) -> None:
        """Initialize action trail logger.
        
        Args:
            db_session: Database session for persistence
        """
        self.db_session = db_session
        self._pending_actions: list[BrowserAction] = []
        
    async def log_action(
        self,
        session_id: str,
        agent_id: str,
        browser_id: str,
        iteration_type: IterationType,
        action_data: dict[str, Any] | None = None,
        success: bool = True,
        error_message: str | None = None,
        duration_ms: int | None = None,
    ) -> None:
        """Log a browser action to the database.
        
        Args:
            session_id: Research session identifier
            agent_id: Agent performing the action
            browser_id: Browser instance identifier
            iteration_type: Type of action performed
            action_data: Action-specific data
            success: Whether the action succeeded
            error_message: Error message if failed
            duration_ms: Action duration in milliseconds
        """
        action = BrowserAction(
            browser_id=browser_id,
            iteration_type=iteration_type,
            timestamp=datetime.now(UTC).isoformat(),
            action_data=action_data or {},
            success=success,
            error_message=error_message,
            duration_ms=duration_ms,
        )
        
        # Store in database
        try:
            trail = BrowserActionTrail(
                session_id=session_id,
                agent_id=agent_id,
                browser_id=browser_id,
                iteration_type=iteration_type.value,
                action_data=action_data or {},
                success=success,
                error_message=error_message,
                duration_ms=duration_ms,
                timestamp=datetime.now(UTC),
            )
            
            self.db_session.add(trail)
            self.db_session.commit()
            
            _logger.info(
                "action_trail_logged",
                session_id=session_id,
                agent_id=agent_id,
                browser_id=browser_id,
                iteration_type=iteration_type.value,
                success=success,
                duration_ms=duration_ms,
            )
            
        except Exception as exc:
            _logger.error(
                "action_trail_log_failed",
                session_id=session_id,
                agent_id=agent_id,
                browser_id=browser_id,
                iteration_type=iteration_type.value,
                error=str(exc),
            )
            self.db_session.rollback()
            
        # Also keep in memory for immediate access
        self._pending_actions.append(action)
        
    async def log_request_response(
        self,
        session_id: str,
        agent_id: str,
        request: BrowserActionRequest,
        response: BrowserActionResponse,
    ) -> None:
        """Log a complete browser action request/response pair.
        
        Args:
            session_id: Research session identifier
            agent_id: Agent performing the action
            request: Browser action request
            response: Browser action response
        """
        await self.log_action(
            session_id=session_id,
            agent_id=agent_id,
            browser_id=request.browser_id,
            iteration_type=request.iteration_type,
            action_data=request.action_data,
            success=response.success,
            error_message=response.error_message,
            duration_ms=response.duration_ms,
        )
        
    def get_action_trail(
        self,
        session_id: str | None = None,
        agent_id: str | None = None,
        browser_id: str | None = None,
        iteration_type: IterationType | None = None,
        limit: int = 100,
    ) -> list[BrowserActionTrail]:
        """Retrieve action trails from database.
        
        Args:
            session_id: Filter by session ID
            agent_id: Filter by agent ID
            browser_id: Filter by browser ID
            iteration_type: Filter by iteration type
            limit: Maximum number of results
            
        Returns:
            List of browser action trails
        """
        query = self.db_session.query(BrowserActionTrail)
        
        if session_id:
            query = query.filter(BrowserActionTrail.session_id == session_id)
        if agent_id:
            query = query.filter(BrowserActionTrail.agent_id == agent_id)
        if browser_id:
            query = query.filter(BrowserActionTrail.browser_id == browser_id)
        if iteration_type:
            query = query.filter(BrowserActionTrail.iteration_type == iteration_type.value)
            
        return query.order_by(BrowserActionTrail.timestamp.desc()).limit(limit).all()
        
    def get_session_summary(self, session_id: str) -> dict[str, Any]:
        """Get summary statistics for a research session.
        
        Args:
            session_id: Research session identifier
            
        Returns:
            Dictionary with session statistics
        """
        trails = self.get_action_trail(session_id=session_id, limit=1000)
        
        if not trails:
            return {
                "session_id": session_id,
                "total_actions": 0,
                "successful_actions": 0,
                "failed_actions": 0,
                "success_rate": 0.0,
                "average_duration_ms": 0,
                "total_duration_ms": 0,
                "iteration_types": {},
                "browsers_used": set(),
            }
            
        successful = sum(1 for trail in trails if trail.success)
        failed = len(trails) - successful
        
        durations = [trail.duration_ms for trail in trails if trail.duration_ms is not None]
        total_duration = sum(durations) if durations else 0
        avg_duration = total_duration / len(durations) if durations else 0
        
        # Count iteration types
        iteration_counts = {}
        for trail in trails:
            iteration_counts[trail.iteration_type] = iteration_counts.get(trail.iteration_type, 0) + 1
            
        # Get unique browsers
        browsers_used = set(trail.browser_id for trail in trails)
        
        return {
            "session_id": session_id,
            "total_actions": len(trails),
            "successful_actions": successful,
            "failed_actions": failed,
            "success_rate": successful / len(trails) if trails else 0.0,
            "average_duration_ms": avg_duration,
            "total_duration_ms": total_duration,
            "iteration_types": iteration_counts,
            "browsers_used": list(browsers_used),
        }
        
    def get_browser_summary(self, browser_id: str) -> dict[str, Any]:
        """Get summary statistics for a specific browser.
        
        Args:
            browser_id: Browser instance identifier
            
        Returns:
            Dictionary with browser statistics
        """
        trails = self.get_action_trail(browser_id=browser_id, limit=1000)
        
        if not trails:
            return {
                "browser_id": browser_id,
                "total_actions": 0,
                "successful_actions": 0,
                "failed_actions": 0,
                "success_rate": 0.0,
                "average_duration_ms": 0,
                "total_duration_ms": 0,
                "iteration_types": {},
                "first_action": None,
                "last_action": None,
            }
            
        successful = sum(1 for trail in trails if trail.success)
        failed = len(trails) - successful
        
        durations = [trail.duration_ms for trail in trails if trail.duration_ms is not None]
        total_duration = sum(durations) if durations else 0
        avg_duration = total_duration / len(durations) if durations else 0
        
        # Count iteration types
        iteration_counts = {}
        for trail in trails:
            iteration_counts[trail.iteration_type] = iteration_counts.get(trail.iteration_type, 0) + 1
            
        return {
            "browser_id": browser_id,
            "total_actions": len(trails),
            "successful_actions": successful,
            "failed_actions": failed,
            "success_rate": successful / len(trails) if trails else 0.0,
            "average_duration_ms": avg_duration,
            "total_duration_ms": total_duration,
            "iteration_types": iteration_counts,
            "first_action": trails[-1].timestamp.isoformat() if trails else None,
            "last_action": trails[0].timestamp.isoformat() if trails else None,
        }
        
    def get_error_analysis(
        self,
        session_id: str | None = None,
        agent_id: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Get analysis of failed actions.
        
        Args:
            session_id: Filter by session ID
            agent_id: Filter by agent ID
            limit: Maximum number of error results
            
        Returns:
            List of error analysis entries
        """
        query = self.db_session.query(BrowserActionTrail).filter(
            BrowserActionTrail.success == False
        )
        
        if session_id:
            query = query.filter(BrowserActionTrail.session_id == session_id)
        if agent_id:
            query = query.filter(BrowserActionTrail.agent_id == agent_id)
            
        failed_trails = query.order_by(BrowserActionTrail.timestamp.desc()).limit(limit).all()
        
        errors = []
        for trail in failed_trails:
            errors.append({
                "timestamp": trail.timestamp.isoformat(),
                "session_id": trail.session_id,
                "agent_id": trail.agent_id,
                "browser_id": trail.browser_id,
                "iteration_type": trail.iteration_type,
                "error_message": trail.error_message,
                "action_data": trail.action_data,
                "duration_ms": trail.duration_ms,
            })
            
        return errors
        
    def cleanup_old_trails(self, days_to_keep: int = 30) -> int:
        """Clean up old action trails from database.
        
        Args:
            days_to_keep: Number of days to keep trails
            
        Returns:
            Number of trails deleted
        """
        cutoff_date = datetime.now(UTC) - timedelta(days=days_to_keep)
        
        deleted = self.db_session.query(BrowserActionTrail).filter(
            BrowserActionTrail.timestamp < cutoff_date
        ).delete()
        
        self.db_session.commit()
        
        _logger.info(
            "action_trails_cleanup_completed",
            days_to_keep=days_to_keep,
            trails_deleted=deleted,
            cutoff_date=cutoff_date.isoformat(),
        )
        
        return deleted
        
    def get_pending_actions(self) -> list[BrowserAction]:
        """Get actions pending in memory (not yet persisted).
        
        Returns:
            List of pending browser actions
        """
        return self._pending_actions.copy()
        
    def clear_pending_actions(self) -> int:
        """Clear pending actions from memory.
        
        Returns:
            Number of actions cleared
        """
        count = len(self._pending_actions)
        self._pending_actions.clear()
        return count


# Context manager for action trail logging
class ActionTrailContext:
    """Context manager for automatic action trail logging."""
    
    def __init__(
        self,
        logger: ActionTrailLogger,
        session_id: str,
        agent_id: str,
        browser_id: str,
    ) -> None:
        """Initialize action trail context.
        
        Args:
            logger: Action trail logger instance
            session_id: Research session identifier
            agent_id: Agent performing actions
            browser_id: Browser instance identifier
        """
        self.logger = logger
        self.session_id = session_id
        self.agent_id = agent_id
        self.browser_id = browser_id
        self.start_time = time.time()
        
    async def log_action(
        self,
        iteration_type: IterationType,
        action_data: dict[str, Any] | None = None,
        success: bool = True,
        error_message: str | None = None,
    ) -> None:
        """Log an action within this context.
        
        Args:
            iteration_type: Type of action performed
            action_data: Action-specific data
            success: Whether the action succeeded
            error_message: Error message if failed
        """
        duration_ms = int((time.time() - self.start_time) * 1000)
        
        await self.logger.log_action(
            session_id=self.session_id,
            agent_id=self.agent_id,
            browser_id=self.browser_id,
            iteration_type=iteration_type,
            action_data=action_data,
            success=success,
            error_message=error_message,
            duration_ms=duration_ms,
        )
        
        # Reset start time for next action
        self.start_time = time.time()


async def get_action_trail_logger(db_session: Session) -> ActionTrailLogger:
    """Get action trail logger instance.
    
    Args:
        db_session: Database session for persistence
        
    Returns:
        ActionTrailLogger instance
    """
    return ActionTrailLogger(db_session)
