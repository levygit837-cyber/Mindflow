"""intelligent memory system tables

Revision ID: 20260406_0020
Revises: 20260403_0019
Create Date: 2026-04-06 00:00:00.000000

Adds tables for the Intelligent Memory System:
- memory_entries: Unified memory storage
- memory_embeddings: Vector embeddings for semantic search
- memory_tags: Flexible tagging system
- memory_category_types: Base category definitions
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision = '20260406_0020'
down_revision = '20260403_0019'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create memory_category_types table (base categories)
    op.create_table(
        'memory_category_types',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False, unique=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_dynamic', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('default_importance', sa.Float(), nullable=False, server_default='0.5'),
        sa.Column('auto_extract', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', name='uq_memory_category_type_name')
    )

    # Create memory_entries table (unified memory storage)
    op.create_table(
        'memory_entries',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('category_id', sa.Integer(), nullable=True),
        sa.Column('subcategory_id', sa.Integer(), nullable=True),
        sa.Column('scope', sa.String(length=20), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=True),
        sa.Column('session_id', sa.String(length=64), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('content_structured', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('memory_type', sa.String(length=50), nullable=False),
        sa.Column('importance', sa.Float(), nullable=False, server_default='0.5'),
        sa.Column('source_agent_id', sa.String(length=100), nullable=True),
        sa.Column('source_tool', sa.String(length=100), nullable=True),
        sa.Column('access_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_accessed', sa.DateTime(timezone=True), nullable=True),
        sa.Column('search_vector', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['category_id'], ['memory_categories.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['subcategory_id'], ['memory_subcategories.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['project_id'], ['project_memories.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create memory_embeddings table (vector embeddings)
    op.create_table(
        'memory_embeddings',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('memory_id', sa.Integer(), nullable=False),
        sa.Column('vector', Vector(1536), nullable=True),
        sa.Column('embedding_model', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['memory_id'], ['memory_entries.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create memory_tags table (flexible tagging)
    op.create_table(
        'memory_tags',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('memory_id', sa.Integer(), nullable=False),
        sa.Column('tag', sa.String(length=50), nullable=False),
        sa.Column('scope', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['memory_id'], ['memory_entries.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('memory_id', 'tag', name='uq_memory_tag')
    )

    # Create indexes for memory_entries
    op.create_index('ix_memory_entries_scope', 'memory_entries', ['scope'])
    op.create_index('ix_memory_entries_project_id', 'memory_entries', ['project_id'])
    op.create_index('ix_memory_entries_session_id', 'memory_entries', ['session_id'])
    op.create_index('ix_memory_entries_category_id', 'memory_entries', ['category_id'])
    op.create_index('ix_memory_entries_subcategory_id', 'memory_entries', ['subcategory_id'])
    op.create_index('ix_memory_entries_memory_type', 'memory_entries', ['memory_type'])
    op.create_index('ix_memory_entries_importance', 'memory_entries', ['importance'])
    op.create_index('ix_memory_entries_source_agent_id', 'memory_entries', ['source_agent_id'])
    op.create_index('ix_memory_entries_source_tool', 'memory_entries', ['source_tool'])
    op.create_index('ix_memory_entries_created_at', 'memory_entries', ['created_at'])

    # Composite indexes for common query patterns
    op.create_index(
        'ix_memory_entries_scope_project_type',
        'memory_entries',
        ['scope', 'project_id', 'memory_type']
    )
    op.create_index(
        'ix_memory_entries_category_importance',
        'memory_entries',
        ['category_id', 'importance']
    )

    # Create indexes for memory_embeddings
    op.create_index('ix_memory_embeddings_memory_id', 'memory_embeddings', ['memory_id'])
    
    # Create HNSW index for vector similarity search (pgvector)
    op.execute(
        "CREATE INDEX ix_memory_embeddings_vector ON memory_embeddings "
        "USING hnsw (vector vector_cosine_ops) WITH (m = 16, ef_construction = 64)"
    )

    # Create indexes for memory_tags
    op.create_index('ix_memory_tags_memory_id', 'memory_tags', ['memory_id'])
    op.create_index('ix_memory_tags_tag', 'memory_tags', ['tag'])
    op.create_index('ix_memory_tags_scope', 'memory_tags', ['scope'])

    # Create GIN index for full-text search on memory_entries
    # Note: search_vector is a simplified text column, for production use to_tsvector
    op.execute(
        "CREATE INDEX ix_memory_entries_search ON memory_entries "
        "USING GIN (to_tsvector('portuguese', COALESCE(search_vector, '')))"
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_memory_entries_search', table_name='memory_entries')
    op.drop_index('ix_memory_tags_scope', table_name='memory_tags')
    op.drop_index('ix_memory_tags_tag', table_name='memory_tags')
    op.drop_index('ix_memory_tags_memory_id', table_name='memory_tags')
    op.drop_index('ix_memory_embeddings_vector', table_name='memory_embeddings')
    op.drop_index('ix_memory_embeddings_memory_id', table_name='memory_embeddings')
    op.drop_index('ix_memory_entries_category_importance', table_name='memory_entries')
    op.drop_index('ix_memory_entries_scope_project_type', table_name='memory_entries')
    op.drop_index('ix_memory_entries_created_at', table_name='memory_entries')
    op.drop_index('ix_memory_entries_source_tool', table_name='memory_entries')
    op.drop_index('ix_memory_entries_source_agent_id', table_name='memory_entries')
    op.drop_index('ix_memory_entries_importance', table_name='memory_entries')
    op.drop_index('ix_memory_entries_memory_type', table_name='memory_entries')
    op.drop_index('ix_memory_entries_subcategory_id', table_name='memory_entries')
    op.drop_index('ix_memory_entries_category_id', table_name='memory_entries')
    op.drop_index('ix_memory_entries_session_id', table_name='memory_entries')
    op.drop_index('ix_memory_entries_project_id', table_name='memory_entries')
    op.drop_index('ix_memory_entries_scope', table_name='memory_entries')

    # Drop tables
    op.drop_table('memory_tags')
    op.drop_table('memory_embeddings')
    op.drop_table('memory_entries')
    op.drop_table('memory_category_types')
