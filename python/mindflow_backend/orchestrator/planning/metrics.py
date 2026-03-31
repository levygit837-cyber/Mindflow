"""Metrics collection for planning trigger decisions."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.schemas.orchestration.planning import PlanningTriggerMetrics

_logger = get_logger(__name__)


class PlanningMetricsCollector:
    """Collect and analyze metrics for planning trigger decisions."""
    
    def __init__(self):
        self._metrics: dict[str, list[PlanningTriggerMetrics]] = defaultdict(list)
        self._db_session: AsyncSession | None = None
    
    def set_db_session(self, session: AsyncSession) -> None:
        """Set database session for persistence."""
        self._db_session = session
    
    async def track_trigger_decision(
        self,
        session_id: str,
        trigger_decision: bool,
        confidence: float,
        latency_ms: float,
        method_used: str,
    ) -> None:
        """Track a planning trigger decision."""
        metric = PlanningTriggerMetrics(
            session_id=session_id,
            trigger_decision=trigger_decision,
            confidence=confidence,
            latency_ms=latency_ms,
            method_used=method_used,
        )
        self._metrics[session_id].append(metric)
        
        # Persist to database if available
        if self._db_session:
            try:
                from mindflow_backend.orchestrator.planning.models import PlanningTriggerMetric
                
                db_metric = PlanningTriggerMetric(
                    session_id=session_id,
                    trigger_decision=trigger_decision,
                    confidence=confidence,
                    latency_ms=latency_ms,
                    method_used=method_used,
                )
                self._db_session.add(db_metric)
                await self._db_session.commit()
            except Exception as exc:
                _logger.error("failed_to_persist_metric", error=str(exc))
        
        _logger.info(
            "planning_trigger_tracked",
            session_id=session_id,
            decision=trigger_decision,
            confidence=confidence,
            latency_ms=latency_ms,
            method=method_used,
        )
    
    async def track_user_confirmation(
        self,
        session_id: str,
        plan_id: str,
        confirmed: bool,
    ) -> None:
        """Track user confirmation of a plan."""
        # Find most recent metric for this session
        if session_id in self._metrics and self._metrics[session_id]:
            metric = self._metrics[session_id][-1]
            metric.plan_id = plan_id
            metric.user_confirmed = confirmed
        
        # Update in database if available
        if self._db_session:
            try:
                from mindflow_backend.orchestrator.planning.models import PlanningTriggerMetric
                
                stmt = (
                    select(PlanningTriggerMetric)
                    .where(PlanningTriggerMetric.session_id == session_id)
                    .order_by(PlanningTriggerMetric.timestamp.desc())
                    .limit(1)
                )
                result = await self._db_session.execute(stmt)
                db_metric = result.scalar_one_or_none()
                
                if db_metric:
                    db_metric.plan_id = plan_id
                    db_metric.user_confirmed = confirmed
                    await self._db_session.commit()
            except Exception as exc:
                _logger.error("failed_to_update_metric", error=str(exc))
        
        _logger.info(
            "planning_confirmation_tracked",
            session_id=session_id,
            plan_id=plan_id,
            confirmed=confirmed,
        )
    
    async def track_execution_completion(
        self,
        session_id: str,
        plan_id: str,
        completed: bool,
    ) -> None:
        """Track execution completion of a plan."""
        # Find metric with matching plan_id
        if session_id in self._metrics:
            for metric in self._metrics[session_id]:
                if metric.plan_id == plan_id:
                    metric.execution_completed = completed
                    break
        
        # Update in database if available
        if self._db_session:
            try:
                from mindflow_backend.orchestrator.planning.models import PlanningTriggerMetric
                
                stmt = (
                    select(PlanningTriggerMetric)
                    .where(
                        PlanningTriggerMetric.session_id == session_id,
                        PlanningTriggerMetric.plan_id == plan_id,
                    )
                    .limit(1)
                )
                result = await self._db_session.execute(stmt)
                db_metric = result.scalar_one_or_none()
                
                if db_metric:
                    db_metric.execution_completed = completed
                    await self._db_session.commit()
            except Exception as exc:
                _logger.error("failed_to_update_metric", error=str(exc))
        
        _logger.info(
            "planning_execution_tracked",
            session_id=session_id,
            plan_id=plan_id,
            completed=completed,
        )
    
    async def get_metrics_summary(
        self,
        time_window: timedelta | None = None,
    ) -> dict:
        """Get summary of metrics within time window."""
        # Try to get from database first
        if self._db_session:
            try:
                return await self._get_summary_from_db(time_window)
            except Exception as exc:
                _logger.warning("failed_to_get_db_metrics", error=str(exc))
        
        # Fallback to in-memory
        return self._get_summary_from_memory(time_window)
    
    async def _get_summary_from_db(self, time_window: timedelta | None) -> dict:
        """Get summary from database."""

        from mindflow_backend.orchestrator.planning.models import PlanningTriggerMetric
        
        now = datetime.now(UTC)
        cutoff = now - time_window if time_window else datetime.min.replace(tzinfo=UTC)
        
        stmt = select(PlanningTriggerMetric).where(PlanningTriggerMetric.timestamp >= cutoff)
        result = await self._db_session.execute(stmt)
        metrics = result.scalars().all()
        
        if not metrics:
            return {
                "total_triggers": 0,
                "confirmation_rate": 0.0,
                "completion_rate": 0.0,
                "avg_latency_ms": 0.0,
                "method_distribution": {},
            }
        
        triggered = [m for m in metrics if m.trigger_decision]
        confirmed = [m for m in triggered if m.user_confirmed is True]
        completed = [m for m in confirmed if m.execution_completed is True]
        
        method_counts = defaultdict(int)
        for m in metrics:
            method_counts[m.method_used] += 1
        
        return {
            "total_triggers": len(triggered),
            "total_decisions": len(metrics),
            "confirmation_rate": len(confirmed) / len(triggered) if triggered else 0.0,
            "completion_rate": len(completed) / len(confirmed) if confirmed else 0.0,
            "avg_latency_ms": sum(m.latency_ms for m in metrics) / len(metrics),
            "avg_confidence": sum(m.confidence for m in metrics) / len(metrics),
            "method_distribution": dict(method_counts),
        }
    
    def _get_summary_from_memory(self, time_window: timedelta | None) -> dict:
        """Get summary from in-memory metrics."""
        now = datetime.now(UTC)
        cutoff = now - time_window if time_window else datetime.min.replace(tzinfo=UTC)
        
        all_metrics = []
        for metrics_list in self._metrics.values():
            all_metrics.extend(
                m for m in metrics_list
                if m.timestamp >= cutoff
            )
        
        if not all_metrics:
            return {
                "total_triggers": 0,
                "confirmation_rate": 0.0,
                "completion_rate": 0.0,
                "avg_latency_ms": 0.0,
                "method_distribution": {},
            }
        
        triggered = [m for m in all_metrics if m.trigger_decision]
        confirmed = [m for m in triggered if m.user_confirmed is True]
        completed = [m for m in confirmed if m.execution_completed is True]
        
        method_counts = defaultdict(int)
        for m in all_metrics:
            method_counts[m.method_used] += 1
        
        return {
            "total_triggers": len(triggered),
            "total_decisions": len(all_metrics),
            "confirmation_rate": len(confirmed) / len(triggered) if triggered else 0.0,
            "completion_rate": len(completed) / len(confirmed) if confirmed else 0.0,
            "avg_latency_ms": sum(m.latency_ms for m in all_metrics) / len(all_metrics),
            "avg_confidence": sum(m.confidence for m in all_metrics) / len(all_metrics),
            "method_distribution": dict(method_counts),
        }


_collector: PlanningMetricsCollector | None = None


def get_metrics_collector() -> PlanningMetricsCollector:
    """Get or create the global metrics collector instance."""
    global _collector
    if _collector is None:
        _collector = PlanningMetricsCollector()
    return _collector
