"""Review Repository for session review storage and retrieval."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from mindflow_backend.schemas.session.review import SessionReviewResult, ReviewPriority
from mindflow_backend.storage.postgresql.models import SessionReview


class ReviewRepository:
    """Repository for session review operations."""
    
    def __init__(self, db: Session) -> None:
        self.db = db
    
    async def create_review(
        self,
        review_id: str,
        session_id: str,
        window_range: tuple[int, int],
        review_data: Dict[str, Any],
        priority: ReviewPriority,
        created_at: Optional[datetime] = None
    ) -> SessionReview:
        """Create a new session review record."""
        review = SessionReview(
            id=review_id,
            session_id=session_id,
            window_start=window_range[0],
            window_end=window_range[1],
            review_data=review_data,
            priority=priority.value,
            created_at=created_at or datetime.utcnow()
        )
        
        self.db.add(review)
        self.db.flush()
        return review
    
    async def get_reviews_by_session(
        self,
        session_id: str,
        limit: int = 10
    ) -> List[SessionReview]:
        """Get reviews for a specific session."""
        stmt = (
            select(SessionReview)
            .where(SessionReview.session_id == session_id)
            .order_by(SessionReview.created_at.desc())
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())
    
    async def get_recent_reviews(
        self,
        limit: int = 50,
        priority: Optional[ReviewPriority] = None
    ) -> List[SessionReview]:
        """Get recent reviews, optionally filtered by priority."""
        stmt = select(SessionReview).order_by(SessionReview.created_at.desc()).limit(limit)
        
        if priority:
            stmt = stmt.where(SessionReview.priority == priority.value)
        
        return list(self.db.scalars(stmt).all())
    
    async def get_review_by_id(self, review_id: str) -> Optional[SessionReview]:
        """Get a specific review by ID."""
        return self.db.get(SessionReview, review_id)
    
    async def delete_old_reviews(self, days: int = 30) -> int:
        """Delete reviews older than specified days."""
        from sqlalchemy import func
        
        cutoff_date = datetime.utcnow() - datetime.timedelta(days=days)
        stmt = (
            select(SessionReview)
            .where(SessionReview.created_at < cutoff_date)
        )
        
        result = self.db.execute(stmt)
        deleted_count = result.rowcount if result else 0
        
        if deleted_count > 0:
            from mindflow_backend.infra.logging import get_logger
            logger = get_logger(__name__)
            logger.info(
                "deleted_old_reviews",
                deleted_count=deleted_count,
                days=days
            )
        
        return deleted_count
