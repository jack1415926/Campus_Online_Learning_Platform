"""Homework and idempotent chapter completion.

Revision ID: a4b5c6d7e8f9
Revises: f1a2b3c4d5e6
"""
from alembic import op
import sqlalchemy as sa

revision = "a4b5c6d7e8f9"
down_revision = "f1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade():
    # Preserve historical data: require duplicate records to be reviewed, never silently delete them.
    duplicate = op.get_bind().execute(sa.text("SELECT 1 FROM learning_records WHERE chapter_id IS NOT NULL GROUP BY user_id, course_id, chapter_id HAVING COUNT(*) > 1 LIMIT 1")).first()
    if duplicate:
        raise RuntimeError("Duplicate chapter records exist; review them before adding the unique constraint.")
    op.create_unique_constraint("uq_learning_user_chapter", "learning_records", ["user_id", "course_id", "chapter_id"])
    op.add_column("notifications", sa.Column("event_key", sa.String(180), nullable=True))
    op.create_unique_constraint("uq_notification_event", "notifications", ["event_key"])
    common = lambda: [sa.Column("id", sa.CHAR(36), primary_key=True), sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False), sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False)]
    op.create_table("homeworks", *common(),
        sa.Column("course_id", sa.CHAR(36), sa.ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("title", sa.String(255), nullable=False), sa.Column("description", sa.Text(), nullable=False),
        sa.Column("due_at", sa.DateTime(), nullable=False), sa.Column("max_score", sa.Float(), nullable=False),
        sa.Column("grading_notes", sa.Text(), nullable=False), sa.Column("is_required", sa.Boolean(), nullable=False))
    op.create_table("homework_submissions", *common(),
        sa.Column("homework_id", sa.CHAR(36), sa.ForeignKey("homeworks.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("user_id", sa.CHAR(36), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("text", sa.Text(), nullable=False), sa.Column("attachment_key", sa.String(500)),
        sa.Column("attachment_name", sa.String(255)), sa.Column("attachment_mime", sa.String(100)),
        sa.Column("submitted_at", sa.DateTime(), nullable=False), sa.Column("score", sa.Float()),
        sa.Column("feedback", sa.Text()), sa.Column("graded_by", sa.CHAR(36)), sa.Column("graded_at", sa.DateTime()),
        sa.UniqueConstraint("homework_id", "user_id", name="uq_homework_student"))


def downgrade():
    op.drop_table("homework_submissions")
    op.drop_table("homeworks")
    op.drop_constraint("uq_notification_event", "notifications", type_="unique")
    op.drop_column("notifications", "event_key")
    op.drop_constraint("uq_learning_user_chapter", "learning_records", type_="unique")
