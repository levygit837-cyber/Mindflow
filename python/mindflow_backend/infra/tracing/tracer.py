"""Advanced distributed tracer with OpenTelemetry integration.

Provides comprehensive tracing capabilities with span management,
context propagation, and trace collection.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Union, Callable, AsyncGenerator, Generator
from datetime import datetime, UTC, timedelta
from enum import Enum
import json
import weakref

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.infra.tracing.span import Span, SpanContext, SpanKind
from mindflow_backend.infra.tracing.trace_analyzer import TraceAnalyzer
from mindflow_backend.infra.config import get_settings

_logger = get_logger(__name__)


class TraceSamplingDecision(Enum):
    """Trace sampling decisions."""
    RECORD = "record"
    RECORD_AND_SAMPLE = "record_and_sample"
    DROP = "drop"


@dataclass
class TraceConfig:
    """Tracing configuration."""
    service_name: str = "mindflow-backend"
    service_version: str = "1.0.0"
    enabled: bool = True
    sample_rate: float = 1.0
    max_spans_per_trace: int = 1000
    trace_timeout_seconds: int = 60
    include_resource_spans: bool = True
    export_batch_size: int = 100
    export_timeout_ms: int = 30000
    headers_to_propagate: List[str] = field(default_factory=lambda: [
        "traceparent",
        "tracestate",
        "x-trace-id",
        "x-span-id",
        "x-parent-span-id",
    ])
    
    def should_sample(self) -> bool:
        """Determine if trace should be sampled."""
        import random
        return random.random() < self.sample_rate


@dataclass
class TraceContext:
    """Trace context for propagation."""
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    baggage: Dict[str, str] = field(default_factory=dict)
    sampling_decision: TraceSamplingDecision = TraceSamplingDecision.RECORD_AND_SAMPLE
    trace_flags: int = 0
    trace_state: str = ""
    
    def to_headers(self) -> Dict[str, str]:
        """Convert trace context to HTTP headers."""
        headers = {}
        
        # W3C traceparent header
        version = "00"
        trace_id_hex = self.trace_id.replace("-", "")
        span_id_hex = self.span_id.replace("-", "")
        flags = format(self.trace_flags, "02x")
        
        traceparent = f"{version}-{trace_id_hex[:32]}-{span_id_hex[:16]}-{flags}"
        headers["traceparent"] = traceparent
        
        # Custom headers for additional context
        if self.parent_span_id:
            headers["x-parent-span-id"] = self.parent_span_id
            
        # Baggage
        if self.baggage:
            baggage_items = [f"{k}={v}" for k, v in self.baggage.items()]
            headers["baggage"] = ",".join(baggage_items)
            
        return headers
        
    @classmethod
    def from_headers(cls, headers: Dict[str, str]) -> Optional[TraceContext]:
        """Extract trace context from HTTP headers."""
        traceparent = headers.get("traceparent")
        if not traceparent:
            return None
            
        try:
            parts = traceparent.split("-")
            if len(parts) < 4:
                return None
                
            version, trace_id_hex, span_id_hex, flags = parts[:4]
            
            # Convert hex to full UUID format
            trace_id = f"{trace_id_hex[:8]}-{trace_id_hex[8:12]}-{trace_id_hex[12:16]}-{trace_id_hex[16:20]}-{trace_id_hex[20:32]}"
            span_id = f"{span_id_hex[:8]}-{span_id_hex[8:12]}-{span_id_hex[12:16]}-{span_id_hex[16:20]}-{span_id_hex[20:]}"
            
            # Parse baggage
            baggage = {}
            baggage_header = headers.get("baggage", "")
            if baggage_header:
                for item in baggage_header.split(","):
                    if "=" in item:
                        k, v = item.split("=", 1)
                        baggage[k.strip()] = v.strip()
                        
            return cls(
                trace_id=trace_id,
                span_id=span_id,
                parent_span_id=headers.get("x-parent-span-id"),
                baggage=baggage,
                trace_flags=int(flags, 16),
            )
            
        except Exception as e:
            _logger.warning("trace_context_extraction_failed", error=str(e))
            return None


class DistributedTracer:
    """Advanced distributed tracer with OpenTelemetry-like features.
    
    Features:
    - Distributed trace propagation
    - Span lifecycle management
    - Context propagation
    - Sampling strategies
    - Performance optimization
    - Trace analysis
    """
    
    def __init__(self):
        """Initialize distributed tracer."""
        self._config: Optional[TraceConfig] = None
        self._active_spans: Dict[str, Span] = {}
        self._trace_analyzer: Optional[TraceAnalyzer] = None
        self._context_var: Optional[Any] = None
        self._is_initialized = False
        
        # Statistics
        self._stats = {
            "total_spans_created": 0,
            "total_spans_finished": 0,
            "active_spans": 0,
            "traces_sampled": 0,
            "traces_dropped": 0,
            "avg_span_duration_ms": 0.0,
            "span_durations": [],
        }
        
    async def initialize(self, config: Optional[TraceConfig] = None) -> None:
        """Initialize distributed tracer.
        
        Args:
            config: Tracing configuration
        """
        if self._is_initialized:
            return
            
        self._config = config or TraceConfig()
        
        # Initialize trace analyzer
        self._trace_analyzer = TraceAnalyzer()
        await self._trace_analyzer.initialize()
        
        # Initialize context variable (using asyncio context var)
        try:
            from contextvars import ContextVar
            self._context_var = ContextVar("trace_context", default=None)
        except ImportError:
            self._context_var = None
            
        self._is_initialized = True
        
        _logger.info(
            "distributed_tracer_initialized",
            service_name=self._config.service_name,
            sample_rate=self._config.sample_rate,
            enabled=self._config.enabled,
        )
        
    @asynccontextmanager
    async def start_span(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        parent_context: Optional[TraceContext] = None,
        attributes: Optional[Dict[str, Any]] = None,
        start_time: Optional[datetime] = None,
        links: Optional[List[Dict[str, Any]]] = None
    ) -> AsyncGenerator[Span, None]:
        """Start a new span.
        
        Args:
            name: Span name
            kind: Span kind
            parent_context: Parent trace context
            attributes: Span attributes
            start_time: Span start time
            links: Linked spans
            
        Yields:
            Active span
        """
        if not self._is_initialized or not self._config.enabled:
            # Create dummy span if tracing is disabled
            dummy_span = Span(
                trace_id=str(uuid.uuid4()),
                span_id=str(uuid.uuid4()),
                name=name,
                kind=kind,
                start_time=start_time or datetime.now(UTC),
            )
            yield dummy_span
            return
            
        # Get current context
        current_context = parent_context or self._get_current_context()
        
        # Create trace context
        trace_id = current_context.trace_id if current_context else str(uuid.uuid4())
        span_id = str(uuid.uuid4())
        parent_span_id = current_context.span_id if current_context else None
        
        # Check sampling
        sampling_decision = self._determine_sampling(current_context)
        
        trace_context = TraceContext(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
            baggage=current_context.baggage if current_context else {},
            sampling_decision=sampling_decision,
        )
        
        # Create span
        span = Span(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
            name=name,
            kind=kind,
            start_time=start_time or datetime.now(UTC),
            attributes=attributes or {},
            links=links or [],
            context=trace_context,
        )
        
        # Register span
        self._active_spans[span_id] = span
        self._stats["total_spans_created"] += 1
        self._stats["active_spans"] += 1
        
        # Set context
        if self._context_var:
            self._context_var.set(trace_context)
            
        _logger.debug(
            "span_started",
            trace_id=trace_id,
            span_id=span_id,
            name=name,
            kind=kind.value,
            parent_span_id=parent_span_id,
        )
        
        try:
            yield span
        finally:
            await self._finish_span(span)
            
    @contextmanager
    def start_span_sync(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        parent_context: Optional[TraceContext] = None,
        attributes: Optional[Dict[str, Any]] = None,
        start_time: Optional[datetime] = None,
        links: Optional[List[Dict[str, Any]]] = None
    ) -> Generator[Span, None, None]:
        """Start a new span (synchronous version).
        
        Args:
            name: Span name
            kind: Span kind
            parent_context: Parent trace context
            attributes: Span attributes
            start_time: Span start time
            links: Linked spans
            
        Yields:
            Active span
        """
        # For synchronous context, we'll use asyncio.run to handle the async span
        async def _create_span():
            async with self.start_span(
                name=name,
                kind=kind,
                parent_context=parent_context,
                attributes=attributes,
                start_time=start_time,
                links=links,
            ) as span:
                return span
                
        span = asyncio.run(_create_span())
        try:
            yield span
        finally:
            # Span is already finished in the async context
            pass
            
    async def _finish_span(self, span: Span) -> None:
        """Finish a span.
        
        Args:
            span: Span to finish
        """
        if span.end_time:
            return  # Already finished
            
        span.end_time = datetime.now(UTC)
        
        # Calculate duration
        duration_ms = (span.end_time - span.start_time).total_seconds() * 1000
        span.duration_ms = duration_ms
        
        # Update statistics
        self._stats["total_spans_finished"] += 1
        self._stats["active_spans"] -= 1
        
        # Track duration for statistics
        self._stats["span_durations"].append(duration_ms)
        if len(self._stats["span_durations"]) > 1000:
            self._stats["span_durations"] = self._stats["span_durations"][-1000:]
            
        self._stats["avg_span_duration_ms"] = sum(self._stats["span_durations"]) / len(self._stats["span_durations"])
        
        # Remove from active spans
        self._active_spans.pop(span.span_id, None)
        
        # Send to analyzer if sampled
        if span.context.sampling_decision != TraceSamplingDecision.DROP:
            await self._trace_analyzer.process_span(span)
            
        _logger.debug(
            "span_finished",
            trace_id=span.trace_id,
            span_id=span.span_id,
            name=span.name,
            duration_ms=duration_ms,
        )
        
    def _determine_sampling(self, context: Optional[TraceContext]) -> TraceSamplingDecision:
        """Determine sampling decision.
        
        Args:
            context: Current trace context
            
        Returns:
            Sampling decision
        """
        if not self._config:
            return TraceSamplingDecision.RECORD_AND_SAMPLE
            
        # If context already has sampling decision, respect it
        if context and context.sampling_decision != TraceSamplingDecision.RECORD_AND_SAMPLE:
            return context.sampling_decision
            
        # Use configured sampling rate
        if self._config.should_sample():
            self._stats["traces_sampled"] += 1
            return TraceSamplingDecision.RECORD_AND_SAMPLE
        else:
            self._stats["traces_dropped"] += 1
            return TraceSamplingDecision.DROP
            
    def _get_current_context(self) -> Optional[TraceContext]:
        """Get current trace context.
        
        Returns:
            Current trace context or None
        """
        if self._context_var:
            try:
                return self._context_var.get()
            except LookupError:
                return None
        return None
        
    def get_current_span(self) -> Optional[Span]:
        """Get current active span.
        
        Returns:
            Current span or None
        """
        context = self._get_current_context()
        if context:
            return self._active_spans.get(context.span_id)
        return None
        
    def set_span_attribute(self, key: str, value: Any) -> None:
        """Set attribute on current span.
        
        Args:
            key: Attribute key
            value: Attribute value
        """
        span = self.get_current_span()
        if span:
            span.set_attribute(key, value)
            
    def add_span_event(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> None:
        """Add event to current span.
        
        Args:
            name: Event name
            attributes: Event attributes
        """
        span = self.get_current_span()
        if span:
            span.add_event(name, attributes)
            
    def record_span_exception(self, exception: Exception) -> None:
        """Record exception on current span.
        
        Args:
            exception: Exception to record
        """
        span = self.get_current_span()
        if span:
            span.record_exception(exception)
            
    def set_span_status(self, code: str, message: str = "") -> None:
        """Set status on current span.
        
        Args:
            code: Status code
            message: Status message
        """
        span = self.get_current_span()
        if span:
            span.set_status(code, message)
            
    def extract_context_from_headers(self, headers: Dict[str, str]) -> Optional[TraceContext]:
        """Extract trace context from HTTP headers.
        
        Args:
            headers: HTTP headers
            
        Returns:
            Extracted trace context or None
        """
        return TraceContext.from_headers(headers)
        
    def inject_context_to_headers(self, context: Optional[TraceContext] = None) -> Dict[str, str]:
        """Inject trace context into HTTP headers.
        
        Args:
            context: Trace context to inject (current if None)
            
        Returns:
            HTTP headers with trace context
        """
        ctx = context or self._get_current_context()
        if ctx:
            return ctx.to_headers()
        return {}
        
    async def get_trace(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """Get trace by ID.
        
        Args:
            trace_id: Trace ID
            
        Returns:
            Trace data or None
        """
        if not self._trace_analyzer:
            return None
            
        return await self._trace_analyzer.get_trace(trace_id)
        
    async def search_traces(
        self,
        service_name: Optional[str] = None,
        span_name: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        attributes: Optional[Dict[str, Any]] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
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
        if not self._trace_analyzer:
            return []
            
        return await self._trace_analyzer.search_traces(
            service_name=service_name,
            span_name=span_name,
            start_time=start_time,
            end_time=end_time,
            attributes=attributes,
            limit=limit,
        )
        
    def get_stats(self) -> Dict[str, Any]:
        """Get tracer statistics.
        
        Returns:
            Statistics dictionary
        """
        stats = self._stats.copy()
        
        # Add configuration info
        if self._config:
            stats["config"] = {
                "service_name": self._config.service_name,
                "service_version": self._config.service_version,
                "enabled": self._config.enabled,
                "sample_rate": self._config.sample_rate,
                "max_spans_per_trace": self._config.max_spans_per_trace,
            }
            
        # Add active spans info
        stats["active_spans_info"] = {
            "count": len(self._active_spans),
            "spans": [
                {
                    "trace_id": span.trace_id,
                    "span_id": span.span_id,
                    "name": span.name,
                    "kind": span.kind.value,
                    "start_time": span.start_time.isoformat(),
                    "duration_ms": span.duration_ms if span.end_time else None,
                }
                for span in self._active_spans.values()
            ],
        }
        
        return stats
        
    async def health_check(self) -> Dict[str, Any]:
        """Perform tracer health check.
        
        Returns:
            Health check results
        """
        try:
            start_time = time.time()
            
            # Test trace analyzer
            analyzer_health = "healthy"
            if self._trace_analyzer:
                analyzer_health = (await self._trace_analyzer.health_check()).get("status", "unknown")
                
            # Test span creation
            async with self.start_span("health_check", SpanKind.INTERNAL) as span:
                span.set_attribute("test", True)
                test_span_created = True
                
            duration_ms = (time.time() - start_time) * 1000
            
            health_data = {
                "status": "healthy",
                "analyzer_status": analyzer_health,
                "test_span_created": test_span_created,
                "duration_ms": duration_ms,
                "active_spans": len(self._active_spans),
                "config_enabled": self._config.enabled if self._config else False,
                "timestamp": datetime.now(UTC).isoformat(),
            }
            
            _logger.info("distributed_tracer_health_check_success", **health_data)
            return health_data
            
        except Exception as e:
            error_data = {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now(UTC).isoformat(),
            }
            
            _logger.error("distributed_tracer_health_check_failed", **error_data)
            return error_data


# Global tracer instance
_tracer: Optional[DistributedTracer] = None


def get_tracer() -> DistributedTracer:
    """Get global distributed tracer instance.
    
    Returns:
        DistributedTracer instance
    """
    global _tracer
    if _tracer is None:
        _tracer = DistributedTracer()
    return _tracer


# Convenience decorators
def trace_span(
    name: Optional[str] = None,
    kind: SpanKind = SpanKind.INTERNAL,
    attributes: Optional[Dict[str, Any]] = None
):
    """Decorator to trace function execution.
    
    Args:
        name: Span name (function name if None)
        kind: Span kind
        attributes: Span attributes
        
    Returns:
        Decorated function
    """
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            tracer = get_tracer()
            span_name = name or f"{func.__module__}.{func.__name__}"
            
            async with tracer.start_span(span_name, kind, attributes=attributes) as span:
                # Add function arguments as attributes (if not sensitive)
                if kwargs:
                    safe_kwargs = {k: v for k, v in kwargs.items() 
                                 if not any(sensitive in k.lower() 
                                           for sensitive in ['password', 'token', 'secret', 'key'])}
                    if safe_kwargs:
                        span.set_attribute("function.args", str(safe_kwargs))
                        
                try:
                    result = await func(*args, **kwargs)
                    span.set_status("OK")
                    return result
                except Exception as e:
                    tracer.record_span_exception(e)
                    span.set_status("ERROR", str(e))
                    raise
                    
        def sync_wrapper(*args, **kwargs):
            tracer = get_tracer()
            span_name = name or f"{func.__module__}.{func.__name__}"
            
            with tracer.start_span_sync(span_name, kind, attributes=attributes) as span:
                try:
                    result = func(*args, **kwargs)
                    span.set_status("OK")
                    return result
                except Exception as e:
                    tracer.record_span_exception(e)
                    span.set_status("ERROR", str(e))
                    raise
                    
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
            
    return decorator
