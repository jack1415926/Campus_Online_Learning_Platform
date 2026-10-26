"""Campus teacher/course review and unique course membership.

Revision ID: f1a2b3c4d5e6
Revises: e6f7a8b9c1d2
"""
from alembic import op
import sqlalchemy as sa

revision = "f1a2b3c4d5e6"
down_revision = "e6f7a8b9c1d2"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("requested_role", sa.String(20), nullable=False, server_default="student"))
    op.add_column("users", sa.Column("teacher_review_status", sa.String(20), nullable=True))
    op.add_column("users", sa.Column("teacher_review_reason", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("teacher_reviewed_by", sa.CHAR(36), nullable=True))
    op.add_column("users", sa.Column("teacher_reviewed_at", sa.DateTime(), nullable=True))
    op.add_column("courses", sa.Column("review_reason", sa.Text(), nullable=True))
    op.add_column("courses", sa.Column("reviewed_by", sa.CHAR(36), nullable=True))
    op.add_column("courses", sa.Column("reviewed_at", sa.DateTime(), nullable=True))
    op.create_unique_constraint("uq_course_assignment_target", "course_assignments", ["course_id", "assignment_type", "target_id"])


def downgrade():
    op.drop_constraint("uq_course_assignment_target", "course_assignments", type_="unique")
    for name in ("reviewed_at", "reviewed_by", "review_reason"):
        op.drop_column("courses", name)
    for name in ("teacher_reviewed_at", "teacher_reviewed_by", "teacher_review_reason", "teacher_review_status", "requested_role"):
        op.drop_column("users", name)
