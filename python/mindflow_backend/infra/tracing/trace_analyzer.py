"""Trace analysis and storage system.

Provides comprehensive trace analysis, storage,
and querying capabilities for distributed tracing.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any

from mindflow_backend.infra.cache.redis_client import get_redis_client
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.infra.tracing.span import Span

_logger = get_logger(__name__)


class TraceAnalysisLevel(Enum):
    """Trace analysis levels."""
    BASIC = "basic"
    PERFORMANCE = "performance"
    ERROR = "error"
    SECURITY = "security"
    BUSINESS = "business"


@dataclass
class TraceSummary:
    """Trace summary with key metrics."""
    trace_id: str
    span_count: int
    duration_ms: float
    error_count: int
    service_names: set[str]
    span_names: set[str]
    start_time: datetime
    end_time: datetime
    root_span_name: str
    has_errors: bool
    sampling_decision: str
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "trace_id": self.trace_id,
            "span_count": self.span_count,
            "duration_ms": self.duration_ms,
            "error_count": self.error_count,
            "service_names": list(self.service_names),
            "span_names": list(self.span_names),
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "root_span_name": self.root_span_name,
            "has_errors": self.has_errors,
            "sampling_decision": self.sampling_decision,
        }


@dataclass
class PerformanceMetrics:
    """Performance metrics for traces."""
    avg_duration_ms: float
    min_duration_ms: float
    max_duration_ms: float
    p50_duration_ms: float
    p90_duration_ms: float
    p95_duration_ms: float
    p99_duration_ms: float
    error_rate: float
    span_count_avg: float
    traces_per_minute: float
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "avg_duration_ms": self.avg_duration_ms,
            "min_duration_ms": self.min_duration_ms,
            "max_duration_ms": self.max_duration_ms,
            "p50_duration_ms": self.p50_duration_ms,
            "p90_duration_ms": self.p90_duration_ms,
            "p95_duration_ms": self.p95_duration_ms,
            "p99_duration_ms": self.p99_duration_ms,
            "error_rate": self.error_rate,
            "span_count_avg": self.span_count_avg,
            "traces_per_minute": self.traces_per_minute,
        }


@dataclass
class TraceAnalysis:
    """Comprehensive trace analysis results."""
    trace_id: str
    summary: TraceSummary
    performance_metrics: PerformanceMetrics | None = None
    error_analysis: dict[str, Any] | None = None
    security_analysis: dict[str, Any] | None = None
    business_analysis: dict[str, Any] | None = None
    recommendations: list[str] = field(default_factory=list)
    analysis_level: TraceAnalysisLevel = TraceAnalysisLevel.BASIC
    analyzed_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "trace_id": self.trace_id,
            "summary": self.summary.to_dict(),
            "performance_metrics": self.performance_metrics.to_dict() if self.performance_metrics else None,
            "error_analysis": self.error_analysis,
            "security_analysis": self.security_analysis,
            "business_analysis": self.business_analysis,
            "recommendations": self.recommendations,
            "analysis_level": self.analysis_level.value,
            "analyzed_at": self.analyzed_at.isoformat(),
        }


class TraceAnalyzer:
    """Advanced trace analysis system.
    
    Features:
    - Real-time trace processing
    - Performance analysis
    - Error detection and analysis
    - Security analysis
    - Business metrics extraction
    - Trace storage and querying
    """
    
    def __init__(self):
        """Initialize trace analyzer."""
        self._redis_client = None
        self._is_initialized = False
        self._trace_cache: dict[str, list[Span]] = {}
        self._analysis_cache: dict[str, TraceAnalysis] = {}
        self._max_trace_age_hours = 24
        self._max_cache_size = 10000
        
        # Statistics
        self._stats = {
            "traces_processed": 0,
            "spans_processed": 0,
            "traces_analyzed": 0,
            "errors_detected": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "avg_analysis_time_ms": 0.0,
        }
        
    async def initialize(self) -> None:
        """Initialize trace analyzer."""
        self._redis_client = get_redis_client()
        await self._redis_client.initialize()
        
        self._is_initialized = True
        
        _logger.info(
            "trace_analyzer_initialized",
            redis_connected=self._redis_client.is_connected(),
            max_trace_age_hours=self._max_trace_age_hours,
            max_cache_size=self._max_cache_size,
        )
        
    async def process_span(self, span: Span) -> None:
        """Process incoming span.
        
        Args:
            span: Span to process
        """
        if not self._is_initialized:
            return
            
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Add span to trace cache
            if span.trace_id not in self._trace_cache:
                self._trace_cache[span.trace_id] = []
                
            self._trace_cache[span.trace_id].append(span)
            
            # Check if trace is complete (all spans finished)
            if self._is_trace_complete(span.trace_id):
                await self._analyze_trace(span.trace_id)
                
            # Update statistics
            self._stats["spans_processed"] += 1
            
            # Clean up old traces
            await self._cleanup_old_traces()
            
        except Exception as e:
            _logger.error("span_processing_failed", trace_id=span.trace_id, error=str(e))
        finally:
            # Update analysis time statistics
            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            self._update_analysis_time_stats(duration_ms)
            
    def _is_trace_complete(self, trace_id: str) -> bool:
        """Check if trace is complete.
        
        Args:
            trace_id: Trace ID
            
        Returns:
            True if trace is complete
        """
        if trace_id not in self._trace_cache:
            return False
            
        spans = self._trace_cache[trace_id]
        
        # Check if all spans are finished
        for span in spans:
            if not span.is_finished():
                return False
                
        return True
        
    async def _analyze_trace(self, trace_id: str) -> None:
        """Analyze complete trace.
        
        Args:
            trace_id: Trace ID
        """
        if trace_id not in self._trace_cache:
            return
            
        spans = self._trace_cache[trace_id]
        
        try:
            # Create trace summary
            summary = self._create_trace_summary(trace_id, spans)
            
            # Perform analysis
            analysis = TraceAnalysis(
                trace_id=trace_id,
                summary=summary,
                analysis_level=TraceAnalysisLevel.BASIC,
            )
            
            # Add performance analysis
            analysis.performance_metrics = self._analyze_performance(spans)
            
            # Add error analysis
            if summary.has_errors:
                analysis.error_analysis = self._analyze_errors(spans)
                analysis.analysis_level = TraceAnalysisLevel.ERROR
                
            # Add security analysis
            analysis.security_analysis = self._analyze_security(spans)
            
            # Add business analysis
            analysis.business_analysis = self._analyze_business(spans)
            
            # Generate recommendations
            analysis.recommendations = self._generate_recommendations(analysis)
            
            # Store analysis
            self._analysis_cache[trace_id] = analysis
            
            # Store in Redis for persistence
            await self._store_trace_analysis(trace_id, analysis)
            
            # Update statistics
            self._stats["traces_analyzed"] += 1
            if summary.has_errors:
                self._stats["errors_detected"] += 1
                
            _logger.info(
                "trace_analyzed",
                trace_id=trace_id,
                span_count=summary.span_count,
                duration_ms=summary.duration_ms,
                has_errors=summary.has_errors,
            )
            
        except Exception as e:
            _logger.error("trace_analysis_failed", trace_id=trace_id, error=str(e))
            
    def _create_trace_summary(self, trace_id: str, spans: list[Span]) -> TraceSummary:
        """Create trace summary.
        
        Args:
            trace_id: Trace ID
            spans: List of spans
            
        Returns:
            Trace summary
        """
        if not spans:
            raise ValueError("No spans provided for trace summary")
            
        # Find root span (no parent)
        root_span = None
        for span in spans:
            if span.parent_span_id is None:
                root_span = span
                break
                
        if not root_span:
            root_span = spans[0]  # Fallback to first span
            
        # Calculate trace duration
        start_time = min(span.start_time for span in spans)
        end_time = max(span.end_time for span in spans if span.end_time)
        duration_ms = (end_time - start_time).total_seconds() * 1000
        
        # Count errors
        error_count = sum(1 for span in spans if span.status.code.value == "ERROR")
        
        # Collect service and span names
        service_names = set()
        span_names = set()
        for span in spans:
            service_name = span.attributes.get("service.name", "unknown")
            service_names.add(service_name)
            span_names.add(span.name)
            
        return TraceSummary(
            trace_id=trace_id,
            span_count=len(spans),
            duration_ms=duration_ms,
            error_count=error_count,
            service_names=service_names,
            span_names=span_names,
            start_time=start_time,
            end_time=end_time,
            root_span_name=root_span.name,
            has_errors=error_count > 0,
            sampling_decision="recorded",  # Would come from span context
        )
        
    def _analyze_performance(self, spans: list[Span]) -> PerformanceMetrics:
        """Analyze performance metrics.
        
        Args:
            spans: List of spans
            
        Returns:
            Performance metrics
        """
        durations = [span.get_duration_ms() for span in spans if span.get_duration_ms() is not None]
        
        if not durations:
            return PerformanceMetrics(
                avg_duration_ms=0.0,
                min_duration_ms=0.0,
                max_duration_ms=0.0,
                p50_duration_ms=0.0,
                p90_duration_ms=0.0,
                p95_duration_ms=0.0,
                p99_duration_ms=0.0,
                error_rate=0.0,
                span_count_avg=len(spans),
                traces_per_minute=0.0,
            )
            
        durations.sort()
        
        # Calculate percentiles
        def percentile(data, p):
            index = int(len(data) * p / 100)
            return data[min(index, len(data) - 1)]
            
        error_count = sum(1 for span in spans if span.status.code.value == "ERROR")
        
        return PerformanceMetrics(
            avg_duration_ms=sum(durations) / len(durations),
            min_duration_ms=min(durations),
            max_duration_ms=max(durations),
            p50_duration_ms=percentile(durations, 50),
            p90_duration_ms=percentile(durations, 90),
            p95_duration_ms=percentile(durations, 95),
            p99_duration_ms=percentile(durations, 99),
            error_rate=error_count / len(spans),
            span_count_avg=len(spans),
            traces_per_minute=0.0,  # Would be calculated over time window
        )
        
    def _analyze_errors(self, spans: list[Span]) -> dict[str, Any]:
        """Analyze errors in trace.
        
        Args:
            spans: List of spans
            
        Returns:
            Error analysis
        """
        error_spans = [span for span in spans if span.status.code.value == "ERROR"]
        
        if not error_spans:
            return {}
            
        # Analyze error patterns
        error_types = {}
        error_services = {}
        error_timeline = []
        
        for span in error_spans:
            # Count error types
            error_type = span.attributes.get("exception.type", "unknown")
            error_types[error_type] = error_types.get(error_type, 0) + 1
            
            # Count errors by service
            service_name = span.attributes.get("service.name", "unknown")
            error_services[service_name] = error_services.get(service_name, 0) + 1
            
            # Create error timeline
            error_timeline.append({
                "timestamp": span.start_time.isoformat(),
                "span_name": span.name,
                "service": service_name,
                "error_type": error_type,
                "error_message": span.status.message,
            })
            
        return {
            "total_errors": len(error_spans),
            "error_types": error_types,
            "error_services": error_services,
            "error_timeline": error_timeline,
            "error_rate": len(error_spans) / len(spans),
        }
        
    def _analyze_security(self, spans: list[Span]) -> dict[str, Any]:
        """Analyze security aspects of trace.
        
        Args:
            spans: List of spans
            
        Returns:
            Security analysis
        """
        security_issues = []
        
        for span in spans:
            # Check for authentication failures
            if "auth" in span.name.lower() and span.status.code.value == "ERROR":
                security_issues.append({
                    "type": "authentication_failure",
                    "span": span.name,
                    "message": span.status.message,
                })
                
            # Check for authorization failures
            if "permission" in span.name.lower() and span.status.code.value == "ERROR":
                security_issues.append({
                    "type": "authorization_failure",
                    "span": span.name,
                    "message": span.status.message,
                })
                
            # Check for sensitive data exposure
            sensitive_keywords = ["password", "token", "secret", "key", "credential"]
            for key, value in span.attributes.items():
                if any(keyword in key.lower() for keyword in sensitive_keywords):
                    security_issues.append({
                        "type": "sensitive_data_exposure",
                        "span": span.name,
                        "attribute": key,
                    })
                    
        return {
            "security_issues": security_issues,
            "risk_level": "high" if security_issues else "low",
            "issue_count": len(security_issues),
        }
        
    def _analyze_business(self, spans: list[Span]) -> dict[str, Any]:
        """Analyze business metrics from trace.
        
        Args:
            spans: List of spans
            
        Returns:
            Business analysis
        """
        business_events = []
        user_actions = []
        performance_metrics = {}
        
        for span in spans:
            # Extract business events
            if "business" in span.attributes.get("event.category", ""):
                business_events.append({
                    "name": span.name,
                    "type": span.attributes.get("event.type", "unknown"),
                    "user_id": span.attributes.get("user.id", "anonymous"),
                    "timestamp": span.start_time.isoformat(),
                })
                
            # Extract user actions
            if "user" in span.name.lower():
                user_actions.append({
                    "action": span.name,
                    "user_id": span.attributes.get("user.id", "anonymous"),
                    "duration_ms": span.get_duration_ms(),
                    "success": span.status.code.value == "OK",
                })
                
            # Extract performance metrics
            if "performance" in span.attributes:
                metric_name = span.attributes.get("performance.metric", "unknown")
                performance_metrics[metric_name] = {
                    "value": span.attributes.get("performance.value"),
                    "unit": span.attributes.get("performance.unit", "unknown"),
                }
                
        return {
            "business_events": business_events,
            "user_actions": user_actions,
            "performance_metrics": performance_metrics,
            "event_count": len(business_events),
            "action_count": len(user_actions),
        }
        
    def _generate_recommendations(self, analysis: TraceAnalysis) -> list[str]:
        """Generate recommendations based on analysis.
        
        Args:
            analysis: Trace analysis
            
        Returns:
            List of recommendations
        """
        recommendations = []
        
        # Performance recommendations
        if analysis.performance_metrics:
            perf = analysis.performance_metrics
            if perf.avg_duration_ms > 1000:
                recommendations.append("Consider optimizing slow operations - average duration exceeds 1s")
            if perf.error_rate > 0.1:
                recommendations.append(f"High error rate detected ({perf.error_rate:.1%}) - investigate root causes")
                
        # Error recommendations
        if analysis.error_analysis:
            error_analysis = analysis.error_analysis
            if error_analysis.get("error_rate", 0) > 0.05:
                recommendations.append("Implement better error handling and retry logic")
                
        # Security recommendations
        if analysis.security_analysis:
            security = analysis.security_analysis
            if security.get("issue_count", 0) > 0:
                recommendations.append("Address security issues detected in trace")
                
        return recommendations
        
    async def _store_trace_analysis(self, trace_id: str, analysis: TraceAnalysis) -> None:
        """Store trace analysis in Redis.
        
        Args:
            trace_id: Trace ID
            analysis: Trace analysis
        """
        try:
            # Store summary
            summary_key = f"trace:summary:{trace_id}"
            await self._redis_client.set(summary_key, analysis.summary.to_dict(), ttl=86400)  # 24 hours
            
            # Store full analysis
            analysis_key = f"trace:analysis:{trace_id}"
            await self._redis_client.set(analysis_key, analysis.to_dict(), ttl=86400)
            
            # Store in trace index for searching
            index_key = f"trace:index:{analysis.summary.start_time.date().isoformat()}"
            await self._redis_client.sadd(index_key, trace_id)
            await self._redis_client.expire(index_key, 86400 * 7)  # 7 days
            
        except Exception as e:
            _logger.error("trace_analysis_storage_failed", trace_id=trace_id, error=str(e))
            
    async def get_trace(self, trace_id: str) -> dict[str, Any] | None:
        """Get trace by ID.
        
        Args:
            trace_id: Trace ID
            
        Returns:
            Trace data or None
        """
        try:
            # Check cache first
            if trace_id in self._analysis_cache:
                self._stats["cache_hits"] += 1
                return self._analysis_cache[trace_id].to_dict()
                
            self._stats["cache_misses"] += 1
            
            # Get from Redis
            analysis_key = f"trace:analysis:{trace_id}"
            analysis_data = await self._redis_client.get(analysis_key)
            
            if analysis_data:
                return analysis_data
                
        except Exception as e:
            _logger.error("trace_retrieval_failed", trace_id=trace_id, error=str(e))
            
        return None
        
    async def search_traces(
        self,
        service_name: str | None = None,
        span_name: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        attributes: dict[str, Any] | None = None,
        limit: int = 100
    ) -> list[dict[str, Any]]:
        """Search traces with filters.
        
        Args:
            service_name: Service name filter
            span_name: Span name filter
            start_time: Start time filter
            end_time: End time filter
            attributes: Attributes filter
            limit: Result limit
            
        Returns:
            List of matching traces
        """
        results = []
        
        try:
            # This is a simplified search implementation
            # In production, you'd use proper indexing and search
            
            # Search through cached analyses
            for analysis in self._analysis_cache.values():
                summary = analysis.summary
                
                # Apply filters
                if service_name and service_name not in summary.service_names:
                    continue
                    
                if span_name and span_name not in summary.span_names:
                    continue
                    
                if start_time and summary.start_time < start_time:
                    continue
                    
                if end_time and summary.end_time > end_time:
                    continue
                    
                results.append(analysis.to_dict())
                
                if len(results) >= limit:
                    break
                    
        except Exception as e:
            _logger.error("trace_search_failed", error=str(e))
            
        return results
        
    async def _cleanup_old_traces(self) -> None:
        """Clean up old traces from cache."""
        try:
            current_time = datetime.now(UTC)
            cutoff_time = current_time - timedelta(hours=self._max_trace_age_hours)
            
            # Clean up analysis cache
            traces_to_remove = []
            for trace_id, analysis in self._analysis_cache.items():
                if analysis.summary.start_time < cutoff_time:
                    traces_to_remove.append(trace_id)
                    
            for trace_id in traces_to_remove:
                del self._analysis_cache[trace_id]
                if trace_id in self._trace_cache:
                    del self._trace_cache[trace_id]
                    
            # Clean up trace cache
            if len(self._trace_cache) > self._max_cache_size:
                # Remove oldest traces
                sorted_traces = sorted(
                    self._trace_cache.items(),
                    key=lambda x: min(span.start_time for span in x[1])
                )
                
                traces_to_remove = [trace_id for trace_id, _ in sorted_traces[:-self._max_cache_size]]
                
                for trace_id in traces_to_remove:
                    del self._trace_cache[trace_id]
                    if trace_id in self._analysis_cache:
                        del self._analysis_cache[trace_id]
                        
        except Exception as e:
            _logger.error("trace_cleanup_failed", error=str(e))
            
    def _update_analysis_time_stats(self, duration_ms: float) -> None:
        """Update analysis time statistics.
        
        Args:
            duration_ms: Analysis duration in milliseconds
        """
        current_avg = self._stats["avg_analysis_time_ms"]
        count = self._stats["traces_analyzed"]
        
        if count == 0:
            self._stats["avg_analysis_time_ms"] = duration_ms
        else:
            self._stats["avg_analysis_time_ms"] = (current_avg * count + duration_ms) / (count + 1)
            
    def get_stats(self) -> dict[str, Any]:
        """Get analyzer statistics.
        
        Returns:
            Statistics dictionary
        """
        stats = self._stats.copy()
        
        # Add cache statistics
        total_requests = stats["cache_hits"] + stats["cache_misses"]
        if total_requests > 0:
            stats["cache_hit_rate"] = stats["cache_hits"] / total_requests
        else:
            stats["cache_hit_rate"] = 0.0
            
        # Add cache sizes
        stats["trace_cache_size"] = len(self._trace_cache)
        stats["analysis_cache_size"] = len(self._analysis_cache)
        
        return stats
        
    async def health_check(self) -> dict[str, Any]:
        """Perform analyzer health check.
        
        Returns:
            Health check results
        """
        try:
            start_time = time.time()
            
            # Test Redis connection
            redis_health = await self._redis_client.health_check()
            
            # Test trace processing
            test_trace_id = "health_check_trace"
            test_span = Span(
                trace_id=test_trace_id,
                span_id="test_span",
                name="health_check",
                start_time=datetime.now(UTC),
                end_time=datetime.now(UTC),
            )
            
            await self.process_span(test_span)
            
            duration_ms = (time.time() - start_time) * 1000
            
            health_data = {
                "status": "healthy",
                "redis_status": redis_health.get("status", "unknown"),
                "test_trace_processed": True,
                "duration_ms": duration_ms,
                "trace_cache_size": len(self._trace_cache),
                "analysis_cache_size": len(self._analysis_cache),
                "timestamp": datetime.now(UTC).isoformat(),
            }
            
            _logger.info("trace_analyzer_health_check_success", **health_data)
            return health_data
            
        except Exception as e:
            error_data = {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now(UTC).isoformat(),
            }
            
            _logger.error("trace_analyzer_health_check_failed", **error_data)
            return error_data


# Global trace analyzer instance
_trace_analyzer: TraceAnalyzer | None = None


def get_trace_analyzer() -> TraceAnalyzer:
    """Get global trace analyzer instance.
    
    Returns:
        TraceAnalyzer instance
    """
    global _trace_analyzer
    if _trace_analyzer is None:
        _trace_analyzer = TraceAnalyzer()
    return _trace_analyzer
