"""Migrate embedding columns from JSON to pgvector; drop session_chunks table.

Revision ID: 20260309_0009
Revises: 20260308_0008
Create Date: 2026-03-09 00:00:00

Changes:
  - Enable pgvector extension
  - Migrate agent_memory_embeddings.vector   JSON → vector(768)
  - Migrate session_embeddings.embedding     JSON → vector(768)
  - Drop session_chunks table (superseded by real-time event embeddings)
  - Drop chunk tracking columns from agent_memory_cursor
  - Create HNSW indexes on all vector columns
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260309_0009"
down_revision = "20260308_0008"
branch_labels = None
depends_on = None

VECTOR_DIM = 768


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. Enable pgvector extension
    # ------------------------------------------------------------------
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # ------------------------------------------------------------------
    # 2. agent_memory_embeddings: JSON → vector(768)
    # ------------------------------------------------------------------
    op.execute(
        f"ALTER TABLE agent_memory_embeddings ADD COLUMN vector_v2 vector({VECTOR_DIM})"
    )
    # Backfill rows whose JSON array has exactly VECTOR_DIM elements
    op.execute(
        f"""
        UPDATE agent_memory_embeddings
           SET vector_v2 = vector::text::vector
         WHERE vector IS NOT NULL
           AND json_typeof(vector::json) = 'array'
           AND json_array_length(vector::json) = {VECTOR_DIM}
        """
    )
    op.drop_column("agent_memory_embeddings", "vector")
    op.execute("ALTER TABLE agent_memory_embeddings RENAME COLUMN vector_v2 TO vector")
    op.execute(
        "CREATE INDEX ix_agent_memory_embeddings_vector "
        "ON agent_memory_embeddings USING hnsw (vector vector_cosine_ops)"
    )

    # ------------------------------------------------------------------
    # 3. session_embeddings: JSON → vector(768)
    # ------------------------------------------------------------------
    op.execute(
        f"ALTER TABLE session_embeddings ADD COLUMN embedding_v2 vector({VECTOR_DIM})"
    )
    op.execute(
        f"""
        UPDATE session_embeddings
           SET embedding_v2 = embedding::text::vector
         WHERE embedding IS NOT NULL
           AND json_typeof(embedding::json) = 'array'
           AND json_array_length(embedding::json) = {VECTOR_DIM}
        """
    )
    op.drop_column("session_embeddings", "embedding")
    op.execute("ALTER TABLE session_embeddings RENAME COLUMN embedding_v2 TO embedding")
    op.execute(
        "CREATE INDEX ix_session_embeddings_embedding "
        "ON session_embeddings USING hnsw (embedding vector_cosine_ops)"
    )

    # ------------------------------------------------------------------
    # 4. Drop session_chunks table and chunk tracking cursor columns
    # ------------------------------------------------------------------
    # Drop indexes first (created by 20260304_0007_session_chunks migration)
    op.execute("DROP INDEX IF EXISTS ix_session_chunks_chunk_type")
    op.execute("DROP INDEX IF EXISTS ix_session_chunks_agent_id")
    op.execute("DROP INDEX IF EXISTS ix_session_chunks_session_id")
    op.drop_table("session_chunks")

    op.drop_column("agent_memory_cursor", "tokens_since_chunk")
    op.drop_column("agent_memory_cursor", "last_chunked_event_id")
    op.drop_column("agent_memory_cursor", "chunk_sequence")


def downgrade() -> None:
    # Restore chunk tracking columns on agent_memory_cursor
    op.add_column("agent_memory_cursor", sa.Column("chunk_sequence", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("agent_memory_cursor", sa.Column("last_chunked_event_id", sa.Integer(), nullable=True))
    op.add_column("agent_memory_cursor", sa.Column("tokens_since_chunk", sa.Integer(), nullable=False, server_default="0"))

    # Recreate session_chunks table
    op.create_table(
        "session_chunks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.String(length=64), nullable=False),
        sa.Column("agent_id", sa.String(length=64), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("chunk_type", sa.String(length=32), nullable=False, server_default="discussion"),
        sa.Column("content_summary", sa.Text(), nullable=False),
        sa.Column("topic_tags", sa.JSON(), nullable=True),
        sa.Column("token_count", sa.Integer(), nullable=False),
        sa.Column("event_start_id", sa.Integer(), nullable=False),
        sa.Column("event_end_id", sa.Integer(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id", "agent_id", "sequence", name="uq_session_chunk"),
    )
    op.create_index("ix_session_chunks_session_id", "session_chunks", ["session_id"])
    op.create_index("ix_session_chunks_agent_id", "session_chunks", ["agent_id"])
    op.create_index("ix_session_chunks_chunk_type", "session_chunks", ["chunk_type"])

    # Restore session_embeddings.embedding as JSON
    op.execute("DROP INDEX IF EXISTS ix_session_embeddings_embedding")
    op.execute("ALTER TABLE session_embeddings ADD COLUMN embedding_json json")
    op.drop_column("session_embeddings", "embedding")
    op.execute("ALTER TABLE session_embeddings RENAME COLUMN embedding_json TO embedding")

    # Restore agent_memory_embeddings.vector as JSON
    op.execute("DROP INDEX IF EXISTS ix_agent_memory_embeddings_vector")
    op.execute("ALTER TABLE agent_memory_embeddings ADD COLUMN vector_json json")
    op.drop_column("agent_memory_embeddings", "vector")
    op.execute("ALTER TABLE agent_memory_embeddings RENAME COLUMN vector_json TO vector")
