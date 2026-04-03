"""session facts for memory session

Revision ID: 20260403_0018
Revises: 20260402_0017
Create Date: 2026-04-03 00:00:00.000000

Adds session_facts table for Memory Session feature:
- Stores LLM-extracted facts from session analysis
- Enables cross-session recall via semantic search
- Links to session_embeddings for vector retrieval
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260403_0018'
down_revision = '20260402_0017'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create session_facts table
    op.create_table(
        'session_facts',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('session_id', sa.String(length=64), nullable=False),
        sa.Column('agent_id', sa.String(length=64), nullable=False),
        sa.Column('fact_type', sa.String(length=50), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('importance', sa.Float(), nullable=False, server_default='0.5'),
        sa.Column('related_files', postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('embedding_id', sa.Integer(), nullable=True),
        sa.Column('source_window_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['embedding_id'], ['session_embeddings.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['source_window_id'], ['agent_memory_windows.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for session_facts
    op.create_index('ix_session_facts_session_id', 'session_facts', ['session_id'])
    op.create_index('ix_session_facts_agent_id', 'session_facts', ['agent_id'])
    op.create_index('ix_session_facts_fact_type', 'session_facts', ['fact_type'])
    op.create_index('ix_session_facts_category', 'session_facts', ['category'])
    op.create_index('ix_session_facts_importance', 'session_facts', ['importance'])

    # Composite index for common query pattern (session + category + importance)
    op.create_index(
        'ix_session_facts_session_category_importance',
        'session_facts',
        ['session_id', 'category', 'importance']
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_session_facts_session_category_importance', table_name='session_facts')
    op.drop_index('ix_session_facts_importance', table_name='session_facts')
    op.drop_index('ix_session_facts_category', table_name='session_facts')
    op.drop_index('ix_session_facts_fact_type', table_name='session_facts')
    op.drop_index('ix_session_facts_agent_id', table_name='session_facts')
    op.drop_index('ix_session_facts_session_id', table_name='session_facts')

    # Drop table
    op.drop_table('session_facts')
