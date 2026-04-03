"""Create task management tables.

Revision ID: 20260403_0019
Revises: 20260403_0018
Create Date: 2026-04-03

Changes:
  - Create tasks table for persistent task storage
  - Create task_dependencies table for bidirectional dependency graph
  - Create task_high_water_mark table for sequential ID generation
  - Add indexes for performance
  - Add constraints for data integrity
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260403_0019"
down_revision = "20260403_0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create task management tables."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # Create tasks table
    if not inspector.has_table("tasks"):
        op.execute(
            """
            CREATE TABLE tasks (
                id SERIAL PRIMARY KEY,
                task_list_id VARCHAR(64) NOT NULL,
                subject VARCHAR(256) NOT NULL,
                description TEXT DEFAULT '',
                active_form VARCHAR(256),
                owner VARCHAR(64),
                status VARCHAR(32) NOT NULL DEFAULT 'pending',
                task_metadata JSONB DEFAULT '{}'::jsonb,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                version INTEGER NOT NULL DEFAULT 1,
                CONSTRAINT tasks_status_check CHECK (status IN ('pending', 'in_progress', 'completed', 'blocked', 'failed'))
            )
            """
        )

        # Create indexes for tasks table
        op.create_index(
            "ix_tasks_task_list_id",
            "tasks",
            ["task_list_id"],
        )
        op.create_index(
            "ix_tasks_owner",
            "tasks",
            ["owner"],
        )
        op.create_index(
            "ix_tasks_status",
            "tasks",
            ["status"],
        )
        op.create_index(
            "ix_tasks_created_at",
            "tasks",
            ["created_at"],
            postgresql_using="btree",
        )

    # Create task_dependencies table
    if not inspector.has_table("task_dependencies"):
        op.execute(
            """
            CREATE TABLE task_dependencies (
                id SERIAL PRIMARY KEY,
                task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
                blocks_task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                CONSTRAINT task_deps_unique UNIQUE (task_id, blocks_task_id),
                CONSTRAINT task_deps_no_self_ref CHECK (task_id != blocks_task_id)
            )
            """
        )

        # Create indexes for task_dependencies table
        op.create_index(
            "ix_task_dependencies_task_id",
            "task_dependencies",
            ["task_id"],
        )
        op.create_index(
            "ix_task_dependencies_blocks_task_id",
            "task_dependencies",
            ["blocks_task_id"],
        )


def downgrade() -> None:
    """Drop task management tables."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # Drop tables in reverse order (respecting foreign keys)
    if inspector.has_table("task_dependencies"):
        op.drop_index("ix_task_dependencies_blocks_task_id", table_name="task_dependencies")
        op.drop_index("ix_task_dependencies_task_id", table_name="task_dependencies")
        op.drop_table("task_dependencies")

    if inspector.has_table("task_high_water_mark"):
        op.drop_table("task_high_water_mark")

    if inspector.has_table("tasks"):
        op.drop_index("ix_tasks_created_at", table_name="tasks")
        op.drop_index("ix_tasks_status", table_name="tasks")
        op.drop_index("ix_tasks_owner", table_name="tasks")
        op.drop_index("ix_tasks_task_list_id", table_name="tasks")
        op.drop_table("tasks")
