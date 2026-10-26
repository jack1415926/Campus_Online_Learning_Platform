"""add image to content_type enum

Revision ID: e5d1b3a9c4f6
Revises: d4c0a2f8b3e5
Create Date: 2026-08-07 18:00:00.000000
"""
from typing import Sequence, Union

from alembic import op


revision: str = 'e5d1b3a9c4f6'
down_revision: Union[str, None] = 'd4c0a2f8b3e5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE chapters MODIFY COLUMN content_type ENUM('video','document','text','image','scorm') NOT NULL DEFAULT 'video'")


def downgrade() -> None:
    op.execute("ALTER TABLE chapters MODIFY COLUMN content_type ENUM('video','document','text','scorm') NOT NULL DEFAULT 'video'")
