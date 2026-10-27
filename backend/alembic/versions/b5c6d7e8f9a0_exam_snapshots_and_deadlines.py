"""Fixed papers, attempt deadlines and attempt uniqueness."""
from alembic import op
import sqlalchemy as sa

revision = "b5c6d7e8f9a0"
down_revision = "a4b5c6d7e8f9"
branch_labels = None
depends_on = None


def upgrade():
    if op.get_bind().execute(sa.text("SELECT 1 FROM exam_records GROUP BY exam_id,user_id,attempt_number HAVING COUNT(*)>1 LIMIT 1")).first():
        raise RuntimeError("Duplicate exam attempts exist; review historical rows before migration.")
    op.add_column("exams", sa.Column("paper_snapshot", sa.JSON(), nullable=True))
    op.add_column("exams", sa.Column("grading_notes", sa.Text(), nullable=True))
    op.add_column("exam_records", sa.Column("question_snapshot", sa.JSON(), nullable=True))
    op.add_column("exam_records", sa.Column("draft_answers", sa.JSON(), nullable=True))
    op.add_column("exam_records", sa.Column("deadline_at", sa.String(50), nullable=True))
    op.add_column("exam_records", sa.Column("pass_percent", sa.Float(), nullable=True))
    op.create_unique_constraint("uq_exam_attempt", "exam_records", ["exam_id", "user_id", "attempt_number"])


def downgrade():
    op.drop_constraint("uq_exam_attempt", "exam_records", type_="unique")
    for name in ("question_snapshot", "draft_answers", "deadline_at", "pass_percent"):
        op.drop_column("exam_records", name)
    op.drop_column("exams", "paper_snapshot")
    op.drop_column("exams", "grading_notes")
