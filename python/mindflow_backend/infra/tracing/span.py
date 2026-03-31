"""Span implementation for distributed tracing.

Provides comprehensive span management with attributes,
events, status, and relationships.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from mindflow_backend.infra.tracing.tracer import TraceContext


class SpanKind(Enum):
    """Span kinds."""
    INTERNAL = "internal"
    SERVER = "server"
    CLIENT = "client"
    PRODUCER = "producer"
    CONSUMER = "consumer"


class StatusCode(Enum):
    """Span status codes."""
    OK = "OK"
    ERROR = "ERROR"
    UNSET = "UNSET"


@dataclass
class SpanEvent:
    """Span event with timestamp and attributes."""
    name: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    attributes: dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "timestamp": self.timestamp.isoformat(),
            "attributes": self.attributes,
        }


@dataclass
class SpanLink:
    """Link to another span."""
    trace_id: str
    span_id: str
    attributes: dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "attributes": self.attributes,
        }


@dataclass
class SpanStatus:
    """Span status with code and message."""
    code: StatusCode = StatusCode.UNSET
    message: str = ""
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "code": self.code.value,
            "message": self.message,
        }


class Span:
    """Comprehensive span implementation.
    
    Features:
    - Rich attributes and metadata
    - Events and status tracking
    - Exception recording
    - Link management
    - Performance metrics
    """
    
    def __init__(
        self,
        trace_id: str,
        span_id: str,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        parent_span_id: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        attributes: dict[str, Any] | None = None,
        events: list[SpanEvent] | None = None,
        links: list[SpanLink] | None = None,
        status: SpanStatus | None = None,
        context: TraceContext | None = None,
    ):
        """Initialize span.
        
        Args:
            trace_id: Trace ID
            span_id: Span ID
            name: Span name
            kind: Span kind
            parent_span_id: Parent span ID
            start_time: Span start time
            end_time: Span end time
            attributes: Span attributes
            events: Span events
            links: Span links
            status: Span status
            context: Trace context
        """
        self.trace_id = trace_id
        self.span_id = span_id
        self.name = name
        self.kind = kind
        self.parent_span_id = parent_span_id
        self.start_time = start_time or datetime.now(UTC)
        self.end_time = end_time
        self.attributes = attributes or {}
        self.events = events or []
        self.links = links or []
        self.status = status or SpanStatus()
        self.context = context
        self.duration_ms: float | None = None
        
        # Calculate duration if end time is provided
        if self.end_time:
            self.duration_ms = (self.end_time - self.start_time).total_seconds() * 1000
            
    def set_attribute(self, key: str, value: Any) -> None:
        """Set span attribute.
        
        Args:
            key: Attribute key
            value: Attribute value
        """
        # Convert value to string for serialization
        if isinstance(value, (list, dict)):
            import json
            self.attributes[key] = json.dumps(value)
        else:
            self.attributes[key] = str(value)
            
    def add_attributes(self, attributes: dict[str, Any]) -> None:
        """Add multiple attributes.
        
        Args:
            attributes: Attributes to add
        """
        for key, value in attributes.items():
            self.set_attribute(key, value)
            
    def add_event(self, name: str, attributes: dict[str, Any] | None = None) -> None:
        """Add event to span.
        
        Args:
            name: Event name
            attributes: Event attributes
        """
        event = SpanEvent(name=name, attributes=attributes or {})
        self.events.append(event)
        
    def add_link(self, trace_id: str, span_id: str, attributes: dict[str, Any] | None = None) -> None:
        """Add link to another span.
        
        Args:
            trace_id: Linked trace ID
            span_id: Linked span ID
            attributes: Link attributes
        """
        link = SpanLink(trace_id=trace_id, span_id=span_id, attributes=attributes or {})
        self.links.append(link)
        
    def set_status(self, code: str | StatusCode, message: str = "") -> None:
        """Set span status.
        
        Args:
            code: Status code
            message: Status message
        """
        if isinstance(code, str):
            try:
                code = StatusCode(code.upper())
            except ValueError:
                code = StatusCode.UNSET
                
        self.status = SpanStatus(code=code, message=message)
        
    def record_exception(self, exception: Exception) -> None:
        """Record exception on span.
        
        Args:
            exception: Exception to record
        """
        self.add_event(
            name="exception",
            attributes={
                "exception.type": exception.__class__.__name__,
                "exception.message": str(exception),
                "exception.stacktrace": self._get_stack_trace(exception),
            }
        )
        self.set_status(StatusCode.ERROR, str(exception))
        
    def _get_stack_trace(self, exception: Exception) -> str:
        """Get stack trace from exception.
        
        Args:
            exception: Exception
            
        Returns:
            Stack trace string
        """
        import traceback
        return "".join(traceback.format_exception(type(exception), exception, exception.__traceback__))
        
    def is_finished(self) -> bool:
        """Check if span is finished.
        
        Returns:
            True if span has end time
        """
        return self.end_time is not None
        
    def get_duration_ms(self) -> float | None:
        """Get span duration in milliseconds.
        
        Returns:
            Duration in milliseconds or None if not finished
        """
        if self.duration_ms is not None:
            return self.duration_ms
            
        if self.end_time:
            self.duration_ms = (self.end_time - self.start_time).total_seconds() * 1000
            return self.duration_ms
            
        return None
        
    def to_dict(self) -> dict[str, Any]:
        """Convert span to dictionary.
        
        Returns:
            Span dictionary representation
        """
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "name": self.name,
            "kind": self.kind.value,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_ms": self.get_duration_ms(),
            "attributes": self.attributes,
            "events": [event.to_dict() for event in self.events],
            "links": [link.to_dict() for link in self.links],
            "status": self.status.to_dict(),
            "context": {
                "trace_id": self.context.trace_id,
                "span_id": self.context.span_id,
                "sampling_decision": self.context.sampling_decision.value,
            } if self.context else None,
        }
        
    def to_json(self) -> str:
        """Convert span to JSON.
        
        Returns:
            JSON string
        """
        import json
        return json.dumps(self.to_dict(), default=str)
        
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Span:
        """Create span from dictionary.
        
        Args:
            data: Span dictionary
            
        Returns:
            Span instance
        """
        # Parse dates
        start_time = datetime.fromisoformat(data["start_time"])
        end_time = datetime.fromisoformat(data["end_time"]) if data["end_time"] else None
        
        # Parse events
        events = []
        for event_data in data.get("events", []):
            events.append(SpanEvent(
                name=event_data["name"],
                timestamp=datetime.fromisoformat(event_data["timestamp"]),
                attributes=event_data["attributes"],
            ))
            
        # Parse links
        links = []
        for link_data in data.get("links", []):
            links.append(SpanLink(
                trace_id=link_data["trace_id"],
                span_id=link_data["span_id"],
                attributes=link_data["attributes"],
            ))
            
        # Parse status
        status_data = data.get("status", {})
        status = SpanStatus(
            code=StatusCode(status_data.get("code", "UNSET")),
            message=status_data.get("message", ""),
        )
        
        return cls(
            trace_id=data["trace_id"],
            span_id=data["span_id"],
            parent_span_id=data.get("parent_span_id"),
            name=data["name"],
            kind=SpanKind(data["kind"]),
            start_time=start_time,
            end_time=end_time,
            attributes=data.get("attributes", {}),
            events=events,
            links=links,
            status=status,
        )
        
    def __repr__(self) -> str:
        """String representation."""
        return f"Span(trace_id={self.trace_id}, span_id={self.span_id}, name={self.name})"


class SpanContext:
    """Span context for propagation."""
    
    def __init__(
        self,
        trace_id: str,
        span_id: str,
        baggage: dict[str, str] | None = None,
        sampling_decision: str | None = None,
        trace_flags: int = 0,
        trace_state: str = "",
    ):
        """Initialize span context.
        
        Args:
            trace_id: Trace ID
            span_id: Span ID
            baggage: Baggage items
            sampling_decision: Sampling decision
            trace_flags: Trace flags
            trace_state: Trace state
        """
        self.trace_id = trace_id
        self.span_id = span_id
        self.baggage = baggage or {}
        self.sampling_decision = sampling_decision
        self.trace_flags = trace_flags
        self.trace_state = trace_state
        
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary.
        
        Returns:
            Context dictionary
        """
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "baggage": self.baggage,
            "sampling_decision": self.sampling_decision,
            "trace_flags": self.trace_flags,
            "trace_state": self.trace_state,
        }
        
    def copy(self) -> SpanContext:
        """Create a copy of the context.
        
        Returns:
            Copied context
        """
        return SpanContext(
            trace_id=self.trace_id,
            span_id=self.span_id,
            baggage=self.baggage.copy(),
            sampling_decision=self.sampling_decision,
            trace_flags=self.trace_flags,
            trace_state=self.trace_state,
        )
