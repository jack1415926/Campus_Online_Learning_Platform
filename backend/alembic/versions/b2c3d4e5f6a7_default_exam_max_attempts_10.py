"""set default max_attempts to 10 for exams

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-08-10 14:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Update column default and existing rows
    op.alter_column('exams', 'max_attempts', server_default=sa.text('10'))
    op.execute("UPDATE exams SET max_attempts = 10 WHERE max_attempts = 3 OR max_attempts IS NULL OR max_attempts <= 0")


def downgrade() -> None:
    op.alter_column('exams', 'max_attempts', server_default=sa.text('3'))
    op.execute("UPDATE exams SET max_attempts = 3 WHERE max_attempts = 10")
