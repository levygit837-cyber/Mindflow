"""Create durable execution memory tables.

Revision ID: 20260317_0015
Revises: 20260317_0014
Create Date: 2026-03-17 21:40:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260317_0015"
down_revision = "20260317_0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("agent_executions"):
        op.create_table(
            "agent_executions",
            sa.Column("id", sa.String(length=64), primary_key=True),
            sa.Column("session_id", sa.String(length=64), nullable=False),
            sa.Column("run_id", sa.String(length=64), nullable=True),
            sa.Column("agent_id", sa.String(length=64), nullable=False),
            sa.Column("mode", sa.String(length=32), nullable=False, server_default="orchestrated"),
            sa.Column("goal", sa.Text(), nullable=False, server_default=""),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="running"),
            sa.Column("current_stage", sa.String(length=64), nullable=True),
            sa.Column("current_step", sa.String(length=128), nullable=True),
            sa.Column("pause_requested", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("pause_reason", sa.Text(), nullable=True),
            sa.Column("provider", sa.String(length=100), nullable=True),
            sa.Column("model", sa.String(length=100), nullable=True),
            sa.Column("progress", sa.Float(), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("last_event_sequence", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("last_snapshot_sequence", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("last_effect_sequence", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("last_event_id", sa.Integer(), nullable=True),
            sa.Column("last_snapshot_id", sa.Integer(), nullable=True),
            sa.Column("context_digest", sa.String(length=64), nullable=True),
            sa.Column("metadata", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("paused_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("resumed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        )
        op.create_index("ix_agent_executions_session_id", "agent_executions", ["session_id"])
        op.create_index("ix_agent_executions_run_id", "agent_executions", ["run_id"])
        op.create_index("ix_agent_executions_agent_id", "agent_executions", ["agent_id"])
        op.create_index("ix_agent_executions_status", "agent_executions", ["status"])

    if not inspector.has_table("agent_execution_events"):
        op.create_table(
            "agent_execution_events",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("execution_id", sa.String(length=64), sa.ForeignKey("agent_executions.id", ondelete="CASCADE"), nullable=False),
            sa.Column("sequence", sa.Integer(), nullable=False),
            sa.Column("event_type", sa.String(length=64), nullable=False),
            sa.Column("message", sa.Text(), nullable=True),
            sa.Column("payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
            sa.Column("stage", sa.String(length=64), nullable=True),
            sa.Column("step_id", sa.String(length=128), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.UniqueConstraint("execution_id", "sequence", name="uq_agent_execution_event_sequence"),
        )
        op.create_index("ix_agent_execution_events_execution_id", "agent_execution_events", ["execution_id"])
        op.create_index("ix_agent_execution_events_event_type", "agent_execution_events", ["event_type"])

    if not inspector.has_table("agent_execution_snapshots"):
        op.create_table(
            "agent_execution_snapshots",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("execution_id", sa.String(length=64), sa.ForeignKey("agent_executions.id", ondelete="CASCADE"), nullable=False),
            sa.Column("sequence", sa.Integer(), nullable=False),
            sa.Column("snapshot_kind", sa.String(length=32), nullable=False, server_default="checkpoint"),
            sa.Column("stage", sa.String(length=64), nullable=True),
            sa.Column("state_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
            sa.Column("context_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
            sa.Column("checkpoint_id", sa.String(length=128), nullable=True),
            sa.Column("next_nodes", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
            sa.Column("is_resume_point", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("state_hash", sa.String(length=64), nullable=False),
            sa.Column("parent_event_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.UniqueConstraint("execution_id", "sequence", name="uq_agent_execution_snapshot_sequence"),
        )
        op.create_index("ix_agent_execution_snapshots_execution_id", "agent_execution_snapshots", ["execution_id"])
        op.create_index("ix_agent_execution_snapshots_checkpoint_id", "agent_execution_snapshots", ["checkpoint_id"])
        op.create_index("ix_agent_execution_snapshots_state_hash", "agent_execution_snapshots", ["state_hash"])

    if not inspector.has_table("agent_execution_effects"):
        op.create_table(
            "agent_execution_effects",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("execution_id", sa.String(length=64), sa.ForeignKey("agent_executions.id", ondelete="CASCADE"), nullable=False),
            sa.Column("sequence", sa.Integer(), nullable=False),
            sa.Column("effect_key", sa.String(length=255), nullable=False),
            sa.Column("effect_type", sa.String(length=64), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
            sa.Column("request", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
            sa.Column("response", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
            sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.UniqueConstraint("execution_id", "sequence", name="uq_agent_execution_effect_sequence"),
            sa.UniqueConstraint("effect_key", name="uq_agent_execution_effect_key"),
        )
        op.create_index("ix_agent_execution_effects_execution_id", "agent_execution_effects", ["execution_id"])
        op.create_index("ix_agent_execution_effects_effect_key", "agent_execution_effects", ["effect_key"])
        op.create_index("ix_agent_execution_effects_effect_type", "agent_execution_effects", ["effect_type"])

    if not inspector.has_table("session_runtime_state"):
        op.create_table(
            "session_runtime_state",
            sa.Column("session_id", sa.String(length=64), primary_key=True),
            sa.Column("execution_id", sa.String(length=64), sa.ForeignKey("agent_executions.id", ondelete="SET NULL"), nullable=True),
            sa.Column("state_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
            sa.Column("state_hash", sa.String(length=64), nullable=False),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        )
        op.create_index("ix_session_runtime_state_execution_id", "session_runtime_state", ["execution_id"])
        op.create_index("ix_session_runtime_state_state_hash", "session_runtime_state", ["state_hash"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("session_runtime_state"):
        op.drop_index("ix_session_runtime_state_state_hash", table_name="session_runtime_state")
        op.drop_index("ix_session_runtime_state_execution_id", table_name="session_runtime_state")
        op.drop_table("session_runtime_state")

    if inspector.has_table("agent_execution_effects"):
        op.drop_index("ix_agent_execution_effects_effect_type", table_name="agent_execution_effects")
        op.drop_index("ix_agent_execution_effects_effect_key", table_name="agent_execution_effects")
        op.drop_index("ix_agent_execution_effects_execution_id", table_name="agent_execution_effects")
        op.drop_table("agent_execution_effects")

    if inspector.has_table("agent_execution_snapshots"):
        op.drop_index("ix_agent_execution_snapshots_state_hash", table_name="agent_execution_snapshots")
        op.drop_index("ix_agent_execution_snapshots_checkpoint_id", table_name="agent_execution_snapshots")
        op.drop_index("ix_agent_execution_snapshots_execution_id", table_name="agent_execution_snapshots")
        op.drop_table("agent_execution_snapshots")

    if inspector.has_table("agent_execution_events"):
        op.drop_index("ix_agent_execution_events_event_type", table_name="agent_execution_events")
        op.drop_index("ix_agent_execution_events_execution_id", table_name="agent_execution_events")
        op.drop_table("agent_execution_events")

    if inspector.has_table("agent_executions"):
        op.drop_index("ix_agent_executions_status", table_name="agent_executions")
        op.drop_index("ix_agent_executions_agent_id", table_name="agent_executions")
        op.drop_index("ix_agent_executions_run_id", table_name="agent_executions")
        op.drop_index("ix_agent_executions_session_id", table_name="agent_executions")
        op.drop_table("agent_executions")
