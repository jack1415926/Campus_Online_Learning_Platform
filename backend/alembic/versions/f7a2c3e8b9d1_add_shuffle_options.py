"""add shuffle_options to exams

Revision ID: f7a2c3e8b9d1
Revises: 85041b284392
Create Date: 2026-08-07 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f7a2c3e8b9d1'
down_revision: Union[str, None] = '85041b284392'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('exams', sa.Column('shuffle_options', sa.Boolean(),
                  nullable=False, server_default=sa.text('0')))


def downgrade() -> None:
    op.drop_column('exams', 'shuffle_options')