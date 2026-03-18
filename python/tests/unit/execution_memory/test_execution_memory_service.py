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
async def test_start_execution_supports_root_and_child_metadata(db, service):
    created = await service.start_execution(
        db,
        session_id="sess-root",
        agent_id="coder",
        goal="inspect delegated work",
        execution_id="exec-child",
        root_execution_id="exec-root",
        parent_execution_id="exec-parent",
        execution_role="delegated_agent",
        owner_execution_id="exec-root",
        status="queued",
        stage="booting",
        metadata={"source": "delegation"},
    )

    assert created.id == "exec-child"
    assert created.root_execution_id == "exec-root"
    assert created.parent_execution_id == "exec-parent"
    assert created.execution_role == "delegated_agent"
    assert created.owner_execution_id == "exec-root"
    assert created.status == "queued"
    assert created.current_stage == "booting"
    assert created.state_version == 1
    assert created.last_heartbeat_at is not None


@pytest.mark.asyncio
async def test_record_event_increments_sequence_and_persists_event(db, service):
    execution = SimpleNamespace(
        id="exec-1",
        session_id="sess-1",
        agent_id="coder",
        status="running",
        current_stage="running",
        current_step=None,
        root_execution_id="exec-1",
        parent_execution_id=None,
        execution_role="root_orchestrator",
        owner_execution_id="exec-1",
        state_version=1,
        last_heartbeat_at=None,
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
        root_execution_id="exec-1",
        parent_execution_id=None,
        execution_role="root_orchestrator",
        owner_execution_id="exec-1",
        state_version=1,
        last_heartbeat_at=None,
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
        root_execution_id="exec-1",
        parent_execution_id=None,
        execution_role="root_orchestrator",
        owner_execution_id="exec-1",
        state_version=1,
        last_heartbeat_at=None,
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
        root_execution_id="exec-1",
        parent_execution_id=None,
        execution_role="root_orchestrator",
        owner_execution_id="exec-1",
        state_version=1,
        last_heartbeat_at=None,
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


@pytest.mark.asyncio
async def test_record_message_tracks_append_only_mailbox_and_consumption(db, service):
    execution = SimpleNamespace(
        id="exec-child",
        session_id="sess-1",
        agent_id="coder",
        status="running",
        current_stage="working",
        current_step=None,
        root_execution_id="exec-root",
        parent_execution_id="exec-root",
        execution_role="delegated_agent",
        owner_execution_id="exec-root",
        state_version=1,
        last_heartbeat_at=None,
        pause_requested=False,
        pause_reason=None,
        last_event_sequence=1,
        last_snapshot_sequence=0,
        last_effect_sequence=0,
        last_message_sequence=0,
        last_event_id=None,
        last_snapshot_id=None,
        context_digest=None,
        metadata={},
        goal="",
    )
    stored_messages: list[SimpleNamespace] = []

    async def _add(row):
        if row.__class__.__name__ == "AgentExecutionMessage":
            row.id = len(stored_messages) + 1
            stored_messages.append(row)

    async def _refresh(_row):
        return None

    def _scalars_result(rows):
        return SimpleNamespace(
            scalars=lambda: SimpleNamespace(
                first=lambda: rows[0] if rows else None,
                all=lambda: list(rows),
            )
        )

    async def _execute(_query):
        pending = [row for row in stored_messages if getattr(row, "status", "pending") == "pending"]
        return _scalars_result(pending)

    db.get = AsyncMock(return_value=execution)
    db.add = AsyncMock(side_effect=_add)
    db.refresh = AsyncMock(side_effect=_refresh)
    db.execute = AsyncMock(side_effect=_execute)

    message = await service.record_message(
        db,
        execution_id="exec-child",
        message_type="context_update",
        sender_execution_id="exec-root",
        recipient_execution_id="exec-child",
        content="Novo contexto para o agente",
        visibility="internal",
        payload={"source": "orchestrator"},
    )

    assert message.sequence == 1
    assert message.status == "pending"
    assert execution.last_message_sequence == 1

    pending = await service.consume_pending_messages(db, execution_id="exec-child")
    assert len(pending) == 1
    assert pending[0].content == "Novo contexto para o agente"
    assert stored_messages[0].status == "consumed"
    assert stored_messages[0].consumed_at is not None


@pytest.mark.asyncio
async def test_get_execution_tree_includes_children_messages_and_processes(db, service):
    root = SimpleNamespace(
        id="exec-root",
        session_id="sess-1",
        agent_id="orchestrator",
        status="running",
        current_stage="reflecting",
        current_step="wait",
        root_execution_id="exec-root",
        parent_execution_id=None,
        execution_role="root_orchestrator",
        owner_execution_id="exec-root",
        state_version=2,
        last_heartbeat_at=None,
        pause_requested=False,
        pause_reason=None,
        progress=0.5,
        metadata_json={},
    )
    child = SimpleNamespace(
        id="exec-child",
        session_id="sess-1",
        agent_id="coder",
        status="running",
        current_stage="working",
        current_step="inspect",
        root_execution_id="exec-root",
        parent_execution_id="exec-root",
        execution_role="delegated_agent",
        owner_execution_id="exec-root",
        state_version=1,
        last_heartbeat_at=None,
        pause_requested=False,
        pause_reason=None,
        progress=0.2,
        metadata_json={},
    )
    message = SimpleNamespace(
        id=1,
        execution_id="exec-child",
        sequence=1,
        message_type="direct_message",
        sender_execution_id="exec-child",
        recipient_execution_id="exec-root",
        visibility="internal",
        status="pending",
        content="Preciso de mais contexto",
        payload_json={},
        created_at=None,
        consumed_at=None,
    )
    process = SimpleNamespace(
        id=1,
        execution_id="exec-child",
        process_key="proc-1",
        tab_id="tab-1",
        pid=4242,
        state="running",
        cwd="/tmp/work",
        owner_agent_id="coder",
        terminal_key="term-1",
        metadata_json={},
        started_at=None,
        updated_at=None,
        ended_at=None,
        last_heartbeat_at=None,
    )

    async def _get(model, key):
        if key == "exec-root":
            return root
        return None

    db.get = AsyncMock(side_effect=_get)
    db.execute = AsyncMock(
        side_effect=[
            SimpleNamespace(
                scalars=lambda: SimpleNamespace(
                    all=lambda: [root],
                    first=lambda: root,
                )
            ),
            SimpleNamespace(
                scalars=lambda: SimpleNamespace(
                    all=lambda: [root, child],
                    first=lambda: root,
                )
            ),
            SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [message])),
            SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [process])),
        ]
    )

    tree = await service.get_execution_tree("exec-root", db=db)

    assert tree["execution"]["id"] == "exec-root"
    assert len(tree["children"]) == 1
    assert tree["children"][0]["execution"]["id"] == "exec-child"
    assert tree["children"][0]["messages"][0]["content"] == "Preciso de mais contexto"
    assert tree["children"][0]["processes"][0]["pid"] == 4242
