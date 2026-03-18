from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest


@pytest.fixture
def db():
    session = AsyncMock()
    session.add = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.get = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def service():
    from mindflow_backend.execution_memory.service import ExecutionMemoryService

    return ExecutionMemoryService()


@pytest.mark.asyncio
async def test_start_execution_creates_running_session(db, service):
    created = await service.start_execution(
        db,
        session_id="sess-1",
        agent_id="orchestrator",
        goal="ship execution memory",
        metadata={"source": "unit-test"},
    )

    assert created.session_id == "sess-1"
    assert created.agent_id == "orchestrator"
    assert created.goal == "ship execution memory"
    assert created.status == "running"
    db.add.assert_called_once()
    db.commit.assert_awaited_once()
    db.refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_record_event_increments_sequence_and_persists_event(db, service):
    execution = SimpleNamespace(
        id="exec-1",
        session_id="sess-1",
        agent_id="coder",
        status="running",
        current_stage="running",
        current_step=None,
        pause_requested=False,
        pause_reason=None,
        last_event_sequence=2,
        last_snapshot_sequence=1,
        last_effect_sequence=0,
        last_event_id=None,
        last_snapshot_id=None,
        context_digest=None,
        metadata={},
        goal="",
    )
    db.get = AsyncMock(return_value=execution)

    recorded = await service.record_event(
        db,
        execution_id="exec-1",
        event_type="tool_call",
        message="Calling shell",
        payload={"tool": "shell"},
        step_id="step-1",
    )

    assert recorded.sequence == 3
    assert recorded.event_type == "tool_call"
    assert execution.last_event_sequence == 3
    db.add.assert_called_once()
    db.commit.assert_awaited_once()
    db.refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_snapshot_persists_state_and_hash(db, service):
    execution = SimpleNamespace(
        id="exec-1",
        session_id="sess-1",
        agent_id="analyst",
        status="running",
        current_stage="running",
        current_step=None,
        pause_requested=False,
        pause_reason=None,
        last_event_sequence=2,
        last_snapshot_sequence=0,
        last_effect_sequence=0,
        last_event_id=None,
        last_snapshot_id=None,
        context_digest=None,
        metadata={},
        goal="",
    )
    db.get = AsyncMock(return_value=execution)

    snapshot = await service.create_snapshot(
        db,
        execution_id="exec-1",
        snapshot_kind="checkpoint",
        stage="paused",
        state={"phase": "analysis", "done": True},
        context="summary of state",
        is_resume_point=True,
        parent_event_id=10,
    )

    assert snapshot.sequence == 1
    assert snapshot.snapshot_kind == "checkpoint"
    assert snapshot.is_resume_point is True
    assert snapshot.state_hash
    assert execution.last_snapshot_sequence == 1
    db.add.assert_called_once()
    db.commit.assert_awaited_once()
    db.refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_request_pause_and_mark_resumed_update_execution_state(db, service):
    execution = SimpleNamespace(
        id="exec-1",
        session_id="sess-1",
        agent_id="analyst",
        status="running",
        current_stage="running",
        current_step=None,
        pause_requested=False,
        pause_reason=None,
        last_event_sequence=1,
        last_snapshot_sequence=0,
        last_effect_sequence=0,
        last_event_id=None,
        last_snapshot_id=None,
        context_digest=None,
        metadata={},
        goal="",
    )
    db.get = AsyncMock(return_value=execution)

    paused = await service.request_pause(db, execution_id="exec-1", reason="waiting for user")
    assert paused.status == "pause_requested"
    assert paused.pause_requested is True
    assert paused.pause_reason == "waiting for user"

    resumed = await service.mark_resumed(db, execution_id="exec-1")
    assert resumed.status == "running"
    assert resumed.pause_requested is False
    assert resumed.resumed_at is not None


@pytest.mark.asyncio
async def test_save_and_load_session_runtime_state_round_trip(db, service):
    saved = await service.save_session_runtime_state(
        db,
        session_id="sess-1",
        execution_id="exec-1",
        state={"current_stage": "analysis", "resume_token": "token-1"},
    )

    assert saved.session_id == "sess-1"
    assert saved.execution_id == "exec-1"
    assert saved.state_json["current_stage"] == "analysis"
    db.add.assert_called_once()
    db.commit.assert_awaited_once()
    db.refresh.assert_awaited_once()

    stored_row = SimpleNamespace(
        session_id="sess-1",
        execution_id="exec-1",
        state_json={"current_stage": "analysis", "resume_token": "token-1"},
        state_hash=saved.state_hash,
        version=1,
        created_at=saved.created_at,
        updated_at=saved.updated_at,
    )
    db.get = AsyncMock(return_value=stored_row)

    loaded = await service.load_session_runtime_state(db, session_id="sess-1")
    assert loaded is not None
    assert loaded.state_json["resume_token"] == "token-1"


@pytest.mark.asyncio
async def test_record_external_effect_uses_effect_key_idempotency(db, service):
    execution = SimpleNamespace(
        id="exec-1",
        session_id="sess-1",
        agent_id="coder",
        status="running",
        current_stage="running",
        current_step=None,
        pause_requested=False,
        pause_reason=None,
        last_event_sequence=1,
        last_snapshot_sequence=0,
        last_effect_sequence=0,
        last_event_id=None,
        last_snapshot_id=None,
        context_digest=None,
        metadata={},
        goal="",
    )
    db.get = AsyncMock(return_value=execution)
    db.execute = AsyncMock(return_value=SimpleNamespace(scalars=lambda: SimpleNamespace(first=lambda: None)))

    effect = await service.record_external_effect(
        db,
        execution_id="exec-1",
        effect_key="file-write:abc",
        effect_type="file_write",
        request={"path": "/tmp/file.txt"},
    )

    assert effect.effect_key == "file-write:abc"
    assert effect.status == "pending"
    db.add.assert_called_once()
