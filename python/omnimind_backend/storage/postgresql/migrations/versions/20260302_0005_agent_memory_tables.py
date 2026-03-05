"""Create per-agent memory tables for rolling summaries and RAG retrieval.

Revision ID: 20260302_0005
Revises: 20260302_0004
Create Date: 2026-03-02 13:30:00
"""

import sqlalchemy as sa
from alembic import op

revision = "20260302_0005"
down_revision = "20260302_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_memory_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("session_id", sa.String(length=64), nullable=False),
        sa.Column("agent_id", sa.String(length=64), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False),
        sa.Column("source_message_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["source_message_id"], ["chat_messages.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_agent_memory_events_session_id", "agent_memory_events", ["session_id"])
    op.create_index("ix_agent_memory_events_agent_id", "agent_memory_events", ["agent_id"])

    op.create_table(
        "agent_memory_cursor",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("session_id", sa.String(length=64), nullable=False),
        sa.Column("agent_id", sa.String(length=64), nullable=False),
        sa.Column("token_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tokens_since_summary", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("window_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_summarized_event_id", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("session_id", "agent_id", name="uq_agent_memory_cursor"),
    )
    op.create_index("ix_agent_memory_cursor_session_id", "agent_memory_cursor", ["session_id"])
    op.create_index("ix_agent_memory_cursor_agent_id", "agent_memory_cursor", ["agent_id"])

    op.create_table(
        "agent_memory_windows",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("session_id", sa.String(length=64), nullable=False),
        sa.Column("agent_id", sa.String(length=64), nullable=False),
        sa.Column("window_index", sa.Integer(), nullable=False),
        sa.Column("token_start", sa.Integer(), nullable=False),
        sa.Column("token_end", sa.Integer(), nullable=False),
        sa.Column("event_start_id", sa.Integer(), nullable=False),
        sa.Column("event_end_id", sa.Integer(), nullable=False),
        sa.Column("summary_md", sa.Text(), nullable=False),
        sa.Column("key_points", sa.JSON(), nullable=False),
        sa.Column("coverage_ratio", sa.Float(), nullable=False, server_default="1"),
        sa.Column("checksum", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("session_id", "agent_id", "window_index", name="uq_agent_memory_window"),
    )
    op.create_index("ix_agent_memory_windows_session_id", "agent_memory_windows", ["session_id"])
    op.create_index("ix_agent_memory_windows_agent_id", "agent_memory_windows", ["agent_id"])

    op.create_table(
        "agent_memory_facts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("session_id", sa.String(length=64), nullable=False),
        sa.Column("agent_id", sa.String(length=64), nullable=False),
        sa.Column("window_id", sa.Integer(), nullable=False),
        sa.Column("fact_type", sa.String(length=32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["window_id"], ["agent_memory_windows.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_agent_memory_facts_session_id", "agent_memory_facts", ["session_id"])
    op.create_index("ix_agent_memory_facts_agent_id", "agent_memory_facts", ["agent_id"])

    op.create_table(
        "agent_memory_embeddings",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("session_id", sa.String(length=64), nullable=False),
        sa.Column("agent_id", sa.String(length=64), nullable=False),
        sa.Column("source_type", sa.String(length=16), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("content_excerpt", sa.Text(), nullable=False),
        sa.Column("vector", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_agent_memory_embeddings_session_id", "agent_memory_embeddings", ["session_id"])
    op.create_index("ix_agent_memory_embeddings_agent_id", "agent_memory_embeddings", ["agent_id"])


def downgrade() -> None:
    op.drop_index("ix_agent_memory_embeddings_agent_id", table_name="agent_memory_embeddings")
    op.drop_index("ix_agent_memory_embeddings_session_id", table_name="agent_memory_embeddings")
    op.drop_table("agent_memory_embeddings")

    op.drop_index("ix_agent_memory_facts_agent_id", table_name="agent_memory_facts")
    op.drop_index("ix_agent_memory_facts_session_id", table_name="agent_memory_facts")
    op.drop_table("agent_memory_facts")

    op.drop_index("ix_agent_memory_windows_agent_id", table_name="agent_memory_windows")
    op.drop_index("ix_agent_memory_windows_session_id", table_name="agent_memory_windows")
    op.drop_table("agent_memory_windows")

    op.drop_index("ix_agent_memory_cursor_agent_id", table_name="agent_memory_cursor")
    op.drop_index("ix_agent_memory_cursor_session_id", table_name="agent_memory_cursor")
    op.drop_table("agent_memory_cursor")

    op.drop_index("ix_agent_memory_events_agent_id", table_name="agent_memory_events")
    op.drop_index("ix_agent_memory_events_session_id", table_name="agent_memory_events")
    op.drop_table("agent_memory_events")
