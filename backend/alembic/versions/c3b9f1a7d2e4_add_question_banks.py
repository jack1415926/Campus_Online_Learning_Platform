"""add question_banks table and question_bank_id

Revision ID: c3b9f1a7d2e4
Revises: f7a2c3e8b9d1
Create Date: 2026-08-07 14:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c3b9f1a7d2e4'
down_revision: Union[str, None] = 'f7a2c3e8b9d1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('question_banks',
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_by', sa.String(length=36), nullable=True),
        sa.Column('id', sa.CHAR(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_question_banks_name'), 'question_banks', ['name'], unique=False)

    op.add_column('questions', sa.Column('question_bank_id', sa.String(length=36), nullable=True))
    op.create_index(op.f('ix_questions_question_bank_id'), 'questions', ['question_bank_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_questions_question_bank_id'), table_name='questions')
    op.drop_column('questions', 'question_bank_id')
    op.drop_index(op.f('ix_question_banks_name'), table_name='question_banks')
    op.drop_table('question_banks')