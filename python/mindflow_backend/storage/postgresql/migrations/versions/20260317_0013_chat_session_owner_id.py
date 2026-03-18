"""Add owner_id to chat_sessions for session isolation.

Revision ID: 20260317_0013
Revises: 20260317_0012
Create Date: 2026-03-17

Changes:
  - Add owner_id column (nullable) to chat_sessions
  - Backfill legacy rows with 'legacy-system'
  - Create index on owner_id for efficient per-owner queries
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260317_0013"
down_revision = "20260317_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # Guard: only add column if it doesn't already exist (idempotent)
    existing_cols = {c["name"] for c in inspector.get_columns("chat_sessions")}
    if "owner_id" not in existing_cols:
        op.add_column(
            "chat_sessions",
            sa.Column("owner_id", sa.String(length=255), nullable=True),
        )

    # Backfill legacy rows so queries filtering by owner_id don't miss them
    op.execute(
        "UPDATE chat_sessions SET owner_id = 'legacy-system' WHERE owner_id IS NULL"
    )

    # Create index for efficient per-owner queries (if not already present)
    existing_indexes = {idx["name"] for idx in inspector.get_indexes("chat_sessions")}
    if "ix_chat_sessions_owner_id" not in existing_indexes:
        op.create_index(
            "ix_chat_sessions_owner_id",
            "chat_sessions",
            ["owner_id"],
        )


def downgrade() -> None:
    op.drop_index("ix_chat_sessions_owner_id", table_name="chat_sessions")
    op.drop_column("chat_sessions", "owner_id")
