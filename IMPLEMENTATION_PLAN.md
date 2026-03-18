# MindFlow Long-Session Coordination — Implementation Plan

## Overview

Este documento detalha o plano de implementação para adicionar suporte a **coordenação real com iterações longas** ao MindFlow, permitindo que especialistas trabalhem em sessões estendidas com feedback em tempo real do orquestrador.

---

## Phase 1: Data Structures & Schemas (Week 1)

### 1.1 Create Schema Definitions

**File**: `python/mindflow_backend/schemas/orchestration/work_sessions.py`

```python
"""Work session schemas for long-running specialist iterations."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

class IterationStatus(str, Enum):
    """Status of an iteration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"

class FindingType(str, Enum):
    """Types of findings that can be extracted."""
    VULNERABILITY = "vulnerability"
    PATTERN = "pattern"
    SYMBOL = "symbol"
    FILE = "file"
    COMPONENT = "component"
    ISSUE = "issue"
    RECOMMENDATION = "recommendation"
    ALTERNATIVE = "alternative"

@dataclass
class Finding:
    """A structured finding from an iteration."""
    finding_id: str
    finding_type: FindingType
    title: str
    description: str
    confidence: float  # 0-1
    evidence: list[str] = field(default_factory=list)
    related_findings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)

@dataclass
class Iteration:
    """A single iteration within a work session."""
    iteration_id: str
    iteration_number: int
    session_id: str
    
    # Objective for this iteration
    objective: str
    
    # Input context
    context: str  # Accumulated context
    previous_findings: list[Finding] = field(default_factory=list)
    
    # Processing
    agent_response: str = ""
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    
    # Output
    findings: list[Finding] = field(default_factory=list)
    confidence: float = 0.0
    
    # Reflection
    reflection: str = ""  # What we learned, next steps
    should_continue: bool = True
    
    # Status
    status: IterationStatus = IterationStatus.PENDING
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_seconds: float = 0.0

@dataclass
class Checkpoint:
    """A checkpoint for pause/resume."""
    checkpoint_id: str
    session_id: str
    iteration_number: int
    
    # State snapshot
    working_memory: dict[str, Any]
    findings_so_far: list[Finding]
    next_objective: str
    
    # Metadata
    is_resumable: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    reason: str = ""  # Why was this checkpoint created?

@dataclass
class WorkSession:
    """A long-running work session for a specialist."""
    session_id: str
    agent_id: str
    objective: str
    
    # Iteration control
    max_iterations: int = 50
    current_iteration: int = 0
    
    # Accumulated context
    working_memory: dict[str, Any] = field(default_factory=dict)
    findings: list[Finding] = field(default_factory=list)
    
    # Checkpoints
    checkpoints: list[Checkpoint] = field(default_factory=list)
    
    # Iterations
    iterations: list[Iteration] = field(default_factory=list)
    
    # Status
    status: str = "running"  # running, paused, completed, failed
    started_at: datetime = field(default_factory=datetime.utcnow)
    last_heartbeat: datetime = field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    
    # Metadata
    metadata: dict[str, Any] = field(default_factory=dict)
    
    # Execution tracking
    root_execution_id: str | None = None
    parent_execution_id: str | None = None
```

### 1.2 Create Database Models

**File**: `python/mindflow_backend/storage/postgresql/models/work_sessions.py`

```python
"""SQLAlchemy models for work sessions."""

from datetime import UTC, datetime
from sqlalchemy import (
    JSON, Column, DateTime, Float, ForeignKey, Integer, String, Text, Boolean, Enum
)
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class WorkSessionModel(Base):
    """Persistent work session."""
    __tablename__ = "work_sessions"
    
    session_id = Column(String(255), primary_key=True)
    agent_id = Column(String(255), nullable=False, index=True)
    objective = Column(Text, nullable=False)
    
    max_iterations = Column(Integer, default=50)
    current_iteration = Column(Integer, default=0)
    
    working_memory_json = Column(JSON, default={})
    
    status = Column(String(50), default="running", index=True)
    started_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    last_heartbeat = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    root_execution_id = Column(String(255), nullable=True, index=True)
    parent_execution_id = Column(String(255), nullable=True)
    
    metadata_json = Column(JSON, default={})

class IterationModel(Base):
    """Persistent iteration."""
    __tablename__ = "iterations"
    
    iteration_id = Column(String(255), primary_key=True)
    session_id = Column(String(255), ForeignKey("work_sessions.session_id"), index=True)
    iteration_number = Column(Integer, nullable=False)
    
    objective = Column(Text, nullable=False)
    context = Column(Text, default="")
    
    agent_response = Column(Text, default="")
    tool_calls_json = Column(JSON, default=[])
    
    confidence = Column(Float, default=0.0)
    reflection = Column(Text, default="")
    should_continue = Column(Boolean, default=True)
    
    status = Column(String(50), default="pending")
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Float, default=0.0)

class FindingModel(Base):
    """Persistent finding."""
    __tablename__ = "findings"
    
    finding_id = Column(String(255), primary_key=True)
    session_id = Column(String(255), ForeignKey("work_sessions.session_id"), index=True)
    iteration_id = Column(String(255), ForeignKey("iterations.iteration_id"), nullable=True)
    
    finding_type = Column(String(50), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    confidence = Column(Float, default=0.0)
    
    evidence_json = Column(JSON, default=[])
    related_findings_json = Column(JSON, default=[])
    metadata_json = Column(JSON, default={})
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

class CheckpointModel(Base):
    """Persistent checkpoint."""
    __tablename__ = "checkpoints"
    
    checkpoint_id = Column(String(255), primary_key=True)
    session_id = Column(String(255), ForeignKey("work_sessions.session_id"), index=True)
    iteration_number = Column(Integer, nullable=False)
    
    working_memory_json = Column(JSON, default={})
    findings_count = Column(Integer, default=0)
    next_objective = Column(Text, nullable=False)
    
    is_resumable = Column(Boolean, default=True)
    reason = Column(String(500), default="")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
```

### 1.3 Create Alembic Migration

**File**: `python/alembic/versions/XXXX_add_work_sessions.py`

```python
"""Add work sessions tables."""

from alembic import op
import sqlalchemy as sa

def upgrade():
    """Create work sessions tables."""
    op.create_table(
        'work_sessions',
        sa.Column('session_id', sa.String(255), primary_key=True),
        sa.Column('agent_id', sa.String(255), nullable=False, index=True),
        sa.Column('objective', sa.Text, nullable=False),
        sa.Column('max_iterations', sa.Integer, default=50),
        sa.Column('current_iteration', sa.Integer, default=0),
        sa.Column('working_memory_json', sa.JSON, default={}),
        sa.Column('status', sa.String(50), default='running', index=True),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('last_heartbeat', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('root_execution_id', sa.String(255), nullable=True, index=True),
        sa.Column('parent_execution_id', sa.String(255), nullable=True),
        sa.Column('metadata_json', sa.JSON, default={}),
    )
    
    # Similar for iterations, findings, checkpoints tables
    # ...

def downgrade():
    """Drop work sessions tables."""
    op.drop_table('checkpoints')
    op.drop_table('findings')
    op.drop_table('iterations')
    op.drop_table('work_sessions')
```

### 1.4 Update Imports

**File**: `python/mindflow_backend/storage/postgresql/models/__init__.py`

```python
from .work_sessions import WorkSessionModel, IterationModel, FindingModel, CheckpointModel

__all__ = [
    "WorkSessionModel",
    "IterationModel",
    "FindingModel",
    "CheckpointModel",
]
```

### 1.5 Tests for Schemas

**File**: `python/mindflow_backend/tests/test_work_session_schemas.py`

```python
"""Tests for work session schemas."""

import pytest
from datetime import datetime
from mindflow_backend.schemas.orchestration.work_sessions import (
    Finding, FindingType, Iteration, Checkpoint, WorkSession, IterationStatus
)

def test_finding_creation():
    """Test creating a finding."""
    finding = Finding(
        finding_id="f1",
        finding_type=FindingType.VULNERABILITY,
        title="SQL Injection",
        description="Unvalidated user input in query",
        confidence=0.95,
        evidence=["line 42: query = f'SELECT * FROM users WHERE id={user_id}'"],
    )
    assert finding.finding_id == "f1"
    assert finding.finding_type == FindingType.VULNERABILITY
    assert finding.confidence == 0.95

def test_iteration_creation():
    """Test creating an iteration."""
    iteration = Iteration(
        iteration_id="i1",
        iteration_number=1,
        session_id="s1",
        objective="Explore authentication flow",
        context="Initial context",
    )
    assert iteration.iteration_number == 1
    assert iteration.status == IterationStatus.PENDING

def test_work_session_creation():
    """Test creating a work session."""
    session = WorkSession(
        session_id="s1",
        agent_id="analyst:security_guard",
        objective="Audit authentication system",
        max_iterations=30,
    )
    assert session.agent_id == "analyst:security_guard"
    assert session.max_iterations == 30
    assert session.status == "running"
```

---

## Phase 2: WorkSessionManager (Week 2)

### 2.1 Create WorkSessionManager

**File**: `python/mindflow_backend/orchestrator/work_sessions/manager.py`

```python
"""Manages long-running work sessions for specialists."""

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from mindflow_backend.execution_memory import get_execution_memory_service
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.schemas.orchestration.work_sessions import (
    Checkpoint, Finding, Iteration, IterationStatus, WorkSession
)
from mindflow_backend.storage.postgresql.models import (
    CheckpointModel, FindingModel, IterationModel, WorkSessionModel
)

_logger = get_logger(__name__)

class WorkSessionManager:
    """Manages work sessions for long-running specialist iterations."""
    
    def __init__(self, *, db_session_factory=None, execution_memory=None):
        self._db_session_factory = db_session_factory
        self._execution_memory = execution_memory or get_execution_memory_service()
    
    async def create_session(
        self,
        agent_id: str,
        objective: str,
        max_iterations: int = 50,
        context: str = "",
        root_execution_id: str | None = None,
        parent_execution_id: str | None = None,
    ) -> WorkSession:
        """Create a new work session."""
        session_id = f"ws-{uuid4().hex[:12]}"
        now = datetime.now(UTC)
        
        session = WorkSession(
            session_id=session_id,
            agent_id=agent_id,
            objective=objective,
            max_iterations=max_iterations,
            working_memory={"initial_context": context},
            root_execution_id=root_execution_id,
            parent_execution_id=parent_execution_id,
            started_at=now,
            last_heartbeat=now,
        )
        
        # Persist to database
        await self._persist_session(session)
        
        _logger.info(
            "work_session_created",
            session_id=session_id,
            agent_id=agent_id,
            max_iterations=max_iterations,
        )
        
        return session
    
    async def run_iteration(
        self,
        session: WorkSession,
        iteration_objective: str,
    ) -> Iteration:
        """Run a single iteration within the session."""
        iteration_number = session.current_iteration + 1
        iteration_id = f"iter-{session.session_id}-{iteration_number}"
        
        iteration = Iteration(
            iteration_id=iteration_id,
            iteration_number=iteration_number,
            session_id=session.session_id,
            objective=iteration_objective,
            context=self._build_context_for_iteration(session),
            previous_findings=session.findings,
            status=IterationStatus.RUNNING,
            started_at=datetime.now(UTC),
        )
        
        # Persist iteration
        await self._persist_iteration(iteration)
        
        _logger.info(
            "iteration_started",
            session_id=session.session_id,
            iteration_number=iteration_number,
            objective=iteration_objective,
        )
        
        return iteration
    
    async def complete_iteration(
        self,
        iteration: Iteration,
        agent_response: str,
        findings: list[Finding],
        confidence: float,
        reflection: str = "",
        should_continue: bool = True,
    ) -> Iteration:
        """Mark iteration as complete with results."""
        now = datetime.now(UTC)
        iteration.agent_response = agent_response
        iteration.findings = findings
        iteration.confidence = confidence
        iteration.reflection = reflection
        iteration.should_continue = should_continue
        iteration.status = IterationStatus.COMPLETED
        iteration.completed_at = now
        iteration.duration_seconds = (now - iteration.started_at).total_seconds()
        
        # Persist results
        await self._persist_iteration(iteration)
        
        # Update session
        session = await self.get_session(iteration.session_id)
        session.current_iteration = iteration.iteration_number
        session.findings.extend(findings)
        session.last_heartbeat = now
        await self._persist_session(session)
        
        _logger.info(
            "iteration_completed",
            session_id=iteration.session_id,
            iteration_number=iteration.iteration_number,
            findings_count=len(findings),
            confidence=confidence,
        )
        
        return iteration
    
    async def collect_findings(self, session: WorkSession) -> list[Finding]:
        """Collect all findings from a session."""
        # Load from database
        findings = await self._load_findings_for_session(session.session_id)
        return findings
    
    async def create_checkpoint(
        self,
        session: WorkSession,
        reason: str = "manual",
    ) -> Checkpoint:
        """Create a checkpoint for pause/resume."""
        checkpoint_id = f"cp-{session.session_id}-{session.current_iteration}"
        
        checkpoint = Checkpoint(
            checkpoint_id=checkpoint_id,
            session_id=session.session_id,
            iteration_number=session.current_iteration,
            working_memory=session.working_memory,
            findings_so_far=session.findings,
            next_objective="",  # Will be set by coordinator
            reason=reason,
        )
        
        await self._persist_checkpoint(checkpoint)
        
        _logger.info(
            "checkpoint_created",
            session_id=session.session_id,
            iteration_number=session.current_iteration,
            reason=reason,
        )
        
        return checkpoint
    
    async def resume_from_checkpoint(
        self,
        checkpoint: Checkpoint,
    ) -> WorkSession:
        """Resume a session from a checkpoint."""
        session = await self.get_session(checkpoint.session_id)
        session.working_memory = checkpoint.working_memory
        session.findings = checkpoint.findings_so_far
        session.current_iteration = checkpoint.iteration_number
        session.status = "running"
        session.last_heartbeat = datetime.now(UTC)
        
        await self._persist_session(session)
        
        _logger.info(
            "session_resumed",
            session_id=session.session_id,
            from_iteration=checkpoint.iteration_number,
        )
        
        return session
    
    async def get_session(self, session_id: str) -> WorkSession | None:
        """Get a work session by ID."""
        # Load from database
        return await self._load_session(session_id)
    
    async def pause_session(self, session_id: str, reason: str = "") -> WorkSession:
        """Pause a work session."""
        session = await self.get_session(session_id)
        if session is None:
            raise ValueError(f"Session not found: {session_id}")
        
        session.status = "paused"
        await self._persist_session(session)
        
        _logger.info("session_paused", session_id=session_id, reason=reason)
        
        return session
    
    async def resume_session(self, session_id: str) -> WorkSession:
        """Resume a paused work session."""
        session = await self.get_session(session_id)
        if session is None:
            raise ValueError(f"Session not found: {session_id}")
        
        session.status = "running"
        session.last_heartbeat = datetime.now(UTC)
        await self._persist_session(session)
        
        _logger.info("session_resumed", session_id=session_id)
        
        return session
    
    # Private methods for persistence
    
    async def _persist_session(self, session: WorkSession) -> None:
        """Persist session to database."""
        # Implementation using db_session_factory
        pass
    
    async def _persist_iteration(self, iteration: Iteration) -> None:
        """Persist iteration to database."""
        pass
    
    async def _persist_checkpoint(self, checkpoint: Checkpoint) -> None:
        """Persist checkpoint to database."""
        pass
    
    async def _load_session(self, session_id: str) -> WorkSession | None:
        """Load session from database."""
        pass
    
    async def _load_findings_for_session(self, session_id: str) -> list[Finding]:
        """Load all findings for a session."""
        pass
    
    def _build_context_for_iteration(self, session: WorkSession) -> str:
        """Build context string for next iteration."""
        lines = [
            f"Session: {session.session_id}",
            f"Iteration: {session.current_iteration + 1}/{session.max_iterations}",
            f"Objective: {session.objective}",
        ]
        
        if session.findings:
            lines.append(f"\nFindings so far ({len(session.findings)}):")
            for finding in session.findings[-5:]:  # Last 5 findings
                lines.append(f"  - [{finding.finding_type.value}] {finding.title}")
        
        if session.working_memory:
            lines.append("\nWorking memory:")
            for key, value in list(session.working_memory.items())[-3:]:
                lines.append(f"  - {key}: {str(value)[:100]}")
        
        return "\n".join(lines)


# Global instance
_work_session_manager: WorkSessionManager | None = None

def get_work_session_manager() -> WorkSessionManager:
    """Get or create global work session manager."""
    global _work_session_manager
    if _work_session_manager is None:
        _work_session_manager = WorkSessionManager()
    return _work_session_manager
```

### 2.2 Tests for WorkSessionManager

**File**: `python/mindflow_backend/tests/test_work_session_manager.py`

```python
"""Tests for WorkSessionManager."""

import pytest
from mindflow_backend.orchestrator.work_sessions.manager import WorkSessionManager
from mindflow_backend.schemas.orchestration.work_sessions import (
    Finding, FindingType, IterationStatus
)

@pytest.mark.asyncio
async def test_create_session():
    """Test creating a work session."""
    manager = WorkSessionManager()
    
    session = await manager.create_session(
        agent_id="analyst:security_guard",
        objective="Audit authentication",
        max_iterations=30,
    )
    
    assert session.agent_id == "analyst:security_guard"
    assert session.max_iterations == 30
    assert session.status == "running"

@pytest.mark.asyncio
async def test_run_iteration():
    """Test running an iteration."""
    manager = WorkSessionManager()
    
    session = await manager.create_session(
        agent_id="analyst",
        objective="Analyze code",
    )
    
    iteration = await manager.run_iteration(
        session,
        iteration_objective="Explore main module",
    )
    
    assert iteration.iteration_number == 1
    assert iteration.status == IterationStatus.RUNNING

@pytest.mark.asyncio
async def test_complete_iteration():
    """Test completing an iteration."""
    manager = WorkSessionManager()
    
    session = await manager.create_session(
        agent_id="analyst",
        objective="Analyze code",
    )
    
    iteration = await manager.run_iteration(
        session,
        iteration_objective="Explore main module",
    )
    
    findings = [
        Finding(
            finding_id="f1",
            finding_type=FindingType.PATTERN,
            title="Singleton pattern",
            description="Found singleton pattern in main module",
            confidence=0.9,
        )
    ]
    
    completed = await manager.complete_iteration(
        iteration,
        agent_response="Found singleton pattern",
        findings=findings,
        confidence=0.9,
    )
    
    assert completed.status == IterationStatus.COMPLETED
    assert len(completed.findings) == 1
```

---

## Phase 3: IterationCoordinator (Week 2-3)

### 3.1 Create IterationCoordinator

**File**: `python/mindflow_backend/orchestrator/work_sessions/coordinator.py`

```python
"""Coordinates iterations with real-time feedback from orchestrator."""

from typing import Any
from mindflow_backend.execution_memory import get_execution_memory_service
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.orchestrator.work_sessions.manager import get_work_session_manager
from mindflow_backend.schemas.orchestration.work_sessions import Iteration, WorkSession

_logger = get_logger(__name__)

class IterationCoordinator:
    """Coordinates iterations with feedback in real-time."""
    
    def __init__(self, *, work_session_manager=None, execution_memory=None):
        self._work_session_manager = work_session_manager or get_work_session_manager()
        self._execution_memory = execution_memory or get_execution_memory_service()
    
    async def run_iteration_with_feedback(
        self,
        session: WorkSession,
        iteration_number: int,
        objective: str,
    ) -> Iteration:
        """Run iteration with opportunity for feedback."""
        # Start iteration
        iteration = await self._work_session_manager.run_iteration(
            session,
            iteration_objective=objective,
        )
        
        # TODO: Invoke agent with iteration objective
        # agent_response = await self._invoke_agent(session, iteration)
        
        # TODO: Extract findings from response
        # findings = await self._extract_findings(agent_response)
        
        # TODO: Complete iteration
        # await self._work_session_manager.complete_iteration(
        #     iteration,
        #     agent_response=agent_response,
        #     findings=findings,
        #     confidence=0.8,
        # )
        
        return iteration
    
    async def send_feedback_to_agent(
        self,
        session: WorkSession,
        feedback: str,
    ) -> None:
        """Send feedback from orchestrator to agent."""
        # Record message in execution memory
        if session.root_execution_id:
            await self._execution_memory.record_message(
                execution_id=session.root_execution_id,
                message_type="orchestrator_feedback",
                sender_execution_id=session.root_execution_id,
                recipient_execution_id=session.root_execution_id,
                content=feedback,
                visibility="internal",
                status="pending",
            )
        
        _logger.info(
            "feedback_sent",
            session_id=session.session_id,
            feedback_length=len(feedback),
        )
    
    async def should_continue_iterating(
        self,
        session: WorkSession,
        iteration: Iteration,
    ) -> bool:
        """Decide if should continue iterating."""
        # Check if max iterations reached
        if session.current_iteration >= session.max_iterations:
            _logger.info(
                "max_iterations_reached",
                session_id=session.session_id,
                iterations=session.current_iteration,
            )
            return False
        
        # Check if iteration says to continue
        if not iteration.should_continue:
            _logger.info(
                "iteration_recommends_stop",
                session_id=session.session_id,
                iteration_number=iteration.iteration_number,
            )
            return False
        
        # Check if pause requested
        if session.status == "paused":
            _logger.info(
                "session_paused",
                session_id=session.session_id,
            )
            return False
        
        return True


# Global instance
_iteration_coordinator: IterationCoordinator | None = None

def get_iteration_coordinator() -> IterationCoordinator:
    """Get or create global iteration coordinator."""
    global _iteration_coordinator
    if _iteration_coordinator is None:
        _iteration_coordinator = IterationCoordinator()
    return _iteration_coordinator
```

---

## Phase 4: StructuredFindingExtractor (Week 3)

### 4.1 Create StructuredFindingExtractor

**File**: `python/mindflow_backend/orchestrator/work_sessions/finding_extractor.py`

```python
"""Extracts structured findings from agent responses using LLM."""

import json
from typing import Any

from mindflow_backend.infra.config import get_settings
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.runtime import get_model_for_provider, normalize_response_for_json
from mindflow_backend.schemas.orchestration.work_sessions import Finding, FindingType

_logger = get_logger(__name__)

class StructuredFindingExtractor:
    """Extracts structured findings from agent responses."""
    
    def __init__(self):
        self.settings = get_settings()
    
    async def extract_findings(
        self,
        agent_response: str,
        finding_types: list[str],
        context: str = "",
    ) -> list[Finding]:
        """Extract structured findings from agent response using LLM."""
        
        extraction_prompt = f"""You are a finding extractor. Analyze the agent response and extract structured findings.

Agent Response:
{agent_response}

Context:
{context}

Expected Finding Types: {', '.join(finding_types)}

Extract findings as JSON array. Each finding must have:
- finding_type: one of {finding_types}
- title: short title
- description: detailed description
- confidence: 0-1
- evidence: list of supporting evidence/quotes
- metadata: any additional metadata

Return ONLY valid JSON array, no markdown or explanation."""
        
        try:
            llm = get_model_for_provider(
                self.settings.default_provider,
                self.settings.default_model,
            )
            
            messages = [
                {"role": "system", "content": "You are a precise finding extractor. Return only valid JSON."},
                {"role": "user", "content": extraction_prompt},
            ]
            
            response = await llm.ainvoke(messages)
            response_text = normalize_response_for_json(response)
            
            # Parse JSON
            try:
                data = json.loads(response_text)
                if not isinstance(data, list):
                    data = [data]
            except json.JSONDecodeError:
                # Try extracting JSON from prose
                import re
                json_match = re.search(r'\[[\s\S]*\]', response_text)
                if json_match:
                    data = json.loads(json_match.group())
                else:
                    _logger.warning("finding_extraction_failed_no_json", response=response_text[:200])
                    return []
            
            # Convert to Finding objects
            findings = []
            for item in data:
                try:
                    finding = Finding(
                        finding_id=f"f-{len(findings)}",
                        finding_type=FindingType(item.get("finding_type", "issue")),
                        title=item.get("title", ""),
                        description=item.get("description", ""),
                        confidence=float(item.get("confidence", 0.5)),
                        evidence=item.get("evidence", []),
                        metadata=item.get("metadata", {}),
                    )
                    findings.append(finding)
                except (ValueError, KeyError) as e:
                    _logger.warning("finding_parse_error", error=str(e), item=item)
                    continue
            
            _logger.info(
                "findings_extracted",
                count=len(findings),
                types=[f.finding_type.value for f in findings],
            )
            
            return findings
            
        except Exception as exc:
            _logger.error("finding_extraction_error", error=str(exc))
            return []
    
    async def validate_findings(
        self,
        findings: list[Finding],
    ) -> list[Finding]:
        """Validate and enrich findings."""
        # TODO: Implement validation logic
        # - Check for duplicates
        # - Validate confidence scores
        # - Enrich with additional context
        return findings
```

---

## Phase 5: Integration with DelegationEngine (Week 4)

### 5.1 Modify DelegationEngine

**File**: `python/mindflow_backend/orchestrator/delegation/engine.py` (modifications)

```python
# Add to imports
from mindflow_backend.orchestrator.work_sessions.manager import get_work_session_manager
from mindflow_backend.orchestrator.work_sessions.coordinator import get_iteration_coordinator
from mindflow_backend.orchestrator.work_sessions.finding_extractor import StructuredFindingExtractor

# Modify delegate_task to support long sessions
async def delegate_task(
    self,
    task: DelegationTask,
    session: Any,
    *,
    session_id: str | None = None,
    root_execution_id: str | None = None,
    parent_execution_id: str | None = None,
    use_long_session: bool = False,  # NEW
) -> DelegationResult:
    """Execute a delegated task with optional long-session support."""
    
    if use_long_session:
        return await self._delegate_task_long_session(
            task=task,
            session=session,
            session_id=session_id,
            root_execution_id=root_execution_id,
            parent_execution_id=parent_execution_id,
        )
    else:
        # Existing implementation
        return await self._delegate_task_single(...)

async def _delegate_task_long_session(
    self,
    task: DelegationTask,
    session: Any,
    *,
    session_id: str | None = None,
    root_execution_id: str | None = None,
    parent_execution_id: str | None = None,
) -> DelegationResult:
    """Execute task using long-session iteration."""
    
    work_session_manager = get_work_session_manager()
    iteration_coordinator = get_iteration_coordinator()
    finding_extractor = StructuredFindingExtractor()
    
    # Create work session
    work_session = await work_session_manager.create_session(
        agent_id=task.agent_id or task.agent.value,
        objective=task.objective,
        max_iterations=task.max_iterations,
        context=task.context_from_session or "",
        root_execution_id=root_execution_id,
        parent_execution_id=parent_execution_id,
    )
    
    all_findings = []
    
    # Run iterations
    for iteration_num in range(1, task.max_iterations + 1):
        # Determine objective for this iteration
        if iteration_num == 1:
            iteration_objective = f"Initial exploration: {task.objective}"
        else:
            # TODO: Use LLM to determine next objective based on findings
            iteration_objective = f"Continue: {task.objective}"
        
        # Run iteration
        iteration = await iteration_coordinator.run_iteration_with_feedback(
            work_session,
            iteration_number=iteration_num,
            objective=iteration_objective,
        )
        
        # TODO: Invoke agent and get response
        # agent_response = await self._invoke_agent_for_iteration(...)
        
        # Extract findings
        # findings = await finding_extractor.extract_findings(
        #     agent_response,
        #     finding_types=["vulnerability", "pattern", "issue"],
        # )
        
        # all_findings.extend(findings)
        
        # Check if should continue
        # should_continue = await iteration_coordinator.should_continue_iterating(
        #     work_session,
        #     iteration,
        # )
        # if not should_continue:
        #     break
    
    # Return aggregated result
    return DelegationResult(
        task_id=task.task_id,
        agent=task.agent,
        status="completed",
        key_findings=self._format_findings(all_findings),
        full_output="",  # TODO: Aggregate all iteration responses
        confidence=0.8,
        tokens_consumed=0,  # TODO: Track tokens
    )

def _format_findings(self, findings: list[Finding]) -> str:
    """Format findings for display."""
    lines = []
    for finding in findings:
        lines.append(f"[{finding.finding_type.value}] {finding.title}")
        lines.append(f"  {finding.description}")
        if finding.evidence:
            lines.append(f"  Evidence: {', '.join(finding.evidence[:2])}")
    return "\n".join(lines)
```

---

## Phase 6: Integration with Orchestrator (Week 4-5)

### 6.1 Modify IntelligentRouter

**File**: `python/mindflow_backend/orchestrator/routing/intelligent_router.py` (modifications)

```python
# Add to ExecutionStrategy enum
class ExecutionStrategy(str, Enum):
    DIRECT_RESPONSE = "direct_response"
    SINGLE_AGENT = "single_agent"
    CHAIN = "chain"
    GRAPH = "graph"
    LONG_SESSION = "long_session"  # NEW

# Modify analyze_intent_with_llm to detect long_session
async def analyze_intent_with_llm(
    self,
    message: str,
    session_context: str = "",
    folder_path: str | None = None,
    has_folder_path: bool = False,
) -> IntentAnalysis:
    """Analyze intent and detect if long session is needed."""
    
    # ... existing code ...
    
    # Add to prompt:
    """
    ## Long Session Detection
    
    Use execution_strategy = "long_session" when:
    - Task requires deep, iterative analysis (security audit, architecture review)
    - Task involves exploring multiple alternatives
    - Task requires refinement based on findings
    - Task is complex and benefits from multiple passes
    
    Examples:
    - "Audita a segurança do sistema de autenticação" → long_session
    - "Redesenha a arquitetura do módulo de cache" → long_session
    - "Analisa o código e propõe 3 alternativas de refatoração" → long_session
    """
```

---

## Testing Strategy

### Unit Tests
- `test_work_session_schemas.py` — Schema creation and validation
- `test_work_session_manager.py` — Session lifecycle
- `test_iteration_coordinator.py` — Iteration coordination
- `test_finding_extractor.py` — Finding extraction

### Integration Tests
- `test_long_session_e2e.py` — End-to-end long session workflow
- `test_feedback_loop.py` — Feedback from orchestrator to agent
- `test_checkpoint_resume.py` — Pause/resume functionality

### Example Tests
- `examples/long_session_security_audit.py` — Security audit example
- `examples/long_session_architecture_design.py` — Architecture design example

---

## Success Criteria

- ✅ Agentes podem iterar 50+ vezes sem limite artificial
- ✅ Contexto acumulado entre iterações
- ✅ Feedback em tempo real do orquestrador
- ✅ Achados estruturados (não apenas texto)
- ✅ Pausa/retomada com checkpoints
- ✅ Auditoria completa de cada iteração
- ✅ Testes e2e passando
- ✅ Documentação atualizada

---

## Timeline

| Fase | Semanas | Tarefas |
|------|---------|--------|
| 1 | 1 | Schemas, models, migrations |
| 2 | 2 | WorkSessionManager, testes |
| 3 | 2-3 | IterationCoordinator, testes |
| 4 | 3 | StructuredFindingExtractor, testes |
| 5 | 4 | Integração com DelegationEngine |
| 6 | 4-5 | Integração com Orchestrator, e2e |
| **Total** | **~5 semanas** | |

---

## Rollout Plan

1. **Develop in feature branch**: `feature/long-session-coordination`
2. **Internal testing**: Validar com casos de uso reais
3. **Code review**: Peer review antes de merge
4. **Merge to main**: Quando todos os testes passarem
5. **Deploy**: Gradual rollout com feature flags
6. **Monitor**: Rastrear performance e erros

