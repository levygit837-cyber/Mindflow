"""Increase chat session id columns to 64 chars.

Revision ID: 20260302_0004
Revises: 20260302_0003
Create Date: 2026-03-02 00:15:00
"""

from alembic import op

revision = "20260302_0004"
down_revision = "20260302_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE chat_messages
        DROP CONSTRAINT IF EXISTS chat_messages_session_id_fkey
        """
    )
    op.execute(
        """
        ALTER TABLE chat_sessions
        ALTER COLUMN id TYPE VARCHAR(64)
        """
    )
    op.execute(
        """
        ALTER TABLE chat_messages
        ALTER COLUMN session_id TYPE VARCHAR(64)
        """
    )
    op.execute(
        """
        ALTER TABLE chat_messages
        ADD CONSTRAINT chat_messages_session_id_fkey
        FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE chat_messages
        DROP CONSTRAINT IF EXISTS chat_messages_session_id_fkey
        """
    )
    op.execute(
        """
        ALTER TABLE chat_messages
        ALTER COLUMN session_id TYPE VARCHAR(36) USING LEFT(session_id, 36)
        """
    )
    op.execute(
        """
        ALTER TABLE chat_sessions
        ALTER COLUMN id TYPE VARCHAR(36) USING LEFT(id, 36)
        """
    )
    op.execute(
        """
        ALTER TABLE chat_messages
        ADD CONSTRAINT chat_messages_session_id_fkey
        FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
        """
    )
