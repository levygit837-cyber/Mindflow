"""Add durable execution tree mailbox and process tables.

Revision ID: 20260317_0016
Revises: 20260317_0015
Create Date: 2026-03-17 23:20:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260317_0016"
down_revision = "20260317_0015"
branch_labels = None
depends_on = None


def _has_column(inspector: sa.Inspector, table_name: str, column_name: str) -> bool:
    return any(column.get("name") == column_name for column in inspector.get_columns(table_name))


def _index_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {index.get("name") for index in inspector.get_indexes(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("agent_executions"):
        execution_indexes = _index_names(inspector, "agent_executions")

        if not _has_column(inspector, "agent_executions", "root_execution_id"):
            op.add_column("agent_executions", sa.Column("root_execution_id", sa.String(length=64), nullable=True))
        if "ix_agent_executions_root_execution_id" not in execution_indexes:
            op.create_index("ix_agent_executions_root_execution_id", "agent_executions", ["root_execution_id"])

        if not _has_column(inspector, "agent_executions", "parent_execution_id"):
            op.add_column("agent_executions", sa.Column("parent_execution_id", sa.String(length=64), nullable=True))
        if "ix_agent_executions_parent_execution_id" not in execution_indexes:
            op.create_index("ix_agent_executions_parent_execution_id", "agent_executions", ["parent_execution_id"])

        if not _has_column(inspector, "agent_executions", "execution_role"):
            op.add_column(
                "agent_executions",
                sa.Column("execution_role", sa.String(length=64), nullable=False, server_default="root_orchestrator"),
            )
        if "ix_agent_executions_execution_role" not in execution_indexes:
            op.create_index("ix_agent_executions_execution_role", "agent_executions", ["execution_role"])

        if not _has_column(inspector, "agent_executions", "owner_execution_id"):
            op.add_column("agent_executions", sa.Column("owner_execution_id", sa.String(length=64), nullable=True))
        if "ix_agent_executions_owner_execution_id" not in execution_indexes:
            op.create_index("ix_agent_executions_owner_execution_id", "agent_executions", ["owner_execution_id"])

        if not _has_column(inspector, "agent_executions", "state_version"):
            op.add_column("agent_executions", sa.Column("state_version", sa.Integer(), nullable=False, server_default="1"))

        if not _has_column(inspector, "agent_executions", "last_heartbeat_at"):
            op.add_column("agent_executions", sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=True))

        if not _has_column(inspector, "agent_executions", "last_message_sequence"):
            op.add_column("agent_executions", sa.Column("last_message_sequence", sa.Integer(), nullable=False, server_default="0"))

    if not inspector.has_table("agent_execution_messages"):
        op.create_table(
            "agent_execution_messages",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("execution_id", sa.String(length=64), sa.ForeignKey("agent_executions.id", ondelete="CASCADE"), nullable=False),
            sa.Column("root_execution_id", sa.String(length=64), nullable=True),
            sa.Column("parent_execution_id", sa.String(length=64), nullable=True),
            sa.Column("sequence", sa.Integer(), nullable=False),
            sa.Column("message_type", sa.String(length=32), nullable=False),
            sa.Column("sender_execution_id", sa.String(length=64), nullable=True),
            sa.Column("recipient_execution_id", sa.String(length=64), nullable=True),
            sa.Column("visibility", sa.String(length=16), nullable=False, server_default="internal"),
            sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
            sa.Column("content", sa.Text(), nullable=False, server_default=""),
            sa.Column("payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint("execution_id", "sequence", name="uq_agent_execution_message_sequence"),
        )
        op.create_index("ix_agent_execution_messages_execution_id", "agent_execution_messages", ["execution_id"])
        op.create_index("ix_agent_execution_messages_root_execution_id", "agent_execution_messages", ["root_execution_id"])
        op.create_index("ix_agent_execution_messages_parent_execution_id", "agent_execution_messages", ["parent_execution_id"])
        op.create_index("ix_agent_execution_messages_message_type", "agent_execution_messages", ["message_type"])
        op.create_index("ix_agent_execution_messages_sender_execution_id", "agent_execution_messages", ["sender_execution_id"])
        op.create_index("ix_agent_execution_messages_recipient_execution_id", "agent_execution_messages", ["recipient_execution_id"])
        op.create_index("ix_agent_execution_messages_status", "agent_execution_messages", ["status"])

    if not inspector.has_table("agent_execution_processes"):
        op.create_table(
            "agent_execution_processes",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("execution_id", sa.String(length=64), sa.ForeignKey("agent_executions.id", ondelete="CASCADE"), nullable=False),
            sa.Column("process_key", sa.String(length=128), nullable=False),
            sa.Column("tab_id", sa.String(length=64), nullable=True),
            sa.Column("pid", sa.Integer(), nullable=True),
            sa.Column("owner_agent_id", sa.String(length=64), nullable=True),
            sa.Column("terminal_key", sa.String(length=255), nullable=True),
            sa.Column("cwd", sa.Text(), nullable=True),
            sa.Column("state", sa.String(length=32), nullable=False, server_default="running"),
            sa.Column("metadata", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint("execution_id", "process_key", name="uq_agent_execution_process_key"),
        )
        op.create_index("ix_agent_execution_processes_execution_id", "agent_execution_processes", ["execution_id"])
        op.create_index("ix_agent_execution_processes_process_key", "agent_execution_processes", ["process_key"])
        op.create_index("ix_agent_execution_processes_tab_id", "agent_execution_processes", ["tab_id"])
        op.create_index("ix_agent_execution_processes_pid", "agent_execution_processes", ["pid"])
        op.create_index("ix_agent_execution_processes_owner_agent_id", "agent_execution_processes", ["owner_agent_id"])
        op.create_index("ix_agent_execution_processes_state", "agent_execution_processes", ["state"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("agent_execution_processes"):
        op.drop_index("ix_agent_execution_processes_state", table_name="agent_execution_processes")
        op.drop_index("ix_agent_execution_processes_owner_agent_id", table_name="agent_execution_processes")
        op.drop_index("ix_agent_execution_processes_pid", table_name="agent_execution_processes")
        op.drop_index("ix_agent_execution_processes_tab_id", table_name="agent_execution_processes")
        op.drop_index("ix_agent_execution_processes_process_key", table_name="agent_execution_processes")
        op.drop_index("ix_agent_execution_processes_execution_id", table_name="agent_execution_processes")
        op.drop_table("agent_execution_processes")

    if inspector.has_table("agent_execution_messages"):
        op.drop_index("ix_agent_execution_messages_status", table_name="agent_execution_messages")
        op.drop_index("ix_agent_execution_messages_recipient_execution_id", table_name="agent_execution_messages")
        op.drop_index("ix_agent_execution_messages_sender_execution_id", table_name="agent_execution_messages")
        op.drop_index("ix_agent_execution_messages_message_type", table_name="agent_execution_messages")
        op.drop_index("ix_agent_execution_messages_parent_execution_id", table_name="agent_execution_messages")
        op.drop_index("ix_agent_execution_messages_root_execution_id", table_name="agent_execution_messages")
        op.drop_index("ix_agent_execution_messages_execution_id", table_name="agent_execution_messages")
        op.drop_table("agent_execution_messages")

    if inspector.has_table("agent_executions"):
        execution_indexes = _index_names(inspector, "agent_executions")
        if "ix_agent_executions_owner_execution_id" in execution_indexes:
            op.drop_index("ix_agent_executions_owner_execution_id", table_name="agent_executions")
        if "ix_agent_executions_execution_role" in execution_indexes:
            op.drop_index("ix_agent_executions_execution_role", table_name="agent_executions")
        if "ix_agent_executions_parent_execution_id" in execution_indexes:
            op.drop_index("ix_agent_executions_parent_execution_id", table_name="agent_executions")
        if "ix_agent_executions_root_execution_id" in execution_indexes:
            op.drop_index("ix_agent_executions_root_execution_id", table_name="agent_executions")

        if _has_column(inspector, "agent_executions", "last_message_sequence"):
            op.drop_column("agent_executions", "last_message_sequence")
        if _has_column(inspector, "agent_executions", "last_heartbeat_at"):
            op.drop_column("agent_executions", "last_heartbeat_at")
        if _has_column(inspector, "agent_executions", "state_version"):
            op.drop_column("agent_executions", "state_version")
        if _has_column(inspector, "agent_executions", "owner_execution_id"):
            op.drop_column("agent_executions", "owner_execution_id")
        if _has_column(inspector, "agent_executions", "execution_role"):
            op.drop_column("agent_executions", "execution_role")
        if _has_column(inspector, "agent_executions", "parent_execution_id"):
            op.drop_column("agent_executions", "parent_execution_id")
        if _has_column(inspector, "agent_executions", "root_execution_id"):
            op.drop_column("agent_executions", "root_execution_id")
