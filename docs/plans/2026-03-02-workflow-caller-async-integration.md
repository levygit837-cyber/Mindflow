# Workflow Caller Async Integration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a TaskBus abstraction for sync/async task dispatch, a workflow registry for pre-built workflows, retry/DLQ policies, and hybrid sync/async execution with latency fallback.

**Architecture:** Defines protocol-based abstractions (`TaskBus`, `WorkflowRegistry`) with an in-memory implementation for testing. The actual RabbitMQ adapter is future work. Extends `infra/resilience.py` with DLQ and idempotency. Adds a `deferred_to_async` SSE event type to the streaming contract.

**Tech Stack:** Python 3.12, Pydantic v2, pytest, Protocol for abstractions, existing `infra/resilience.py`

---

## Task 1: Workflow and TaskBus Schemas

**Files:**
- Create: `python/omnimind_backend/schemas/workflow.py`
- Test: `python/tests/test_workflow_schemas.py`

**Step 1: Write the failing test**

Create `python/tests/test_workflow_schemas.py`:

```python
"""Tests for workflow caller schemas."""

from uuid import uuid4

from omnimind_backend.schemas.workflow import (
    WorkflowDefinition,
    WorkflowTrigger,
    WorkflowResult,
    WorkflowStatus,
    QueueName,
    DLQEntry,
    ErrorClassification,
)


def test_workflow_definition() -> None:
    wf = WorkflowDefinition(
        workflow_id="research_pipeline_v1",
        description="Deep research with browser automation",
        version="1.0.0",
        input_schema={"type": "object", "properties": {"query": {"type": "string"}}},
        output_schema={"type": "object", "properties": {"results": {"type": "array"}}},
    )
    assert wf.workflow_id == "research_pipeline_v1"
    assert wf.version == "1.0.0"


def test_workflow_trigger() -> None:
    trigger = WorkflowTrigger(
        message_id=uuid4(),
        correlation_id=uuid4(),
        conversation_id="conv-123",
        workflow_id="research_pipeline_v1",
        payload={"query": "best Python web frameworks 2026"},
    )
    assert trigger.workflow_id == "research_pipeline_v1"


def test_workflow_result_success() -> None:
    r = WorkflowResult(
        correlation_id=uuid4(),
        status=WorkflowStatus.SUCCESS,
        payload={"results": [{"title": "FastAPI"}]},
    )
    assert r.status == WorkflowStatus.SUCCESS


def test_workflow_result_failure() -> None:
    r = WorkflowResult(
        correlation_id=uuid4(),
        status=WorkflowStatus.FAILURE,
        error="Timeout after 300s",
    )
    assert r.status == WorkflowStatus.FAILURE


def test_error_classification() -> None:
    assert ErrorClassification.TRANSIENT == "transient"
    assert ErrorClassification.NON_TRANSIENT == "non_transient"
    assert ErrorClassification.AMBIGUOUS == "ambiguous"


def test_queue_names() -> None:
    assert QueueName.AGENT_EVENTS == "agent.events"
    assert QueueName.REASONING_REQUESTS == "reasoning.requests"
    assert QueueName.DEAD_LETTER == "dead_letter"
```

**Step 2: Run test to verify it fails**

Run: `cd python && python -m pytest tests/test_workflow_schemas.py -v`
Expected: FAIL with `ModuleNotFoundError`

**Step 3: Write minimal implementation**

Create `python/omnimind_backend/schemas/workflow.py`:

```python
"""Workflow caller and async integration schemas.

Defines workflow definitions, triggers, results, queue topology,
and error classification as specified in workflow-caller-async-integration.md.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class WorkflowStatus(StrEnum):
    """Result status of a workflow execution."""

    SUCCESS = "success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    PENDING = "pending"


class ErrorClassification(StrEnum):
    """Classification of errors for retry policy."""

    TRANSIENT = "transient"
    NON_TRANSIENT = "non_transient"
    AMBIGUOUS = "ambiguous"


class QueueName(StrEnum):
    """RabbitMQ queue topology names from SPADE plan."""

    AGENT_TASKS = "agent.tasks"
    REASONING_REQUESTS = "reasoning.requests"
    REASONING_RESULTS = "reasoning.results"
    AGENT_EVENTS = "agent.events"
    DEAD_LETTER = "dead_letter"


class WorkflowDefinition(BaseModel):
    """A registered pre-built workflow."""

    workflow_id: str
    description: str = ""
    version: str = "1.0.0"
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    max_retries: int = 3
    timeout_ms: int = 300_000


class WorkflowTrigger(BaseModel):
    """A message to trigger a workflow execution."""

    message_id: UUID
    correlation_id: UUID
    conversation_id: str
    workflow_id: str
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class WorkflowResult(BaseModel):
    """Result from a completed workflow."""

    correlation_id: UUID
    status: WorkflowStatus
    payload: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    completed_at: datetime = Field(default_factory=datetime.utcnow)


class DLQEntry(BaseModel):
    """A dead letter queue entry for exhausted messages."""

    original_trigger: WorkflowTrigger
    error_history: list[str] = Field(default_factory=list)
    attempt_count: int = 0
    last_attempt_at: datetime = Field(default_factory=datetime.utcnow)
```

**Step 4: Run test to verify it passes**

Run: `cd python && python -m pytest tests/test_workflow_schemas.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add python/omnimind_backend/schemas/workflow.py python/tests/test_workflow_schemas.py
git commit -m "feat(schemas): add workflow caller schemas with queue topology and DLQ"
```

---

## Task 2: TaskBus Protocol and In-Memory Implementation

**Files:**
- Create: `python/omnimind_backend/workers/task_bus.py`
- Test: `python/tests/test_task_bus.py`

**Step 1: Write the failing test**

Create `python/tests/test_task_bus.py`:

```python
"""Tests for TaskBus abstraction."""

import pytest
from uuid import uuid4

from omnimind_backend.workers.task_bus import InMemoryTaskBus
from omnimind_backend.schemas.workflow import (
    WorkflowTrigger,
    WorkflowResult,
    WorkflowStatus,
)


@pytest.mark.asyncio
async def test_publish_and_consume() -> None:
    bus = InMemoryTaskBus()
    trigger = WorkflowTrigger(
        message_id=uuid4(),
        correlation_id=uuid4(),
        conversation_id="conv-1",
        workflow_id="test_wf",
        payload={"data": "hello"},
    )
    await bus.publish(trigger)
    received = await bus.consume("test_wf")
    assert received is not None
    assert received.workflow_id == "test_wf"


@pytest.mark.asyncio
async def test_consume_empty_returns_none() -> None:
    bus = InMemoryTaskBus()
    received = await bus.consume("nonexistent")
    assert received is None


@pytest.mark.asyncio
async def test_publish_result() -> None:
    bus = InMemoryTaskBus()
    corr_id = uuid4()
    result = WorkflowResult(
        correlation_id=corr_id,
        status=WorkflowStatus.SUCCESS,
        payload={"answer": "42"},
    )
    await bus.publish_result(result)
    received = await bus.get_result(corr_id)
    assert received is not None
    assert received.status == WorkflowStatus.SUCCESS


@pytest.mark.asyncio
async def test_idempotent_publish() -> None:
    bus = InMemoryTaskBus()
    msg_id = uuid4()
    trigger = WorkflowTrigger(
        message_id=msg_id,
        correlation_id=uuid4(),
        conversation_id="conv-1",
        workflow_id="test_wf",
    )
    await bus.publish(trigger)
    await bus.publish(trigger)  # Duplicate
    # Should only have one message
    first = await bus.consume("test_wf")
    second = await bus.consume("test_wf")
    assert first is not None
    assert second is None
```

**Step 2: Run test to verify it fails**

Run: `cd python && python -m pytest tests/test_task_bus.py -v`
Expected: FAIL with `ModuleNotFoundError`

**Step 3: Write minimal implementation**

Create `python/omnimind_backend/workers/task_bus.py`:

```python
"""TaskBus abstraction for sync/async task dispatch.

Defines a Protocol for task buses and provides an in-memory
implementation for testing. RabbitMQ adapter is future work.
"""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Protocol
from uuid import UUID

from omnimind_backend.schemas.workflow import WorkflowTrigger, WorkflowResult


class TaskBus(Protocol):
    """Abstract interface for publishing and consuming workflow tasks."""

    async def publish(self, trigger: WorkflowTrigger) -> None: ...
    async def consume(self, workflow_id: str) -> WorkflowTrigger | None: ...
    async def publish_result(self, result: WorkflowResult) -> None: ...
    async def get_result(self, correlation_id: UUID) -> WorkflowResult | None: ...


class InMemoryTaskBus:
    """In-memory TaskBus for testing and development."""

    def __init__(self) -> None:
        self._queues: dict[str, deque[WorkflowTrigger]] = defaultdict(deque)
        self._results: dict[UUID, WorkflowResult] = {}
        self._seen_message_ids: set[UUID] = set()

    async def publish(self, trigger: WorkflowTrigger) -> None:
        """Publish a workflow trigger. Deduplicates by message_id."""
        if trigger.message_id in self._seen_message_ids:
            return  # Idempotent: skip duplicate
        self._seen_message_ids.add(trigger.message_id)
        self._queues[trigger.workflow_id].append(trigger)

    async def consume(self, workflow_id: str) -> WorkflowTrigger | None:
        """Consume the next trigger for a workflow, or None if empty."""
        q = self._queues.get(workflow_id)
        if q:
            return q.popleft()
        return None

    async def publish_result(self, result: WorkflowResult) -> None:
        """Publish a workflow result keyed by correlation_id."""
        self._results[result.correlation_id] = result

    async def get_result(self, correlation_id: UUID) -> WorkflowResult | None:
        """Retrieve a result by correlation_id."""
        return self._results.get(correlation_id)
```

**Step 4: Run test to verify it passes**

Run: `cd python && python -m pytest tests/test_task_bus.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add python/omnimind_backend/workers/task_bus.py python/tests/test_task_bus.py
git commit -m "feat(workers): add TaskBus protocol and InMemoryTaskBus implementation"
```

---

## Task 3: Workflow Registry

**Files:**
- Create: `python/omnimind_backend/workers/workflow_registry.py`
- Test: `python/tests/test_workflow_registry.py`

**Step 1: Write the failing test**

Create `python/tests/test_workflow_registry.py`:

```python
"""Tests for workflow registry."""

import pytest

from omnimind_backend.workers.workflow_registry import WorkflowRegistry
from omnimind_backend.schemas.workflow import WorkflowDefinition


def test_register_and_get() -> None:
    reg = WorkflowRegistry()
    wf = WorkflowDefinition(workflow_id="research_v1", description="Research pipeline")
    reg.register(wf)
    assert reg.get("research_v1") == wf


def test_get_unregistered_raises() -> None:
    reg = WorkflowRegistry()
    with pytest.raises(KeyError):
        reg.get("nonexistent")


def test_list_all() -> None:
    reg = WorkflowRegistry()
    reg.register(WorkflowDefinition(workflow_id="wf1"))
    reg.register(WorkflowDefinition(workflow_id="wf2"))
    assert len(reg.list_all()) == 2


def test_duplicate_version_rejected() -> None:
    reg = WorkflowRegistry()
    wf1 = WorkflowDefinition(workflow_id="wf1", version="1.0.0")
    wf2 = WorkflowDefinition(workflow_id="wf1", version="1.0.0")  # Same ID + version
    reg.register(wf1)
    with pytest.raises(ValueError, match="already registered"):
        reg.register(wf2)


def test_different_version_accepted() -> None:
    reg = WorkflowRegistry()
    reg.register(WorkflowDefinition(workflow_id="wf1", version="1.0.0"))
    reg.register(WorkflowDefinition(workflow_id="wf1", version="2.0.0"))
    assert reg.get("wf1").version == "2.0.0"  # Latest version
```

**Step 2: Run test to verify it fails**

Run: `cd python && python -m pytest tests/test_workflow_registry.py -v`
Expected: FAIL with `ModuleNotFoundError`

**Step 3: Write minimal implementation**

Create `python/omnimind_backend/workers/workflow_registry.py`:

```python
"""Workflow registry for pre-built external workflows.

Workflows are registered at startup and exposed as callable tools
to agents. Versioned and immutable once deployed.
"""

from __future__ import annotations

from omnimind_backend.schemas.workflow import WorkflowDefinition


class WorkflowRegistry:
    """Registry of pre-built workflow definitions."""

    def __init__(self) -> None:
        self._workflows: dict[str, WorkflowDefinition] = {}
        self._versions: dict[str, set[str]] = {}

    def register(self, workflow: WorkflowDefinition) -> None:
        """Register a workflow. Rejects duplicate (id, version) pairs."""
        key = workflow.workflow_id
        version = workflow.version

        if key in self._versions and version in self._versions[key]:
            raise ValueError(
                f"Workflow '{key}' version '{version}' already registered. "
                "Workflows are immutable once deployed."
            )

        if key not in self._versions:
            self._versions[key] = set()
        self._versions[key].add(version)
        self._workflows[key] = workflow

    def get(self, workflow_id: str) -> WorkflowDefinition:
        """Get the latest registered version of a workflow.

        Raises:
            KeyError: If workflow_id is not registered.
        """
        if workflow_id not in self._workflows:
            raise KeyError(f"Workflow '{workflow_id}' is not registered.")
        return self._workflows[workflow_id]

    def list_all(self) -> list[WorkflowDefinition]:
        """Return all registered workflows (latest versions)."""
        return list(self._workflows.values())
```

**Step 4: Run test to verify it passes**

Run: `cd python && python -m pytest tests/test_workflow_registry.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add python/omnimind_backend/workers/workflow_registry.py python/tests/test_workflow_registry.py
git commit -m "feat(workers): add WorkflowRegistry with versioned immutable definitions"
```

---

## Task 4: Error Classification for Retry Policy

**Files:**
- Create: `python/omnimind_backend/workers/error_classifier.py`
- Test: `python/tests/test_error_classifier.py`

**Step 1: Write the failing test**

Create `python/tests/test_error_classifier.py`:

```python
"""Tests for error classification in retry policy."""

from omnimind_backend.workers.error_classifier import classify_error
from omnimind_backend.schemas.workflow import ErrorClassification


def test_transient_429() -> None:
    assert classify_error(status_code=429) == ErrorClassification.TRANSIENT


def test_transient_500() -> None:
    assert classify_error(status_code=500) == ErrorClassification.TRANSIENT


def test_transient_503() -> None:
    assert classify_error(status_code=503) == ErrorClassification.TRANSIENT


def test_non_transient_400() -> None:
    assert classify_error(status_code=400) == ErrorClassification.NON_TRANSIENT


def test_non_transient_401() -> None:
    assert classify_error(status_code=401) == ErrorClassification.NON_TRANSIENT


def test_non_transient_404() -> None:
    assert classify_error(status_code=404) == ErrorClassification.NON_TRANSIENT


def test_ambiguous_408() -> None:
    assert classify_error(status_code=408) == ErrorClassification.AMBIGUOUS


def test_connection_error_is_transient() -> None:
    assert classify_error(exception=ConnectionError("timeout")) == ErrorClassification.TRANSIENT


def test_value_error_is_non_transient() -> None:
    assert classify_error(exception=ValueError("bad input")) == ErrorClassification.NON_TRANSIENT
```

**Step 2: Run test to verify it fails**

Run: `cd python && python -m pytest tests/test_error_classifier.py -v`
Expected: FAIL with `ModuleNotFoundError`

**Step 3: Write minimal implementation**

Create `python/omnimind_backend/workers/error_classifier.py`:

```python
"""Error classification for retry policy.

Determines whether an error is transient (retry), non-transient (fail),
or ambiguous (retry with backoff).
"""

from __future__ import annotations

from omnimind_backend.schemas.workflow import ErrorClassification

_TRANSIENT_STATUS_CODES = {429, 500, 502, 503, 504}
_NON_TRANSIENT_STATUS_CODES = {400, 401, 403, 404, 405, 422}
_AMBIGUOUS_STATUS_CODES = {408}

_TRANSIENT_EXCEPTIONS = (ConnectionError, TimeoutError, OSError)


def classify_error(
    status_code: int | None = None,
    exception: Exception | None = None,
) -> ErrorClassification:
    """Classify an error for retry policy decisions.

    Args:
        status_code: HTTP status code if available.
        exception: Python exception if available.

    Returns:
        Error classification determining retry behavior.
    """
    if status_code is not None:
        if status_code in _TRANSIENT_STATUS_CODES:
            return ErrorClassification.TRANSIENT
        if status_code in _NON_TRANSIENT_STATUS_CODES:
            return ErrorClassification.NON_TRANSIENT
        if status_code in _AMBIGUOUS_STATUS_CODES:
            return ErrorClassification.AMBIGUOUS

    if exception is not None:
        if isinstance(exception, _TRANSIENT_EXCEPTIONS):
            return ErrorClassification.TRANSIENT
        return ErrorClassification.NON_TRANSIENT

    return ErrorClassification.AMBIGUOUS
```

**Step 4: Run test to verify it passes**

Run: `cd python && python -m pytest tests/test_error_classifier.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add python/omnimind_backend/workers/error_classifier.py python/tests/test_error_classifier.py
git commit -m "feat(workers): add error classifier for retry policy decisions"
```

---

## Task 5: Full Regression Check

**Step 1: Run the full test suite**

Run: `cd python && python -m pytest tests/ -v --tb=short`
Expected: All tests PASS

---

## Summary

| Task | What | Files |
|------|------|-------|
| 1 | Workflow + DLQ + queue schemas | `schemas/workflow.py` |
| 2 | TaskBus protocol + InMemoryTaskBus | `workers/task_bus.py` |
| 3 | WorkflowRegistry with versioning | `workers/workflow_registry.py` |
| 4 | Error classifier for retry policy | `workers/error_classifier.py` |
| 5 | Full regression check | — |
