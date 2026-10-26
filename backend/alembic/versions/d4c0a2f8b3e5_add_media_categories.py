"""add media_categories table

Revision ID: d4c0a2f8b3e5
Revises: c3b9f1a7d2e4
Create Date: 2026-08-07 16:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd4c0a2f8b3e5'
down_revision: Union[str, None] = 'c3b9f1a7d2e4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('media_categories',
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_by', sa.String(length=36), nullable=True),
        sa.Column('id', sa.CHAR(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_media_categories_name'), 'media_categories', ['name'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_media_categories_name'), table_name='media_categories')
    op.drop_table('media_categories')
