"""Minimal course discussion and private messages."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.mysql import DATETIME

revision = "c6d7e8f9a0b1"
down_revision = "b5c6d7e8f9a0"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("discussion_topics",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("course_id", sa.CHAR(36), sa.ForeignKey("courses.id"), nullable=False, index=True),
        sa.Column("user_id", sa.CHAR(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False), sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", DATETIME(fsp=6), nullable=False),
        sa.Column("deleted_at", sa.DateTime()), sa.Column("deleted_by", sa.CHAR(36)))
    op.create_table("discussion_replies",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("topic_id", sa.CHAR(36), sa.ForeignKey("discussion_topics.id"), nullable=False, index=True),
        sa.Column("user_id", sa.CHAR(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("body", sa.Text(), nullable=False), sa.Column("created_at", DATETIME(fsp=6), nullable=False),
        sa.Column("deleted_at", sa.DateTime()), sa.Column("deleted_by", sa.CHAR(36)))
    op.create_table("private_messages",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("course_id", sa.CHAR(36), sa.ForeignKey("courses.id"), nullable=False, index=True),
        sa.Column("sender_id", sa.CHAR(36), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("recipient_id", sa.CHAR(36), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("body", sa.Text(), nullable=False), sa.Column("created_at", DATETIME(fsp=6), nullable=False),
        sa.Column("read_at", sa.DateTime()))


def downgrade():
    op.drop_table("private_messages")
    op.drop_table("discussion_replies")
    op.drop_table("discussion_topics")
