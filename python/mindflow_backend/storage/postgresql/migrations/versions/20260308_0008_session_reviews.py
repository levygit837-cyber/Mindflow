"""Add session review tables

Revision ID: 20260308_0008
Revises: 20260304_0007
Create Date: 2026-03-08 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20260308_0008'
down_revision: Union[str, None] = '20260304_0007_session_chunks'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create session_reviews table
    op.create_table(
        'session_reviews',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('session_id', sa.String(length=64), nullable=False),
        sa.Column('window_start', sa.Integer(), nullable=False),
        sa.Column('window_end', sa.Integer(), nullable=False),
        sa.Column('review_data', sa.JSON(), nullable=False),
        sa.Column('priority', sa.String(length=16), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_session_reviews_session_id', 'session_id')
    )
    
    # Create session_review_results table
    op.create_table(
        'session_review_results',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('review_id', sa.String(length=64), nullable=False),
        sa.Column('result_type', sa.String(length=32), nullable=False),
        sa.Column('result_data', sa.JSON(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['review_id'], ['session_reviews.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_session_review_results_review_id', 'review_id')
    )
    
    # Add foreign key constraint for session relationship
    op.create_foreign_key(
        'fk_session_reviews_session_id',
        'session_reviews',
        'chat_sessions',
        ['session_id'],
        ['id'],
        ondelete='CASCADE'
    )


def downgrade() -> None:
    # Drop foreign key constraint
    op.drop_constraint('fk_session_reviews_session_id', 'session_reviews', type_='foreignkey')
    
    # Drop tables
    op.drop_table('session_review_results')
    op.drop_table('session_reviews')
