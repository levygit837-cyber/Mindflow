"""Agent-only + Mind refactor.

Revision ID: 20260227_0002
Revises: 20260227_0001
Create Date: 2026-02-27 03:30:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260227_0002"
down_revision = "20260227_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Planned data reset: old conversation history is intentionally discarded.
    op.execute("DROP TABLE IF EXISTS swarm_events CASCADE")
    op.execute("DROP TABLE IF EXISTS swarm_tasks CASCADE")
    op.execute("DROP TABLE IF EXISTS messages CASCADE")
    op.execute("DROP TABLE IF EXISTS conversations CASCADE")
    op.execute("DROP TYPE IF EXISTS topic_type CASCADE")

    topic_type = postgresql.ENUM(
        "project_main",
        "project_topic",
        "standalone",
        name="topic_type",
        create_type=False,
    )
    topic_type.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "conversations",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("topic_about", sa.Text(), nullable=True),
        sa.Column("topic_type", topic_type, nullable=False),
        sa.Column("folder_path", sa.Text(), nullable=True),
        sa.Column("project_root_session_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_root_session_id"], ["conversations.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_conversations_folder_path", "conversations", ["folder_path"])

    op.create_table(
        "messages",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("conversation_id", sa.String(length=64), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("thoughts", sa.Text(), nullable=True),
        sa.Column("tool_calls", sa.JSON(), nullable=True),
        sa.Column("run_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_messages_conversation_id", "messages", ["conversation_id"])
    op.create_index("ix_messages_run_id", "messages", ["run_id"])

    op.create_table(
        "session_runs",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("conversation_id", sa.String(length=64), nullable=False),
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("conversation_id", "run_id", name="uq_session_run"),
    )
    op.create_index("ix_session_runs_conversation_id", "session_runs", ["conversation_id"])

    op.create_table(
        "mind_session_links",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("folder_path", sa.Text(), nullable=False),
        sa.Column("source_session_id", sa.String(length=64), nullable=False),
        sa.Column("target_session_id", sa.String(length=64), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["source_session_id"], ["conversations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_session_id"], ["conversations.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "folder_path", "source_session_id", "target_session_id", name="uq_mind_session_link"
        ),
    )
    op.create_index("ix_mind_session_links_folder_path", "mind_session_links", ["folder_path"])
    op.create_index("ix_mind_session_links_source_session_id", "mind_session_links", ["source_session_id"])
    op.create_index("ix_mind_session_links_target_session_id", "mind_session_links", ["target_session_id"])

    op.create_table(
        "mind_jobs",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("folder_path", sa.Text(), nullable=False),
        sa.Column("selected_session_ids", sa.JSON(), nullable=False),
        sa.Column("query", sa.Text(), nullable=True),
        sa.Column("requested_by_session_id", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("result_summary", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["requested_by_session_id"], ["conversations.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_mind_jobs_folder_path", "mind_jobs", ["folder_path"])
    op.create_index("ix_mind_jobs_requested_by_session_id", "mind_jobs", ["requested_by_session_id"])
    op.create_index("ix_mind_jobs_status", "mind_jobs", ["status"])

    op.create_table(
        "mind_job_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("job_id", sa.String(length=64), nullable=False),
        sa.Column("snapshot_index", sa.Integer(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["mind_jobs.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("job_id", "snapshot_index", name="uq_mind_job_snapshot"),
    )
    op.create_index("ix_mind_job_snapshots_job_id", "mind_job_snapshots", ["job_id"])

    op.create_table(
        "allowed_paths",
        sa.Column("path", sa.Text(), primary_key=True),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "neural_documents",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("session_id", sa.String(length=64), nullable=True),
        sa.Column("folder_path", sa.Text(), nullable=True),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["conversations.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_neural_documents_folder_path", "neural_documents", ["folder_path"])
    op.create_index("ix_neural_documents_sequence", "neural_documents", ["sequence"])
    op.create_index("ix_neural_documents_session_id", "neural_documents", ["session_id"])


def downgrade() -> None:
    op.drop_index("ix_neural_documents_session_id", table_name="neural_documents")
    op.drop_index("ix_neural_documents_sequence", table_name="neural_documents")
    op.drop_index("ix_neural_documents_folder_path", table_name="neural_documents")
    op.drop_table("neural_documents")

    op.drop_table("allowed_paths")

    op.drop_index("ix_mind_job_snapshots_job_id", table_name="mind_job_snapshots")
    op.drop_table("mind_job_snapshots")

    op.drop_index("ix_mind_jobs_status", table_name="mind_jobs")
    op.drop_index("ix_mind_jobs_requested_by_session_id", table_name="mind_jobs")
    op.drop_index("ix_mind_jobs_folder_path", table_name="mind_jobs")
    op.drop_table("mind_jobs")

    op.drop_index("ix_mind_session_links_target_session_id", table_name="mind_session_links")
    op.drop_index("ix_mind_session_links_source_session_id", table_name="mind_session_links")
    op.drop_index("ix_mind_session_links_folder_path", table_name="mind_session_links")
    op.drop_table("mind_session_links")

    op.drop_index("ix_session_runs_conversation_id", table_name="session_runs")
    op.drop_table("session_runs")

    op.drop_index("ix_messages_run_id", table_name="messages")
    op.drop_index("ix_messages_conversation_id", table_name="messages")
    op.drop_table("messages")

    op.drop_index("ix_conversations_folder_path", table_name="conversations")
    op.drop_table("conversations")

    topic_type = sa.Enum("project_main", "project_topic", "standalone", name="topic_type")
    topic_type.drop(op.get_bind(), checkfirst=True)
