"""Database models for planning metrics."""

from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from mindflow_backend.memory.storage.models import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class PlanningTriggerMetric(Base):
    """Planning trigger decision metrics."""
    
    __tablename__ = "planning_trigger_metrics"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(64), index=True)
    plan_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    trigger_decision: Mapped[bool] = mapped_column(Boolean)
    confidence: Mapped[float] = mapped_column(Float)
    user_confirmed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    execution_completed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    latency_ms: Mapped[float] = mapped_column(Float)
    method_used: Mapped[str] = mapped_column(String(20), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
