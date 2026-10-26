"""add question_mode to exams

Revision ID: d5e6f7a8b9c1
Revises: c3d4e5f6a7b8
Create Date: 2026-08-11

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "d5e6f7a8b9c1"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("exams", sa.Column("question_mode", sa.String(length=20),
                                     nullable=True, server_default="manual"))


def downgrade():
    op.drop_column("exams", "question_mode")
