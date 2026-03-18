"""Add session block storage and session embedding identity columns.

Revision ID: 20260317_0012
Revises: 20260316_0011
Create Date: 2026-03-17 14:05:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision = "20260317_0012"
down_revision = "20260316_0011"
branch_labels = None
depends_on = None


def _constraint_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {constraint["name"] for constraint in inspector.get_unique_constraints(table_name)}


def _foreign_key_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {foreign_key["name"] for foreign_key in inspector.get_foreign_keys(table_name)}


def _index_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {index["name"] for index in inspector.get_indexes(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    if inspector.has_table("session_embeddings"):
        session_embedding_columns = {
            column["name"] for column in inspector.get_columns("session_embeddings")
        }
        session_embedding_constraints = _constraint_names(inspector, "session_embeddings")
        session_embedding_foreign_keys = _foreign_key_names(inspector, "session_embeddings")

        if "source_message_id" not in session_embedding_columns:
            op.add_column(
                "session_embeddings",
                sa.Column("source_message_id", sa.Integer(), nullable=True),
            )
        if "idempotency_key" not in session_embedding_columns:
            op.add_column(
                "session_embeddings",
                sa.Column("idempotency_key", sa.String(length=128), nullable=True),
            )
        if "role" not in session_embedding_columns:
            op.add_column(
                "session_embeddings",
                sa.Column("role", sa.String(length=50), nullable=True),
            )
        if "agent_id" not in session_embedding_columns:
            op.add_column(
                "session_embeddings",
                sa.Column("agent_id", sa.String(length=64), nullable=True),
            )

        if "fk_session_embeddings_source_message_id_chat_messages" not in session_embedding_foreign_keys:
            op.create_foreign_key(
                "fk_session_embeddings_source_message_id_chat_messages",
                "session_embeddings",
                "chat_messages",
                ["source_message_id"],
                ["id"],
                ondelete="SET NULL",
            )

        if "uq_session_embedding_message" not in session_embedding_constraints:
            op.create_unique_constraint(
                "uq_session_embedding_message",
                "session_embeddings",
                ["session_id", "source_message_id"],
            )
        if "uq_session_embedding_idempotency" not in session_embedding_constraints:
            op.create_unique_constraint(
                "uq_session_embedding_idempotency",
                "session_embeddings",
                ["session_id", "idempotency_key"],
            )

    if not inspector.has_table("session_blocks"):
        op.create_table(
            "session_blocks",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("session_id", sa.String(length=64), nullable=False),
            sa.Column("sequence", sa.Integer(), nullable=False),
            sa.Column("category", sa.String(length=64), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("summary_md", sa.Text(), nullable=False),
            sa.Column("content_excerpt", sa.Text(), nullable=False),
            sa.Column(
                "topic_tags",
                sa.JSON(),
                nullable=False,
                server_default=sa.text("'[]'::json"),
            ),
            sa.Column("message_start_id", sa.Integer(), nullable=False),
            sa.Column("message_end_id", sa.Integer(), nullable=False),
            sa.Column("token_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("confidence", sa.Float(), nullable=False, server_default="0.5"),
            sa.Column("source", sa.String(length=32), nullable=False, server_default="inferred"),
            sa.Column("embedding", Vector(768), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["message_start_id"], ["chat_messages.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["message_end_id"], ["chat_messages.id"], ondelete="RESTRICT"),
            sa.UniqueConstraint("session_id", "sequence", name="uq_session_block"),
        )
        op.create_index(
            "ix_session_blocks_session_id",
            "session_blocks",
            ["session_id"],
        )
        op.create_index(
            "ix_session_blocks_category",
            "session_blocks",
            ["category"],
        )
        op.execute(
            "CREATE INDEX ix_session_blocks_embedding "
            "ON session_blocks USING hnsw (embedding vector_cosine_ops)"
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("session_blocks"):
        session_block_indexes = _index_names(inspector, "session_blocks")
        if "ix_session_blocks_category" in session_block_indexes:
            op.drop_index("ix_session_blocks_category", table_name="session_blocks")
        if "ix_session_blocks_session_id" in session_block_indexes:
            op.drop_index("ix_session_blocks_session_id", table_name="session_blocks")
        op.execute("DROP INDEX IF EXISTS ix_session_blocks_embedding")
        op.drop_table("session_blocks")

    if inspector.has_table("session_embeddings"):
        session_embedding_constraints = _constraint_names(inspector, "session_embeddings")
        session_embedding_foreign_keys = _foreign_key_names(inspector, "session_embeddings")
        session_embedding_columns = {
            column["name"] for column in inspector.get_columns("session_embeddings")
        }

        if "uq_session_embedding_idempotency" in session_embedding_constraints:
            op.drop_constraint(
                "uq_session_embedding_idempotency",
                "session_embeddings",
                type_="unique",
            )
        if "uq_session_embedding_message" in session_embedding_constraints:
            op.drop_constraint(
                "uq_session_embedding_message",
                "session_embeddings",
                type_="unique",
            )
        if "fk_session_embeddings_source_message_id_chat_messages" in session_embedding_foreign_keys:
            op.drop_constraint(
                "fk_session_embeddings_source_message_id_chat_messages",
                "session_embeddings",
                type_="foreignkey",
            )

        for column_name in ("agent_id", "role", "idempotency_key", "source_message_id"):
            if column_name in session_embedding_columns:
                op.drop_column("session_embeddings", column_name)
