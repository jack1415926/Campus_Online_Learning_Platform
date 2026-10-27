"""Minimal course certificates and designated assessment."""
from alembic import op
import sqlalchemy as sa

revision = "d7e8f9a0b1c2"
down_revision = "c6d7e8f9a0b1"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("courses", sa.Column("certificate_exam_id", sa.CHAR(36), nullable=True))
    op.create_table("certificates",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("course_id", sa.CHAR(36), sa.ForeignKey("courses.id"), nullable=False, index=True),
        sa.Column("user_id", sa.CHAR(36), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("exam_record_id", sa.CHAR(36), sa.ForeignKey("exam_records.id"), nullable=False),
        sa.Column("number", sa.String(50), nullable=False, unique=True),
        sa.Column("student_name", sa.String(100), nullable=False),
        sa.Column("course_title", sa.String(255), nullable=False),
        sa.Column("platform_name", sa.String(100), nullable=False),
        sa.Column("issued_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("course_id", "user_id", name="uq_certificate_student_course"))


def downgrade():
    op.drop_table("certificates")
    op.drop_column("courses", "certificate_exam_id")
