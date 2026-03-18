"""Add semantic-index curation metadata to session memory tables.

Revision ID: 20260317_0014
Revises: 20260317_0013
Create Date: 2026-03-17 19:10:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260317_0014"
down_revision = "20260317_0013"
branch_labels = None
depends_on = None


def _column_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {column["name"] for column in inspector.get_columns(table_name)}


def _add_memory_indexing_columns(table_name: str, *, default_content_kind: str) -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = _column_names(inspector, table_name)

    if "indexable" not in columns:
        op.add_column(
            table_name,
            sa.Column("indexable", sa.Boolean(), nullable=False, server_default=sa.true()),
        )
    if "content_kind" not in columns:
        op.add_column(
            table_name,
            sa.Column("content_kind", sa.String(length=32), nullable=False, server_default=default_content_kind),
        )
    if "quality_flags" not in columns:
        op.add_column(
            table_name,
            sa.Column("quality_flags", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        )
    if "source_status" not in columns:
        op.add_column(
            table_name,
            sa.Column("source_status", sa.String(length=16), nullable=False, server_default="final"),
        )
    if "derived_from_recall" not in columns:
        op.add_column(
            table_name,
            sa.Column("derived_from_recall", sa.Boolean(), nullable=False, server_default=sa.false()),
        )


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("session_embeddings"):
        _add_memory_indexing_columns("session_embeddings", default_content_kind="query")

    if inspector.has_table("session_blocks"):
        _add_memory_indexing_columns("session_blocks", default_content_kind="answer")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    for table_name in ("session_blocks", "session_embeddings"):
        if not inspector.has_table(table_name):
            continue
        columns = _column_names(inspector, table_name)
        for column_name in (
            "derived_from_recall",
            "source_status",
            "quality_flags",
            "content_kind",
            "indexable",
        ):
            if column_name in columns:
                op.drop_column(table_name, column_name)
