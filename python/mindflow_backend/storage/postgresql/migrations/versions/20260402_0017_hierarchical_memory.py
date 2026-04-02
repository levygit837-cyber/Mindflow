"""hierarchical memory observer

Revision ID: 20260402_0017
Revises: 20260317_0016
Create Date: 2026-04-02 00:00:00.000000

Adds hierarchical memory tables for Memory Observer Enhanced:
- project_memories: Root container for project-level memory
- memory_categories: First-level categorization (API, Services, etc.)
- memory_subcategories: Second-level categorization (Controllers, Middleware, etc.)
- hierarchical_annotations: Rich annotations with code change tracking
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260402_0017'
down_revision = '20260317_0016'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create project_memories table
    op.create_table(
        'project_memories',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('project_name', sa.String(length=255), nullable=False),
        sa.Column('root_path', sa.String(length=512), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_project_memories_project_name', 'project_memories', ['project_name'])

    # Create memory_categories table
    op.create_table(
        'memory_categories',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('path_pattern', sa.String(length=512), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['project_id'], ['project_memories.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('project_id', 'name', name='uq_memory_category_project_name')
    )
    op.create_index('ix_memory_categories_project_id', 'memory_categories', ['project_id'])

    # Create memory_subcategories table
    op.create_table(
        'memory_subcategories',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('category_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('path_pattern', sa.String(length=512), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['category_id'], ['memory_categories.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('category_id', 'name', name='uq_memory_subcategory_category_name')
    )
    op.create_index('ix_memory_subcategories_category_id', 'memory_subcategories', ['category_id'])

    # Create hierarchical_annotations table
    op.create_table(
        'hierarchical_annotations',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('category_id', sa.Integer(), nullable=True),
        sa.Column('subcategory_id', sa.Integer(), nullable=True),
        sa.Column('observer_agent_id', sa.String(length=100), nullable=False),
        sa.Column('source_agent_id', sa.String(length=100), nullable=False),
        sa.Column('mission_id', sa.String(length=100), nullable=False),
        sa.Column('session_id', sa.String(length=64), nullable=False),
        sa.Column('file_path', sa.String(length=512), nullable=True),
        sa.Column('lines_modified', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('diff_summary', sa.Text(), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('annotation_type', sa.String(length=50), nullable=False, server_default='observation'),
        sa.Column('importance', sa.Float(), nullable=False, server_default='0.5'),
        sa.Column('tags', postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('raw_event_type', sa.String(length=100), nullable=True),
        sa.Column('metadata', postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['project_id'], ['project_memories.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['category_id'], ['memory_categories.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['subcategory_id'], ['memory_subcategories.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for hierarchical_annotations
    op.create_index('ix_hierarchical_annotations_project_id', 'hierarchical_annotations', ['project_id'])
    op.create_index('ix_hierarchical_annotations_category_id', 'hierarchical_annotations', ['category_id'])
    op.create_index('ix_hierarchical_annotations_subcategory_id', 'hierarchical_annotations', ['subcategory_id'])
    op.create_index('ix_hierarchical_annotations_observer_agent_id', 'hierarchical_annotations', ['observer_agent_id'])
    op.create_index('ix_hierarchical_annotations_source_agent_id', 'hierarchical_annotations', ['source_agent_id'])
    op.create_index('ix_hierarchical_annotations_mission_id', 'hierarchical_annotations', ['mission_id'])
    op.create_index('ix_hierarchical_annotations_session_id', 'hierarchical_annotations', ['session_id'])
    op.create_index('ix_hierarchical_annotations_file_path', 'hierarchical_annotations', ['file_path'])
    op.create_index('ix_hierarchical_annotations_annotation_type', 'hierarchical_annotations', ['annotation_type'])
    op.create_index('ix_hierarchical_annotations_importance', 'hierarchical_annotations', ['importance'])
    op.create_index('ix_hierarchical_annotations_created_at', 'hierarchical_annotations', ['created_at'])


def downgrade() -> None:
    # Drop hierarchical_annotations table and its indexes
    op.drop_index('ix_hierarchical_annotations_created_at', table_name='hierarchical_annotations')
    op.drop_index('ix_hierarchical_annotations_importance', table_name='hierarchical_annotations')
    op.drop_index('ix_hierarchical_annotations_annotation_type', table_name='hierarchical_annotations')
    op.drop_index('ix_hierarchical_annotations_file_path', table_name='hierarchical_annotations')
    op.drop_index('ix_hierarchical_annotations_session_id', table_name='hierarchical_annotations')
    op.drop_index('ix_hierarchical_annotations_mission_id', table_name='hierarchical_annotations')
    op.drop_index('ix_hierarchical_annotations_source_agent_id', table_name='hierarchical_annotations')
    op.drop_index('ix_hierarchical_annotations_observer_agent_id', table_name='hierarchical_annotations')
    op.drop_index('ix_hierarchical_annotations_subcategory_id', table_name='hierarchical_annotations')
    op.drop_index('ix_hierarchical_annotations_category_id', table_name='hierarchical_annotations')
    op.drop_index('ix_hierarchical_annotations_project_id', table_name='hierarchical_annotations')
    op.drop_table('hierarchical_annotations')

    # Drop memory_subcategories table and its indexes
    op.drop_index('ix_memory_subcategories_category_id', table_name='memory_subcategories')
    op.drop_table('memory_subcategories')

    # Drop memory_categories table and its indexes
    op.drop_index('ix_memory_categories_project_id', table_name='memory_categories')
    op.drop_table('memory_categories')

    # Drop project_memories table and its indexes
    op.drop_index('ix_project_memories_project_name', table_name='project_memories')
    op.drop_table('project_memories')
