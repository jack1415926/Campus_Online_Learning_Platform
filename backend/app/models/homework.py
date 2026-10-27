"""One homework definition and one current submission per student."""
from datetime import datetime

from sqlalchemy import CHAR, Boolean, DateTime, Float, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKey


class Homework(Base, UUIDPrimaryKey, TimestampMixin):
    __tablename__ = "homeworks"
    course_id: Mapped[str] = mapped_column(CHAR(36), ForeignKey("courses.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    due_at: Mapped[datetime] = mapped_column(DateTime)
    max_score: Mapped[float] = mapped_column(Float)
    grading_notes: Mapped[str] = mapped_column(Text, default="")
    is_required: Mapped[bool] = mapped_column(Boolean, default=True)


class HomeworkSubmission(Base, UUIDPrimaryKey, TimestampMixin):
    __tablename__ = "homework_submissions"
    __table_args__ = (UniqueConstraint("homework_id", "user_id", name="uq_homework_student"),)
    homework_id: Mapped[str] = mapped_column(CHAR(36), ForeignKey("homeworks.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str] = mapped_column(CHAR(36), ForeignKey("users.id"), index=True)
    text: Mapped[str] = mapped_column(Text, default="")
    attachment_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    attachment_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    attachment_mime: Mapped[str | None] = mapped_column(String(100), nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(DateTime)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    graded_by: Mapped[str | None] = mapped_column(CHAR(36), nullable=True)
    graded_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
