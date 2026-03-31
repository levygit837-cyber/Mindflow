"""Add session chunks table and chunk tracking columns to agent_memory_cursor

Revision ID: 20260304_0007_session_chunks
Revises: 20260304_0006_research_tables
Create Date: 2026-03-04 00:00:00.000000

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260304_0007_session_chunks"
down_revision = "20260304_0006_research_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add chunk tracking columns to agent_memory_cursor table
    op.add_column('agent_memory_cursor', sa.Column('tokens_since_chunk', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('agent_memory_cursor', sa.Column('last_chunked_event_id', sa.Integer(), nullable=True))
    op.add_column('agent_memory_cursor', sa.Column('chunk_sequence', sa.Integer(), nullable=False, server_default='0'))
    
    # Create session_chunks table
    op.create_table(
        'session_chunks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.String(length=64), nullable=False),
        sa.Column('agent_id', sa.String(length=64), nullable=False),
        sa.Column('sequence', sa.Integer(), nullable=False),
        sa.Column('chunk_type', sa.String(length=32), nullable=False, server_default='discussion'),
        sa.Column('content_summary', sa.Text(), nullable=False),
        sa.Column('topic_tags', sa.JSON(), nullable=True),
        sa.Column('token_count', sa.Integer(), nullable=False),
        sa.Column('event_start_id', sa.Integer(), nullable=False),
        sa.Column('event_end_id', sa.Integer(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False, server_default='0.5'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('session_id', 'agent_id', 'sequence', name='uq_session_chunk')
    )
    
    # Create indexes for session_chunks
    op.create_index(op.f('ix_session_chunks_session_id'), 'session_chunks', ['session_id'], unique=False)
    op.create_index(op.f('ix_session_chunks_agent_id'), 'session_chunks', ['agent_id'], unique=False)
    op.create_index(op.f('ix_session_chunks_chunk_type'), 'session_chunks', ['chunk_type'], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index(op.f('ix_session_chunks_chunk_type'), table_name='session_chunks')
    op.drop_index(op.f('ix_session_chunks_agent_id'), table_name='session_chunks')
    op.drop_index(op.f('ix_session_chunks_session_id'), table_name='session_chunks')
    
    # Drop session_chunks table
    op.drop_table('session_chunks')
    
    # Remove columns from agent_memory_cursor
    op.drop_column('agent_memory_cursor', 'chunk_sequence')
    op.drop_column('agent_memory_cursor', 'last_chunked_event_id')
    op.drop_column('agent_memory_cursor', 'tokens_since_chunk')
