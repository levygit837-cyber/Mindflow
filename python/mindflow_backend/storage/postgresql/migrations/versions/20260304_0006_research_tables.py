"""Add research and browser automation tables

Revision ID: 20260304_0006_research_tables
Revises: 20260302_0005_agent_memory_tables
Create Date: 2026-03-04 00:00:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260304_0006_research_tables"
down_revision = "20260302_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create browser_action_trails table
    op.create_table(
        "browser_action_trails",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.String(length=64), nullable=False),
        sa.Column("agent_id", sa.String(length=64), nullable=False),
        sa.Column("browser_id", sa.String(length=64), nullable=False),
        sa.Column("iteration_type", sa.String(length=32), nullable=False),
        sa.Column("action_data", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=True, default=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_browser_action_trails_agent_id"), "browser_action_trails", ["agent_id"], unique=False)
    op.create_index(op.f("ix_browser_action_trails_browser_id"), "browser_action_trails", ["browser_id"], unique=False)
    op.create_index(op.f("ix_browser_action_trails_iteration_type"), "browser_action_trails", ["iteration_type"], unique=False)
    op.create_index(op.f("ix_browser_action_trails_session_id"), "browser_action_trails", ["session_id"], unique=False)
    op.create_index(op.f("ix_browser_action_trails_timestamp"), "browser_action_trails", ["timestamp"], unique=False)

    # Create research_sessions table
    op.create_table(
        "research_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", sa.String(length=64), nullable=False),
        sa.Column("agent_id", sa.String(length=64), nullable=False),
        sa.Column("original_query", sa.Text(), nullable=False),
        sa.Column("question_type", sa.String(length=32), nullable=True),
        sa.Column("complexity_level", sa.String(length=16), nullable=True),
        sa.Column("browser_count", sa.Integer(), nullable=True, default=1),
        sa.Column("status", sa.String(length=16), nullable=True, default="pending"),
        sa.Column("confidence_level", sa.String(length=16), nullable=True, default="unknown"),
        sa.Column("synthesis_summary", sa.Text(), nullable=True),
        sa.Column("total_duration_seconds", sa.Integer(), nullable=True, default=0),
        sa.Column("actions_completed", sa.Integer(), nullable=True, default=0),
        sa.Column("errors_encountered", sa.Integer(), nullable=True, default=0),
        sa.Column("metadata", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_research_sessions_agent_id"), "research_sessions", ["agent_id"], unique=False)
    op.create_index(op.f("ix_research_sessions_session_id"), "research_sessions", ["session_id"], unique=False)

    # Create research_findings table
    op.create_table(
        "research_findings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("research_session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=True),
        sa.Column("trust_level", sa.String(length=16), nullable=True),
        sa.Column("domain_authority", sa.Float(), nullable=True, default=0.0),
        sa.Column("content_summary", sa.Text(), nullable=False),
        sa.Column("key_points", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=True, default=0.0),
        sa.Column("relevance_score", sa.Float(), nullable=True, default=0.0),
        sa.Column("extraction_method", sa.String(length=32), nullable=True, default="text_extraction"),
        sa.Column("conflicts_with", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("browser_id", sa.String(length=64), nullable=True),
        sa.Column("extracted_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_research_findings_browser_id"), "research_findings", ["browser_id"], unique=False)
    op.create_index(op.f("ix_research_findings_research_session_id"), "research_findings", ["research_session_id"], unique=False)
    op.create_index(op.f("ix_research_findings_source_type"), "research_findings", ["source_type"], unique=False)
    op.create_foreign_key(
        "fk_research_findings_research_session_id",
        "research_findings",
        "research_sessions",
        ["research_session_id"],
        ["id"],
        ondelete="CASCADE"
    )

    # Create source_classifications table
    op.create_table(
        "source_classifications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("domain", sa.String(length=255), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=True),
        sa.Column("trust_level", sa.String(length=16), nullable=True),
        sa.Column("domain_authority", sa.Float(), nullable=True, default=0.0),
        sa.Column("content_type", sa.String(length=64), nullable=True),
        sa.Column("classification_confidence", sa.Float(), nullable=True, default=0.0),
        sa.Column("last_classified", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("verified_count", sa.Integer(), nullable=True, default=0),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("domain"),
    )
    op.create_index(op.f("ix_source_classifications_domain"), "source_classifications", ["domain"], unique=False)

    # Create browser_instances table
    op.create_table(
        "browser_instances",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("browser_id", sa.String(length=64), nullable=False),
        sa.Column("instance_id", sa.String(length=64), nullable=False),
        sa.Column("tab_id", sa.String(length=64), nullable=False),
        sa.Column("research_session_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("current_url", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=True, default="pending"),
        sa.Column("actions_completed", sa.Integer(), nullable=True, default=0),
        sa.Column("error_count", sa.Integer(), nullable=True, default=0),
        sa.Column("last_activity", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("browser_id"),
    )
    op.create_index(op.f("ix_browser_instances_browser_id"), "browser_instances", ["browser_id"], unique=False)
    op.create_index(op.f("ix_browser_instances_research_session_id"), "browser_instances", ["research_session_id"], unique=False)
    op.create_foreign_key(
        "fk_browser_instances_research_session_id",
        "browser_instances",
        "research_sessions",
        ["research_session_id"],
        ["id"],
        ondelete="CASCADE"
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_browser_instances_research_session_id"), table_name="browser_instances")
    op.drop_index(op.f("ix_browser_instances_browser_id"), table_name="browser_instances")
    op.drop_table("browser_instances")
    
    op.drop_index(op.f("ix_source_classifications_domain"), table_name="source_classifications")
    op.drop_table("source_classifications")
    
    op.drop_index(op.f("ix_research_findings_source_type"), table_name="research_findings")
    op.drop_index(op.f("ix_research_findings_research_session_id"), table_name="research_findings")
    op.drop_index(op.f("ix_research_findings_browser_id"), table_name="research_findings")
    op.drop_table("research_findings")
    
    op.drop_index(op.f("ix_research_sessions_session_id"), table_name="research_sessions")
    op.drop_index(op.f("ix_research_sessions_agent_id"), table_name="research_sessions")
    op.drop_table("research_sessions")
    
    op.drop_index(op.f("ix_browser_action_trails_timestamp"), table_name="browser_action_trails")
    op.drop_index(op.f("ix_browser_action_trails_session_id"), table_name="browser_action_trails")
    op.drop_index(op.f("ix_browser_action_trails_iteration_type"), table_name="browser_action_trails")
    op.drop_index(op.f("ix_browser_action_trails_browser_id"), table_name="browser_action_trails")
    op.drop_index(op.f("ix_browser_action_trails_agent_id"), table_name="browser_action_trails")
    op.drop_table("browser_action_trails")
