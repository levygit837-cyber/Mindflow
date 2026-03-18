"""Extend browser_instances for dockerized PinchTab fleet state.

Revision ID: 20260316_0010
Revises: 20260309_0009
Create Date: 2026-03-16 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260316_0010"
down_revision = "20260309_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("browser_instances", sa.Column("container_id", sa.String(length=128), nullable=True))
    op.add_column("browser_instances", sa.Column("container_name", sa.String(length=255), nullable=True))
    op.add_column("browser_instances", sa.Column("runtime_endpoint", sa.Text(), nullable=True))
    op.add_column(
        "browser_instances",
        sa.Column("economy_mode", sa.String(length=32), nullable=False, server_default="warm_paused"),
    )
    op.add_column(
        "browser_instances",
        sa.Column("runtime_state", sa.String(length=32), nullable=False, server_default="pending"),
    )
    op.add_column("browser_instances", sa.Column("paused_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("browser_instances", sa.Column("resumed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("browser_instances", sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index(op.f("ix_browser_instances_container_id"), "browser_instances", ["container_id"], unique=False)

    op.alter_column("browser_instances", "economy_mode", server_default=None)
    op.alter_column("browser_instances", "runtime_state", server_default=None)


def downgrade() -> None:
    op.drop_index(op.f("ix_browser_instances_container_id"), table_name="browser_instances")
    op.drop_column("browser_instances", "last_heartbeat_at")
    op.drop_column("browser_instances", "resumed_at")
    op.drop_column("browser_instances", "paused_at")
    op.drop_column("browser_instances", "runtime_state")
    op.drop_column("browser_instances", "economy_mode")
    op.drop_column("browser_instances", "runtime_endpoint")
    op.drop_column("browser_instances", "container_name")
    op.drop_column("browser_instances", "container_id")
