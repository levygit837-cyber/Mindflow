"""Create session_embeddings table when missing.

Revision ID: 20260316_0011
Revises: 20260316_0010
Create Date: 2026-03-16 21:15:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision = "20260316_0011"
down_revision = "20260316_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    if inspector.has_table("session_embeddings"):
        return

    op.create_table(
        "session_embeddings",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("session_id", sa.String(length=64), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(768), nullable=False),
        sa.Column(
            "session_metadata",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'::json"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_session_embeddings_session_id",
        "session_embeddings",
        ["session_id"],
    )
    op.execute(
        "CREATE INDEX ix_session_embeddings_embedding "
        "ON session_embeddings USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("session_embeddings"):
        return

    op.execute("DROP INDEX IF EXISTS ix_session_embeddings_embedding")
    op.drop_index("ix_session_embeddings_session_id", table_name="session_embeddings")
    op.drop_table("session_embeddings")
